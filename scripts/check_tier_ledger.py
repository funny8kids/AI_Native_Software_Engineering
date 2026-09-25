#!/usr/bin/env python3
"""第十二条守卫：台账那一列档位，必须逐行等于对应卡片自己声明的档位。

判据：第 4 章 §4.5c 的 49 行工具台账是**抄件**，卡内那行 `> **档位声明（<工具名>）**：` 才是
权威。逐行按落点（第 N 章 / 案例 X ＋可选节号 ＋可选卡名）找到卡片，要求：
① 该文件里这个键的声明**有且只有一条**（键按整串相等判，`Kafka` 不许命中 `Kafka 分区键与顺序语义`）；
② 声明所在的小节就是落点指的那一节（有节号按节号，有卡名按卡名，两者都无按文件内唯一）；
③ 档位集合相等（A／B／C／规范／形状；一卡两半证据不同时，两边的档位集合都要对上）；
④ 反向闸：卡上声明了却不在台账里的键同样报红——台账漏登记等于抄件比实物少。

为什么要机检：2026-09-25 推送前自检发现台账把三个本机根本没装的工（OpenAPI／protoc／nginx）
写成 A 档。第十一条守卫量的是"print↔围栏输出"，抓不到"假读数和假代码天然自洽"的编造；
这一条量的是两个抄件之间的一致性，是当时登记在案的缺口。

盲区（打印出来，不当通过）：卡片正文里的自然语言是否诚实支撑它自己声明的档位，机检判不了，
仍要人读；本闸只保证"台账 == 卡上写的"，不保证"卡上写的 == 机器上发生的"。

用法：python3 scripts/check_tier_ledger.py [--verbose] [--selftest]
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MS = ROOT / "docs" / "manuscript"
DECL = re.compile(r"^>\s*\*\*档位声明（(.+?)）\*\*：\*\*(.+?)\*\*")
ANCHOR = re.compile(r"^(?:第\s*(\d+)\s*章|(案例[一二三四]))(?:\s+([0-9]+\.[0-9]+[a-z]?(?![0-9a-z])))?"
                    r"(?:\s*·\s*(.+))?$")
HEAD = re.compile(r"^(#{2,6})\s+(.*)$")
TIERS = [("规范", re.compile(r"规范档")), ("形状", re.compile(r"形状档")),
         ("A", re.compile(r"A\s*档|\*\*A\*\*")), ("B", re.compile(r"B\s*档|\*\*B\*\*")),
         ("C", re.compile(r"C\s*档|\*\*C\*\*"))]


def norm(s):
    return re.sub(r"[`\*]", "", s).strip()


def key_of(cell):
    return norm(cell).split("（")[0].strip()


def tier_set(cell):
    """档位标签集合：A／B／C／规范／形状。中文档名按整词收，不按字符拆。"""
    return {name for name, pat in TIERS if pat.search(cell)} or {"?"}


def ledger_rows(text):
    """解析 §4.5c 那张表：只收 5 列、且第 4 列形如落点的行。"""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if not ln.startswith("|") or norm(ln.split("|")[1]) != "工具":
            continue
        rows = []
        for ln in lines[i + 1:]:
            if not ln.startswith("|"):
                break
            c = ln.split("|")
            if len(c) < 6 or set(c[1].strip()) <= set("-: "):
                continue
            a = ANCHOR.match(norm(c[4]))
            if not a:
                break
            rows.append({"tool": c[1], "key": key_of(c[1]), "anchor": norm(c[4]),
                         "ch": a.group(1) or a.group(2), "sid": a.group(3),
                         "card": norm(a.group(4)) if a.group(4) else None,
                         "tier": c[5]})
        return rows
    return []


def file_for(ch, fmap):
    return fmap.get(ch)


def chapter_map(paths):
    m = {}
    for p in paths:
        a = re.match(r"^ch\d+-(?:第\s*(\d+)\s*章|(案例[一二三四]))", p.name)
        if a:
            m[a.group(1) or a.group(2)] = p
    return m


FENCE = re.compile(r"^```")


def decls_of(path):
    """带节归属的声明清单（stack = 该声明所在的各级标题）。围栏整体跳过：
    示例块里的 `# 注释` 不是小节，块内照抄的一条声明也不是这本书在声明自己的档位。"""
    out, stack, fenced = [], [], False
    for no, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(ln):
            fenced = not fenced
            continue
        if fenced:
            continue
        h = HEAD.match(ln)
        if h:
            lv = len(h.group(1))
            stack = [x for x in stack if x[0] < lv] + [(lv, h.group(2))]
            continue
        d = DECL.match(ln)
        if d:
            heads = [x[1] for x in stack]
            out.append({"key": norm(d.group(1)), "tier": d.group(2), "line": no,
                        "head": heads[-1] if heads else "", "stack": heads, "file": path.name})
    return out


def where_ok(d, row):
    """落点与声明所在标题链相符：节号要在某级标题开头，卡名要在某级标题里。"""
    sid_ok = card_ok = True
    if row["sid"]:
        sid_ok = any(re.match(r"^" + re.escape(row["sid"]) + r"(?![0-9a-z])", h) for h in d["stack"])
    if row["card"]:
        card_ok = any(row["card"] in h for h in d["stack"])
    elif not row["sid"]:
        card_ok = True
    return sid_ok and card_ok


def compare(rows, decl_index, fmap):
    """rows×decls 的对账；返回 (失败列表, 覆盖计数)。纯函数，注入即可变异。"""
    fails, seen = [], {"行": 0, "落点缺文件": 0, "命中": 0, "孤立声明": 0}
    used = set()
    for row in rows:
        文件 = file_for(row["ch"], fmap)
        if 文件 is None:
            fails.append(f"落点查无此文件：「{row['anchor']}」（台账行「{row['key']}」）")
            seen["落点缺文件"] += 1
            continue
        hits = [d for d in decl_index.get(文件.name, []) if d["key"] == row["key"]]
        seen["行"] += 1
        if len(hits) != 1:
            fails.append(f"档位声明缺失或多条：「{row['key']}」在 {文件.name} 命中 {len(hits)} 条"
                         + (f"（第 {'、'.join(str(d['line']) for d in hits)} 行）" if len(hits) > 1 else ""))
            continue
        d = hits[0]
        used.add((文件.name, d["line"]))
        if not where_ok(d, row):
            fails.append(f"落点与实际位置不符：「{row['key']}」声明在「{d['head'][:34]}」，"
                         f"台账写「{row['anchor']}」")
            continue
        lt, dt = tier_set(row["tier"]), tier_set(d["tier"])
        if lt != dt:
            fails.append(f"档位不符：台账「{row['key']}」= {sorted(lt)}，卡上（{文件.name}:{d['line']}）= {sorted(dt)}")
            continue
        seen["命中"] += 1
    for fname, ds in decl_index.items():
        for d in ds:
            if (fname, d["line"]) not in used:
                fails.append(f"孤立声明：{fname}:{d['line']} 的键「{d['key']}」不在台账里（台账少登记一行）")
                seen["孤立声明"] += 1
    return fails, seen


def real():
    paths = sorted(MS.glob("*.md"))
    ch09 = [p for p in paths if "第4章" in p.name]
    if not ch09:
        print("台账闸未通过：找不到第 4 章文件，抄件在哪都不知道")
        return [], {}, {}, {"行": 0, "落点缺文件": 0, "命中": 0, "孤立声明": 0}, [], 0, None
    rows = ledger_rows(ch09[0].read_text(encoding="utf-8"))
    fmap = chapter_map(paths)
    decl_index = {p.name: decls_of(p) for p in paths if p != ch09[0]}
    total_decl = sum(len(v) for v in decl_index.values())
    fails, seen = compare(rows, decl_index, fmap)
    return rows, decl_index, fmap, seen, fails, total_decl, ch09


def selftest():
    """四支变异＋一支正对照：判据必须可注入，否则今天的相等会掩盖改坏比较。"""
    fmap = {"9": pathlib.Path("chX.md"), "21": pathlib.Path("chY.md")}
    mkrow = lambda k, anc, tier, sid=None, card=None: {
        "tool": k, "key": k, "anchor": anc, "ch": anc.split()[1] if anc.startswith("第") else anc[:3],
        "sid": sid, "card": card, "tier": tier}
    r1 = mkrow("Kafka", "第 21 章 21.4 · 真系统", "**B**", card="真系统")
    r2 = mkrow("Kafka 分区键与顺序语义", "第 21 章 21.4b", "**A**", sid="21.4b")
    idx = {"chY.md": [
        {"key": "Kafka", "tier": "B 档 · 文档逐字", "line": 10, "head": "工具落地卡：真系统",
         "stack": ["21.4 监控", "工具落地卡：真系统"], "file": "chY.md"},
        {"key": "Kafka 分区键与顺序语义", "tier": "A 档 · 本机实跑", "line": 20, "head": "21.4b 三信号",
         "stack": ["21.4b 三信号"], "file": "chY.md"}]}
    cases = []

    def run(rows, index):
        return compare(rows, index, fmap)

    f, s = run([r1, r2], idx)
    cases.append(("正对照：两行全对上，不许报红", f, len(f) == 0 and s["命中"] == 2))
    f, s = run([r1, r2], {"chY.md": [idx["chY.md"][1]]})
    cases.append(("删掉一条声明 → 必须红", f, len(f) == 1 and "缺失" in f[0]))
    f, _ = run([r1, r2], {"chY.md": list(idx["chY.md"]) + [
        {"key": "Kafka", "tier": "B 档 · 文档逐字", "line": 99, "head": "工具落地卡：真系统",
         "stack": ["21.4 监控", "工具落地卡：真系统"], "file": "chY.md"}]})
    cases.append(("同一键声明两次 → 必须红", f, any("多条" in x for x in f)))
    bad = dict(idx["chY.md"][0], tier="A 档 · 本机实跑")
    f, _ = run([r1, r2], {"chY.md": [bad, idx["chY.md"][1]]})
    cases.append(("卡上把 B 写成 A → 必须红（这条就是本闸存在的理由）", f, any("档位不符" in x for x in f)))
    moved = dict(idx["chY.md"][1], head="21.9 遗留问题", stack=["21.9 遗留问题"])
    f, _ = run([r1, r2], {"chY.md": [idx["chY.md"][0], moved]})
    cases.append(("声明挪到别的小节 → 必须红", f, any("落点与实际位置不符" in x for x in f)))
    f, _ = run([r1, r2], {"chY.md": list(idx["chY.md"]) + [
        {"key": "pytest 扩展点", "tier": "A 档 · 本机实跑", "line": 30, "head": "10.5f",
         "stack": ["10.5f"], "file": "chY.md"}]})
    cases.append(("卡上声明了台账没有的键 → 必须红（反向闸）", f, any("孤立声明" in x for x in f)))
    prefix = dict(r2, key="Kafka 分区", anchor="第 21 章 21.4b", sid="21.4b")
    f, _ = run([prefix], {"chY.md": [idx["chY.md"][1]]})
    cases.append(("键整串相等：台账写成「Kafka 分区」不许命中「Kafka 分区键与顺序语义」的声明 → 必须红", f,
                  any("缺失或多条" in x and "命中 0 条" in x for x in f) and len(f) == 2))
    e_out, e_skip = emit([r1, r2], idx, fmap)
    ok = len(e_out) == 2 and all("**B**" in x for x in e_out[:1]) and "**A**" in e_out[1] and e_skip == 0
    cases.append(("派生支（写侧生产者）：两行都能由卡派生，且档位取自卡不是台账", e_out, ok))
    e_out, e_skip = emit([r1, r2], {"chY.md": [idx["chY.md"][1]]}, fmap)
    cases.append(("派生支遇缺声明：不许猜字母 → 只出 1 行、skip 记 1", (e_out, e_skip),
                  len(e_out) == 1 and e_skip == 1))
    import tempfile, os
    d = tempfile.mkdtemp()
    fp = pathlib.Path(d) / "probe.md"
    fp.write_text("## 21.4 监控\n\n```bash\n# 21.4z 围栏内的注释标题\n> **档位声明（Kafka）**：**A 档 · 抄来的示例**\n```\n\n"
                  "> **档位声明（Kafka）**：**B 档 · 文档逐字**\n", encoding="utf-8")
    got = decls_of(fp)
    cases.append(("围栏内的标题与照抄的声明都不许进账（只收块外那一条）", got,
                  len(got) == 1 and got[0]["tier"].startswith("B 档") and "21.4z" not in got[0]["stack"]))
    os.path.isdir(d) and __import__("shutil").rmtree(d)
    red = 0
    for name, msgs, ok in cases:
        print(f"  [{'✓' if ok else '✗'}] {name}" + ("" if ok else f" —— {msgs}"))
        red += 0 if ok else 1
    print(f"自检：{len(cases)} 支 fixture，{red} 支未达预期")
    return 1 if red else 0


def emit(rows, decl_index, fmap):
    """把台账的档位整列**由卡派生**打印出来（抄件的生产者）。

    有了这一支，"以卡为准"就不只是红字之后的人话：改档位的动作是跑这条命令、把格子贴回表里，
    而不是先编辑表再指望闸去追。派生不出来（缺声明／落点不符）就跳过并计数，绝不猜一个字母填进格子。
    """
    out, skipped = [], 0
    for row in rows:
        f = file_for(row["ch"], fmap)
        hits = [d for d in (decl_index.get(f.name, []) if f else []) if d["key"] == row["key"]]
        if len(hits) != 1 or not where_ok(hits[0], row):
            skipped += 1
            continue
        label = "／".join(f"**{x}**" for x in sorted(tier_set(hits[0]["tier"])))
        out.append(f"{row['tool'].strip()}\t{label}（{hits[0]['file'].split('-')[0]}:{hits[0]['line']}）")
    return out, skipped


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--print" in sys.argv:
        rows, decl_index, fmap, *_ = real()
        out, skipped = emit(rows, decl_index, fmap)
        print("\n".join(out))
        print(f"[派生] 可由卡派生 {len(out)} 行；派生不出来（缺声明／落点不符）{skipped} 行——"
              "这些格子不许手填字母；档位括号外的理由是人写的，不参与对账")
        return 0 if len(out) == len(rows) else 1
    rows, decl_index, fmap, seen, fails, total_decl, ch09 = real()
    if not rows:
        print("台账闸未通过：抄件一行都没解析出来——表改形状了，先去看 §4.5c")
        return 1
    verbose = "--verbose" in sys.argv
    print(f"[覆盖] 台账 {seen['行']} 行（解析 {len(rows)} 行）；卡上带键声明 {total_decl} 条；"
          f"逐行对上 {seen['命中']} 行；落点查无文件 {seen['落点缺文件']} 行；"
          f"孤立声明 {seen['孤立声明']} 条")
    if verbose:
        for f in fails:
            print("  · " + f)
    if seen["命中"] != len(rows) or fails:
        print(f"台账闸报红 {len(fails)} 处：卡内声明与台账抄件不逐行相等")
        for f in fails:
            print(f"  ✗ {f}")
        print("[盲区] 本闸只判「台账 == 卡上写的」；卡上写的是否 == 机器上发生的，仍要人读那张卡。")
        return 1
    print(f"台账闸通过：{len(rows)} 行档位全部由对应卡片自己那行声明支撑，键整串相等、落点相符。")
    print("[盲区] 本闸只判「台账 == 卡上写的」；卡上写的是否 == 机器上发生的，仍要人读那张卡。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
