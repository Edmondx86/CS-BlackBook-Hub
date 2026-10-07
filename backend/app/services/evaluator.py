"""app/services/evaluator.py —— Socket 作业自动化判题（按 lab_id 分发的多策略）。

设计
----
- ``JudgeStrategy`` 基类封装公共流程：动态端口 -> 启动沙箱 -> 实时采日志 ->
  等待启动 -> 调用具体 ``verify`` -> 强杀清理 -> 汇总 :class:`EvaluationResult`。
- 子类只需提供：``script_filename``（写入的脚本名）、``build_command``（启动命令）
  与 ``verify``（具体校验逻辑，``test_cases`` 作为唯一判据）。
- ``STRATEGIES`` 注册表按 lab_id 分发；``evaluate_submission`` 是统一入口。

安全：运行在 :mod:`~app.services.sandbox` 提供的沙箱内（Docker 隔离或子进程兜底），
叠加整体硬超时与 Body 截断。
"""

from __future__ import annotations

import ast
import asyncio
import shutil
import socket
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from ..schemas import EvaluationCheck, EvaluationResult, TestCase
from .sandbox import SandboxHandle, SandboxSpec, start_sandbox

# —— 判题参数 ——
STARTUP_WAIT_SECONDS = 1.0
READY_TIMEOUT_SECONDS = 5.0
REQUEST_TIMEOUT_SECONDS = 3.0
EXEC_TIMEOUT_SECONDS = 5.0
# 静态判题里“单独跑一次学生函数”的硬超时，防止死循环拖住后端进程
CHECKSUM_TIMEOUT_SECONDS = 3.0
MAX_BODY_PREVIEW = 500

# 在一次性的判题沙箱里执行的驱动脚本：加载学生提交的 checksum 函数，对固定样例报文求值。
# 成功输出 ``OK:<数值>``，失败输出 ``ERR:<原因>``；顶层不放任何业务逻辑。
_CHECKSUM_DRIVER = '''\
"""判题沙箱内的一次性驱动：加载学生提交的 checksum 函数并计算样例报文的校验和。

用法：``python <驱动> <样例文件> <学生模块文件>``
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys


def _load_module(path: str):
    spec = importlib.util.spec_from_file_location("student_checksum", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    sample_path, module_path = sys.argv[1], sys.argv[2]
    try:
        module = _load_module(module_path)
    except Exception as exc:  # noqa: BLE001 - 学生代码可能以任意方式崩溃
        print(f"ERR:模块加载失败 {type(exc).__name__}: {exc}")
        return 0

    fn = getattr(module, "checksum", None)
    if not callable(fn):
        print("ERR:checksum 不是一个可调用函数")
        return 0

    data = pathlib.Path(sample_path).read_bytes()
    try:
        got = fn(data)
    except Exception as exc:  # noqa: BLE001
        print(f"ERR:checksum 调用失败 {type(exc).__name__}: {exc}")
        return 0

    print(f"OK:{got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

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

        # 1. 在沙箱中启动用户程序（Docker 隔离 / 子进程兜底）
        handle = await start_sandbox(
            SandboxSpec(
                command=self.build_command(script, port),
                cwd=str(script.parent),
                host=host,
                port=port,
            )
        )
        if handle is None:
            return _fail("error", "无法启动沙箱进程")

        # 2. 后台实时采集 stdout / stderr
        async def _pump(stream: asyncio.StreamReader, name: str) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                await _emit(name, text)
                (stdout_lines if name == "stdout" else stderr_lines).append(text)

        pump_stdout = asyncio.create_task(_pump(handle.stdout, "stdout"))
        pump_stderr = asyncio.create_task(_pump(handle.stderr, "stderr"))

        outcome = _VerifyOutcome(
            status="error",
            checks=[EvaluationCheck(name="判题", passed=False, detail="判题流程未完成")],
        )

        # 3. 等待启动 -> 4. 校验（整体硬超时）
        try:
            await asyncio.sleep(STARTUP_WAIT_SECONDS)
            async with asyncio.timeout(EXEC_TIMEOUT_SECONDS):
                if handle.returncode is not None:
                    outcome = _VerifyOutcome(
                        status="error",
                        checks=[
                            EvaluationCheck(
                                name="服务启动",
                                passed=False,
                                detail=f"进程提前退出，returncode={handle.returncode}",
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
                    outcome = await self.verify(handle, host, port, test_cases, REQUEST_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            outcome = _VerifyOutcome(
                status="timeout",
                checks=[
                    EvaluationCheck(
                        name="硬超时",
                        passed=False,
                        detail=f"整体执行超过 {EXEC_TIMEOUT_SECONDS}s",
                    )
                ],
            )
        finally:
            # 5. 无论成功失败，强杀沙箱并收尾日志管道
            await handle.stop()
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

    教材 ``WebServer.py`` 把端口硬编码为 80、并从工作目录读取文件，因此判题固定用
    80 端口，运行前写入一个 ``index.html`` 供 ``GET /index.html`` 返回 200。
    这些判题细节与学生可见的参考答案/初始模板解耦，编辑器里仍是干净的教材代码。
    """

    name = "web_server"
    script_filename = "ch2_web_server.py"
    # 教材 Web 服务器把端口硬编码为 80，判题固定用该端口
    fixed_port = 80

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        # 教材服务器从工作目录读取文件（GET /index.html -> index.html），提前备好。
        (script.parent / "index.html").write_text(
            "<!doctype html><html><body><h1>Hello</h1></body></html>",
            encoding="utf-8",
        )
        return await super().judge(
            script, test_cases, host=host, port=self.fixed_port, on_log=on_log
        )

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


class UdpPingerClientStrategy(JudgeStrategy):
    """学生写 UDP 客户端：后端跑教材参考服务器（随机丢包），客户端 ping 它并打印回显。

    客户端约定：教材 UDPPingerClient 硬编码 ``127.0.0.1:12000``，发 ping 后打印含
    ``RTT`` 的行、超时打印 ``lost``（不解析 ``--port``）。
    参考服务器按教材 ``UDPPingerServer.py`` 实现，约 4/11 概率随机丢包，判题固定监听
    12000 端口，以「客户端打印了 RTT 且打印了 lost」为通过。

    说明：参考服务器与学生客户端同处 ``127.0.0.1``、都走子进程路径（等价于
    :func:`sandbox.start_sandbox` 的子进程兜底），以便客户端能直接连到服务器。
    """

    name = "udp_pinger_client"
    script_filename = "ch2_udp_pinger.py"
    fixed_port = 12000  # 教材客户端硬编码 12000
    client_timeout_seconds = 15.0

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        port = self.fixed_port  # 客户端硬编码 12000，忽略传入的随机端口
        started = time.monotonic()
        logs: list[str] = []
        client_stdout: list[str] = []
        client_stderr: list[str] = []
        server_logs: list[str] = []

        async def _emit(stream: str, line: str) -> None:
            logs.append(f"[{stream}] {line}")
            if on_log is not None:
                ret = on_log(stream, line)
                if asyncio.iscoroutine(ret):
                    await ret

        def _result(status: str, summary: str, checks: list[EvaluationCheck]) -> EvaluationResult:
            return EvaluationResult(
                passed=status == "passed",
                status=status,
                summary=summary,
                port=port,
                duration_ms=int((time.monotonic() - started) * 1000),
                checks=checks,
                logs=logs,
                stdout="\n".join(client_stdout),
                stderr="\n".join(client_stderr),
            )

        # 1. 参考服务器（可信代码）：直接 subprocess 起在 127.0.0.1，回显并记录收到的报文。
        server_script = Path(__file__).resolve().parents[2] / "static" / "solutions" / "ch2_udp_pinger_server.py"
        server_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(server_script), "--port", str(port),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        await asyncio.sleep(0.5)  # 等待服务器完成 bind

        # 2. 学生客户端（不可信代码）：走沙箱 + 硬超时；客户端硬编码 127.0.0.1:12000，不传 --port。
        client = await _spawn_untrusted(script)

        async def _drain(reader, sink, stream):
            while True:
                line = await reader.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                sink.append(text)
                await _emit(stream, text)

        pumps = [
            asyncio.create_task(_drain(client.stdout, client_stdout, "client")),
            asyncio.create_task(_drain(client.stderr, client_stderr, "client:err")),
            asyncio.create_task(_drain(server_proc.stdout, server_logs, "server")),
        ]

        try:
            await asyncio.wait_for(client.wait(), timeout=self.client_timeout_seconds)
            timed_out = False
        except asyncio.TimeoutError:
            timed_out = True

        # 可信参考服务器用通用收尾；不可信代码走沙箱自己的 stop()（POSIX 下杀整个进程组，更彻底）
        await _terminate_proc(server_proc)
        await client.stop()
        await asyncio.gather(*pumps, return_exceptions=True)

        if timed_out:
            return _result(
                "timeout",
                f"客户端运行超过 {self.client_timeout_seconds:.0f}s",
                [EvaluationCheck(name="客户端", passed=False, detail="运行超时")],
            )

        client_text = "\n".join(client_stdout)
        got_reply = "rtt" in client_text.lower() or "reply" in client_text.lower()
        got_lost = "lost" in client_text.lower()

        checks = [
            EvaluationCheck(
                name="客户端收到回显",
                passed=got_reply,
                detail="客户端打印了 RTT" if got_reply else "客户端 stdout 未见回显（RTT / reply=）",
            ),
            EvaluationCheck(
                name="客户端处理丢包/超时",
                passed=got_lost,
                detail="客户端打印了 lost" if got_lost else "客户端 stdout 未见 lost（未处理超时）",
            ),
        ]
        passed = got_reply and got_lost
        return _result(
            "passed" if passed else "failed",
            "完成 ping 往返并正确处理丢包" if passed else "未观察到完整的 ping 往返（含丢包处理）",
            checks,
        )


class UdpPingerServerStrategy(JudgeStrategy):
    """学生写 UDP Pinger 服务器（教材风格）：监听 ``--port``，收到报文转大写并随机丢包。

    后端以 UDP 客户端身份连上学生服务器、发若干 ping，校验「服务器能响应且回显正确转大写」。
    随机丢包由学生代码里的 random.seed(42) 决定，判题不强制要求精确的丢包概率。
    """

    name = "udp_pinger_server"
    script_filename = "ch2_udp_pinger_server.py"

    async def verify(self, proc, host, port, test_cases, request_timeout):
        loop = asyncio.get_running_loop()
        received = 0
        correct = 0

        for i in range(11):
            payload = f"ping {i}".encode()
            reply = await _udp_ping_once(loop, host, port, payload, timeout=1.0)
            if reply is not None:
                received += 1
                if reply == payload.upper():
                    correct += 1

        ok = received >= 3 and correct == received
        detail = (
            f"11 次 ping 收到 {received} 次回显，全部转大写正确"
            if ok
            else f"11 次 ping 收到 {received} 次回显、{correct} 次转大写正确（期望至少 3 次且全部正确）"
        )
        return _VerifyOutcome(
            status="passed" if ok else "failed",
            checks=[EvaluationCheck(name="UDP 回显与转大写", passed=ok, detail=detail)],
        )


class WebClientStrategy(JudgeStrategy):
    """学生写 TCP Web 客户端（教材风格）：硬编码 127.0.0.1:80，发 GET /hello.html。

    后端在 127.0.0.1:80 起 HTTP 参考服务器（/hello.html -> 200），直接运行学生客户端
    （不传额外参数），判题以「服务器收到 /hello.html 且 客户端打印了 200 OK」为通过。

    说明：客户端代码硬编码端口 80（教材示例写法），因此参考服务器也必须监听 80 端口；
    若 80 端口被占用会导致判题失败。
    """

    name = "web_client"
    script_filename = "ch2_web_client.py"
    fixed_port = 80
    client_timeout_seconds = 10.0

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        port = self.fixed_port  # 客户端硬编码 80，忽略传入的随机端口
        started = time.monotonic()
        logs: list[str] = []
        client_stdout: list[str] = []
        client_stderr: list[str] = []
        server_logs: list[str] = []

        async def _emit(stream: str, line: str) -> None:
            logs.append(f"[{stream}] {line}")
            if on_log is not None:
                ret = on_log(stream, line)
                if asyncio.iscoroutine(ret):
                    await ret

        def _result(status: str, summary: str, checks: list[EvaluationCheck]) -> EvaluationResult:
            return EvaluationResult(
                passed=status == "passed",
                status=status,
                summary=summary,
                port=port,
                duration_ms=int((time.monotonic() - started) * 1000),
                checks=checks,
                logs=logs,
                stdout="\n".join(client_stdout),
                stderr="\n".join(client_stderr),
            )

        # 1. 参考服务器（可信代码）：/hello.html -> 200，其它 -> 404，并记录收到的路径。
        server_script = Path(__file__).resolve().parents[2] / "judge" / "servers" / "ch2_web_client_server.py"
        server_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(server_script), "--port", str(port),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        await asyncio.sleep(0.5)  # 等待服务器完成 bind/listen

        async def _drain_server() -> None:
            while True:
                line = await server_proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                server_logs.append(text)
                await _emit("server", text)

        pump_server = asyncio.create_task(_drain_server())

        # 2. 参考服务器若因端口被占用而提前退出，直接报错。
        if server_proc.returncode is not None:
            await _terminate_proc(server_proc)
            await asyncio.gather(pump_server, return_exceptions=True)
            return _result(
                "error",
                f"无法在 {port} 端口启动参考服务器（端口可能被占用）",
                [EvaluationCheck(name="参考服务器", passed=False, detail=f"{port} 端口启动失败")],
            )

        # 3. 运行学生客户端（教材风格：硬编码 127.0.0.1:80 + GET /hello.html，无需传参）—— 走沙箱
        client = await _spawn_untrusted(script)

        async def _drain_client(reader, sink, stream):
            while True:
                line = await reader.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                sink.append(text)
                await _emit(stream, text)

        pumps = [
            asyncio.create_task(_drain_client(client.stdout, client_stdout, "client")),
            asyncio.create_task(_drain_client(client.stderr, client_stderr, "client:err")),
        ]

        try:
            await asyncio.wait_for(client.wait(), timeout=self.client_timeout_seconds)
            timed_out = False
        except asyncio.TimeoutError:
            timed_out = True

        await client.stop()
        await _terminate_proc(server_proc)
        await asyncio.gather(pump_server, *pumps, return_exceptions=True)

        if timed_out:
            return _result(
                "timeout",
                f"客户端运行超过 {self.client_timeout_seconds:.0f}s",
                [EvaluationCheck(name="客户端", passed=False, detail="运行超时")],
            )

        client_text = "\n".join(client_stdout)
        server_text = "\n".join(server_logs)
        server_received = "/hello.html" in server_text
        got_200 = "200 OK" in client_text

        checks = [
            EvaluationCheck(
                name="服务器收到 /hello.html",
                passed=server_received,
                detail="服务器收到请求" if server_received else "服务器未收到 /hello.html 请求",
            ),
            EvaluationCheck(
                name="客户端打印 200 OK",
                passed=got_200,
                detail="客户端输出包含 200 OK" if got_200 else "客户端输出未见 200 OK",
            ),
        ]
        passed = server_received and got_200
        return _result(
            "passed" if passed else "failed",
            "客户端成功完成 HTTP 请求" if passed else "客户端请求未通过",
            checks,
        )


class PingCommandStrategy(JudgeStrategy):
    """第一章引导：学生直接输入 ``ping <host>:<port>`` 命令，后端起一个回 ``pong`` 的
    TCP 服务器并验证往返。

    学生提交的「代码」其实是一行命令（如 ``ping 127.0.0.1:8000``），后端读取后：
    1. 识别是否为 ``ping`` 命令；
    2. 起参考服务器（回 ``pong``），发 ``ping`` 收到 ``pong``；
    3. 通过则返回 ``pong，恭喜你成功通过测试``。
    """

    name = "ping_command"
    script_filename = "ch1_ping.txt"

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        started = time.monotonic()
        logs: list[str] = []

        async def _emit(stream: str, line: str) -> None:
            logs.append(f"[{stream}] {line}")
            if on_log is not None:
                ret = on_log(stream, line)
                if asyncio.iscoroutine(ret):
                    await ret

        def _result(status: str, summary: str, checks: list[EvaluationCheck]) -> EvaluationResult:
            return EvaluationResult(
                passed=status == "passed",
                status=status,
                summary=summary,
                port=port,
                duration_ms=int((time.monotonic() - started) * 1000),
                checks=checks,
                logs=logs,
                stdout="\n".join(logs),
                stderr="",
            )

        raw = script.read_text(encoding="utf-8")
        command = _strip_comment_lines(raw)
        if not command.lower().startswith("ping"):
            await _emit("judge", f"收到的输入：{command!r}")
            return _result(
                "failed",
                "未识别到 ping 命令",
                [EvaluationCheck(name="识别 ping 命令", passed=False,
                                 detail="请输入 ping 命令，例如 ping 127.0.0.1:8000")],
            )

        await _emit("judge", f"识别到命令：{command}")

        # 参考服务器（回 pong）
        server_script = Path(__file__).resolve().parents[2] / "judge" / "servers" / "ch1_ping_server.py"
        server_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(server_script), "--port", str(port),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        await asyncio.sleep(0.5)  # 等待服务器完成 bind/listen

        async def _drain(reader):
            while True:
                line = await reader.readline()
                if not line:
                    break
                await _emit("server", line.decode("utf-8", errors="replace").rstrip("\n"))

        pump = asyncio.create_task(_drain(server_proc.stdout))

        reply: str | None = None
        try:
            reply = await _tcp_ping(host, port, b"ping", timeout=3.0)
            await _emit("client", f"发送 ping，收到回显 {reply!r}")
        except (OSError, asyncio.TimeoutError) as exc:
            await _emit("client", f"连接/收发失败：{type(exc).__name__}: {exc}")

        await _terminate_proc(server_proc)
        await asyncio.gather(pump, return_exceptions=True)

        ok = reply == "pong"
        checks = [
            EvaluationCheck(name="识别 ping 命令", passed=True, detail=f"命令：{command}"),
            EvaluationCheck(name="收到 pong", passed=ok,
                            detail=f"服务器回显 {reply!r}" if ok else f"期望 pong，实际 {reply!r}"),
        ]
        if ok:
            return _result("passed", "pong，恭喜你成功通过测试", checks)
        return _result("failed", "未收到 pong", checks)


class SmtpStrategy(JudgeStrategy):
    """学生写 SMTP 客户端：后端跑参考 SMTP 服务器，客户端完成 SMTP 对话。

    客户端约定：连接 127.0.0.1:25，发送 HELO / MAIL FROM / RCPT TO / DATA / 正文 / QUIT。
    判题以「服务器收到完整 SMTP 对话」为通过。
    """

    name = "smtp"
    script_filename = "ch2_smtp.py"
    fixed_port = 25  # 教材客户端硬编码 25 端口
    client_timeout_seconds = 10.0

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        port = self.fixed_port
        started = time.monotonic()
        logs: list[str] = []
        client_stdout: list[str] = []
        client_stderr: list[str] = []
        server_logs: list[str] = []

        async def _emit(stream: str, line: str) -> None:
            logs.append(f"[{stream}] {line}")
            if on_log is not None:
                ret = on_log(stream, line)
                if asyncio.iscoroutine(ret):
                    await ret

        def _result(status: str, summary: str, checks: list[EvaluationCheck]) -> EvaluationResult:
            return EvaluationResult(
                passed=status == "passed",
                status=status,
                summary=summary,
                port=port,
                duration_ms=int((time.monotonic() - started) * 1000),
                checks=checks,
                logs=logs,
                stdout="\n".join(client_stdout),
                stderr="\n".join(client_stderr),
            )

        # 1. SMTP 参考服务器（25 端口）
        server_script = Path(__file__).resolve().parents[2] / "judge" / "servers" / "ch2_smtp_server.py"
        server_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(server_script), "--port", str(port),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        await asyncio.sleep(0.5)  # 等待服务器完成 bind/listen

        if server_proc.returncode is not None:
            await _terminate_proc(server_proc)
            return _result(
                "error",
                f"无法在 {port} 端口启动 SMTP 参考服务器（端口可能被占用）",
                [EvaluationCheck(name="参考服务器", passed=False, detail="25 端口启动失败")],
            )

        async def _drain_server():
            while True:
                line = await server_proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                server_logs.append(text)
                await _emit("server", text)

        pump_server = asyncio.create_task(_drain_server())

        # 2. 学生客户端（无参数：硬编码 127.0.0.1:25）—— 走沙箱
        client = await _spawn_untrusted(script)

        async def _drain_client(reader, sink, stream):
            while True:
                line = await reader.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                sink.append(text)
                await _emit(stream, text)

        pumps = [
            asyncio.create_task(_drain_client(client.stdout, client_stdout, "client")),
            asyncio.create_task(_drain_client(client.stderr, client_stderr, "client:err")),
        ]

        try:
            await asyncio.wait_for(client.wait(), timeout=self.client_timeout_seconds)
            timed_out = False
        except asyncio.TimeoutError:
            timed_out = True

        await client.stop()
        await _terminate_proc(server_proc)
        await asyncio.gather(pump_server, *pumps, return_exceptions=True)

        if timed_out:
            return _result(
                "timeout",
                f"客户端运行超过 {self.client_timeout_seconds:.0f}s",
                [EvaluationCheck(name="客户端", passed=False, detail="运行超时")],
            )

        server_text = "\n".join(server_logs).upper()
        required = ["HELO", "MAIL", "RCPT", "DATA", "QUIT"]
        missing = [c for c in required if f"RECEIVED {c}" not in server_text]

        checks = [
            EvaluationCheck(
                name="完成 SMTP 对话",
                passed=not missing,
                detail="服务器收到 HELO/MAIL/RCPT/DATA/QUIT" if not missing else f"缺少：{', '.join(missing)}",
            )
        ]
        passed = not missing
        return _result(
            "passed" if passed else "failed",
            "SMTP 对话完整" if passed else "SMTP 对话不完整",
            checks,
        )


class ProxyStrategy(JudgeStrategy):
    """学生写 Web 代理服务器：后端跑源服务器，代理转发请求。

    代理约定：从 ``sys.argv[1]`` 读取监听端口；收到请求后转发给源服务器（127.0.0.1:80）。
    判题以「代理能返回源服务器的内容」为通过。
    """

    name = "proxy"
    script_filename = "ch2_proxy.py"
    origin_port = 80
    read_timeout = 10.0

    def build_command(self, script, port):
        return [sys.executable, str(script), str(port)]

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        # 先起源服务器（80 端口，代理会连接它）
        origin_script = Path(__file__).resolve().parents[2] / "judge" / "servers" / "ch2_proxy_origin_server.py"
        origin_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(origin_script), "--port", str(self.origin_port),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        await asyncio.sleep(0.5)
        try:
            return await super().judge(script, test_cases, host=host, port=port, on_log=on_log)
        finally:
            await _terminate_proc(origin_proc)

    async def verify(self, proc, host, port, test_cases, request_timeout):
        # 请求路径带 host，符合教材代理的解析格式（GET /host/file HTTP/1.0）
        raw = b"GET /127.0.0.1/hello.html HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=request_timeout
            )
        except (OSError, asyncio.TimeoutError):
            return _VerifyOutcome(
                status="failed",
                checks=[EvaluationCheck(name="代理响应", passed=False, detail="无法连接代理")],
            )
        try:
            writer.write(raw)
            await writer.drain()
            data = await asyncio.wait_for(reader.read(8192), timeout=self.read_timeout)
        except (OSError, asyncio.TimeoutError) as exc:
            return _VerifyOutcome(
                status="failed",
                checks=[EvaluationCheck(name="代理响应", passed=False, detail=f"读取响应失败：{type(exc).__name__}")],
            )
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

        ok = b"PROXY_ORIGIN_HELLO" in data
        return _VerifyOutcome(
            status="passed" if ok else "failed",
            checks=[
                EvaluationCheck(
                    name="代理转发请求",
                    passed=ok,
                    detail="代理返回了源服务器内容" if ok else "代理响应中未包含源服务器内容",
                )
            ],
        )


class IcmpPingStrategy(JudgeStrategy):
    """学生写 ICMP Echo Request 客户端（教材 raw socket ping）。

    说明：raw socket 需要 root / ``CAP_NET_RAW``，而判题沙箱 ``--cap-drop ALL``、
    禁外网、以非 root 运行，无法真实收发 ICMP 报文。因此本策略对提交代码做
    **静态结构校验**：检查学生是否完成了教材要求的原始套接字创建、ICMP Echo
    Request 报文头构造与收发逻辑，再把 ``checksum`` 函数单独放进沙箱执行一次，
    校验其结果与参考答案一致。
    """

    name = "icmp_ping"
    script_filename = "ch5_icmp.py"

    # 静态校验需要出现在学生代码里的关键要素（教材 ICMP Ping 客户端）。
    STRUCTURAL_CHECKS: list[tuple[str, tuple[str, ...]]] = [
        ("创建原始套接字 SOCK_RAW", ("SOCK_RAW",)),
        ("指定 ICMP 协议", ("getprotobyname", "IPPROTO_ICMP")),
        ("构造 ICMP 报文头 struct.pack", ("struct.pack",)),
        ("网络字节序 htons", ("htons",)),
        ("发送报文 sendto", ("sendto",)),
        ("接收响应 recvfrom", ("recvfrom",)),
    ]

    # 用于校验 checksum 的固定报文：8 字节 ICMP Echo Request 头（type=8, code=0, id=1, seq=1）。
    _CHECKSUM_SAMPLE = b"\x08\x00\x00\x00\x00\x01\x00\x01"

    async def judge(self, script, test_cases, *, host, port, on_log=None):
        started = time.monotonic()
        logs: list[str] = []

        async def _emit(stream: str, line: str) -> None:
            logs.append(f"[{stream}] {line}")
            if on_log is not None:
                ret = on_log(stream, line)
                if asyncio.iscoroutine(ret):
                    await ret

        def _result(status: str, summary: str, checks: list[EvaluationCheck]) -> EvaluationResult:
            return EvaluationResult(
                passed=status == "passed",
                status=status,
                summary=summary,
                port=port or 0,
                duration_ms=int((time.monotonic() - started) * 1000),
                checks=checks,
                logs=logs,
                stdout="\n".join(logs),
                stderr="",
            )

        code = script.read_text(encoding="utf-8", errors="replace")
        await _emit("judge", f"收到提交代码 {len(code)} 字节，开始静态校验")

        checks: list[EvaluationCheck] = []
        for name, markers in self.STRUCTURAL_CHECKS:
            ok = any(marker in code for marker in markers)
            checks.append(
                EvaluationCheck(name=name, passed=ok, detail="已实现" if ok else "代码中未找到该要素")
            )
            await _emit("judge", f"[{'✓' if ok else '✗'}] {name}")

        checksum_ok, checksum_detail = await _verify_checksum(code, self._CHECKSUM_SAMPLE)
        checks.append(EvaluationCheck(name="校验和 checksum", passed=checksum_ok, detail=checksum_detail))
        await _emit("judge", f"[{'✓' if checksum_ok else '✗'}] 校验和 checksum：{checksum_detail}")

        passed = all(c.passed for c in checks)
        summary = "ICMP 客户端结构完整且校验和正确" if passed else "ICMP 客户端实现不完整（见下方检查项）"
        return _result("passed" if passed else "failed", summary, checks)


def _ref_checksum(data: bytes) -> int:
    """参考答案 ``checksum`` 的实现（教材「自顶向下」ICMP Ping 客户端）。

    作为校验基准：提取学生代码里的 ``checksum`` 函数后，对同一段报文调用并与之比对。
    """
    csum = 0
    count_to = (len(data) // 2) * 2
    count = 0
    while count < count_to:
        csum = (csum + data[count + 1] * 256 + data[count]) & 0xFFFFFFFF
        count += 2
    if count_to < len(data):
        csum = (csum + data[len(data) - 1]) & 0xFFFFFFFF
    csum = (csum >> 16) + (csum & 0xFFFF)
    csum = csum + (csum >> 16)
    answer = ~csum & 0xFFFF
    return answer >> 8 | (answer << 8 & 0xFF00)


def _extract_checksum_source(code: str) -> tuple[str | None, str]:
    """从学生代码里抽出 ``checksum`` 函数的源码。

    只抽函数、不带上模块顶层语句，因此学生的 ``ping(...)`` 之类顶层调用不会被执行；
    函数体本身的执行交给沙箱（见 :func:`_verify_checksum`）。
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return None, f"代码存在语法错误：{exc.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "checksum":
            try:
                return ast.unparse(node), ""
            except Exception as exc:  # noqa: BLE001
                return None, f"无法解析 checksum 函数：{type(exc).__name__}: {exc}"
    return None, "未找到名为 checksum 的函数"


async def _call_checksum_in_sandbox(fn_source: str, sample: bytes) -> tuple[bool, str]:
    """在判题沙箱里执行学生提交的 ``checksum`` 函数，返回 ``(是否取到值, 值或错误说明)``。

    安全边界：学生代码始终在 :func:`start_sandbox` 提供的沙箱（Docker 隔离或子进程兜底）
    中运行，并叠加硬超时，避免死循环或恶意代码拖垮后端进程。
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="judge-checksum-"))
    try:
        (tmp_dir / "student_checksum.py").write_text(fn_source, encoding="utf-8")
        (tmp_dir / "sample.bin").write_bytes(sample)
        driver = tmp_dir / "_checksum_driver.py"
        driver.write_text(_CHECKSUM_DRIVER, encoding="utf-8")

        handle = await start_sandbox(
            SandboxSpec(
                command=[sys.executable, str(driver), "sample.bin", "student_checksum.py"],
                cwd=str(tmp_dir),
                timeout_seconds=CHECKSUM_TIMEOUT_SECONDS,
            )
        )
        if handle is None:
            return False, "无法启动判题沙箱进程"

        try:
            raw = await asyncio.wait_for(handle.stdout.read(), timeout=CHECKSUM_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            return False, f"checksum 执行超过 {CHECKSUM_TIMEOUT_SECONDS}s（疑似死循环）"
        finally:
            await handle.stop()

        output = raw.decode("utf-8", errors="replace")
        line = next((ln.strip() for ln in output.splitlines() if ln.startswith(("OK:", "ERR:"))), "")
        if not line:
            return False, "checksum 未产生有效输出（可能崩溃或被沙箱终止）"
        if line.startswith("ERR:"):
            return False, line[len("ERR:") :].strip()
        return True, line[len("OK:") :].strip()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _verify_checksum(code: str, sample: bytes) -> tuple[bool, str]:
    """在沙箱中执行学生代码里的 ``checksum`` 函数，与参考答案对同一段报文比对。"""
    fn_source, error = _extract_checksum_source(code)
    if fn_source is None:
        return False, error

    ok, payload = await _call_checksum_in_sandbox(fn_source, sample)
    if not ok:
        return False, payload

    try:
        got = int(payload, 0)
    except ValueError:
        return False, f"checksum 返回值不是整数：{payload!r}"

    expected = _ref_checksum(sample)
    if got == expected:
        return True, f"校验和正确（{got:#06x}）"
    return False, f"校验和错误：期望 {expected:#06x}，实际 {got:#06x}"


# --------------------------------------------------------------------------
# 注册表：按 lab_id 分发（新增 lab 在这里登记策略）
# --------------------------------------------------------------------------

STRATEGIES: dict[str, JudgeStrategy] = {
    "sock-web": WebServerStrategy(),
    "sock-web-client": WebClientStrategy(),
    "sock-pinger": UdpPingerClientStrategy(),
    "sock-pinger-server": UdpPingerServerStrategy(),
    "sock-smtp": SmtpStrategy(),
    "sock-proxy": ProxyStrategy(),
    "sock-websocket": PingCommandStrategy(),
    "sock-icmp": IcmpPingStrategy(),
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
    proc,
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


async def _spawn_untrusted(script: Path) -> SandboxHandle:
    """启动「学生提交的代码」——一律走 :func:`start_sandbox`，不要用裸的 create_subprocess_exec。

    走沙箱才能同时拿到三样东西：命名空间隔离（bwrap）、内存/CPU/进程数上限、
    以及只含最小变量的环境（不再把后端进程的全部环境变量透传给不可信代码）。

    注意：这些 Lab 的学生客户端按教材写法硬编码连 ``127.0.0.1``，所以沙箱**必须保留网络命名空间**
    —— 这正是 sandbox.py 里刻意不加 ``--unshare-net`` 的原因。
    """
    handle = await start_sandbox(
        SandboxSpec(command=[sys.executable, str(script)], cwd=str(script.parent))
    )
    if handle is None:
        raise RuntimeError("无法启动判题沙箱进程")
    return handle


async def _terminate_proc(proc: asyncio.subprocess.Process, grace: float = 2.0) -> None:
    """终止子进程：先 terminate，宽限后仍存活则 kill。"""
    if proc.returncode is not None:
        return
    try:
        proc.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(proc.wait(), timeout=grace)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()


async def _tcp_ping(host: str, port: int, payload: bytes, timeout: float) -> str:
    """建立 TCP 连接、发送 ``payload`` 并读取一行回显。"""
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    try:
        writer.write(payload)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
        return data.decode(errors="replace").strip()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _udp_ping_once(loop, host, port, payload, timeout):
    """发一个 UDP 报文并等待回显，超时返回 None（服务器可能随机丢包不响应）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    try:
        await loop.sock_sendto(sock, payload, (host, port))
        try:
            data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 1024), timeout)
            return data
        except asyncio.TimeoutError:
            return None
    finally:
        sock.close()


def _strip_comment_lines(text: str) -> str:
    """去掉以 ``#`` 开头的注释行，返回剩余内容（用于识别命令行输入）。

    学生提交的「代码」里常保留占位符注释（如 ``# 请在下方输入一条 ping 命令``），
    若不去除会干扰命令识别；这里只剔除「整行都是注释」的行，保留真正的命令。
    """
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lines).strip()


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


def _summary(status: str) -> str:
    return {
        "passed": "测试通过：所有 test_cases 校验通过",
        "failed": "测试失败：存在未通过的 test_case",
        "timeout": "测试超时",
        "error": "运行出错",
    }.get(status, status)


async def _self_test() -> None:
    """本地自测：对内置示例分别跑 Web Server / UDP Pinger / Web Client 判题。"""
    static_dir = Path(__file__).resolve().parents[2] / "static" / "solutions"

    ws_code = (static_dir / "ch2_web_server.py").read_text(encoding="utf-8")
    ws_cases = [TestCase(name="GET 200", input="GET /index.html HTTP/1.1", expected="HTTP/1.1 200 OK")]
    print("== Web Server ==")
    print((await evaluate_submission("sock-web", ws_code, ws_cases)).model_dump_json(indent=2))

    pinger_code = (static_dir / "ch2_udp_pinger.py").read_text(encoding="utf-8")
    pinger_cases = [TestCase(name="回显 ping", input="ping 1", expected="ping 1")]
    print("== UDP Pinger ==")
    print((await evaluate_submission("sock-pinger", pinger_code, pinger_cases)).model_dump_json(indent=2))

    web_client_code = (static_dir / "ch2_web_client.py").read_text(encoding="utf-8")
    web_client_cases = [
        TestCase(name="GET 200", input="GET /hello.html HTTP/1.1", expected="HTTP/1.1 200 OK"),
        TestCase(name="GET 404", input="GET /missing.html HTTP/1.1", expected="HTTP/1.1 404 Not Found"),
    ]
    print("== Web Client ==")
    print((await evaluate_submission("sock-web-client", web_client_code, web_client_cases)).model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(_self_test())
