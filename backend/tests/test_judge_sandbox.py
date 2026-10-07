"""判题沙箱的关键不变量测试（标准库 unittest，无需额外依赖）。

运行：``cd backend && python -m unittest discover -s tests -v``

为什么值得为这几行写测试：判题是整站唯一执行不可信代码的地方，而下面这些约束
一旦被后续重构破坏，**线上会静默地失去隔离或直接全部判题失败**，本地却不一定能发现
（本机 Windows 没有 bwrap，走的永远是回退路径）。
"""

from __future__ import annotations

import os
import unittest

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
            return object()  # 只关心「有没有走沙箱」，不需要真的进程

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


if __name__ == "__main__":
    unittest.main()
