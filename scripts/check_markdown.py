#!/usr/bin/env python3
"""Markdown 结构闸：围栏成对、正文不裸写围栏串、HTML 块后必须空行隔开、
相对 HEAD 不丢小节标题、小节子树不得为空、同文件小节编号不得撞号、
根/docs 双副本逐字节一致。

Why：Docsify 用 marked 解析，两类破损都不报错、不产生死链，只有渲染后才看得见：
· 正文里出现三个及以上反引号会被当作代码块起点，该行之后的整页被吞成裸文本
  （实测：`## 下一轮` 变成正文可见的裸标记）；
· `<div>` 起的 HTML 块要遇到空行才结束，紧跟标签行的 `---`/`#`/表格会被当字面量
  渲染（实测：docs/README.md 总览页上原样显示出一条 `---`）。
第三类破损是**空小节**：标题在、内容不在（实测：第 28 章「回滚决策矩阵」只有标题，
而附录 A 的提示词要读者"基于"它干活）。它不破结构也不破链接，只有人在读。
第四类破损是**同文件撞号**：两条标题共用一个 `N.Nx` 编号（实测：第 23 章曾同时挂着
两个 `23.4b`、第 24 章挂着两个 `24.9`）。Docsify 按标题文本生成锚点，撞号的两节
各引用一次就不破链——破的是书：编号从此不能唯一指认一节，改号也没有机器读者会拦。
所以在提交前用文本闸拦住。

用法：python3 scripts/check_markdown.py            # 校验
      python3 scripts/check_markdown.py --count    # 只报覆盖量
      python3 scripts/check_markdown.py --selftest # 标题闸 6 条 + 空节闸 4 条 + 撞号闸 5 条已知答案自检
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


# ---------------------------------------------------------------- 撞号闸
# 为什么要加这一条（2026-09-26 量产命中面）：连续两轮在人工扩写里撞出同号小节——
# 第 23 章两个 `23.4b`（托管形态与版本化的实现面各占一个，改号后登记于 DIAGNOSIS），
# 本轮量命中面时又抓到第 24 章两个 `24.9`（检查清单与遗留问题）。全书文本引用靠
# 「见 N.Nx」指认小节，而 Docsify 的锚点按标题文本生成：撞号不破任何一条现有闸，
# 只让编号失去唯一指认能力——下一轮引用"24.9"时没人知道指哪节，改号也没机器读者拦。
# 口径：只认「至少一个点、可带字母后缀」的纯数字编号（`26.5f`、`3.5b`），按整串相等
# 分组，同文件 ≥2 条即报；围栏内不算（与空节闸/标题闸共用 heading_kinds 口径）；
# 范围收在手稿目录——附录与站点页不靠 N.Nx 做文本引用，闸不该替它们立法。
# 命中面基线：54 个手稿文件，修掉 24.9 后为 0——本闸立在一个已修好的缺陷上，不立空头闸。
SID_HEAD = re.compile(r"^ {,3}#{1,6}\s+(\d+(?:\.\d+)+[a-z]?)(?![0-9a-z])")


def sid_collisions(text):
    """返回 [(编号, [(行号, 标题原文), ...]), ...]：同文件内出现 ≥2 次的 N.Nx 小节编号。"""
    lines = text.splitlines()
    kinds = heading_kinds(lines)
    groups = {}
    for i, line in enumerate(lines, 1):
        if kinds[i - 1] != "head":
            continue
        m = SID_HEAD.match(line)
        if m:
            groups.setdefault(m.group(1), []).append((i, line.strip()))
    return [(k, v) for k, v in sorted(groups.items()) if len(v) > 1]


def sid_collision_problems():
    problems, checked = [], 0
    for path in sorted((DOCS / "manuscript").glob("*.md")):
        checked += 1
        for sid, hits in sid_collisions(path.read_text()):
            where = "、".join(f"{no} 行「{t[:32]}」" for no, t in hits)
            problems.append(f"{path.relative_to(ROOT)}: 小节编号 {sid} 撞号（{where}）"
                            f"→ 编号要能唯一指认一节，给后出现的让它顺延")
    if checked < 50:
        raise SystemExit(f"撞号闸只扫到 {checked} 个手稿文件（<50）——枚举口径塌了，这条闸不能算通过")
    return problems, checked


SID_SELFTEST = [
    ("同文件两条 `24.9`（本轮实测形状）→ 必须报 1 组",
     "## 24.9 检查清单\n\n正文。\n\n## 24.9 遗留问题\n\n正文。\n", 1),
    ("三级与带后缀是不同编号（3.5 / 3.5b）→ 必须不报",
     "## 3.5 契约\n\n正文。\n\n## 3.5b 操作步骤\n\n正文。\n", 0),
    ("围栏内照抄的同号标题不进账：块外仅一条、块内同串两条 → 必须不报（不感知围栏会报 1 组）",
     "## 26.5f 决策表\n\n正文。\n\n```markdown\n## 26.5f 示例块里照抄的标题\n\n## 26.5f 块里再来一条\n```\n", 0),
    ("`### 3. 列表式小标题`不是小节编号 → 必须不报",
     "## 28.4 产出物\n\n### 1. 清单\n\n正文。\n\n### 2. 矩阵\n\n正文。\n\n### 3. 记录\n\n正文。\n", 0),
    ("四段编号各一条（25.10 / 25.11）→ 必须不报",
     "## 25.10 检查清单\n\n正文。\n\n## 25.11 遗留问题\n\n正文。\n", 0),
]


def sid_selftest():
    bad = 0
    for name, text, want in SID_SELFTEST:
        got = len(sid_collisions(text))
        flag = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  [{flag}] {name}：报 {got} 组（应为 {want}）")
    if bad:
        raise SystemExit(f"撞号闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：整串相等才算撞号，围栏内与 `### 1.` 列表头不进账；"
          "排除支各带同段正对照，不靠整段读空蒙混过关。")
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
    """取正文所有标题，剥掉编号（J.6→J.9 这种重编号不该被判成丢失）。

    口径与空节闸共用 `heading_kinds`：**围栏里的行不是标题**。这条不是顺手做的优雅，
    是 2026-09-25 的一次假红逼出来的——`FIGURE_LIST.md` 的 ```bash 命令块里有五行
    `# 口径边界……`  shell 注释，旧口径把它们记成小节，于是改一次注释文字就报五条
    "HEAD 里的小节查无此人"。判据把"编辑事故"和"我在改代码示例"混成同一类，
    报红就失去了指认能力；而空节闸早就用围栏感知口径了，同一文件里两把尺子不一样。
    """
    lines = text.splitlines()
    kinds = heading_kinds(lines)
    out = []
    for line, kind in zip(lines, kinds):
        if kind != "head":
            continue
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
    """已知答案 fixture：删除必须报、改名必须不报、原样必须 0、围栏里的 `#` 不是标题。"""
    base = "# 标题\n\n## 3.3 AI 使用规模（治理前 vs 治理后）\n\n## J.9 与治理章的映射\n"
    fenced = ("## 复核命令\n\n```bash\npython3 x.py\n# 口径边界：这是 shell 注释不是小节\n```\n")
    cases = [
        ("删掉一节 → 必须报 1 条", base, base.replace("## 3.3 AI 使用规模（治理前 vs 治理后）\n\n", ""), 1),
        ("改标题名 → 必须不报", base, base.replace("与治理章的映射", "与治理章的映射与上下游"), 0),
        ("原样不动 → 必须 0 条", base, base, 0),
        ("重编号（J.9→J.11）→ 必须不报", base, base.replace("## J.9", "## J.11"), 0),
        # 围栏感知两条各自带基线：改围栏里的注释必须不报，同一段里围栏外的小节被吃掉必须报。
        # 对照放在**同一份文本**里做，否则"围栏里不报"可能只是因为整段都没被读。
        ("围栏里的 shell 注释改了措辞 → 必须不报", fenced,
         fenced.replace("# 口径边界：这是 shell 注释不是小节", "# 口径边界：换成五行新说明"), 0),
        ("围栏外的真小节被吃掉 → 必须报 1 条", fenced,
         fenced.replace("## 复核命令\n\n", ""), 1),
    ]
    bad = 0
    for name, b, cur, want in cases:
        got = len(lost_headings(b, cur))
        flag = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  [{flag}] {name}：报 {got} 条（应为 {want}）")
    if bad:
        raise SystemExit(f"标题闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：删除会报、改名与重编号不报、围栏里的 `#` 不当小节；判据的排除集没有被自己放宽。")
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
        print("[撞号闸] 同文件小节编号不得撞号")
        rc3 = sid_selftest()
        return rc1 or rc2 or rc3
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
    sid_problems, sid_scanned = sid_collision_problems()
    problems += sid_problems
    if "--count" in sys.argv:
        print(f"{len(files())} 个 md 文件 / {fence_lines} 行围栏标记 / {total_code} 行代码块内容"
              f" / {baselined} 个文件有 HEAD 基线可对标题 / 空节闸扫 {scanned} 个文件"
              f" / 撞号闸扫 {sid_scanned} 个手稿文件。")
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
        f"{baselined} 个文件的相对 HEAD 小节标题零丢失；{scanned} 个文件无空小节；"
        f"{sid_scanned} 个手稿文件无小节编号撞号。结构闸通过。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
