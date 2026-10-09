"""判题沙箱的关键不变量测试（标准库 unittest，无需额外依赖）。

运行：``cd backend && python -m unittest discover -s tests -v``

为什么值得为这几行写测试：判题是整站唯一执行不可信代码的地方，而下面这些约束
一旦被后续重构破坏，**线上会静默地失去隔离或直接全部判题失败**，本地却不一定能发现
（本机 Windows 没有 bwrap，走的永远是回退路径）。
"""

from __future__ import annotations

import os
import sys
import types
import unittest
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
    """假的 resource 模块：如实模拟「只接受整数」，并记录调用。"""

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


if __name__ == "__main__":
    unittest.main()
