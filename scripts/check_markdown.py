#!/usr/bin/env python3
"""Markdown 结构闸：围栏成对、正文不裸写围栏串、HTML 块后必须空行隔开、
相对 HEAD 不丢小节标题、小节子树不得为空、根/docs 双副本逐字节一致。

Why：Docsify 用 marked 解析，两类破损都不报错、不产生死链，只有渲染后才看得见：
· 正文里出现三个及以上反引号会被当作代码块起点，该行之后的整页被吞成裸文本
  （实测：`## 下一轮` 变成正文可见的裸标记）；
· `<div>` 起的 HTML 块要遇到空行才结束，紧跟标签行的 `---`/`#`/表格会被当字面量
  渲染（实测：docs/README.md 总览页上原样显示出一条 `---`）。
第三类破损是**空小节**：标题在、内容不在（实测：第 28 章「回滚决策矩阵」只有标题，
而附录 A 的提示词要读者"基于"它干活）。它不破结构也不破链接，只有人在读。
所以在提交前用文本闸拦住。

用法：python3 scripts/check_markdown.py            # 校验
      python3 scripts/check_markdown.py --count    # 只报覆盖量
      python3 scripts/check_markdown.py --selftest # 标题闸 4 条 + 空节闸 4 条已知答案自检
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FENCE = re.compile(r"^ {,3}(`{3,}|~{3,})(\S*)\s*$")
BARE = re.compile(r"`{3,}|~{3,}")
# HTML 块里的行不会被当作 markdown 解析，块尾要空行才结束
HTML_LINE = re.compile(r"^ {,3}</?[a-zA-Z][^>]*>\s*$")
SWALLOW = re.compile(r"^ {,3}(?:-{3,}|\*{3,}|_{3,}|#{1,6}\s|>\s|\|.*\||[-*+]\s|\d+\.\s)")

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


# ---------------------------------------------------------------- 空节闸
# 为什么要加这一条（2026-09-25 实测）：第 28 章的产出物写着"可落地的四件"，第三件是
# `### 3. 回滚决策矩阵（见 28.4）`——标题下面**一行都没有**。前两条判据（围栏成对、
# 相对 HEAD 不丢标题）都接不住这种破损：它不破结构、不破链接，Docsify 渲染出来就是
# 一个光秃秃的标题。真正的代价在别处——附录 A 的 P-28-4-01 提示词写着"基于回滚决策
# 矩阵给建议"，读者和 AI 一起指向同一个空标题。
# 口径：**子树**（本标题到下一个同级或更浅标题之间）不含一行正文才算空。分组标题
# （## 下面只有 ### 子节）因此天然豁免，附录 A 那种"标题 + 一段围栏"也不算空——
# 围栏是给读者的内容。全站实测：补掉那一处之后命中 0 处。
FENCE_MARK = re.compile(r"^ {,3}(`{3,}|~{3,})(\S*)\s*$")
HEAD_LINE = re.compile(r"^ {,3}(#{1,6})\s+")


def heading_kinds(lines):
    """逐行标类别：fence（围栏内或围栏标记行）/ head / text。"""
    kinds, stack = [], []
    for line in lines:
        m = FENCE_MARK.match(line)
        if stack:
            kinds.append("fence")
            if m and m.group(1)[0] == stack[-1][0] \
                    and len(m.group(1)) >= stack[-1][1] and not m.group(2):
                stack.pop()
            continue
        if m:
            stack.append((m.group(1)[0], len(m.group(1))))
            kinds.append("fence")
            continue
        kinds.append("head" if HEAD_LINE.match(line) else "text")
    return kinds


def empty_sections(text):
    """返回 (行号, 标题原文) 列表：子树里一行正文都没有的标题。"""
    lines = text.splitlines()
    kinds = heading_kinds(lines)
    heads = [(i, len(HEAD_LINE.match(l).group(1)))
             for i, l in enumerate(lines, 1) if kinds[i - 1] == "head"]
    out = []
    for n, (i, lv) in enumerate(heads):
        end = len(lines) + 1
        for j, lv2 in heads[n + 1:]:
            if lv2 <= lv:
                end = j
                break
        body = sum(len(lines[x - 1].strip()) for x in range(i + 1, end)
                   if kinds[x - 1] != "head")
        if body == 0:
            out.append((i, lines[i - 1].strip()))
    return out


def empty_section_problems():
    problems, checked = [], 0
    for path in files():
        checked += 1
        for no, title in empty_sections(path.read_text()):
            problems.append(f"{path.relative_to(ROOT)}:{no}: 小节「{title[:40]}」"
                            f"下面一行正文都没有（分组标题不算，这里连子节也没有）"
                            f"→ 要么补内容，要么删掉这个标题")
    if checked < 70:
        raise SystemExit(f"只扫到 {checked} 个 md（<70）——枚举口径塌了，这条闸不能算通过")
    return problems, checked


EMPTY_SELFTEST = [
    ("分组标题（## 下只有 ###）→ 必须不报",
     "## 1. 目的\n\n### 1.1 范围\n\n说清楚范围。\n", 0),
    ("标题 + 一段围栏（提示词卡）→ 必须不报",
     "### P-1 让 AI 自评\n\n```text\n照抄的提示词正文\n```\n", 0),
    ("真空节 → 必须报 1 条",
     "## 26.5 产出物\n\n### 1. 有内容的一节\n\n正文在此。\n\n### 2. 回滚决策矩阵（见 28.4）\n\n### 3. 又有内容\n\n正文也在此。\n", 1),
    ("文件末尾的空标题 → 必须报 1 条",
     "## 甲\n\n正文。\n\n## 乙（什么都没有）\n", 1),
]


def empty_section_selftest():
    bad = 0
    for name, text, want in EMPTY_SELFTEST:
        got = len(empty_sections(text))
        flag = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  [{flag}] {name}：报 {got} 条（应为 {want}）")
    if bad:
        raise SystemExit(f"空节闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：分组标题与「标题 + 一段围栏」都不报，真空节与末尾空标题必报。")
    return 0


# ---------------------------------------------------------------- 标题丢失闸
# 为什么要加这一条（2026-09-24 实测）：本轮用 Edit 改稿时**连着三次**把下一块的
# 头部一起吃掉了——ch27 少了一段围栏、ch26 少了 `## 21.5` 标题、ch05 少了 `## 3.3` 标题。
# 围栏那类由本闸原有判据接住；**标题被吃掉既不破围栏也不破链接**，只剩一张没有标题的
# 孤儿表格，Docsify 照渲染、链接照绿，读者却再也跳不到那一节。所以拿 HEAD 当基线对账。
# 允许改名（改名不算丢失：用"互相包含"匹配），只判"这一节整块查无此人"。
HEAD_MARK = re.compile(r"^ {,3}#{1,6}\s+(.*)$")
NUM_PREFIX = re.compile(
    r"^(?:第\s*[0-9一二三四五六七八九十百]+\s*[章部分篇]?|[0-9]+(?:\.[0-9]+)*[a-z]?"
    r"|[①-⑳]|[A-Z][.、][0-9]+|[A-Z]{1,4}-[0-9IVX]+)\s*[｜|:：.、\s]*", re.I)


def heading_titles(text):
    """取正文所有标题，剥掉编号（J.6→J.9 这种重编号不该被判成丢失）。"""
    out = []
    for line in text.splitlines():
        m = HEAD_MARK.match(line)
        if not m:
            continue
        t = NUM_PREFIX.sub("", m.group(1).replace("**", "").strip()).strip()
        out.append(t or m.group(1).strip())
    return out


def _survives(before, after):
    """精确命中，或一方包含另一方（≥6 字）⇒ 视为改名后仍在。"""
    if before in after:
        return True
    for t in after:
        shorter = min(len(before), len(t))
        if shorter >= 6 and (before in t or t in before):
            return True
    return False


def lost_headings(base_text, cur_text):
    """返回 base 里有、cur 里查无此人的标题（按重数比对）。"""
    b, c = Counter(heading_titles(base_text)), Counter(heading_titles(cur_text))
    return [t for t in b if not _survives(t, c)]


def heading_problems():
    import subprocess
    problems, baselined = [], 0
    for path in sorted(DOCS.rglob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{rel}"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            continue                      # 本轮新建的文件：没有基线，不参与比对
        baselined += 1
        for t in lost_headings(r.stdout, path.read_text()):
            problems.append(f"{rel}: HEAD 里的小节「{t}」在工作树查无此人"
                            f"（改名不算丢失）→ 多半是编辑时把下一块的头部一起吃掉了")
    if baselined < 60:
        raise SystemExit(f"只有 {baselined} 个文件取到 HEAD 基线（<60）——"
                         f"比对集近乎为空，这条闸不能算通过")
    return problems, baselined


def heading_selftest():
    """已知答案 fixture：删除必须报、改名必须不报、原样必须 0。"""
    base = "# 标题\n\n## 3.3 AI 使用规模（治理前 vs 治理后）\n\n## J.9 与治理章的映射\n"
    cases = [
        ("删掉一节 → 必须报 1 条", base.replace("## 3.3 AI 使用规模（治理前 vs 治理后）\n\n", ""), 1),
        ("改标题名 → 必须不报", base.replace("与治理章的映射", "与治理章的映射与上下游"), 0),
        ("原样不动 → 必须 0 条", base, 0),
        ("重编号（J.9→J.11）→ 必须不报", base.replace("## J.9", "## J.11"), 0),
    ]
    bad = 0
    for name, cur, want in cases:
        got = len(lost_headings(base, cur))
        flag = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  [{flag}] {name}：报 {got} 条（应为 {want}）")
    if bad:
        raise SystemExit(f"标题闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：删除会报、改名与重编号不报；判据的排除集没有被自己放宽。")
    return 0


def check(path):
    """返回 (问题列表, 代码块行数)。"""
    problems, stack, code_lines = [], [], 0
    lines = path.read_text().splitlines()
    for no, line in enumerate(lines, 1):
        prev = lines[no - 2] if no > 1 else ""
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
        # HTML 块（`<div>` 起）要到一个空行才结束：紧跟在标签行后的 markdown 语法
        # 会被当字面量渲染出去（实测 docs/README.md 的 `---` 原样显示在总览页上）。
        if SWALLOW.match(line) and HTML_LINE.match(prev):
            problems.append(
                f"{path.relative_to(ROOT)}:{no}: 上一行是 HTML 标签行、中间没有空行"
                f"→ Docsify 把 {line.strip()[:20]!r} 当字面量渲染"
            )
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
    if "--selftest" in sys.argv:
        print("[标题闸] 相对 HEAD 不丢小节")
        rc1 = heading_selftest()
        print("[空节闸] 小节子树不得为空")
        rc2 = empty_section_selftest()
        return rc1 or rc2
    problems, total_code, fence_lines = [], 0, 0
    for path in files():
        text = path.read_text()
        fence_lines += len([l for l in text.splitlines() if FENCE.match(l)])
        p, code = check(path)
        problems += p
        total_code += code
    problems += dual_copy_problems()
    empty_problems, scanned = empty_section_problems()
    problems += empty_problems
    head_problems, baselined = heading_problems()
    problems += head_problems
    if "--count" in sys.argv:
        print(f"{len(files())} 个 md 文件 / {fence_lines} 行围栏标记 / {total_code} 行代码块内容"
              f" / {baselined} 个文件有 HEAD 基线可对标题 / 空节闸扫 {scanned} 个文件。")
        return 0
    if problems:
        print("不通过：")
        for p in problems:
            print(f"  - {p}")
        print(f"共 {len(problems)} 处结构问题。")
        return 1
    print(
        f"{len(files())} 个 md 文件：围栏全部成对，正文无裸围栏串，"
        f"HTML 块后无未隔空的 markdown 语法；{len(DUAL_COPY)} 对根/docs 副本逐字节一致；"
        f"{baselined} 个文件的相对 HEAD 小节标题零丢失；{scanned} 个文件无空小节。"
        "结构闸通过。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
