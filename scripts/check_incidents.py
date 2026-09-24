#!/usr/bin/env python3
"""第十条守卫·事实一致性闸：事故编号 ↔ 日期 ↔ 时间线 ↔ 登记，四向对齐。

为什么立这条：DIAGNOSIS 上一轮白纸黑字记着「**跨文件叙事一致性仍无守卫**……要么立闸，要么别声称有」，
那两处"A 章写 2024-05、B 章写 2024-06"式的矛盾一直是人眼抓的。而规矩早就写了、只是没有执行者：
`ch05-数字清单.md` 开头写着"构造原则：与时间线（ch03-案例时间线.md）逐一对应"
与"任何新增数字必须先回写本清单，再进正文"，1.2 节又写着"全书涉及这三件事的数字，一律以本表为准"。
这几条判据就是把这些话变成会报红的东西。

判据（每条都在现网量过命中面；命中数一并打印，防止把"报 0"读成"干净"）：
  N1 清单自洽   —— 事故编号尾四位 == 本行日期的月-日；日期缺失、编号字母跨案例重复也算坏。
  N2 时间线区间 —— ch03 每个「阶段」标题必须自带（YYYY-MM ～ YYYY-MM）区间；
                   阶段内日期表的每一行必须落在该阶段窗口里（按月首～月末归一）。现网 17 窗口 / 90 行。
  N3 阶段推进   —— 同一案例的阶段窗口必须严格递增且不重叠（重叠＝一行日期可以属两段，N2 失去意义）。
  N4 事故入窗   —— 清单里每件事故的日期必须落在**本案**某个阶段窗口内。这是"与时间线逐一对应"的执行者。现网 12 件。
  N5 登记性     —— 正文出现的任何 `[A-Z]-\\d{4}` 编号都必须先在清单里。这是"先回写清单，再进正文"的写侧读者。
  N6 点名覆盖   —— 清单里每件事故在正文（清单之外）至少被点名 1 次；0 次＝清单里有、全书没讲。
  N7 编号旁日期 —— 除时间线章外，任一行同时给出编号与完整日期时，日期必须等于清单日期。
                   **诚实记账：现网命中 0 行**（正文从不把编号和日期写进同一行），它咬的是"以后有人这么写"，
                   牙齿只由 --selftest 的桩证明；别把它算进"已经拦过什么"。

被量过之后**故意没有做**的判据（写在这里，别误以为闸比实际更宽）：
  · 「点名事故时同行给出的钱数必须等于清单损失估算」——现网 13 处命中里 10 处是合法的另一数字
    （D-0114 的 15 分钟窗口、Z-0612 的回测三数、X-0719 那行的 KPI 百分数），假阳性 77%，不做。
  · 「事件名（不带编号）与日期同现时须一致」——现网命中 0 处（他章复用事件名时从不同行带日期），不做。
  · 时间线章不入 N7：`2025-08-14 | 大会复盘（D-0114、E-0311、F-0515）` 是复盘日、
    `2025-02-14 | 事故 Y-0820（前奏）` 是前奏日，两条都合法——量出来过，所以把 ch03 排除在 N7 之外。
  · 「四案例数字禁止交叉引用」——正文确有合法的跨案对照（ch35:315 是给案例一的公开信、ch38 整章就是交叉启示），
    机械禁跨案会把合法件全打红；**这一轴至今无守卫**，别声称有。

用法：
    python3 scripts/check_incidents.py            # 全量
    python3 scripts/check_incidents.py --report   # 逐编号、逐阶段窗口打印读数
    python3 scripts/check_incidents.py --selftest # 控制跑必干净 + 7 条变异各自报红 + 2 条正例必不报
"""
from __future__ import annotations

import calendar
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LEDGER_REL = Path("manuscript") / "ch05-数字清单.md"
TIMELINE_REL = Path("manuscript") / "ch03-案例时间线.md"
BODY_REL = Path("manuscript") / "ch06-第1章-AI原生不是让AI写代码.md"

MIN_INCIDENTS = 10
MIN_STAGE_ROWS = 50
MIN_STAGES = 4
MIN_MENTIONS = 50

# 不用 \b：Python 的 \b 把 CJK 当 \w，"D-0114后" 这种写法会被漏掉
ID_RE = re.compile(r"(?<![0-9A-Za-z])([A-Z]-\d{4})(?![0-9])")
ROW_RE = re.compile(r"^\|\s*\**([A-Z]-\d{4})\**\s*\|")
DATE_RE = re.compile(r"(20\d{2})[-/年]\s?(\d{1,2})[-/月]\s?(\d{1,2})日?")
LEAD_DATE_RE = re.compile(r"^\s*\**\s*(20\d{2})[-/年]\s?(\d{1,2})[-/月]\s?(\d{1,2})")
RANGE_RE = re.compile(r"[（(]\s*(20\d{2})[-/年](\d{1,2})\s*[～~—-]\s*(?:(20\d{2})[-/年])?(\d{1,2})")
CASE_HEAD_RE = re.compile(r"^#{1,2}\s+案例([一二三四])")
STAGE_HEAD_RE = re.compile(r"^#{2,3}\s+阶段")


def iso(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def month_bound(y: str, m: str, end: bool = False) -> str:
    day = calendar.monthrange(int(y), int(m))[1] if end else 1
    return f"{int(y):04d}-{int(m):02d}-{day:02d}"


def parse_ledger(path: Path) -> dict[str, dict]:
    """读清单里的事故：编号 → {case, name, date}。只有 `# 案例N` 小节下的编号行才算事故。"""
    incidents: dict[str, dict] = {}
    cur_case = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        m_case = CASE_HEAD_RE.match(s)
        if m_case:
            cur_case = m_case.group(1)
            continue
        m_id = ROW_RE.match(line)
        if not m_id or not cur_case:
            continue
        cells = [c.strip().strip("*").strip() for c in s.strip("|").split("|")]
        d = DATE_RE.search(s)
        incidents[m_id.group(1)] = {
            "case": cur_case,
            "name": cells[1] if len(cells) > 1 else "",
            "date": iso(*d.groups()) if d else "",
        }
    return incidents


def parse_stages(path: Path):
    """读时间线：返回 (案例→窗口列表, 阶段内日期行读数, 不带区间的阶段标题数)。"""
    windows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    rows: list[tuple[int, str, str, tuple[str, str]]] = []
    headless = 0
    case = ""
    win: tuple[str, str] | None = None
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        m_case = CASE_HEAD_RE.match(s)
        if m_case:
            case = m_case.group(1)
            win = None
            continue
        if STAGE_HEAD_RE.match(s):
            r = RANGE_RE.search(s)
            if not r:
                headless += 1
                win = None
                continue
            win = (month_bound(r.group(1), r.group(2)),
                   month_bound(r.group(3) or r.group(1), r.group(4), end=True))
            windows[case].append(win)
            continue
        if not s.startswith("|") or not win or set(s) <= set("|-: "):
            continue
        cells = [c.strip().strip("*").strip() for c in s.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        d = LEAD_DATE_RE.match(cells[0])
        if d:
            rows.append((i, case, iso(*d.groups()), win))
    return windows, rows, headless


def scan_mentions(files: list[Path], incidents: dict[str, dict]):
    mentions: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    unregistered: list[tuple[Path, int, str]] = []
    dated_lines: list[tuple[Path, int, list[str], list[str]]] = []
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for tok in ID_RE.findall(line):
                if tok in incidents:
                    mentions[tok].append((f, i))
                else:
                    unregistered.append((f, i, tok))
            ids = sorted({x for x in ID_RE.findall(line) if x in incidents})
            ds = [iso(*g) for g in DATE_RE.findall(line)]
            if ids and ds:
                dated_lines.append((f, i, ids, ds))
    return mentions, unregistered, dated_lines


def judge(docs_dir: Path) -> tuple[list[str], dict]:
    problems: list[str] = []
    ledger_p = docs_dir / LEDGER_REL
    timeline_p = docs_dir / TIMELINE_REL
    missing = [p.name for p in (ledger_p, timeline_p) if not p.is_file()]
    if missing:
        return [f"分母缺失：{'、'.join(missing)} 读不到——本闸无法判定，不是通过"], {}
    incidents = parse_ledger(ledger_p)
    windows, stage_rows, headless = parse_stages(timeline_p)
    files = [p for p in sorted(docs_dir.rglob("*.md")) if p.is_file() and p != ledger_p]

    if len(incidents) < MIN_INCIDENTS:
        problems.append(f"覆盖自证：清单只解析出 {len(incidents)} 件事故（< {MIN_INCIDENTS}）——分母可疑，不认为通过")
    if len(windows) < MIN_STAGES:
        problems.append(f"覆盖自证：时间线只解析出 {len(windows)} 个案例的阶段窗口（< {MIN_STAGES}）")
    if len(stage_rows) < MIN_STAGE_ROWS:
        problems.append(f"覆盖自证：时间线只读到 {len(stage_rows)} 行阶段内日期（< {MIN_STAGE_ROWS}）——判据够不到数据")
    if not files:
        problems.append("覆盖自证：枚举到 0 个 md 文件——口径坏了，不是全站干净")

    letters: dict[str, list[str]] = defaultdict(list)
    for iid, v in incidents.items():
        letters[iid[0]].append(iid)
        if not v["date"]:
            problems.append(f"N1 清单自洽：{iid}（{v['name'][:16]}）本行没有日期")
            continue
        if iid.split("-")[1] != v["date"][5:].replace("-", ""):
            problems.append(f"N1 清单自洽：编号 {iid} 的尾四位与本行日期 {v['date']} 的月-日不一致")
    for letter, ids in sorted(letters.items()):
        cases = {incidents[x]["case"] for x in ids}
        if len(ids) > 1 and len(cases) > 1:
            problems.append(f"N1 清单自洽：字母 {letter} 跨案例重复（{'、'.join(sorted(ids))}）——正文点名将无法判定归属")

    for i, case, v, win in stage_rows:
        if not (win[0] <= v <= win[1]):
            problems.append(f"N2 时间线区间：ch03:{i} 的日期 {v} 越出所在阶段窗口 {win[0]} ～ {win[1]}（案例{case}）")
    if headless:
        problems.append(f"N2 时间线区间：{headless} 个阶段标题不带（YYYY-MM ～ YYYY-MM）区间——闸无法判定其行所属窗口")

    for case, ws in sorted(windows.items()):
        for k in range(len(ws) - 1):
            if not (ws[k][0] < ws[k + 1][0] and ws[k][1] < ws[k + 1][0]):
                problems.append(
                    f"N3 阶段推进：案例{case} 第 {k + 1}／{k + 2} 段未严格递增或重叠"
                    f"（{ws[k][0]}～{ws[k][1]} 与 {ws[k + 1][0]}～{ws[k + 1][1]}）"
                )

    for iid, v in sorted(incidents.items()):
        if not v["date"]:
            continue
        ws = windows.get(v["case"], [])
        if not any(a <= v["date"] <= b for a, b in ws):
            span = f"{ws[0][0]} ～ {ws[-1][1]}" if ws else "无窗口"
            problems.append(
                f"N4 事故入窗：{iid}（{v['name'][:16]}）日期 {v['date']} 不在案例{v['case']} 的任何阶段窗口内"
                f"（本案时间线 {span}）——清单与时间线不对应"
            )

    mentions, unregistered, dated_lines = scan_mentions(files, incidents)

    for f, i, tok in unregistered:
        problems.append(f"N5 登记性：{f.name}:{i} 出现未登记编号 {tok}——先回写 ch05-数字清单.md，再进正文")

    for iid in sorted(incidents):
        if not mentions.get(iid):
            problems.append(f"N6 点名覆盖：{iid}（{incidents[iid]['name'][:16]}）在正文从未被点名——清单里有、全书没讲")

    n7_hits = 0
    for f, i, ids, ds in dated_lines:
        # 适用面收窄到书稿正文：立闸当轮这条就在 DIAGNOSIS 自己的记录行上报红
        # （那一行同时点名 D-0114/X-0719/Y-0820/Z-0612 并写着 2025-08-14 与 2025-02-14 两个日期，
        # 是在**描述**时间线里的合法形状，不是叙述事实）。工程日志不入这条判据。
        if f.parent.name != "manuscript":
            continue
        if f.name == TIMELINE_REL.name:
            continue
        n7_hits += 1
        canon = {incidents[x]["date"] for x in ids}
        for d in ds:
            if d not in canon:
                problems.append(
                    f"N7 编号旁日期：{f.name}:{i} 把 {'、'.join(ids)} 与 {d} 写在同一行，"
                    f"但清单日期是 {'、'.join(sorted(canon))}"
                )

    total_mentions = sum(len(v) for v in mentions.values())
    if total_mentions < MIN_MENTIONS:
        problems.append(f"覆盖自证：正文点名仅 {total_mentions} 次（< {MIN_MENTIONS}）——枚举口径可疑")
    readings = {
        "incidents": len(incidents),
        "cases": len(windows),
        "stages": sum(len(v) for v in windows.values()),
        "stage_rows": len(stage_rows),
        "files": len(files),
        "mentions": total_mentions,
        "per_id": {k: len(mentions.get(k, [])) for k in sorted(incidents)},
        "unregistered": len(unregistered),
        "dated_lines": len(dated_lines),
        "n7_corpus_hits": n7_hits,
        "windows": windows,
    }
    return problems, readings


def report() -> None:
    problems, r = judge(DOCS)
    incidents = parse_ledger(DOCS / LEDGER_REL)
    print(f"清单 {r['incidents']} 件事故 / 时间线 {r['cases']} 案 {r['stages']} 阶段 {r['stage_rows']} 行日期 / "
          f"扫 {r['files']} 个 md（不含清单）/ 点名 {r['mentions']} 次")
    for iid, v in sorted(incidents.items()):
        print(f"  {iid} 案例{v['case']} {v['date']}  点名 {r['per_id'].get(iid, 0):3d} 次  {v['name'][:26]}")
    for case, ws in sorted(r["windows"].items()):
        print(f"  案例{case} 阶段：" + " | ".join(f"{a}～{b}" for a, b in ws))
    print(f"N7 命中面：时间线之外 {r['n7_corpus_hits']} 行（含编号又含完整日期的行）")
    print(f"问题 {len(problems)} 条")


def patch(text: str, old: str, new: str) -> str:
    """变异锚点必须唯一：不唯一就停下——打在重复锚上的变异会伪装成「判据太松」。"""
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"!! 变异锚点在副本里出现 {n} 次（要求恰好 1 次）：{old[:44]!r}——自检不可信，中止")
    return text.replace(old, new)


# (标签, 期望判据码或 None, 文件, 旧串, 新串, 说明)
MUTATIONS: list[tuple[str, str | None, Path, str, str, str]] = [
    ("M1", "N1", LEDGER_REL, "| **D-0114** | **支付对账迁移漏字段** | **2025-01-14** |",
     "| **D-0119** | **支付对账迁移漏字段** | **2025-01-14** |",
     "变异：只改编号不改日期 → 必报 N1"),
    ("M2", "N2", TIMELINE_REL, "| 2024-04-02 | **事故 A-0402", "| 2024-07-02 | **事故 A-0402",
     "变异：阶段一的行日期推到窗口外 → 必报 N2"),
    ("M3", "N3", TIMELINE_REL, "## 阶段二 · 立界期（2024-06 ～ 2024-08",
     "## 阶段二 · 立界期（2024-03 ～ 2024-08",
     "变异：第二段起点压回第一段之前 → 必报 N3"),
    ("M4", "N4", LEDGER_REL, "| B-0527 | 订单接口改了未同步契约 | 2024-05-27 |",
     "| B-0527 | 订单接口改了未同步契约 | 2026-05-27 |",
     "变异：编号与日期仍自洽，但日期掉出本案时间线 → 必报 N4"),
    ("M5", "N5", BODY_REL, "", "另一起事故 G-0230 也属于同类失灵。",
     "变异：正文出现未登记编号 → 必报 N5"),
    ("M6", "N7", BODY_REL, "", "复盘 D-0114（2025-01-15）的记录。",
     "变异：正文把编号与错误日期写进同一行 → 必报 N7"),
    ("M7", "N6", LEDGER_REL, "| F-0515 | 合规灰度被叫停 | 2025-05-15 |",
     "| J-0515 | 合规灰度被叫停 | 2025-05-15 |",
     "变异：把一件事故改成正文从未点名的新编号 → 必报 N6"),
    ("P1", None, BODY_REL, "", "复盘 D-0114（2025-01-14）的记录。",
     "正例：编号与清单日期同行出现 → 必不报"),
    ("P2", None, TIMELINE_REL, "| 2024-04-02 | **事故 A-0402", "| 2024-04-03 | **事故 A-0402",
     "正例：换成同窗口内的另一天 → 必不报（否则 N2 就是「任何改动都红」）"),
]


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "docs"
        shutil.copytree(DOCS, dst)
        rels = sorted({m[2] for m in MUTATIONS})
        orig = {rel: (dst / rel).read_text(encoding="utf-8") for rel in rels}

        def restore() -> None:
            for rel, txt in orig.items():
                (dst / rel).write_text(txt, encoding="utf-8")

        base, rb = judge(dst)
        print(f"  [控制] 未变异的副本：{len(base)} 条问题 / 清单 {rb['incidents']} 件 / 点名 {rb['mentions']} 次 / "
              f"时间线 {rb['stage_rows']} 行 / N7 命中面 {rb['n7_corpus_hits']} 行")
        for p in base:
            print(f"       └ {p}")
        if base:
            print("!! 控制跑不干净——副本与原件对不上，后面所有对照都不成立")
            return 1
        results = []
        for tag, code, rel, old, new, why in MUTATIONS:
            restore()
            path = dst / rel
            text = path.read_text(encoding="utf-8")
            path.write_text(patch(text, old, new) if old else text.rstrip() + "\n\n" + new + "\n",
                            encoding="utf-8")
            problems, _ = judge(dst)
            fired = {p.split(" ")[0] for p in problems}
            ok = (code in fired) if code else not fired
            results.append(ok)
            print(f"  {'[✔]' if ok else '[✘]'} {why}（期望 {code or '不报'}，实报 {sorted(fired) or '无'}）")
            for p in problems[:3]:
                print(f"       └ {p}")
            if len(problems) > 3:
                print(f"       └ …另 {len(problems) - 3} 条（改一个编号会连带打红所有点名处，是预期的级联）")
        restore()
        again, _ = judge(dst)
        print(f"  [还原] 全部桩撤净后：{len(again)} 条问题")
        neg = sum(1 for _, c, *_ in MUTATIONS if c)
        print(f"自检结论：{len(results)} 条对照（变异 {neg}、正例 {len(results) - neg}），未达预期 {results.count(False)} 条")
        if False in results:
            print("!! 自检未通过——变异没红说明判据太松，正例报了说明闸会把合法写法一并打红")
            return 1
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    problems, r = judge(DOCS)
    if not r:
        print("\n".join(problems))
        return 1
    if "--report" in argv:
        report()
        return 1 if problems else 0
    print(f"[覆盖] 清单 {r['incidents']} 件事故 / 时间线 {r['cases']} 案 {r['stages']} 阶段（{r['stage_rows']} 行日期）/ "
          f"扫 {r['files']} 个 md / 正文点名 {r['mentions']} 次 / 未登记 {r['unregistered']} 个 / "
          f"N7 时间线外命中面 {r['n7_corpus_hits']} 行")
    print("  逐编号点名：" + "  ".join(f"{k}:{v}" for k, v in r["per_id"].items()))
    if problems:
        print("\n".join(problems))
        print(f"事实一致性闸未通过：{len(problems)} 条")
        return 1
    print("事实一致性闸通过：编号↔日期自洽、时间线行日期在阶段窗口内、阶段推进不重叠、"
          "事故日期落在本案时间线内、无未登记编号、每件事故都在正文被点名过。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
