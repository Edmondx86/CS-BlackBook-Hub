"""判题沙箱的关键不变量测试（标准库 unittest，无需额外依赖）。

运行：``cd backend && python -m unittest discover -s tests -v``

为什么值得为这几行写测试：判题是整站唯一执行不可信代码的地方，而下面这些约束
一旦被后续重构破坏，**线上会静默地失去隔离或直接全部判题失败**，本地却不一定能发现
（本机 Windows 没有 bwrap，走的永远是回退路径）。
"""

from __future__ import annotations

import asyncio
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from app.services import evaluator, sandbox


class BwrapArgsTest(unittest.TestCase):
    """bwrap 参数构造。"""

    CWD = "/tmp/judge-abc123"
    CMD = ["/srv/cs-blackbook/backend/venv/bin/python", "/tmp/judge-abc123/main.py", "--port", "9000"]

    def setUp(self) -> None:
        self.args = sandbox._wrap_with_bwrap(self.CMD, self.CWD)

    def test_keeps_network_namespace(self) -> None:
        """绝不能切断网络命名空间。

        这些 Lab 的裁判要经 localhost 与学生的进程对话（发 HTTP / UDP / SMTP），
        加了 --unshare-net 裁判就连不上学生对端了。
        """
        self.assertNotIn("--unshare-net", self.args)

    def test_workdir_rebound_after_tmpfs(self) -> None:
        """--tmpfs /tmp 之后必须把工作目录重新挂回来。

        工作目录是 tempfile.mkdtemp() 建在 /tmp 下的，而 --tmpfs /tmp 会把整个 /tmp
        换成空 tmpfs —— 不重新 ro-bind 回来，沙箱里就没有学生脚本，--chdir 也会失败。
        （实测过：bwrap 会报 "Can't chdir to ...: No such file or directory"，
        结果是 Linux 上每个判题都失败。）
        """
        tmpfs_at = self.args.index("--tmpfs")
        rebind_at = next(
            i
            for i in range(len(self.args) - 2)
            if self.args[i] == "--ro-bind" and self.args[i + 1] == self.CWD and self.args[i + 2] == self.CWD
        )
        self.assertGreater(rebind_at, tmpfs_at, "--ro-bind 工作目录必须排在 --tmpfs /tmp 之后")

    def test_chdir_after_rebind(self) -> None:
        """--chdir 必须排在重新挂载之后，否则目录还不存在。"""
        rebind_at = self.args.index(self.CWD, self.args.index("--tmpfs"))
        self.assertGreater(self.args.index("--chdir"), rebind_at)

    def test_root_is_read_only(self) -> None:
        idx = self.args.index("--ro-bind")
        self.assertEqual(self.args[idx : idx + 3], ["--ro-bind", "/", "/"])

    def test_isolation_flags_present(self) -> None:
        for flag in ("--unshare-user", "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--unshare-cgroup"):
            self.assertIn(flag, self.args)

    def test_command_preserved_at_tail(self) -> None:
        self.assertEqual(self.args[-len(self.CMD) :], self.CMD)


class ModeParsingTest(unittest.TestCase):
    """JUDGE_SANDBOX / JUDGE_ENGINE 两个环境开关的解析。"""

    def test_sandbox_mode(self) -> None:
        for raw, want in [("auto", "auto"), ("BWRAP", "bwrap"), (" none ", "none"), ("", "auto")]:
            os.environ["JUDGE_SANDBOX"] = raw
            try:
                self.assertEqual(sandbox._sandbox_mode(), want, f"输入 {raw!r}")
            finally:
                del os.environ["JUDGE_SANDBOX"]

    def test_engine_defaults_to_subprocess(self) -> None:
        """默认必须是 subprocess（bwrap），不能是 docker。

        Docker 路径在 internal 网络上发布端口会静默失效，且 6 个 Lab 的学生代码
        硬编码连 127.0.0.1、容器里够不到宿主机的参考服务器。
        """
        os.environ.pop("JUDGE_ENGINE", None)
        self.assertEqual(sandbox._sandbox_engine(), "subprocess")


class UntrustedSpawnTest(unittest.TestCase):
    """学生代码必须经过 start_sandbox，不能裸跑。"""

    def test_spawn_untrusted_goes_through_sandbox(self) -> None:
        calls: list[sandbox.SandboxSpec] = []

        async def fake_start(spec):
            calls.append(spec)
            return object()  # 只关心“有没有走沙箱”，不需要真的进程

        original = evaluator.start_sandbox
        evaluator.start_sandbox = fake_start
        try:
            import asyncio
            from pathlib import Path

            script = Path("/tmp/judge-x/main.py")
            asyncio.run(evaluator._spawn_untrusted(script))
        finally:
            evaluator.start_sandbox = original

        self.assertEqual(len(calls), 1, "_spawn_untrusted 必须调用 start_sandbox")
        # 用 Path 的结果比对，避免 Windows 的路径分隔符差异
        self.assertEqual(calls[0].cwd, str(script.parent))
        self.assertEqual(calls[0].command[1], str(script))


class _FakeResource:
    """假的 resource 模块：如实模拟“只接受整数”，并记录调用。"""

    RLIMIT_AS = 1
    RLIMIT_CPU = 2
    RLIMIT_NPROC = 3

    def __init__(self, always_raise: BaseException | None = None) -> None:
        self.calls: list[tuple[int, tuple[int, ...]]] = []
        self.always_raise = always_raise

    def setrlimit(self, which: int, limits: tuple) -> None:
        if self.always_raise is not None:
            raise self.always_raise
        for value in limits:
            # 真实的 setrlimit 对 float 抛 TypeError，这里如实复现
            if not isinstance(value, int):
                raise TypeError(
                    f"'{type(value).__name__}' object cannot be interpreted as an integer"
                )
        self.calls.append((which, tuple(limits)))


class PreexecRlimitTest(unittest.TestCase):
    """POSIX preexec 里的 rlimit 设置。

    这一类 bug 在 Windows 上**完全不可见** —— ``os.name != "posix"`` 时直接返回 None，
    ``preexec_fn`` 从不执行 —— 却会让线上每一个判题都 500。实测踩过一次：
    ``spec.timeout_seconds`` 是 ``5.0``（float），而 ``resource.setrlimit`` 只接受整数，
    抛出的 ``TypeError`` 既不在 ``(ValueError, OSError)`` 的捕获范围内，又会冲出
    ``preexec_fn`` 让整个 ``Popen`` 失败，报错还是一句看不出原因的
    ``subprocess.SubprocessError: Exception occurred in preexec_fn.``
    （CPython 只把 ``OSError`` 系异常精确回传给父进程）。

    所以这里即使要打桩，也要把两条不变量锁死：传进去的必须是整数；单个 rlimit
    设不上也不能让判题整个失败。
    """

    def _run_preexec(self, resource_stub: _FakeResource, spec=None) -> _FakeResource:
        fake_os = types.SimpleNamespace(name="posix", write=lambda fd, data: None)
        spec = spec or sandbox.SandboxSpec(
            command=["python", "/tmp/judge-x/main.py", "--port", "9000"],
            cwd="/tmp/judge-x",
            port=9000,
            timeout_seconds=5.0,  # ← 故意用 float，复现线上情形
        )
        with mock.patch.object(sandbox, "os", fake_os), mock.patch.dict(
            sys.modules, {"resource": resource_stub}
        ):
            preexec = sandbox._make_preexec(spec)
            self.assertIsNotNone(preexec, "POSIX 下必须返回可调用的 preexec")
            preexec()  # 旧实现在这一行就会抛 TypeError
        return resource_stub

    def test_float_timeout_is_coerced_to_int(self) -> None:
        stub = self._run_preexec(_FakeResource())
        self.assertEqual(len(stub.calls), 3, "三个 rlimit 都应设置成功")
        for which, limits in stub.calls:
            for value in limits:
                self.assertIsInstance(value, int, f"rlimit {which} 收到了非整数 {value!r}")

    def test_limit_failure_never_escapes_preexec(self) -> None:
        """单个 rlimit 设不上不能让 Popen 失败（某些内核/容器会拒绝）。"""
        self._run_preexec(_FakeResource(always_raise=RuntimeError("operation not permitted")))


class FixedPortInvariantTest(unittest.TestCase):
    """任何策略都不许把端口固定在 1024 以下。

    生产宿主机上 ``net.ipv4.ip_unprivileged_port_start`` 默认是 1024，判题以非特权用户
    （csbb）运行，**根本绑不了 <1024 的端口**；80 还额外被 nginx 占着。
    历史上 WebServer / WebClient 固定 80、Smtp 固定 25，到了真实服务器上这三个 Lab 全废，
    而本机（Windows 上端口随便绑）永远是绿的 —— 所以用测试把这条封死。
    """

    def test_no_strategy_uses_privileged_fixed_port(self) -> None:
        offenders: list[str] = []
        for lab_id, strategy in evaluator.STRATEGIES.items():
            for attr in ("fixed_port", "origin_port"):
                value = getattr(strategy, attr, None)
                if value is not None and value < 1024:
                    offenders.append(f"{lab_id}.{attr}={value}")
        self.assertEqual(offenders, [], f"这些策略用了 <1024 的固定端口：{offenders}")


class _StubHandle:
    """假沙箱句柄：只满足 JudgeStrategy.judge() 用到的接口。"""

    def __init__(self) -> None:
        self.returncode = None
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdout.feed_eof()
        self.stderr.feed_eof()

    async def stop(self) -> None:
        return None


class _NoVerifyStrategy(evaluator.JudgeStrategy):
    """子类既不实现 verify、也没有 test_cases —— 此时**没有任何判据**。"""

    name = "test_no_verify"
    script_filename = "noop.py"


class _VerifyStrategy(evaluator.JudgeStrategy):
    """子类自带判据（实现 verify），即便 test_cases 为空也必须让它跑起来。"""

    name = "test_verify"
    script_filename = "noop.py"
    called = False

    async def verify(self, proc, host, port, test_cases, request_timeout):
        type(self).called = True
        return evaluator._VerifyOutcome(
            status="passed",
            checks=[evaluator.EvaluationCheck(name="自有判据", passed=True, detail="ok")],
        )


class BaseJudgeFallbackTest(unittest.TestCase):
    """没有判据时必须报错，绝不能“空转通过”。

    以前基类在 ``test_cases`` 为空时会直接判 passed（等于“能 bind 端口就算过”），
    sock-proxy / sock-pinger-server 就是这么空转的：学生写个空壳也能得分。
    """

    def setUp(self) -> None:
        self._orig_spawn = evaluator.start_sandbox
        self._orig_wait = evaluator.STARTUP_WAIT_SECONDS
        evaluator.STARTUP_WAIT_SECONDS = 0  # 测试里不必真的等启动
        _VerifyStrategy.called = False

    def tearDown(self) -> None:
        evaluator.start_sandbox = self._orig_spawn
        evaluator.STARTUP_WAIT_SECONDS = self._orig_wait

    def _run(self, strategy, test_cases):
        async def fake_start(spec):
            return _StubHandle()

        evaluator.start_sandbox = fake_start
        script = Path("/tmp/judge-x/main.py")
        return asyncio.run(strategy.judge(script, test_cases, host="127.0.0.1", port=12345))

    def test_missing_criteria_returns_error_not_passed(self) -> None:
        result = self._run(_NoVerifyStrategy(), [])
        self.assertFalse(result.passed, "没有任何判据时绝不能判通过")
        self.assertEqual(result.status, "error")

    def test_verify_runs_even_without_test_cases(self) -> None:
        result = self._run(_VerifyStrategy(), [])
        self.assertTrue(_VerifyStrategy.called, "自带判据的 verify 必须被调用，不能空转")
        self.assertTrue(result.passed)


class ProxyReadUntilMarkerTest(unittest.TestCase):
    """代理响应必须读到出现标记为止，不能只 read() 一次。

    教材风格的代理是分三段 send 的（状态行 / 头 / 正文），单次 ``read(n)`` 只要有
    一个字节就返回，于是只拿到第一段、判题报“响应中未包含源服务器内容”。
    实测这份参考答案在单次 read 下通过率只有 2/6，改成分段读到标记后 6/6。
    """

    MARKER = b"PROXY_ORIGIN_HELLO"
    FRAGMENTS = (b"HTTP/1.1 200 OK\r\n", b"Content-Type:text/html\r\n\r\n", MARKER)

    @staticmethod
    def _reader_with_fragments(delay: float) -> tuple[asyncio.StreamReader, "asyncio.Task"]:
        reader = asyncio.StreamReader()

        async def feed() -> None:
            for part in ProxyReadUntilMarkerTest.FRAGMENTS:
                reader.feed_data(part)
                await asyncio.sleep(delay)
            reader.feed_eof()

        return reader, asyncio.create_task(feed())

    def test_collects_marker_arriving_in_later_fragments(self) -> None:
        strategy = evaluator.ProxyStrategy()

        async def run() -> bytes:
            reader, task = self._reader_with_fragments(0.05)
            data = await strategy._read_until_marker(reader, self.MARKER)
            await task
            return data

        self.assertIn(self.MARKER, asyncio.run(run()))

    def test_single_read_is_not_enough(self) -> None:
        """反向对照：单次 read() 只拿到第一段 —— 这正是被修掉的那个 bug。"""

        async def run() -> bytes:
            reader, task = self._reader_with_fragments(0.05)
            data = await reader.read(8192)
            await task
            return data

        self.assertNotIn(self.MARKER, asyncio.run(run()))


if __name__ == "__main__":
    unittest.main()
