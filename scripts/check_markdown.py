#!/usr/bin/env python3
"""Markdown 结构闸：围栏成对、正文不裸写围栏串、HTML 块后必须空行隔开、
相对 HEAD 不丢小节标题、小节子树不得为空、同文件小节编号不得撞号、
复跑命令块与守卫脚本全集相等、正文不写裸文件路径、手稿正文不引用源码行号、
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
第五类不是渲染破损，是**登记破损**：`FIGURE_LIST.md` 的复跑命令块是全书守卫的名册，
它抄自磁盘上的 `scripts/check_*.py`；新守卫没登记上就永远没有读者，删掉的守卫留在名册上
就成了一条承诺了却没人执行的命令。判据按集合相等，条数不写进任何文案（见「守卫清单闸」）。
第六类是**引用破损**：正文里写着 `./chNN-….md` 这样的裸文件路径——它不是链接（第七条
`check_links.py` 在 DOM 里找 <a>，找不到它），也不是未落地的语法（第九条泄漏闸管的是星号
反引号，路径本身被规规矩矩渲染出来了）。全站量到 12 处并已转成真链接（见「正文裸路径闸」）。
第七类也是**引用破损**，但破的是可对账性：正文写 `第 310 行` 这种源码行号。页面上没有一列
数字可对照，被引文件增删一行引用就集体漂移；本书的锚是小节号、表行汉字序数、图号，三者都在
渲染面上可见（见「源文行号引用闸」）。
所以在提交前用文本闸拦住。

用法：python3 scripts/check_markdown.py            # 校验
      python3 scripts/check_markdown.py --count    # 只报覆盖量
      python3 scripts/check_markdown.py --selftest # 标题闸＋空节闸＋撞号闸＋守卫清单闸＋裸路径闸＋源文行号闸；每闸条数由这条命令自己打印
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


# ---------------------------------------------------------------- 守卫清单闸
# 为什么要加这一条（2026-09-26 量命中面之后立的）：第 25 章那轮把「计数只有一个宿主」
# 用派生收口之后，还剩一个没人量过的同类抄件——`FIGURE_LIST.md` 末尾那条「复跑命令」块
# 逐条列出了全书的守卫。守卫本身是磁盘上的 `scripts/check_*.py`，清单是它的手抄名册：
# 第十三轮加进第十三条守卫而忘了登记，这块清单不会破任何现有判据（围栏成对、双副本一致、
# 小节不撞号全都照绿），而新守卫就此没有读者——它跑不跑全看有没有人记得它存在。
# 比这更坏的是反向：清单里留着一行已删守卫的命令，下轮照抄就等于承诺了一条不存在的闸。
# 判据按集合相等做（不是子集、不是计数）：少了报「没登记」，多了报「幽灵」，
# 条数不写进任何文案——所以这条闸不需要维护它自己的抄件。
# 口径只认命令行的行首形状 `python3 scripts/check_*.py`：散文里提到脚本名不算登记
# （否则正文任何举例都会变成假阳），而重复列同一脚本不报（集合语义，判据不罚罗嗦）。
GUARD_CMD = re.compile(r"^\s*python3 scripts/(check_[a-z_]+\.py)")
GUARD_LIST_REL = "FIGURE_LIST.md"


def guard_cmd_names(text):
    """从清单文本里取出「命令行形态」出现的守卫脚本名（散文提及不算）。"""
    return {m.group(1) for line in text.splitlines() if (m := GUARD_CMD.match(line))}


def guard_index_problems(listed, disk):
    """纯函数：名册集合与磁盘集合的差集判定。两边可注入，自检才量得到比较本身。"""
    problems = []
    for name in sorted(disk - listed):
        problems.append(f"{GUARD_LIST_REL}: 守卫 {name} 在磁盘上存在，但复跑命令块里没有它"
                        f"→ 新闸没有登记，等于没有读者")
    for name in sorted(listed - disk):
        problems.append(f"{GUARD_LIST_REL}: 复跑命令块列了 {name}，而 scripts/ 里没有这个脚本"
                        f"→ 要么删掉这行幽灵命令，要么把守卫补回来")
    return problems


def guard_index_problems_real():
    path = ROOT / GUARD_LIST_REL
    if not path.is_file():
        raise SystemExit(f"守卫清单闸取不到 {GUARD_LIST_REL}——判据够不到名册，不算通过")
    listed = guard_cmd_names(path.read_text())
    disk = {p.name for p in sorted((ROOT / "scripts").glob("check_*.py")) if p.is_file()}
    # 两侧各自要有量：任一侧空掉都说明枚举口径塌了。空名册配上空磁盘会让本闸永远报绿，
    # 那正是本闸要抓的「新守卫静默消失」的形状，不能由它自己表演一遍。
    if len(disk) < 10:
        raise SystemExit(f"守卫清单闸只枚举到 {len(disk)} 个 scripts/check_*.py（<10）"
                         f"——枚举口径塌了，这条闸不能算通过")
    if not listed:
        raise SystemExit("守卫清单闸在名册里一条命令都没匹配到——行首口径坏了，不算通过")
    return guard_index_problems(listed, disk), len(listed), len(disk)


GUARD_SELFTEST = [
    ("原样两边相等 → 必须 0 条",
     {"check_a.py", "check_b.py"}, {"check_a.py", "check_b.py"}, 0),
    ("磁盘上多一条没登记的守卫（本闸要抓的形状）→ 必须报 1 条",
     {"check_a.py"}, {"check_a.py", "check_b.py"}, 1),
    ("名册里留着一行已删守卫的命令 → 必须报 1 条",
     {"check_a.py", "check_ghost.py"}, {"check_a.py"}, 1),
    ("两边同时各缺一半 → 必须报 2 条（少登记与幽灵各自独立判，不互相抵掉）",
     {"check_a.py"}, {"check_b.py"}, 2),
    ("两边同名的不同守卫各一条，纯改名 → 必须报 2 条（不靠字符串相似度放宽）",
     {"check_mobile.py"}, {"check_narrow.py"}, 2),
]


def guard_index_selftest():
    bad = 0
    for name, listed, disk, want in GUARD_SELFTEST:
        got = len(guard_index_problems(set(listed), set(disk)))
        flag = "✔" if got == want else "✘"
        if got != want:
            bad += 1
        print(f"  [{flag}] {name}：报 {got} 条（应为 {want}）")
    # 行首口径的两支判别：散文里出现同名脚本不进账（否则正文举例全被报成登记），
    # 同一命令重复列两行只算一条（集合语义，判据不罚罗嗦）。
    prose = "见 `check_b.py` 的判据说明。\npython3 scripts/check_a.py --selftest\n"
    dup = "python3 scripts/check_a.py\npython3 scripts/check_a.py --selftest\n"
    for label, text, want in (("散文提及不算登记", prose, {"check_a.py"}),
                              ("重复列同一守卫只算一条", dup, {"check_a.py"})):
        got = guard_cmd_names(text)
        if got == want:
            print(f"  [✔] {label}：实取 {sorted(got)}")
        else:
            bad += 1
            print(f"  [✘] {label}：实取 {sorted(got)}（应为 {sorted(want)}）")
    if bad:
        raise SystemExit(f"守卫清单闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：差集两侧各自报，集合语义不罚罗嗦，行首口径把举例挡在登记之外。")
    return 0


# ---------------------------------------------------------------- 正文裸路径闸
# 为什么要加这一条（2026-09-26 实测）：正文里写着 `./ch23-第18章-高并发流量.md` 这样的
# 裸文件路径，源码看着像一句引用，渲染出来是一串文件系统路径。它**两头都不落**：不是链接
# （第七条 `check_links.py` 逐条发 HTTP，DOM 里没有 <a> 就看不见它），也不破结构（本闸
# 原有判据对着它全绿、第九条泄漏闸也不管——星号反引号都落地了，落地的是一串路径）。
# 全站量到 12 处，其中一处指向**不存在的文件名**（第 18 章的真名是
# `ch23-第18章-亿级流量.md`），而那一句旁边还写着"以文件名实际链接为准"——一句要人来
# 兜的口径，正是机检该接管的地方。
# 口径：只认**围栏外、且不在 `](…)` 链接目标位**的 `./xxx.md`。排除集三条各由一支真实
# 形状撑腰，缺一条就误伤全书：`](` 之后是合法链接目标（全书每一条真链接都走这一支）；`../` 开头是跨目录
# 合法链接（`ch01` 指向 `../public-evidence.md` 两处）；围栏内是代码内容（第 9 章的 CI
# YAML 注释里就有一条）。行内代码里的裸路径**照报**——第 19 章那三处就是反引号包着的。
RAW_PATH = re.compile(r"(?<![.\w/(])\./[^\s）)、，。；`|]+\.md")


def raw_path_hits(text):
    """返回 [(行号, 命中串), …]。口径＝围栏外。纯函数、可注入（真产物与桩件走同一条判据）。"""
    lines = text.splitlines()
    kinds = heading_kinds(lines)
    out = []
    for i, (line, kind) in enumerate(zip(lines, kinds), 1):
        if kind == "fence":
            continue
        m = RAW_PATH.search(line)
        if m:
            out.append((i, m.group()))
    return out


def raw_path_problems():
    """返回 (问题列表, 扫描文件数, 命中数)。"""
    problems, scanned, hits = [], 0, 0
    for path in files():
        scanned += 1
        for no, s in raw_path_hits(path.read_text()):
            hits += 1
            problems.append(
                f"{path.relative_to(ROOT)}:{no}: 正文裸写文件路径 {s!r} → 页面上是一串路径、"
                f"不是链接（`check_links.py` 看不见它）→ 写成 [第 N 章]({s})"
            )
    if scanned == 0:
        raise SystemExit("正文裸路径闸一个 md 文件都没枚举到——枚举口径塌了，这条闸不能算通过")
    return problems, scanned, hits


RAW_SELFTEST = [
    ("链接目标位不报（全站真链接都走这一支）", "见[第 2 章](./ch07-第2章-人在回路.md)。\n", 0),
    ("跨目录链接 `../` 不报", "见[公开证据档案](../public-evidence.md)。\n", 0),
    ("正文裸路径报（第 27 章 174 行的形状）",
     "（这条多端现实归第 17 章 ./ch22-第17章-多端BFF.md 管）。\n", 1),
    ("行内代码包着的裸路径照报（第 19 章那三处的形状）",
     "审批链的平台侧治理在第 2 章（`./ch07-第2章-人在回路.md`）。\n", 1),
    ("围栏内是代码内容，不报", "```bash\ngrep -rn ./ch07-第2章-人在回路.md docs/\n```\n", 0),
    ("链接文字里带同名文件名，不报", "| 数字 | 以 [`ch05-数字清单.md`](./ch05-数字清单.md) 为准 |\n", 0),
]


def raw_path_selftest():
    bad = 0
    for name, text, want in RAW_SELFTEST:
        got = len(raw_path_hits(text))
        if got != want:
            bad += 1
            print(f"  [✘] {name}：命中 {got} 条（应为 {want}）")
        else:
            print(f"  [✔] {name}：命中 {got} 条")
    if bad:
        raise SystemExit(f"正文裸路径闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：真产物形状必报，三种合法写法（链接目标、`../`、围栏内）各有一支假阳对照。")
    return 0


# ---------------------------------------------------------------- 源文行号引用闸
# 为什么要加这一条：本轮一份交稿物在三个新小节里写了 **214 处** `第 NNN 行` 式引用。
# 这个读数量在交稿字节上，那些字节随后被本轮改写覆盖，**今天不可复跑**（账记在 DIAGNOSIS
# 第十二波）；仓库里可复跑的是它的两面：HEAD 那三个文件各 **0 处**，而 HEAD 的第 22 章有
# **1 处** `第 310 行`——那一处经核对是指对的，这正是本闸要拦的东西：行号可以当场对，
# 但它对读者不可见、对被引文件的下一次增删毫无抵抗力。这种写法有三重坏：
# · **读者看不见行号**——Docsify 渲染的是段落，页面上没有一列数字可对照，引用等于自证无人读；
# · **手抄就会错**——交稿物里那 214 处中有 2 处经核对指错（一处指向空行，一处把 178 行的
#   原话记成 180 行）；这两处也只能在当场对，对完就再没有机器读者守着；
# · **它比普通抄件腐得更快**——被引文件每次增删一行，全部引用集体失效。
# 本书的既有锚是**小节号、表行汉字序数、图号**（`17.4 第③层`／`度量表第五行`／`图 17-2`），
# 这三者都在渲染面上可见，改稿时也能被人看见。
# 口径：只扫 `docs/manuscript/*.md` 的**围栏外**正文，认 `第` + 2～4 位数字（可带 `～` 区间）+ `行`。
# 三条排除各由真实形状撑腰，缺一条就误伤全书：**汉字序数**（`度量表第五行`，全书表行引用的唯一合法写法）、
# **行数量词**（`36338 行`、`机器人 40 行生成物`，第 22 章与第 6 章的实跑读数）、
# **围栏内**（示例代码与 stdout 里的 `第 N 行` 是代码内容，不是本书的引用）。
# 闸外登记：`DIAGNOSIS.md` 与 `STYLE_GUIDE.md` 里都有 `第 NNN 行` 串（前者指台账行位、读者是守卫维护者
# 而非翻页人；后者是这条规则自己的反面实例）。它们**不在本闸范围内**——这句话写在这里，是为了让
# "手稿正文 0 处"这个读数不被读成"全仓 0 处"；立闸那一刻全站（73 个 md、含根/docs 两份副本）量到 4 处、
# 全部在 `DIAGNOSIS.md`，而写下这条规则的文案后来又各加了 2 处，所以那个 4 只在当场成立。
LINE_REF = re.compile(r"第\s*\d{2,4}(?:\s*[～~]\s*\d{2,4})?\s*行")


def line_ref_hits(text):
    """返回 [(行号, 命中串), …]。口径＝围栏外。纯函数、可注入（真件与桩件走同一条判据）。"""
    lines = text.splitlines()
    kinds = heading_kinds(lines)
    out = []
    for i, (line, kind) in enumerate(zip(lines, kinds), 1):
        if kind == "fence":
            continue
        for m in LINE_REF.finditer(line):
            out.append((i, m.group()))
    return out


def manuscript_files():
    return sorted((DOCS / "manuscript").glob("*.md"))


def line_ref_problems():
    """返回 (问题列表, 扫描文件数, 命中数)。枚举口径塌了就直接中止。"""
    fs = manuscript_files()
    if len(fs) < 50:
        raise SystemExit(f"源文行号闸只扫到 {len(fs)} 个手稿文件（<50）——枚举口径塌了，这条闸不能算通过")
    problems, hits = [], 0
    for path in fs:
        for no, s in line_ref_hits(path.read_text()):
            hits += 1
            problems.append(
                f"{path.relative_to(ROOT)}:{no}: 正文引用源码行号 {s!r} → 页面上没有行号可对照，"
                f"且被引文件一改就漂 → 改成本节小节号／表行汉字序数／图号"
            )
    return problems, len(fs), hits


LINE_REF_SELFTEST = [
    ("真件形状报（第 22 章改锚前那一行的形状）",
     "那条熵命中还是 `ch07-第2章-人在回路.md` 第 310 行那串高熵串。\n", 1),
    ("区间引用报（交稿物里的第二种形状）",
     "端侧字段裁剪清单（第 266～279 行）里有两栏。\n", 1),
    ("汉字序数的表行引用不报（全书表行锚的唯一合法写法）",
     "沿用度量表第五行与本表第八格的读法。\n", 0),
    ("章号与步号不报", "第 27 章的 27.5g 落地第 8 步。\n", 0),
    ("行数量词不报（实跑读数，第 22 章与第 6 章的形状）",
     "118 个受检文件、36338 行；机器人 40 行生成物混进来。\n", 0),
    ("围栏内是代码内容，不报", "```text\n第 310 行: SIG_ID ...\n```\n", 0),
]


def line_ref_selftest():
    bad = 0
    for name, text, want in LINE_REF_SELFTEST:
        got = len(line_ref_hits(text))
        if got != want:
            bad += 1
            print(f"  [✘] {name}：命中 {got} 条（应为 {want}）")
        else:
            print(f"  [✔] {name}：命中 {got} 条")
    if bad:
        raise SystemExit(f"源文行号闸的自检 {bad} 条不符——判据本身不可信")
    print("  自检结论：两种真件形状必报，三种合法写法（汉字序数、行数量词、围栏内）各有一支假阳对照。")
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
        print("[守卫清单闸] 复跑命令块 == scripts/check_*.py 全集")
        rc4 = guard_index_selftest()
        print("[裸路径闸] 正文不写裸文件路径")
        rc5 = raw_path_selftest()
        print("[源文行号闸] 手稿正文不引用源码行号")
        rc6 = line_ref_selftest()
        return rc1 or rc2 or rc3 or rc4 or rc5 or rc6
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
    gi_problems, listed_n, disk_n = guard_index_problems_real()
    problems += gi_problems
    raw_problems, raw_scanned, raw_hits = raw_path_problems()
    problems += raw_problems
    lr_problems, lr_scanned, lr_hits = line_ref_problems()
    problems += lr_problems
    if "--count" in sys.argv:
        print(f"{len(files())} 个 md 文件 / {fence_lines} 行围栏标记 / {total_code} 行代码块内容"
              f" / {baselined} 个文件有 HEAD 基线可对标题 / 空节闸扫 {scanned} 个文件"
              f" / 撞号闸扫 {sid_scanned} 个手稿文件"
              f" / 守卫清单闸对 {disk_n} 个 scripts/check_*.py（名册列 {listed_n} 个）"
              f" / 裸路径闸扫 {raw_scanned} 个文件（命中 {raw_hits} 条）"
              f" / 源文行号闸扫 {lr_scanned} 个手稿文件（命中 {lr_hits} 条）。")
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
        f"{sid_scanned} 个手稿文件无小节编号撞号；"
        f"复跑命令块与 {disk_n} 个守卫脚本集合相等；"
        f"{raw_scanned} 个文件的正文无裸文件路径；"
        f"{lr_scanned} 个手稿文件的正文无源码行号引用。结构闸通过。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
