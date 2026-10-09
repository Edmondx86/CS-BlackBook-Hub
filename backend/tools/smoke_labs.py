"""把所有 Socket 练习用参考答案跑一遍，报告哪些在生产环境真的能过。

为什么需要它：判题有不少**只在 Linux 上才暴露**的问题（bwrap 参数、POSIX preexec、
端口被 nginx 占用、raw socket 权限……），Windows 本机全测不出来。上线前跑一遍这个，
比一个个点过去撞要快得多。

用法（在服务器上，后端已启动）：

    cd /srv/cs-blackbook/backend
    ./venv/bin/python tools/smoke_labs.py                 # 默认 http://127.0.0.1:8000
    ./venv/bin/python tools/smoke_labs.py http://127.0.0.1:8000

注意：判题接口有按 IP 限流（12 次/60 秒，见 app/services/guard.py）。
本脚本串行执行，正常不会触发；若看到 HTTP 429，等 60 秒再跑。
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 180.0

# 输出永不因编码而崩：某些终端/服务器 locale 不是 UTF-8（GBK、POSIX/C…），
# 直接 print 非 ASCII 字符会抛 UnicodeEncodeError 把整个脚本打断。
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def post_json(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def collect_targets() -> list[tuple[str, str, str]]:
    """从 /chapters 里找出所有 Socket 练习，不写死 lab id。"""
    targets: list[tuple[str, str, str]] = []
    for chapter in get_json(f"{BASE}/api/v1/chapters"):
        for ex in chapter.get("socket_exercises") or []:
            targets.append((chapter["id"], ex["id"], ex.get("title") or ex["id"]))
    return targets


def main() -> int:
    targets = collect_targets()
    print(f"发现 {len(targets)} 个 Socket 练习，逐个用参考答案判题 …\n")
    if not targets:
        print("一个都没发现 —— 检查后端是否正常返回 /api/v1/chapters")
        return 2

    passed: list[str] = []
    failed: list[tuple[str, str]] = []

    for chapter_id, lab_id, title in targets:
        try:
            lab = get_json(f"{BASE}/api/v1/chapters/{chapter_id}/labs/{lab_id}")
        except Exception as exc:  # noqa: BLE001
            failed.append((lab_id, f"取 Lab 失败：{type(exc).__name__}: {exc}"))
            print(f"  {lab_id:<20} [FAIL] 取 Lab 失败：{exc}")
            continue

        code = lab.get("reference_code") or ""
        if not code:
            failed.append((lab_id, "没有 reference_code"))
            print(f"  {lab_id:<20} [FAIL] 没有 reference_code，跳过")
            continue

        started = time.monotonic()
        try:
            result = post_json(
                f"{BASE}/api/v1/chapters/{chapter_id}/labs/{lab_id}/run", {"code": code}
            )
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:160]
            except Exception:  # noqa: BLE001
                pass
            failed.append((lab_id, f"HTTP {exc.code} {body}"))
            print(f"  {lab_id:<20} [FAIL] HTTP {exc.code}  {body}")
            continue
        except Exception as exc:  # noqa: BLE001
            failed.append((lab_id, f"{type(exc).__name__}: {exc}"))
            print(f"  {lab_id:<20} [FAIL] {type(exc).__name__}: {exc}")
            continue

        elapsed = time.monotonic() - started
        if result.get("passed"):
            passed.append(lab_id)
            print(f"  {lab_id:<20} [OK]   passed   ({elapsed:.1f}s)")
        else:
            bad = next((c for c in result.get("checks") or [] if not c.get("passed")), None)
            why = (bad or {}).get("detail") or ""
            if not why:
                why = json.dumps(result, ensure_ascii=False)[:180]
            failed.append((lab_id, str(why)))
            print(f"  {lab_id:<20} [FAIL] failed   ({elapsed:.1f}s)  {str(why)[:110]}")

    print(f"\n通过 {len(passed)} / 失败 {len(failed)}")
    if failed:
        print("\n失败明细：")
        for lab_id, why in failed:
            print(f"  {lab_id:<20} {why}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
