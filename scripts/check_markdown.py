#!/usr/bin/env python3
"""Markdown 结构闸：围栏必须成对，且正文里不得裸写围栏串。

Why：Docsify 用 marked 解析，正文中出现的三个及以上反引号会被当作代码块起点，
后果是该行之后的整页被吞成裸文本（实测：`## 下一轮` 变成正文可见的裸标记）。
这类破损不报错、不产生死链，只有渲染后才看得见，所以在提交前用文本闸拦住。

用法：python3 scripts/check_markdown.py            # 校验
      python3 scripts/check_markdown.py --count    # 只报覆盖量
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FENCE = re.compile(r"^ {,3}(`{3,}|~{3,})(\S*)\s*$")
BARE = re.compile(r"`{3,}|~{3,}")

# 根目录与 docs/ 各留一份的规范/元数据文件：必须逐字节相同。
# 实测教训（2026-09-24）：两份 BOOK_SPEC 与 STYLE_GUIDE 曾各自演化了半条规则，
# 结果同一本书里存在两个版本的配图规则，且都自称正确。
DUAL_COPY = ["BOOK_SPEC.md", "DIAGNOSIS.md", "FIGURE_LIST.md", "GLOSSARY.md", "STYLE_GUIDE.md"]


def dual_copy_problems():
    problems = []
    for name in DUAL_COPY:
        a, b = ROOT / name, DOCS / name
        if not a.exists() or not b.exists():
            problems.append(f"{name}: 双副本缺一份（根 {a.exists()} / docs {b.exists()}）")
        elif a.read_bytes() != b.read_bytes():
            delta = len(a.read_text().splitlines()) - len(b.read_text().splitlines())
            problems.append(f"{name}: 根副本与 docs 副本不一致（行数差 {delta:+}）→ 内容已各自演化")
    return problems


def files():
    return sorted(DOCS.rglob("*.md")) + sorted(ROOT.glob("*.md"))


def check(path):
    """返回 (问题列表, 代码块行数)。"""
    problems, stack, code_lines = [], [], 0
    for no, line in enumerate(path.read_text().splitlines(), 1):
        m = FENCE.match(line)
        if stack:
            code_lines += 1
            char, length = stack[-1]
            if m and m.group(1)[0] == char and len(m.group(1)) >= length and not m.group(2):
                stack.pop()
            continue
        if m:
            stack.append((m.group(1)[0], len(m.group(1))))
            continue
        hit = BARE.search(line)
        if hit:
            problems.append(
                f"{path.relative_to(ROOT)}:{no}: 正文裸写围栏串 {hit.group()!r}"
                f"（Docsify 会把后半页吞进代码块）→ {line.strip()[:48]}"
            )
    for char, length in stack:
        problems.append(f"{path.relative_to(ROOT)}: 未闭合围栏：{char * length}")
    return problems, code_lines


def main():
    problems, total_code, fence_lines = [], 0, 0
    for path in files():
        text = path.read_text()
        fence_lines += len([l for l in text.splitlines() if FENCE.match(l)])
        p, code = check(path)
        problems += p
        total_code += code
    problems += dual_copy_problems()
    if "--count" in sys.argv:
        print(f"{len(files())} 个 md 文件 / {fence_lines} 行围栏标记 / {total_code} 行代码块内容。")
        return 0
    if problems:
        print("不通过：")
        for p in problems:
            print(f"  - {p}")
        print(f"共 {len(problems)} 处结构问题。")
        return 1
    print(
        f"{len(files())} 个 md 文件：围栏全部成对，正文无裸围栏串；"
        f"{len(DUAL_COPY)} 对根/docs 副本逐字节一致。结构闸通过。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
