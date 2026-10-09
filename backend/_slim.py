"""降低 flashcards 的标记密度：行内代码只保留「纯 ASCII 的英文标识符/协议名/公式」。

含中文的 `...` 一律去掉反引号，变回纯文本；<strong> 与 **加粗** 原样保留。

用法：python _slim.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path("../frontend/src/content/flashcards")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`([^`\n]+)`")
CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")
APPLY = "--apply" in sys.argv

kept, dropped, formula = [], [], []
formula_re = re.compile(r"[=<>]|\(\)")


def is_cjk(s: str) -> bool:
    return bool(CJK.search(s))


def process_segment(seg: str) -> str:
    def repl(m):
        body = m.group(1)
        if not is_cjk(body):
            kept.append(body.strip())
            return m.group(0)
        dropped.append(body.strip())
        if formula_re.search(body):
            formula.append(body.strip())
        return body  # 去掉反引号

    return INLINE_CODE.sub(repl, seg)


changed_files = 0
for f in sorted(ROOT.glob("*.md")):
    src = f.read_text(encoding="utf-8")
    out, pos = [], 0
    for m in FENCE.finditer(src):
        out.append(process_segment(src[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(process_segment(src[pos:]))
    new = "".join(out)
    if new != src:
        changed_files += 1
        if APPLY:
            f.write_text(new, encoding="utf-8")

print(f"  {'已应用' if APPLY else '试运行'}：{changed_files} 个文件")
print(f"  保留的 ASCII 标记: {len(kept)}")
print(f"  取消标记的中文术语: {len(dropped)}")
print()
print("  —— 保留的 ASCII 标记抽样 30 个 ——")
for k in sorted(set(kept))[:30]:
    print("    " + k)
print(f"    （去重后 {len(set(kept))} 种）")
print()
if formula:
    print("  —— 含中文但像公式的（这些被一并取消标记，若不合适可补回）——")
    for x in sorted(set(formula))[:14]:
        print("    " + x)
else:
    print("  含中文的标记里没有公式形态的")
