"""ProxyStrategy 的两条关键回归：随机标记 + 缓存只能落在临时目录。

为什么值得单独写：这两条都**只在真实服务器上才暴露** —— bwrap 把判题工作目录挂成只读
（相对路径 ``WEB/...`` 会 OSError，被学生代码里的 ``except:`` 吞掉后连响应都不发），
而写死的标记 ``PROXY_ORIGIN_HELLO`` 明写在公开的实验指引里，学生可以先伪造一份缓存、
走缓存分支返回，一次真实转发都不做也能通过。Windows 本机两条都是绿的，所以用测试封死：

1. 标记每次判题现随机生成，只认本次的值；伪造固定标记的响应判不过。
2. 参考答案真的能转发（端到端起真进程），且缓存写在 tempfile 的临时目录、不是工作目录。

运行：``cd backend && python -m unittest discover -s tests -v``
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from app.services import evaluator

BACKEND_DIR = Path(__file__).resolve().parents[1]
STARTER = BACKEND_DIR / "static" / "starter" / "ch2_proxy.py"
SOLUTION = BACKEND_DIR / "static" / "solutions" / "ch2_proxy.py"
ORIGIN_SERVER = BACKEND_DIR / "judge" / "servers" / "ch2_proxy_origin_server.py"

# 旧实现里写死、且公开写在实验指引里的标记：伪造缓存的人只会写这一个值。
FIXED_MARKER = "PROXY_ORIGIN_HELLO"
# 判题请求的路径固定，学生按教材约定缓存到 <临时目录>/WEB/127.0.0.1/hello.html。
CACHE_RELPATH = ("WEB", "127.0.0.1", "hello.html")


def _cache_path() -> Path:
    return Path(tempfile.gettempdir()).joinpath(*CACHE_RELPATH)


def _remove_cache_artifact() -> None:
    """清掉参考答案写下的缓存文件与随之出现的空目录（test 之间不能相互污染）。"""
    path = _cache_path()
    try:
        path.unlink()
    except OSError:
        pass
    for parent in (path.parent, path.parent.parent):
        try:
            parent.rmdir()  # 只在空目录时成功，不会误删别人放的东西
        except OSError:
            pass


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


class _StubProc:
    """假源站进程：只满足 returncode 检查与 _terminate_proc() 的收尾。"""

    def __init__(self) -> None:
        self.returncode: int | None = None
        self.stdout = None

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode or 0


class _FakeOriginLauncher:
    """冒充 asyncio.create_subprocess_exec：记下传给源站的 ``--marker``。"""

    def __init__(self) -> None:
        self.markers: list[str] = []
        self.procs: list[_StubProc] = []

    async def __call__(self, *args, **kwargs) -> _StubProc:
        argv = [str(a) for a in args]
        self.markers.append(argv[argv.index("--marker") + 1])
        proc = _StubProc()
        self.procs.append(proc)
        return proc


class _ProxyJudgeHarness:
    """把源站进程与沙箱都打桩，只跑 judge() 的编排逻辑（不联网、不起真进程）。"""

    def __init__(self) -> None:
        self.strategy = evaluator.STRATEGIES["sock-proxy"]
        self.fake_origin = _FakeOriginLauncher()
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="judge-proxy-test-"))
        self.script = self.tmp_dir / "ch2_proxy.py"
        self.script.write_text("print('stub')\n", encoding="utf-8")
        self._saved = None

    def __enter__(self) -> "_ProxyJudgeHarness":
        self._saved = (
            evaluator.start_sandbox,
            evaluator.STARTUP_WAIT_SECONDS,
            asyncio.create_subprocess_exec,
        )
        evaluator.start_sandbox = self._fake_start
        evaluator.STARTUP_WAIT_SECONDS = 0
        asyncio.create_subprocess_exec = self.fake_origin
        return self

    def __exit__(self, *exc_info) -> None:
        (
            evaluator.start_sandbox,
            evaluator.STARTUP_WAIT_SECONDS,
            asyncio.create_subprocess_exec,
        ) = self._saved
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    async def _fake_start(self, spec):
        return _StubHandle()

    async def judge_once(self):
        # 端口是现分配的空闲端口，没有监听者 —— verify 会以“无法连接代理”结束，
        # 这不影响本类要断言的东西（标记怎么生成、怎么随 ContextVar 传下去）。
        return await self.strategy.judge(
            self.script, [], host="127.0.0.1", port=evaluator.find_free_port()
        )


class MarkerRandomnessTest(unittest.IsolatedAsyncioTestCase):
    """每次判题的源站标记必须不同 —— 相同就等于给了学生一个可以预判的目标。"""

    async def test_marker_differs_between_runs(self) -> None:
        with _ProxyJudgeHarness() as harness:
            await harness.judge_once()
            await harness.judge_once()
        markers = harness.fake_origin.markers
        self.assertEqual(len(markers), 2, "两次判题都应启动源站并带上 --marker")
        self.assertNotEqual(markers[0], markers[1], "两次判题的标记必须不同")
        for marker in markers:
            self.assertTrue(marker.startswith("PROXY_ORIGIN_"), f"标记异常：{marker!r}")
            self.assertNotEqual(marker, FIXED_MARKER, "不能再沿用公开写死的标记")

    async def test_two_concurrent_runs_see_their_own_marker(self) -> None:
        """并发判同一个 Lab（MAX_CONCURRENT_RUNS=4）时标记不能串。

        这正是必须用 ContextVar 而不是实例属性的原因：ProxyStrategy 是单例。
        """
        with _ProxyJudgeHarness() as harness:
            strategy = harness.strategy
            seen: list[str | None] = []

            async def fake_verify(proc, host, port, test_cases, request_timeout):
                seen.append(evaluator._PROXY_ORIGIN_MARKER.get())
                return evaluator._VerifyOutcome(status="failed", checks=[])

            strategy.verify = fake_verify
            try:
                await asyncio.gather(harness.judge_once(), harness.judge_once())
            finally:
                strategy.__dict__.pop("verify", None)  # 还原：不能永久污染这个单例

        markers = harness.fake_origin.markers
        self.assertEqual(len(markers), 2)
        self.assertEqual(len(seen), 2, "两次判题的 verify 都应被调用")
        self.assertNotEqual(markers[0], markers[1])
        self.assertEqual(
            sorted(seen), sorted(markers), "verify 读到的必须是各自那一次判题的标记"
        )


class VerifyMarkerTest(unittest.IsolatedAsyncioTestCase):
    """verify() 只认本次标记：响应里出现旧标记不算通过。"""

    async def _verify_against(self, served: bytes, marker: str | None):
        async def handle(reader, writer) -> None:
            # 必须读到空行为止，不能 read(4096)：客户端不会关闭写方向，read(4096) 会
            # 一直等满 4096 字节或 EOF，于是响应永远发不出去，判题白等满 read_timeout。
            try:
                await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
            except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError):
                pass
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + served)
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            token = evaluator._PROXY_ORIGIN_MARKER.set(marker)
            try:
                return await evaluator.ProxyStrategy().verify(
                    None, "127.0.0.1", port, [], evaluator.REQUEST_TIMEOUT_SECONDS
                )
            finally:
                evaluator._PROXY_ORIGIN_MARKER.reset(token)

    async def test_forged_fixed_marker_is_rejected(self) -> None:
        """伪造“缓存命中”返回公开的固定标记 —— 必须判不过。"""
        marker = evaluator._new_proxy_marker()
        outcome = await self._verify_against(FIXED_MARKER.encode(), marker)
        self.assertEqual(outcome.status, "failed", "写死的公开标记不能再算通过")
        self.assertFalse(outcome.checks[0].passed)

    async def test_current_marker_passes(self) -> None:
        marker = evaluator._new_proxy_marker()
        outcome = await self._verify_against(marker.encode(), marker)
        self.assertEqual(outcome.status, "passed", outcome.checks[0].detail)

    async def test_missing_marker_is_an_error_not_a_pass(self) -> None:
        outcome = await self._verify_against(FIXED_MARKER.encode(), None)
        self.assertEqual(outcome.status, "error", "没有标记时不能给出任何通过结论")


class ProxyCacheLocationTest(unittest.IsolatedAsyncioTestCase):
    """缓存必须写在临时目录（沙箱里唯一可写的地方），不能是工作目录下的相对路径。"""

    async def asyncSetUp(self) -> None:
        self.cwd = Path(tempfile.mkdtemp(prefix="proxy-cwd-"))
        _remove_cache_artifact()
        self.marker = evaluator._new_proxy_marker()
        self.origin_port = evaluator.find_free_port()
        self.proxy_port = evaluator.find_free_port()
        self.origin = await asyncio.create_subprocess_exec(
            sys.executable,
            str(ORIGIN_SERVER),
            "--port",
            str(self.origin_port),
            "--marker",
            self.marker,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await _wait_port(self.origin_port)
        self.proxy = await asyncio.create_subprocess_exec(
            sys.executable,
            str(SOLUTION),
            str(self.proxy_port),
            str(self.origin_port),
            cwd=str(self.cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await _wait_port(self.proxy_port)

    async def asyncTearDown(self) -> None:
        for proc in (getattr(self, "proxy", None), getattr(self, "origin", None)):
            if proc is None:
                continue
            if proc.returncode is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except (asyncio.TimeoutError, ProcessLookupError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
            if proc.stdout is not None:  # 排空管道，免得子进程卡在写 stdout 上
                try:
                    await asyncio.wait_for(proc.stdout.read(), timeout=2)
                except (asyncio.TimeoutError, OSError):
                    pass
        shutil.rmtree(self.cwd, ignore_errors=True)
        _remove_cache_artifact()

    async def _verify_current_marker(self):
        token = evaluator._PROXY_ORIGIN_MARKER.set(self.marker)
        try:
            return await evaluator.ProxyStrategy().verify(
                None, "127.0.0.1", self.proxy_port, [], evaluator.REQUEST_TIMEOUT_SECONDS
            )
        finally:
            evaluator._PROXY_ORIGIN_MARKER.reset(token)

    async def test_forwards_origin_marker_and_caches_in_tempdir(self) -> None:
        outcome = await self._verify_current_marker()
        self.assertEqual(outcome.status, "passed", outcome.checks[0].detail)

        cache_file = _cache_path()
        self.assertTrue(cache_file.exists(), f"参考答案的缓存应落在临时目录：{cache_file}")
        self.assertEqual(cache_file.read_bytes(), self.marker.encode())
        self.assertFalse(
            (self.cwd / "WEB").exists(), "缓存不能写在只读的工作目录（沙箱里这里会 OSError）"
        )

    async def test_forged_cache_with_public_marker_fails(self) -> None:
        """把伪造的缓存放到临时目录里（带公开的固定标记），必须判不过。

        这条同时是缓存位置的回归：缓存路径若不在临时目录，伪造的文件命不中，
        代理会真的去转发、拿到本次标记而“通过”，断言立刻失败。
        """
        cache_file = _cache_path()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(FIXED_MARKER.encode())

        served = await _raw_proxy_request(self.proxy_port)
        # 反向对照：伪造的内容确实被原样吐回来了，所以**旧判据**（找固定标记）会判通过
        # —— 这正是被堵掉的后门；新判据找本次随机标记，于是判不过。
        self.assertIn(FIXED_MARKER.encode(), served)
        self.assertNotIn(self.marker.encode(), served)

        outcome = await self._verify_current_marker()
        self.assertEqual(outcome.status, "failed", "伪造的缓存不能算通过")

    def test_sources_do_not_use_relative_cache_path(self) -> None:
        """静态兜底：starter / 参考答案里不能再出现相对路径 "WEB/" + ...。"""
        for path in (STARTER, SOLUTION):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn('"WEB/" +', source, f"{path.name} 还在用工作目录相对路径")
            self.assertNotIn('open("WEB/', source, f"{path.name} 还在从相对路径读缓存")
            self.assertIn("tempfile.gettempdir()", source, f"{path.name} 应使用临时目录")


async def _raw_proxy_request(port: int, timeout: float = 15.0) -> bytes:
    """直接向代理发一次教材格式的请求，读到连接结束为止（不做任何标记校验）。"""
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        writer.write(b"GET /127.0.0.1/hello.html HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        await writer.drain()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        buffered = b""
        while loop.time() < deadline:
            try:
                chunk = await asyncio.wait_for(reader.read(8192), timeout=deadline - loop.time())
            except asyncio.TimeoutError:
                break
            if not chunk:
                break
            buffered += chunk
        return buffered
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


async def _wait_port(port: int, timeout: float = 20.0) -> None:
    """等 127.0.0.1:<port> 能连上（真进程启动要时间，不能只 sleep）。"""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
        except OSError:
            if loop.time() >= deadline:
                raise AssertionError(f"端口 {port} 在 {timeout}s 内没有就绪")
            await asyncio.sleep(0.1)
            continue
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
        return


if __name__ == "__main__":
    unittest.main()
