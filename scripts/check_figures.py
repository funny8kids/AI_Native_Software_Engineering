#!/usr/bin/env python3
"""图清单守卫：从手稿实测生成 FIGURE_LIST 的表与总数，并校验 BOOK_SPEC §9。

用法：
    python3 scripts/check_figures.py          # 校验，不通过则退出码 1
    python3 scripts/check_figures.py --print   # 打印可直接粘贴进 FIGURE_LIST 的表格
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MS = DOCS / "manuscript"

FENCE = re.compile(r"^(`{3,}|~{3,})(\S*)\s*$")
CAPTION = re.compile(r"^\*\*图 ([^｜]+)｜([^*]+?)\*\* — (.+)(\n|$)")


def live_mermaid(text):
    """返回真正渲染的 mermaid 源码块（跳过被外层围栏包住的示例）。"""
    lines = text.split("\n")
    blocks, i = [], 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        fence, lang, width = m.group(1), m.group(2), len(m.group(1))
        i += 1
        body = []
        while i < len(lines):
            m2 = FENCE.match(lines[i])
            if m2 and m2.group(1)[0] == fence[0] and len(m2.group(1)) >= width:
                i += 1
                break
            body.append(lines[i])
            i += 1
        if lang == "mermaid":
            blocks.append("\n".join(body))
    return blocks


def diagram_type(block):
    head = block.strip().split("\n")[0].strip()
    if head.startswith("flowchart"):
        return "flowchart"
    if head.startswith("sequenceDiagram"):
        return "sequence"
    if head.startswith("stateDiagram"):
        return "state"
    return head.split()[0] if head.split() else "?"


SKIP_PREFIX = ("style ", "classDef ", "class ", "linkStyle ", "click ")


def node_count(block):
    """按图型计算"画布上的可读对象数"——BOOK_SPEC §9 的 12 上限指的就是这个。

    思维导图例外：分支与叶分别计数（分支是读者的读图路径，叶是分支的说明文字），
    两者各自 ≤12；其余图型统一按卡片数 ≤12。
    """
    lines = [l.strip() for l in block.strip().split("\n")]
    kind = diagram_type(block)
    body = [l for l in lines[1:]
            if l and not l.startswith(SKIP_PREFIX) and l not in ("end", "direction TB", "direction LR")]
    if kind == "mindmap":
        depth = []
        for l in lines[1:]:
            if not l.strip():
                continue
            depth.append((len(l) - len(l.lstrip()), l.strip()))
        indent = [d for d, _ in depth if d > 0]
        branches = sum(1 for d, _ in depth if indent and d == min(indent))
        leaves = sum(1 for d, _ in depth if indent and d > min(indent))
        return max(branches, leaves)
    if kind == "gantt":
        return sum(1 for l in body if ":" in l and not l.startswith(("title", "dateFormat", "axisFormat")))
    if kind == "sequence":
        return len({l.split()[1] for l in body if l.startswith(("participant ", "actor "))}) or \
            len({l.split()[0] for l in body if "->" in l})
    if kind == "state":
        states = set()
        for l in body:
            if l.startswith("state ") and "-->" not in l:
                states.add(l.split()[1])
            for a, b in re.findall(r"(\w+)\s*-->\s*(?:\[[^\]]*\]\s*)?(\w+)", l):
                states.update((a, b))
        return len(states - {"[*]"})
    ids = set()
    for l in body:
        if l.startswith("subgraph"):
            continue
        ids.update(re.findall(r"(?<![\w.-])([A-Za-z_][\w_]*)\s*(?:\[[^\]]*]|\([^)]*\)|\{[^}]*\})", l))
        ids.update(re.findall(r"^\s*([A-Za-z_][\w_]*)\s*$", l))
    return len(ids)


def captions(text):
    return [(m.group(1).strip(), m.group(2).strip())
            for m in re.finditer(r"^\*\*图 ([^｜]+)｜([^*]+?)\*\*", text, re.M)]


def main():
    problems, rows = [], []
    total_ms = 0
    for path in sorted(MS.glob("*.md")):
        text = path.read_text()
        blocks = live_mermaid(text)
        if not blocks:
            continue
        caps = captions(text)
        kinds = "/".join(sorted({diagram_type(b) for b in blocks}))
        ids = [c[0] for c in caps]
        stem = path.name[:-3]
        if path.name.startswith("ch"):
            if len(blocks) < 2:
                problems.append(f"{stem}: 只有 {len(blocks)} 张图，低于 BOOK_SPEC §9 的 2 张下限")
            if len(blocks) > 5:
                problems.append(f"{stem}: {len(blocks)} 张图，超过 5 张上限")
            if len(caps) != len(blocks):
                problems.append(f"{stem}: 图注 {len(caps)} 条 ≠ 图 {len(blocks)} 张")
            nums = [int(i.rsplit("-", 1)[1]) for i in ids] if ids else []
            if nums and nums != list(range(1, len(nums) + 1)):
                problems.append(f"{stem}: 图号未按阅读顺序递增 → {ids}")
        for b, cid in zip(blocks, ids + ["?"] * len(blocks)):
            n = node_count(b)
            if n > 12:
                problems.append(f"{stem} 图 {cid}: 可读对象 {n} > 12（BOOK_SPEC §9 节点定义）")
        total_ms += len(blocks)
        if stem == "README":
            stem = "README（书稿总览，非章）"
        rows.append((stem, len(blocks), "、".join(ids), kinds))

    site = []
    for name in ("README.md", "guide.md"):
        text = (DOCS / name).read_text()
        blocks = live_mermaid(text)
        kinds = "/".join(sorted({diagram_type(b) for b in blocks})) if blocks else "—"
        site.append((name[:-3], len(blocks), "、".join(c[0] for c in captions(text)), kinds))
    site_total = sum(n for _, n, _, _ in site)

    if "--print" in sys.argv:
        for stem, n, ids, kinds in rows:
            print(f"| {stem} | {n} | {ids} | {kinds} |")
        for stem, n, ids, kinds in site:
            print(f"| {stem}（站点页） | {n} | {ids} | {kinds} |")

    print(f"手稿 {len(rows)} 个文件 / {total_ms} 张图；站点页 {site_total} 张；合计 {total_ms + site_total} 张。")
    if problems:
        print("\n不通过：")
        for p in problems:
            print(" -", p)
        return 1
    print("BOOK_SPEC §9 校验通过：每章 2–5 张、图号递增、图注与图一一对应、节点 ≤12。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
