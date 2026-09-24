#!/usr/bin/env python3
"""图清单守卫：从手稿实测生成 FIGURE_LIST 的表与总数，并校验 BOOK_SPEC §9。

用法：
    python3 scripts/check_figures.py          # 校验，不通过则退出码 1
    python3 scripts/check_figures.py --print   # 打印可直接粘贴进 FIGURE_LIST 的表格
    python3 scripts/check_figures.py --selftest # 图引用判据的三条负对照
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


CAP_LINE = re.compile(r"^\*\*图 ([^｜]+)｜")
REF = re.compile(r"图\s*([A-Za-z0-9]{1,4}-[0-9]{1,2})")


def body_lines(text):
    """去掉围栏内部与图注行本身：只留真会渲染出来、且不算自指的正文行。"""
    out, fence = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*(`{3,}|~{3,})(\w*)\s*$", line)
        if m:
            tick, lang = m.group(1)[0] * 3, m.group(2)
            if fence is None:
                fence = (tick, len(m.group(1)))
            elif tick == fence[0] and len(m.group(1)) >= fence[1] and not lang:
                fence = None
            continue
        if fence is None and not CAP_LINE.match(line):
            out.append(line)
    return out


def inline_refs(text):
    return [m.group(1) for l in body_lines(text) for m in REF.finditer(l)]


def check_refs(corpus):
    """corpus: [(名字, 全文)] → (问题列表, 引用条数, 图注条数)。

    两条判据：
    1. 正文里每一处「图 X-Y」都必须落到全书某条真图注上（悬空引用 = 读者点空）。
    2. 每条图注必须在**自己那一节**的正文里至少被指一次（无锚图 = 读者路过而不停下）。
    覆盖集自证：引用数为 0 不是"通过"而是口径失效，由 --selftest 的对照 B 把住。
    """
    ids = {c[0] for _, t in corpus for c in captions(t)}
    problems = []
    n_ref = 0
    for name, text in corpus:
        found = set(inline_refs(text))
        n_ref += len(inline_refs(text))
        for rid in sorted(found - ids):
            problems.append(f"{name}: 正文引用「图 {rid}」在全书图注里查无此图")
        stem = name[:-3]
        for cap_id, _ in captions(text):
            if cap_id not in found and name.startswith("ch"):
                problems.append(f"{stem}: 图 {cap_id} 在正文里没有任何指向（无锚图）")
    return problems, n_ref, len(ids)


FIXTURES = {
    "四种前缀写法都算锚，围栏内与图注行不算引用": (
        """正文里 图 4-3、图4-3、见图 4-3、（图 4-3）都指同一张。

```mermaid
graph LR
  a[代码块里的 图 9-9 不算] --> b
```

**图 4-3｜题** — 图注行自己不算指向自己。
""",
        4, 0),
    "图注没有正文锚 → 报一条": (
        """这张图谁都没提。

**图 6-1｜题** — 无人引用。
""",
        0, 1),
    "正文引用了不存在的图 → 报一条": (
        """只有 图 6-1 这一张，另见 图 6-2。

**图 6-1｜题** — 只有这一张。
""",
        2, 1),
    "案例章前缀（C1-x）与罗马前缀（I-x）同属一个口径": (
        """读 图 C1-1 与 图 I-2 两张。

**图 C1-1｜题** — 案例章图。

**图 I-1｜题** — 附录图，无人引用。
""",
        2, 2),
}


def selftest(corpus):
    """已知答案的 fixture 对照 + 真书基准的覆盖读数。"""
    ok = True
    base, n_ref, n_id = check_refs(corpus)
    anchored = sum(1 for n, t in corpus if n.startswith("ch")
                   for c in captions(t) if c[0] in set(inline_refs(t)))
    print(f"[基准] {len(corpus)} 文件 / 图注 {n_id} 条 / 正文引用 {n_ref} 条 / "
          f"有锚图 {anchored} 条 / 报红 {len(base)} 条")
    if n_ref == 0:
        print("  ✗ 基准抓到 0 条引用——口径没有读者，撤掉这条判据或修口径")
        ok = False
    for i, (label, (text, want_ref, want_prob)) in enumerate(FIXTURES.items(), 1):
        corpus_fx = [("ch99-fixture.md", text)]
        probs, got_ref, _ = check_refs(corpus_fx)
        good = (got_ref == want_ref and len(probs) == want_prob)
        ok &= good
        print(f"  对照 {chr(64+i)} {label} → 引用 {got_ref}（应 {want_ref}）"
              f"/ 报红 {len(probs)}（应 {want_prob}）{'✔' if good else '✗'}")
    return 0 if ok else 1


def main():
    corpus = []
    problems, rows = [], []
    total_ms = 0
    for path in sorted(MS.glob("*.md")):
        text = path.read_text()
        corpus.append((path.name, text))
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
        corpus.append((name, text))
        blocks = live_mermaid(text)
        kinds = "/".join(sorted({diagram_type(b) for b in blocks})) if blocks else "—"
        site.append((name[:-3], len(blocks), "、".join(c[0] for c in captions(text)), kinds))
    site_total = sum(n for _, n, _, _ in site)

    ref_problems, n_ref, n_cap = check_refs(corpus)
    problems += ref_problems

    if "--print" in sys.argv:
        for stem, n, ids, kinds in rows:
            print(f"| {stem} | {n} | {ids} | {kinds} |")
        for stem, n, ids, kinds in site:
            print(f"| {stem}（站点页） | {n} | {ids} | {kinds} |")

    print(f"手稿 {len(rows)} 个文件 / {total_ms} 张图；站点页 {site_total} 张；合计 {total_ms + site_total} 张。")
    print(f"正文图引用 {n_ref} 条 / 全书图注 {n_cap} 条 / 悬空 {len(ref_problems)} 条。")
    if problems:
        print("\n不通过：")
        for p in problems:
            print(" -", p)
        return 1
    print("BOOK_SPEC §9 校验通过：每章 2–5 张、图号递增、图注与图一一对应、节点 ≤12、正文图引用全部可解析。")
    return 0


def read_corpus():
    corpus = [(p.name, p.read_text()) for p in sorted(MS.glob("*.md"))]
    corpus += [(n, (DOCS / n).read_text()) for n in ("README.md", "guide.md")]
    return corpus


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest(read_corpus()))
    sys.exit(main())
