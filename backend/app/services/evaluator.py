"""app/services/evaluator.py —— Socket 作业自动化判题（按 lab_id 分发的多策略）。

设计
----
- ``JudgeStrategy`` 基类封装公共流程：动态端口 -> 启动子进程 -> 实时采日志 ->
  等待启动 -> 调用具体 ``verify`` -> 强杀进程 -> 汇总 :class:`EvaluationResult`。
- 子类只需提供：``script_filename``（写入的脚本名）、``build_command``（启动命令）
  与 ``verify``（具体校验逻辑，``test_cases`` 作为唯一判据）。
- ``STRATEGIES`` 注册表按 lab_id 分发；``evaluate_submission`` 是统一入口。

安全：独立进程组 + SIGTERM/SIGKILL、多重超时、Body 截断。
"""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import socket
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from ..schemas import EvaluationCheck, EvaluationResult, TestCase

# —— 判题参数 ——
STARTUP_WAIT_SECONDS = 1.0
READY_TIMEOUT_SECONDS = 5.0
REQUEST_TIMEOUT_SECONDS = 3.0
KILL_GRACE_SECONDS = 2.0
MAX_BODY_PREVIEW = 500

LogCallback = Callable[[str, str], Awaitable[None] | None]


def find_free_port(host: str = "127.0.0.1") -> int:
    """向系统申请一个空闲端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


@dataclass
class _VerifyOutcome:
    """策略 verify() 的返回结果。"""

    status: str
    checks: list[EvaluationCheck] = field(default_factory=list)
    status_code: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body_preview: str = ""


class JudgeStrategy:
    """判题策略基类：封装启动/采日志/清理，子类只实现校验逻辑。"""

    name: str = "base"
    script_filename: str = "main.py"

    def build_command(self, script: Path, port: int) -> list[str]:
        """启动命令，默认 ``python <script> --port <port>``。"""
        return [sys.executable, str(script), "--port", str(port)]

    async def verify(
        self, proc, host: str, port: int, test_cases: list[TestCase], request_timeout: float
    ) -> _VerifyOutcome:
        """具体校验逻辑，子类实现。"""
        raise NotImplementedError

    async def judge(
        self,
        script: Path,
        test_cases: list[TestCase],
        *,
        host: str,
        port: int,
        on_log: LogCallback | None = None,
    ) -> EvaluationResult:
        started = time.monotonic()
        logs: list[str] = []
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def _emit(stream: str, line: str) -> None:
            logs.append(f"[{stream}] {line}")
            if on_log is not None:
                ret = on_log(stream, line)
                if asyncio.iscoroutine(ret):
                    await ret

        def _fail(status: str, message: str) -> EvaluationResult:
            return EvaluationResult(
                passed=False,
                status=status,
                summary=message,
                port=port,
                duration_ms=int((time.monotonic() - started) * 1000),
                checks=[EvaluationCheck(name="判题", passed=False, detail=message)],
                logs=logs,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
            )

        # 1. 启动子进程（独立进程组）
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.build_command(script, port),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(script.parent),
                env={**os.environ, "PORT": str(port)},
                start_new_session=True,
            )
        except OSError as exc:
            return _fail("error", f"无法启动进程：{exc}")

        # 2. 后台实时采集 stdout / stderr
        async def _pump(stream: asyncio.StreamReader, name: str) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                await _emit(name, text)
                (stdout_lines if name == "stdout" else stderr_lines).append(text)

        pump_stdout = asyncio.create_task(_pump(proc.stdout, "stdout"))
        pump_stderr = asyncio.create_task(_pump(proc.stderr, "stderr"))

        # 3. 等待服务启动
        await asyncio.sleep(STARTUP_WAIT_SECONDS)

        # 4. 执行具体校验
        try:
            if proc.returncode is not None:
                outcome = _VerifyOutcome(
                    status="error",
                    checks=[
                        EvaluationCheck(
                            name="服务启动",
                            passed=False,
                            detail=f"进程提前退出，returncode={proc.returncode}",
                        )
                    ],
                )
            elif not test_cases:
                outcome = _VerifyOutcome(
                    status="passed",
                    checks=[
                        EvaluationCheck(
                            name="服务启动",
                            passed=True,
                            detail="无测试用例，仅校验服务成功启动",
                        )
                    ],
                )
            else:
                outcome = await self.verify(proc, host, port, test_cases, REQUEST_TIMEOUT_SECONDS)
        finally:
            # 5. 无论成功失败，强杀进程组并收尾日志管道
            await _terminate(proc)
            await asyncio.gather(pump_stdout, pump_stderr, return_exceptions=True)

        return EvaluationResult(
            passed=outcome.status == "passed",
            status=outcome.status,
            summary=_summary(outcome.status),
            port=port,
            duration_ms=int((time.monotonic() - started) * 1000),
            status_code=outcome.status_code,
            headers=outcome.headers,
            body_preview=outcome.body_preview,
            checks=outcome.checks,
            logs=logs,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
        )


class WebServerStrategy(JudgeStrategy):
    """HTTP 服务器：逐条 test_case 发请求，比对期望状态码。

    test_case 约定：``input`` = 请求行（如 ``GET /index.html HTTP/1.1``），
    ``expected`` = 期望状态行（如 ``HTTP/1.1 200 OK``）。
    """

    name = "web_server"
    script_filename = "web_server.py"

    async def verify(self, proc, host, port, test_cases, request_timeout):
        checks: list[EvaluationCheck] = []
        all_passed = True
        status_code = None
        headers: dict[str, str] = {}
        body_preview = ""
        for tc in test_cases:
            path = _parse_request_path(tc.input)
            expected_code = _parse_status_code(tc.expected)
            try:
                resp = await asyncio.wait_for(
                    _request_with_retry(host, port, path, request_timeout, READY_TIMEOUT_SECONDS, proc),
                    timeout=READY_TIMEOUT_SECONDS + request_timeout + 1.0,
                )
            except (asyncio.TimeoutError, httpx.HTTPError) as exc:
                checks.append(
                    EvaluationCheck(
                        name=tc.name, passed=False, detail=f"请求失败：{type(exc).__name__}: {exc}"
                    )
                )
                all_passed = False
                continue
            if resp is None:
                checks.append(
                    EvaluationCheck(name=tc.name, passed=False, detail=f"端口 {port} 未就绪或进程退出")
                )
                all_passed = False
                continue
            status_code = resp.status_code
            headers = dict(resp.headers)
            body_preview = resp.text[:MAX_BODY_PREVIEW]
            ok = resp.status_code == expected_code
            checks.append(
                EvaluationCheck(
                    name=tc.name,
                    passed=ok,
                    detail=f"期望状态码 {expected_code}，实际 {resp.status_code}",
                )
            )
            all_passed = all_passed and ok
        return _VerifyOutcome(
            status="passed" if (all_passed and checks) else "failed",
            checks=checks,
            status_code=status_code,
            headers=headers,
            body_preview=body_preview,
        )


class UdpPingerStrategy(JudgeStrategy):
    """UDP Pinger：起服务器，用参考客户端逐条发送 test_case 并比对回显。

    test_case 约定：``input`` = 发送的报文内容，``expected`` = 期望回显内容。
    """

    name = "udp_pinger"
    script_filename = "udp_pinger.py"

    def build_command(self, script, port):
        return [sys.executable, str(script), "--role", "server", "--port", str(port)]

    async def verify(self, proc, host, port, test_cases, request_timeout):
        checks: list[EvaluationCheck] = []
        all_passed = True
        for tc in test_cases:
            reply = await _udp_ping(host, port, tc.input, request_timeout)
            ok = reply is not None and reply == tc.expected
            checks.append(
                EvaluationCheck(
                    name=tc.name,
                    passed=ok,
                    detail=f"发送 {tc.input!r}，期望回显 {tc.expected!r}，实际 {reply!r}",
                )
            )
            all_passed = all_passed and ok
        return _VerifyOutcome(status="passed" if (all_passed and checks) else "failed", checks=checks)


# --------------------------------------------------------------------------
# 注册表：按 lab_id 分发（新增 lab 在这里登记策略）
# --------------------------------------------------------------------------

STRATEGIES: dict[str, JudgeStrategy] = {
    "sock-web": WebServerStrategy(),
    "sock-pinger": UdpPingerStrategy(),
}


async def evaluate_submission(
    lab_id: str,
    code: str,
    test_cases: list[TestCase],
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    on_log: LogCallback | None = None,
) -> EvaluationResult:
    """统一判题入口：按 ``lab_id`` 分发策略，``test_cases`` 作为判据。"""
    strategy = STRATEGIES.get(lab_id)
    if strategy is None:
        return EvaluationResult(
            passed=False,
            status="error",
            summary=f"Lab '{lab_id}' 暂无判题策略",
            port=port or 0,
            duration_ms=0,
            checks=[EvaluationCheck(name="判题策略", passed=False, detail=f"未注册 {lab_id} 的判题策略")],
        )

    port = port or find_free_port(host)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"judge-{lab_id}-"))
    script = tmp_dir / strategy.script_filename
    script.write_text(code, encoding="utf-8")

    try:
        return await strategy.judge(script, test_cases, host=host, port=port, on_log=on_log)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# --------------------------------------------------------------------------
# 内部工具
# --------------------------------------------------------------------------

async def _request_with_retry(
    host: str,
    port: int,
    path: str,
    request_timeout: float,
    ready_timeout: float,
    proc: asyncio.subprocess.Process,
):
    """发起 HTTP GET；连接被拒时在 ``ready_timeout`` 窗口内重试。"""
    url = f"http://{host}:{port}{path}"
    deadline = time.monotonic() + ready_timeout
    while True:
        if proc.returncode is not None:
            return None
        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                return await client.get(url)
        except httpx.ConnectError:
            if time.monotonic() >= deadline:
                return None
            await asyncio.sleep(0.3)


async def _udp_ping(host: str, port: int, payload: str, timeout: float) -> str | None:
    """发送一个 UDP 报文并等待回显；超时/失败返回 ``None``。"""

    def _send_recv() -> str | None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.sendto(payload.encode(), (host, port))
            try:
                data, _ = s.recvfrom(1024)
                return data.decode(errors="replace")
            except socket.timeout:
                return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(_send_recv), timeout=timeout + 1.0)
    except (asyncio.TimeoutError, OSError):
        return None


def _parse_request_path(request_line: str) -> str:
    """从请求行提取路径，如 ``GET /index.html HTTP/1.1`` -> ``/index.html``。"""
    parts = request_line.split()
    return parts[1] if len(parts) >= 2 else "/"


def _parse_status_code(status_line: str) -> int:
    """从状态行提取状态码，如 ``HTTP/1.1 200 OK`` -> ``200``。"""
    for token in status_line.split():
        if token.isdigit():
            return int(token)
    return 200


async def _terminate(proc: asyncio.subprocess.Process) -> None:
    """先 SIGTERM 整个进程组，宽限后仍未退出则 SIGKILL；Windows 回退到 kill。"""
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
        await asyncio.wait_for(proc.wait(), timeout=KILL_GRACE_SECONDS)
    except asyncio.TimeoutError:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, PermissionError):
            pass
        await proc.wait()


def _summary(status: str) -> str:
    return {
        "passed": "测试通过：所有 test_cases 校验通过",
        "failed": "测试失败：存在未通过的 test_case",
        "timeout": "测试超时",
        "error": "运行出错",
    }.get(status, status)


async def _self_test() -> None:
    """本地自测：对内置示例分别跑 Web Server 与 UDP Pinger 判题。"""
    static_dir = Path(__file__).resolve().parents[2] / "static" / "solutions"

    ws_code = (static_dir / "web_server.py").read_text(encoding="utf-8")
    ws_cases = [TestCase(name="GET 200", input="GET /index.html HTTP/1.1", expected="HTTP/1.1 200 OK")]
    print("== Web Server ==")
    print((await evaluate_submission("sock-web", ws_code, ws_cases)).model_dump_json(indent=2))

    pinger_code = (static_dir / "udp_pinger.py").read_text(encoding="utf-8")
    pinger_cases = [TestCase(name="回显 ping", input="ping 1", expected="ping 1")]
    print("== UDP Pinger ==")
    print((await evaluate_submission("sock-pinger", pinger_code, pinger_cases)).model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(_self_test())
