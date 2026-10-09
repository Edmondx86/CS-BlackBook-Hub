"""app/services/sandbox.py —— 判题沙箱：Docker 容器隔离 + 子进程兜底。

设计
----
- ``SandboxSpec`` 描述一次运行所需的参数（命令 / 工作目录 / 端口 / 资源上限）。
- ``SandboxHandle`` 统一暴露 stdout/stderr 流、returncode 与 ``stop()`` 清理，
  使 ``evaluator.JudgeStrategy`` 无需感知底层是容器还是子进程。
- ``start_sandbox()`` 优先尝试 Docker（守护进程可用时），失败则回退子进程。

安全边界
--------
- Docker 路径：内存/CPU/进程数限制、只读根文件系统、drop 全部 capability、
  禁外部网络（内部 bridge，仅 127.0.0.1 端口映射可达宿主）。
- 子进程兜底：POSIX 用 rlimit 限内存/CPU/进程数；Windows 无此能力，仅超时 +
  进程组清理，无资源/网络隔离。
- 两者都不再把宿主进程的完整环境变量透传给不可信代码（见 ``_sanitized_env``）。

前置条件（仅 Docker 路径需要，可后补）：
    docker network create --internal csbb-judge
    docker build -f backend/judge/Dockerfile -t csbb-judge .
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# —— 沙箱默认参数 ——
DEFAULT_MEMORY_MB = 128
DEFAULT_CPU_LIMIT = 1.0
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_PIDS_LIMIT = 64
DOCKER_IMAGE = "csbb-judge:latest"
DOCKER_NETWORK = "csbb-judge"

# —— 子进程路径的命名空间隔离（无 Docker 时的替代方案）——
# bubblewrap（bwrap）用 Linux 命名空间做隔离，没有守护进程，`apt install bubblewrap` 即可，
# 比 Docker 更适合轻量服务器。隔离内容：
#   --unshare-user/pid/ipc/uts/cgroup  命名空间隔离（看不到宿主进程、IPC、主机名）
#   --ro-bind / /                      整个根文件系统只读，学生代码写不了任何系统文件
#   --tmpfs /tmp                       私有可写临时目录
#   --die-with-parent                  父进程没了就一起收掉，避免留下孤儿进程
#
# ⚠️ 刻意【不加】--unshare-net。这些 Lab 的裁判要经 localhost 与学生的进程对话
# （发 HTTP / UDP / SMTP），一旦切断网络命名空间，裁判就连不上学生对端了。
# 出站网络改由 iptables 按 uid 封锁，见 deploy/DEPLOY.md 第 7 节。
BWRAP_BIN = "bwrap"
SANDBOX_MODE_ENV = "JUDGE_SANDBOX"  # auto（默认）| bwrap（强制，用于验证）| none
SANDBOX_ENGINE_ENV = "JUDGE_ENGINE"  # subprocess（默认）| docker（实验性，见 start_sandbox）

_bwrap_available: bool | None = None

_docker_available: bool | None = None


@dataclass
class SandboxSpec:
    """一次判题运行所需的沙箱参数。"""

    command: list[str]  # 宿主命令，如 [sys.executable, "<脚本绝对路径>", "--port", "N"]
    cwd: str
    host: str = "127.0.0.1"
    port: int = 0
    memory_mb: int = DEFAULT_MEMORY_MB
    cpu_limit: float = DEFAULT_CPU_LIMIT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    pids_limit: int = DEFAULT_PIDS_LIMIT


class SandboxHandle:
    """正在运行的沙箱进程句柄，屏蔽容器/子进程差异。"""

    def __init__(self, proc: asyncio.subprocess.Process, container_name: str | None = None):
        self._proc = proc
        self._container_name = container_name
        self._stopped = False

    @property
    def returncode(self) -> int | None:
        return self._proc.returncode

    @property
    def stdout(self):
        return self._proc.stdout

    @property
    def stderr(self):
        return self._proc.stderr

    async def wait(self) -> int | None:
        """等待进程结束（与 ``asyncio.subprocess.Process.wait()`` 同义）。"""
        return await self._proc.wait()

    async def stop(self) -> None:
        """终止并清理：先杀进程（组），再对容器做幂等 rm。"""
        if self._stopped:
            return
        self._stopped = True
        await _kill_process(self._proc)
        if self._container_name is not None:
            await _docker_rm(self._container_name)


# --------------------------------------------------------------------------
# 沙箱选择与启动
# --------------------------------------------------------------------------

async def docker_available() -> bool:
    """探测 Docker 守护进程是否可用（结果缓存，避免每次判题都探测）。"""
    global _docker_available
    if _docker_available is not None:
        return _docker_available
    import shutil as _sh
    if _sh.which("docker") is None:
        _docker_available = False
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=2.0)
        _docker_available = proc.returncode == 0
    except (OSError, asyncio.TimeoutError):
        _docker_available = False
    return _docker_available


async def start_sandbox(spec: SandboxSpec) -> SandboxHandle | None:
    """启动判题沙箱。默认走子进程路径（POSIX 上用 bwrap 加命名空间隔离）。

    **为什么不默认用 Docker**（``JUDGE_ENGINE=docker`` 才会启用）：
    1. 现有 Docker 路径用 ``--network <internal>`` + ``-p`` 发布端口，而 Docker 在 internal
       网络上**会静默忽略端口发布**（实测：``docker ps`` 只显示 ``80/tcp``，宿主机连不上），
       裁判因此永远连不上学生容器；
    2. 即使改成直连容器 IP，8 个 Lab 里有 6 个的学生代码按教材写法硬编码连 ``127.0.0.1``
       （``ch2_smtp.py`` / ``ch2_web_client.py`` / ``ch2_udp_pinger.py``），而容器里的
       ``127.0.0.1`` 并不是宿主机 —— 要支持它们必须让参考服务器与容器共享网络命名空间
       （``--network container:<name>``），那是另一套改造，尚未实现。
    bwrap 方案保留网络命名空间，因此 8 个 Lab 都能原样工作，出站则由 iptables 按 uid 封锁。
    """
    if _sandbox_engine() == "docker" and await docker_available():
        try:
            return await _start_docker(spec)
        except (OSError, asyncio.TimeoutError) as exc:
            logger.warning("Docker 沙箱启动失败，回退子进程路径：%s", exc)
    try:
        return await _start_subprocess(spec)
    except OSError:
        return None


# --------------------------------------------------------------------------
# 子进程兜底
# --------------------------------------------------------------------------

def _sanitized_env(spec: SandboxSpec) -> dict[str, str]:
    """构建最小安全环境，避免把后端进程的全部环境变量（密钥等）透传给不可信代码。

    其中 ``PYTHONIOENCODING=utf-8`` 是必须的：Windows 下子进程默认按控制台代码页（GBK）
    输出，中文日志回到父进程按 UTF-8 解码就会变成乱码，判题提示会不可读。
    """
    env = {
        "PORT": str(spec.port),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }
    if os.name == "nt":
        for key in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP", "COMSPEC", "PATHEXT"):
            if key in os.environ:
                env[key] = os.environ[key]
    else:
        for key in ("HOME", "LANG", "LC_ALL", "TMPDIR"):
            if key in os.environ:
                env[key] = os.environ[key]
    return env


def _make_preexec(spec: SandboxSpec):
    """POSIX 下用 rlimit 限制内存/CPU/进程数；Windows 无此能力，返回 None。

    ⚠️ 两个坑，都是只在 POSIX 上才会踩到的：

    1. ``resource.setrlimit`` **只接受整数**。传 float（``spec.timeout_seconds`` 是 5.0）
       会抛 ``TypeError`` —— 而它不在 ``(ValueError, OSError)`` 里，会直接冲出
       ``preexec_fn``，让整个 ``Popen`` 失败，表现为
       ``subprocess.SubprocessError: Exception occurred in preexec_fn.``，
       判题全部 500。CPython 只把 ``OSError`` 系异常精确回传给父进程，
       其他异常统一报成上面那句话，所以原始类型在 traceback 里看不到。
       这里显式取整。
    2. 单个 rlimit 设不上（某些内核/容器会拒绝）不该让判题整个失败，
       所以逐个设置、逐个兜底。但**不能静默**：降级信息要留痕。

    注意：这里处于 fork 之后、exec 之前，**不能用 logging**（锁可能在子进程里死锁），
    只能直接 ``os.write`` 到 stderr —— 那个 fd 此时已接到子进程的 PIPE 上。
    """
    if os.name != "posix":
        return None
    try:
        import resource
    except ImportError:
        return None

    mem_bytes = int(spec.memory_mb) * 1024 * 1024
    cpu_seconds = max(1, int(round(spec.timeout_seconds)))
    pids_limit = int(spec.pids_limit)

    limits = (
        ("RLIMIT_AS", resource.RLIMIT_AS, mem_bytes),
        ("RLIMIT_CPU", resource.RLIMIT_CPU, cpu_seconds),
        ("RLIMIT_NPROC", resource.RLIMIT_NPROC, pids_limit),
    )

    def preexec() -> None:
        for name, which, value in limits:
            try:
                resource.setrlimit(which, (value, value))
            except Exception as exc:  # noqa: BLE001 - 任何异常都不能冲出 preexec
                try:
                    os.write(
                        2,
                        f"[sandbox] {name}={value} 设置失败（已跳过）："
                        f"{type(exc).__name__}: {exc}\n".encode("utf-8", "replace"),
                    )
                except Exception:  # noqa: BLE001
                    pass

    return preexec


def _sandbox_engine() -> str:
    """判题引擎：``subprocess``（默认，POSIX 上用 bwrap 加隔离）/ ``docker``（实验性）。"""
    return os.getenv(SANDBOX_ENGINE_ENV, "subprocess").strip().lower() or "subprocess"


def _sandbox_mode() -> str:
    """读取子进程沙箱模式：``auto``（默认）/ ``bwrap``（强制）/ ``none``。"""
    return os.getenv(SANDBOX_MODE_ENV, "auto").strip().lower() or "auto"


async def _bwrap_usable() -> bool:
    """探测 bwrap 是否真的能建命名空间（结果缓存）。

    装了不代表能用：部分发行版默认禁止非特权用户创建 user namespace
    （如 Ubuntu 23.10+ 的 ``kernel.apparmor_restrict_unprivileged_userns=1``），
    此时 bwrap 会直接失败。探测一次后记住结果，免得每次判题都白跑一遍。
    """
    global _bwrap_available
    if _bwrap_available is not None:
        return _bwrap_available
    if os.name != "posix" or shutil.which(BWRAP_BIN) is None:
        _bwrap_available = False
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            BWRAP_BIN,
            "--unshare-user",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5.0)
        _bwrap_available = proc.returncode == 0
    except (OSError, asyncio.TimeoutError):
        _bwrap_available = False
    if not _bwrap_available:
        logger.warning(
            "bwrap 不可用（未安装或系统禁止非特权 user namespace），判题将退回无命名空间隔离的子进程"
        )
    return _bwrap_available


def _wrap_with_bwrap(command: list[str], cwd: str) -> list[str]:
    """把宿主命令包进 bwrap 沙箱（纯函数，便于单测断言参数）。

    ``--tmpfs /tmp`` 的顺序很关键：它会**把 /tmp 换成空的 tmpfs**，而判题的工作目录
    （学生的脚本）恰恰是 ``tempfile.mkdtemp()`` 建在 /tmp 下的 —— 不重新挂回来，
    沙箱里就找不到脚本、``--chdir`` 也会失败，每个判题都会挂。
    所以必须在 tmpfs 之后再把工作目录**只读**地暴露一次。
    """
    return [
        BWRAP_BIN,
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--unshare-cgroup",
        "--die-with-parent",
        "--ro-bind", "/", "/",
        "--dev", "/dev",
        "--proc", "/proc",
        # 私有可写 /tmp（学生代码可以往这里写临时文件）
        "--tmpfs", "/tmp",
        # ⚠️ 必须放在 --tmpfs /tmp 之后：把本次判题的工作目录重新暴露出来，
        # 否则上面的 tmpfs 会把 /tmp 下的学生脚本盖掉。
        "--ro-bind", cwd, cwd,
        "--chdir", cwd,
        *command,
    ]


async def _start_subprocess(spec: SandboxSpec) -> SandboxHandle:
    command = spec.command
    mode = _sandbox_mode()
    if mode != "none":
        usable = await _bwrap_usable()
        if usable:
            command = _wrap_with_bwrap(spec.command, spec.cwd)
        elif mode == "bwrap":
            # 严格模式：装了就该用上。这里宁可判题失败，也不要静默地失去隔离。
            raise OSError(
                "JUDGE_SANDBOX=bwrap 但 bwrap 不可用：请确认已安装 bubblewrap，"
                "且系统允许非特权用户创建 user namespace（见 deploy/DEPLOY.md）"
            )

    kwargs = dict(
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=spec.cwd,
        env=_sanitized_env(spec),
        start_new_session=True,
    )
    preexec = _make_preexec(spec)
    if preexec is not None:
        kwargs["preexec_fn"] = preexec
    proc = await asyncio.create_subprocess_exec(*command, **kwargs)
    return SandboxHandle(proc)


# --------------------------------------------------------------------------
# Docker 容器隔离
# --------------------------------------------------------------------------

def _to_container_command(host_command: list[str]) -> list[str]:
    """宿主命令 -> 容器命令：解释器换成容器内 python，脚本取 basename（已挂载到 /app）。"""
    if len(host_command) < 2:
        return ["python", *host_command]
    script_name = Path(host_command[1]).name
    return ["python", script_name, *host_command[2:]]


async def _ensure_network() -> None:
    """确保内部判题网络存在（幂等）；内部网络禁止容器访问外网。"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "network", "inspect", DOCKER_NETWORK,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5.0)
        if proc.returncode == 0:
            return
    except (OSError, asyncio.TimeoutError):
        pass
    proc = await asyncio.create_subprocess_exec(
        "docker", "network", "create", "--internal", DOCKER_NETWORK,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await asyncio.wait_for(proc.wait(), timeout=15.0)


async def _docker_image_ready() -> bool:
    """判题镜像是否已构建。

    必须先查这一步：镜像缺失时盲目 ``docker run`` 只会让每个判题都以
    “Unable to find image / pull access denied” 失败，而且这个原因埋在日志里很难看出来。
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "image", "inspect", DOCKER_IMAGE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5.0)
        return proc.returncode == 0
    except (OSError, asyncio.TimeoutError):
        return False


async def _start_docker(spec: SandboxSpec) -> SandboxHandle:
    if not await _docker_image_ready():
        raise OSError(
            f"判题镜像 {DOCKER_IMAGE} 不存在，请先构建："
            f"docker build -f backend/judge/Dockerfile -t {DOCKER_IMAGE} ."
        )
    name = f"csbb-judge-{uuid.uuid4().hex[:12]}"
    await _ensure_network()
    cmd = [
        "docker", "run", "--rm", "--name", name,
        "--network", DOCKER_NETWORK,
        "-p", f"{spec.host}:{spec.port}:{spec.port}",
        "--memory", f"{spec.memory_mb}m",
        "--memory-swap", f"{spec.memory_mb}m",
        "--cpus", str(spec.cpu_limit),
        "--pids-limit", str(spec.pids_limit),
        "--stop-timeout", "1",
        "--read-only", "--tmpfs", "/tmp",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "-v", f"{spec.cwd}:/app:ro",
        "-w", "/app",
        "-e", f"PORT={spec.port}",
        DOCKER_IMAGE,
        *_to_container_command(spec.command),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return SandboxHandle(proc, container_name=name)


# --------------------------------------------------------------------------
# 进程/容器清理
# --------------------------------------------------------------------------

async def _kill_process(proc: asyncio.subprocess.Process, grace: float = 2.0) -> None:
    """先 SIGTERM 整个进程组，宽限后仍未退出则 SIGKILL；Windows 回退到 terminate/kill。"""
    if proc.returncode is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except (ProcessLookupError, PermissionError):
        pass

    try:
        await asyncio.wait_for(proc.wait(), timeout=grace)
    except asyncio.TimeoutError:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, PermissionError):
            pass
        await proc.wait()


async def _docker_rm(name: str) -> None:
    """幂等删除容器，兜底前台 docker run 被强杀后容器泄漏的情况。"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except (OSError, asyncio.TimeoutError):
        pass
