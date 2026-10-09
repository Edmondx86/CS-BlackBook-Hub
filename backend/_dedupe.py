"""同一张卡内只保留术语的首次标记：重复出现的 `X` 去掉反引号，变回纯文本。

围栏代码块与 <strong>/加粗 一律不动。

用法：python _dedupe.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path("../frontend/src/content/flashcards")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`([^`\n]+)`")
APPLY = "--apply" in sys.argv

removed_detail = []
total_removed = 0
changed_files = 0
kept_total = 0

for f in sorted(ROOT.glob("*.md")):
    src = f.read_text(encoding="utf-8")
    seen: set[str] = set()
    removed = 0
    kept = 0

    def process(seg: str) -> str:
        global removed, kept

        def repl(m):
            nonlocal removed, kept
            body = m.group(1).strip()
            if body in seen:
                removed += 1
                removed_detail.append((f.name, body))
                return m.group(1)  # 去掉反引号
            seen.add(body)
            kept += 1
            return m.group(0)

        return INLINE_CODE.sub(repl, seg)

    out, pos = [], 0
    for m in FENCE.finditer(src):
        out.append(process(src[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(process(src[pos:]))
    new = "".join(out)

    if removed:
        changed_files += 1
        total_removed += removed
    kept_total += kept
    if APPLY and new != src:
        f.write_text(new, encoding="utf-8")

print(f"  {'已应用' if APPLY else '试运行'}：{changed_files} 个文件")
print(f"  去掉的重复标记: {total_removed}")
print(f"  保留的首次标记: {kept_total}")
print()
print("  —— 被判定为重复、去掉标记的（按出现次数排序）——")
from collections import Counter

for body, n in Counter(b for _, b in removed_detail).most_common(18):
    print(f"    {body[:34]:<36} x{n}")
