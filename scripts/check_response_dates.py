#!/usr/bin/env python3
"""第十四条守卫：案例时间线里「这条接手落在哪一天」那张对照表，逐行判在位与先后。

被量面只有一处：`ch03-案例时间线.md` 的「失灵 ↔ 接手 ↔ 落地行对照表」。它把四张收束表里
每一条「组织谁接手」钉到该案例时间线的一行落地日期上，并声明回应的是哪一次事故。
本件判的是**钉得对不对得上表内自洽**，不判"这条接手真的回应那次失灵"（见文末盲区）。
范围只到四案：对照案（案例五）是实名公开文献案，日期是文献发表时间，不进这条尺。

判据五条（同一把尺）：
R1 **行集合对账**：对照表每案例的行（失灵点 · 时间）与该案例收束表的行双向相等——收束表加了
   一条而对照表没跟上，就是有一条接手从没被钉过；反向多钉也红。
R2 **先后**：落地行日期 ≥ 实际回应那一次的日期。机制不可能早于它回应的那次失灵。
R3 **在位**：落地行日期必须真的出现在该案例时间线里，且那一行含表中所写的关键词；
   单元格写 `无行 · 归<谁>` 是合法值，不判 R3、单独计数打印（不许表演"每条接手总有落地行"）。
R4 **编号与日期互指**：回应那一次的编号＋日期必须落在该案例时间线的一行上、且那一行含此编号；
   未标「（前奏）」时编号尾四位必须等于该日期的月日（与第十条 N7 同一口径）；标了就要求
   时间线那一行也带（前奏）。
R5 **形状与标记一致**：形状只能取三值；且「前奏」⇔「编号带（前奏）」⇔「回应那次早于收束表失灵日」。

为什么 R5 只判到「前奏」这一档——量测过才立的尺：用「关键词在失灵日之前是否出现过」判
制度化在后／直配 不成立：两档的取值完全重叠（制度化在后两行的"失灵日前出现次数"是 0 与 1，
直配五行是 0、0、0、1、1）。所以这两档的分别是人的声明，机检只打印分布与逐行取值，不判红。
为什么"前奏 ⇒ 日期必不等于尾四位"也没进判据：W-0703 的前奏（2024-07-03）与正式事故
（2025-07-03）同为 07-03、只差一年，那条反向判据会在真产物上红；能判的只有那一行文字带没带（前奏）。

盲区（打印出来，不当通过）：① 对齐是人声明的——把某条接手钉到另一行日期更晚、内容无关的记录上，
R2/R3 照样通过，本件判自洽不判真回应；② 关键词只判子串在场，不判那一行讲的就是那条机制；
③ 案例正文里那句「X 之后我们建了 Y」需要跨文件实体对齐，界画不出来，本件不覆盖。

用法：python3 scripts/check_response_dates.py [--verbose] [--selftest]
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = pathlib.Path("manuscript") / "ch03-案例时间线.md"
ANCHOR_TITLE = "失灵 ↔ 接手 ↔ 落地行对照表"
CLOSURE_TITLE = "失灵 ↔ 接手收束表"
SHAPES = ("直配", "前奏", "制度化在后")
PRELUDE = "（前奏）"
DATE = r"\d{4}-\d{2}-\d{2}"
ROW = re.compile(rf"^\| ({DATE}) \| (.*)\|\s*$", re.M)
AROW = re.compile(r"^\| 案例[一二三四] \|")
CROW = re.compile(rf"^\| ([①②③]) (.*?) \| ({DATE}) \|", re.M)
SEP = re.compile(r"\s*·\s*")
NID = re.compile(r"^([A-Z]-\d{4})")


def split2(cell):
    """把一个 `A · B` 单元格切成两段；段数不是 2 就返回 None，交调用方判红而不猜。"""
    p = [x.strip() for x in SEP.split(cell.strip())]
    return tuple(p[:2]) if len(p) == 2 else None


def parse(text):
    """从 ch03 全文取三件：各案例时间线行、各案例收束表行、对照表行。"""
    timelines, closures, anchors = {}, {}, []
    for part in re.split(r"^# ", text, flags=re.M):
        m = re.match(r"案例([一二三四])", part)
        if m:
            case = "案例" + m.group(1)
            timelines[case] = ROW.findall(part)
            closures[case] = [f"{n} {lbl} · {d}" for n, lbl, d in CROW.findall(part)]
        if part.startswith(ANCHOR_TITLE):
            anchors = [[c.strip() for c in line.strip().strip("|").split("|")]
                       for line in part.splitlines() if AROW.match(line)]
    return timelines, closures, anchors


def check(timelines, closures, anchors):
    """纯函数：五档判据都在这，输入是 parse 的产物——变异只改入参，不改判据。"""
    fails, notes, no_row, seen = [], [], {}, {}
    for cells in anchors:
        if len(cells) != 6:
            fails.append(f"对照表有一行不是 6 格（实得 {len(cells)} 格）：{cells[:2]}")
            continue
        case, failcell, respcell, _mech, landcell, shape = cells
        if case not in timelines:
            fails.append(f"对照表引用了不存在的案例「{case}」")
            continue
        seen.setdefault(case, []).append(failcell)
        if failcell in seen[case][:-1]:
            fails.append(f"{case}：对照表里「{failcell}」钉了不止一次")
        tl = timelines[case]
        row_at = {d: [b for dd, b in tl if dd == d] for d, _ in tl}

        tag = f"{case} {failcell}"
        if shape not in SHAPES:
            fails.append(f"{tag}：形状「{shape}」不在三值词表 {list(SHAPES)} 里")
        ff, rr = split2(failcell), split2(respcell)
        if not ff or not rr:
            fails.append(f"{tag}：失灵点或回应那一次不是 `A · B` 两段：{respcell}")
            continue
        _fail_label, fail_date = ff
        resp_id, resp_date = rr
        rid = NID.match(resp_id)
        if not rid:
            fails.append(f"{tag}：回应那一次的编号不像编号（{resp_id}）")
            continue
        rid = rid.group(1)
        prelude = PRELUDE in resp_id
        earlier = resp_date < fail_date
        if shape == "前奏" and not (prelude and earlier):
            fails.append(f"{tag}：声明前奏，可编号没带{PRELUDE}或回应那次并不早于正式事故"
                         f"（标记={prelude} 回应早于失灵={earlier}）")
        if shape != "前奏" and (prelude or earlier):
            fails.append(f"{tag}：形状是「{shape}」，却带着前奏的形状特征"
                         f"（标记={prelude} 回应早于失灵={earlier}）——含混就退回")

        hit = [b for b in row_at.get(resp_date, []) if rid in b]
        if not hit:
            fails.append(f"{tag}：时间线里 {resp_date} 那一行不含编号 {rid}"
                         f"（该日期在案内有行={bool(row_at.get(resp_date))}）")
        elif prelude and not any(PRELUDE in b for b in hit):
            fails.append(f"{tag}：表里标了{PRELUDE}，时间线 {resp_date} 的 {rid} 那一行没标")
        elif not prelude and rid[-4:] != resp_date[5:].replace("-", ""):
            fails.append(f"{tag}：未标{PRELUDE}，而编号 {rid} 尾四位 ≠ 回应日期 {resp_date} 的月日")

        if landcell.startswith("无行"):
            owner = split2(landcell)
            if not owner or not owner[1]:
                fails.append(f"{tag}：写「无行」却没写归谁（应为 `无行 · 归<谁>`）")
            else:
                no_row[f"{case} {ff[1]}"] = owner[1]
            continue
        ll = split2(landcell)
        if not ll or not re.fullmatch(DATE, ll[0]):
            fails.append(f"{tag}：落地行那一格既不是 `日期 · 关键词` 也不是 `无行 · 归<谁>`：{landcell}")
            continue
        land_date, kw = ll
        if land_date < resp_date:
            fails.append(f"{tag}：落地行 {land_date} 早于它回应的 {resp_date}——机制不会先于事故")
        lh = row_at.get(land_date, [])
        if not lh:
            fails.append(f"{tag}：落地行 {land_date} 在该案例时间线里不存在（日期抄串了案？）")
        elif not any(kw in b for b in lh):
            fails.append(f"{tag}：{land_date} 那一行里没有关键词「{kw}」——机检的把手断了")
        notes.append(f"{tag}｜{shape}｜关键词「{kw}」在失灵日前已出现 "
                     f"{sum(1 for d, b in tl if d < fail_date and kw in b)} 行（只打印，不判红）")
    return fails, notes, no_row, seen


def coverage(timelines, closures, anchors, seen, fails):
    """R1 行集合对账 + R0 覆盖自证：空分母、缺收束表一律判红。"""
    if not anchors:
        fails.append(f"对照表一行都没枚到（缺「{ANCHOR_TITLE}」那一节？）——空分母不算绿")
    if not timelines:
        fails.append("一个案例时间线都没枚到——本件不许在取不到数据时通过")
    for case in sorted(timelines):
        got = seen.get(case, [])
        want = closures.get(case, [])
        if not want:
            fails.append(f"{case}：没枚到「{CLOSURE_TITLE}」的行——一侧分母为空，对账不成立")
        for miss in sorted(set(want) - set(got)):
            fails.append(f"{case}：收束表有「{miss}」这条接手，对照表没钉它（覆盖缺口）")
        for extra in sorted(set(got) - set(want)):
            fails.append(f"{case}：对照表钉了「{extra}」，该案例收束表里没有这一行")
    return len(anchors), sum(len(v) for v in closures.values())


def run(path, verbose=False):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    timelines, closures, anchors = parse(text)
    fails, notes, no_row, seen = check(timelines, closures, anchors)
    na, nc = coverage(timelines, closures, anchors, seen, fails)
    dist = {s: sum(1 for c in anchors if len(c) == 6 and c[5] == s) for s in SHAPES}
    print(f"覆盖：对照表 {na} 行／收束表 {nc} 行／案例时间线 {len(timelines)} 案 "
          f"{sum(len(v) for v in timelines.values())} 行日期／形状 "
          + "、".join(f"{k} {v}" for k, v in dist.items()))
    if no_row:
        print("  写「无行」的接手（合法值，逐条交人读归谁）："
              + "；".join(f"{a} → {b}" for a, b in no_row.items()))
    if verbose:
        for n in notes:
            print("  " + n)
    for f in fails:
        print("✗ " + f)
    if fails:
        print("落地行先后闸未通过。")
        return 1
    print("落地行先后闸通过：每条接手钉到的落地行都在位、且不早于它回应的那一次。")
    return 0


def fixture():
    """一案两行的最小语料：一条直配、一条前奏——正例与极性的共同基准。"""
    return """# 案例一 · 测试案

## 阶段一

| 日期 | 事件 | AI 做了什么 | 谁介入 | 结果 | 代价 |
|------|------|------------|--------|------|------|
| 2025-01-14 | **事故 D-0114**：漏字段 | 生成迁移 | 风控 | 回滚 | — |
| 2025-01-16 | 支付域彻底人工化 | — | 风控 | 人工化 | — |
| 2025-02-14 | **事故 Y-0820（前奏）**：巡检拦截 | 判定冗余 | 合规 | 保留 | — |
| 2025-03-20 | 发布《合规不可删清单》 | — | 合规 | 生效 | — |
| 2025-08-20 | **事故 Y-0820**：正式那次 | 重构漏字段 | 合规 | 约谈 | — |

## 失灵 ↔ 接手收束表

| 失灵点 | 时间 | AI 失灵在哪 | 组织谁接手 | 接手方式 |
|--------|------|------------|-----------|---------|
| ① 对账脚本漏字段 | 2025-01-14 | 漏字段 | 风控 | 人工化 |
| ② KYC 漏字段 | 2025-08-20 | 重构漏字段 | 合规 | 不可删清单 |

# 失灵 ↔ 接手 ↔ 落地行对照表

| 案例 | 收束表里的那一行（失灵点 · 时间） | 实际回应的那一次（编号 · 日期） | 接手机制 | 时间线里的落地行（日期 · 该行可核的关键词） | 形状 |
|------|--------------------------------|------------------------------|---------|----------------------------------------|------|
| 案例一 | ① 对账脚本漏字段 · 2025-01-14 | D-0114 · 2025-01-14 | 支付域人工化 | 2025-01-16 · 人工化 | 直配 |
| 案例一 | ② KYC 漏字段 · 2025-08-20 | Y-0820（前奏）· 2025-02-14 | 合规不可删清单 | 2025-03-20 · 合规不可删 | 前奏 |
"""


def score(text):
    tl, cl, an = parse(text)
    f, _n, _r, seen = check(tl, cl, an)
    coverage(tl, cl, an, seen, f)
    return f


def mutate(text, old, new):
    n = text.count(old)
    if n != 1:
        raise AssertionError(f"变异锚不唯一（{n} 处）：{old[:28]}")
    return text.replace(old, new, 1)


def selftest():
    """正例／假阳对照／极性／空分母四类各若干条，都打在 parse→check→coverage 同一份实现上。

    条数与分类明细不在这里写：上一版这段 docstring 抄的是「极性 6、九条对照」，而打印句抄的是
    「极性 7、11 条」——两处手抄已经互相不等，同一份 cases 才是那第三个源头，所以本轮起由它给数。
    """
    base = fixture()
    cases = [("C1 正例：直配＋前奏两行各判各的，0 红", "正例", len(score(base)) == 0)]
    cases.append(("C2 假阳对照：把一条落地行改成合法值「无行 · 归第 5 章」不许红", "假阳",
                  len(score(mutate(base, "2025-01-16 · 人工化 | 直配",
                                   "无行 · 归第 5 章 | 直配"))) == 0))
    cases.append(("C3 假阳对照：把两条前奏行都摘干净（只留直配）不许红", "假阳",
                  len(score(mutate(mutate(base, "\n| 案例一 | ② KYC 漏字段 · 2025-08-20 | "
                                              "Y-0820（前奏）· 2025-02-14 | 合规不可删清单 | "
                                              "2025-03-20 · 合规不可删 | 前奏 |", ""),
                                   "| ② KYC 漏字段 | 2025-08-20 | 重构漏字段 | 合规 | 不可删清单 |\n",
                                   ""))) == 0))
    pol = [
        ("C4 极性·日期倒挂（落地早于回应）", mutate(base, "2025-01-16 · 人工化", "2024-01-16 · 人工化"), "早于它回应的"),
        ("C5 极性·把手断了（那一行没有所写关键词）", mutate(base, "2025-01-16 · 人工化", "2025-01-16 · 精度铁律"), "关键词"),
        ("C6 极性·落地日期抄串到别案", mutate(base, "2025-01-16 · 人工化", "2025-01-17 · 人工化"), "不存在"),
        ("C7 极性·摘掉编号里的（前奏）", mutate(base, "Y-0820（前奏）· 2025-02-14", "Y-0820 · 2025-02-14"), "尾四位"),
        ("C8 极性·形状写直配却带前奏标记", mutate(base, "合规不可删 | 前奏 |", "合规不可删 | 直配 |"), "形状特征"),
        ("C9 极性·收束表删掉一行 ⇒ 对照表成多钉", mutate(base, "| ② KYC 漏字段 | 2025-08-20 | 重构漏字段 | 合规 | 不可删清单 |\n", ""), "收束表里没有"),
        ("C10 极性·对照表漏钉一条", mutate(base, "| 案例一 | ① 对账脚本漏字段 · 2025-01-14 | D-0114 · 2025-01-14 | 支付域人工化 | 2025-01-16 · 人工化 | 直配 |\n", ""), "覆盖缺口"),
    ]
    for name, mutated, kw in pol:
        f = score(mutated)
        cases.append((f"{name}（命中「{kw}」）", "极性", any(kw in x for x in f)))
    f0 = []
    coverage({}, {}, [], {}, f0)
    cases.append(("C11 空分母必红（一枚都没枚到 ⇒ 两条都报，不报通过）", "空分母", len(f0) == 2))
    ok = all(p for _, _, p in cases)
    for name, kind, passed in cases:
        print(f"  [{'OK' if passed else 'NO'}] {name}")
    kinds = list(dict.fromkeys(k for _, k, _ in cases))
    detail = "、".join(f"{k} {sum(1 for _, kk, _ in cases if kk == k)}" for k in kinds)
    print(f"自检结论：{len(cases)} 条对照（{detail}）——"
          f"{'全部按预期' if ok else '有对照未按预期，判据不可信'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(run(ROOT / "docs" / TARGET, verbose="--verbose" in sys.argv))
