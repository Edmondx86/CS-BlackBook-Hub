"""判题接口的公网防护：并发上限 + 按客户端限流 + 熔断开关。

公网部署下 ``POST /chapters/{id}/labs/{lab}/run`` 会执行访客提交的代码，必须防两件事：

1. **被当成免费算力**：刷接口跑自己的程序（挖矿、压测别人）；
2. **并发打满**：同时提交大量判题把后端进程和宿主机资源耗尽。

设计取舍
--------
- 纯进程内实现，不引入 Redis 等外部依赖：uvicorn 单 worker 时完全有效。
  若将来改成多 worker，每个 worker 各持一份计数，实际限额会放大到“限额 × worker 数”，
  届时要么按 worker 数下调限额，要么换成共享存储。
- 客户端 IP 取自 ``X-Forwarded-For``。**这只在“后端不直接对外暴露、仅由 nginx 反代”
  的前提下可信**（compose 已去掉后端的 ports 发布，只留 expose）。若后端能被直连，
  请求方可以伪造该头绕过限流。
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque

# —— 限额参数（可按需调整）——
MAX_CONCURRENT_RUNS = 4  # 同时进行的判题数；单次判题最长占用 EXEC_TIMEOUT_SECONDS 秒
RATE_WINDOW_SECONDS = 60.0  # 速率统计窗口
RATE_MAX_REQUESTS = 12  # 每个客户端在窗口内允许提交的判题次数
MAX_TRACKED_CLIENTS = 4096  # 记录上限，防止大量伪造 IP 撑爆内存


class JudgeBusy(RuntimeError):
    """并发判题数已达上限，请稍后重试。"""


class RateLimited(RuntimeError):
    """单个客户端提交过于频繁。"""


class JudgeDisabled(RuntimeError):
    """判题功能被运维临时关闭。"""


_lock = asyncio.Lock()
_running = 0
_hits: dict[str, deque[float]] = {}


def judge_enabled() -> bool:
    """熔断开关：``JUDGE_ENABLED=false`` 时直接拒绝所有判题请求（默认开启）。

    用途：公网被刷时不必重启/改代码，改环境变量重启即可止血。
    """
    return os.getenv("JUDGE_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def client_ip(forwarded_for: str | None, peer: str | None) -> str:
    """解析真实客户端 IP：优先取 ``X-Forwarded-For`` 的第一段，退回 socket 对端地址。"""
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return peer or "unknown"


def _evict_oldest(now: float) -> None:
    """丢掉最久没活动的记录，避免内存被伪造 IP 撑爆（不会整体清空，防止绕过限流）。"""
    stale = sorted(_hits.items(), key=lambda kv: kv[1][-1] if kv[1] else now)
    for key, _ in stale[: max(1, len(stale) // 2)]:
        _hits.pop(key, None)


async def enter_judge(key: str) -> None:
    """占用一个判题名额。

    :raises JudgeDisabled: 熔断开关已关闭判题
    :raises RateLimited: 该客户端在窗口内提交次数超限
    :raises JudgeBusy: 当前并发判题数已达上限
    """
    global _running
    if not judge_enabled():
        raise JudgeDisabled("判题功能暂时关闭，请稍后再试")

    async with _lock:
        now = time.monotonic()
        if len(_hits) >= MAX_TRACKED_CLIENTS:
            _evict_oldest(now)

        q = _hits.setdefault(key, deque())
        while q and now - q[0] > RATE_WINDOW_SECONDS:
            q.popleft()

        if len(q) >= RATE_MAX_REQUESTS:
            raise RateLimited(
                f"提交过于频繁：每 {int(RATE_WINDOW_SECONDS)} 秒最多 {RATE_MAX_REQUESTS} 次，请稍后再试"
            )
        if _running >= MAX_CONCURRENT_RUNS:
            raise JudgeBusy(f"当前判题任务已满（上限 {MAX_CONCURRENT_RUNS} 个），请稍后重试")

        q.append(now)
        _running += 1


def leave_judge() -> None:
    """释放判题名额（必须放在 ``finally`` 中调用，否则名额会泄漏）。"""
    global _running
    if _running > 0:
        _running -= 1


def stats() -> dict[str, int]:
    """当前占用情况，便于观测与排查。"""
    return {"running": _running, "tracked_clients": len(_hits)}
