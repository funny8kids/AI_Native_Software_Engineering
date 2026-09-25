#!/usr/bin/env python3
"""第十一条守卫：声称「本机实跑」的读数块，每一行都要有打印依据。

判据：对每个「```python 块 + 紧邻 ```text 块」的相邻对，把 python 块里每条 print 编译成
一个**输出正则**（字面段转义、f-string 插值段换成 `.+`），text 块的非空行必须匹配其中至少一条。
匹配不到 = 作者手写的"输出"，A 档口径当场失效（本轮真抓到一条：21.4d 的滞后反例行，
同段脚本里没有一句 print 打印它）。

为什么不用"字面开头"当判据：循环里的 print(f"  {s} -> {d}") 以变量开场，前缀判据把这类
真读数判成违规——第一版实测 34 条假红，全是这一形。模板匹配是它的修正版。

豁免（分类计数、全部打印，不做静默豁免）：`$ ` 命令回显 / 以三个等号开头的分节标签 /
`EXIT=`·`退出码`·`rc` 开头的退出码行（由 shell 产生，不在 python 里）。
整块交人工：多参 print、带 sep=/end= 的 print、语法不可解析的块——宁可交人工也不猜。

用法：python3 scripts/check_replay.py [--verbose] [--selftest]
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MD = sorted((ROOT / "docs" / "manuscript").glob("*.md"))
OPEN = re.compile(r"^```(python|text)[ \t]*$")
CLOSE = re.compile(r"^```[ \t]*$")
EXEMPT = [("命令回显", re.compile(r"^\$\s")),
          ("分节标记", re.compile(r"^={3,}\s\S.*")),
          ("退出码行", re.compile(r"^(EXIT=|退出码|rc[ =])"))]


def chunks(text):
    """按 CommonMark 口径配对围栏；只取 python / text 两种块。"""
    out, i, lines = [], 0, text.splitlines()
    while i < len(lines):
        m = OPEN.match(lines[i])
        if m:
            lang, body, i, closed = m.group(1), [], i + 1, False
            while i < len(lines):
                if CLOSE.match(lines[i]):
                    i += 1
                    closed = True
                    break
                body.append(lines[i])
                i += 1
            if not closed:
                raise SystemExit(f"围栏开了没关（{lang} 块）——不在半途读数上下结论")
            out.append((lang, "\n".join(body)))
            continue
        i += 1
    return out


def print_templates(src):
    """把每条 print 的输出形状编译成正则；返回 (模板, 是否整块交人工)。"""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [], True
    pats, manual = [], False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            continue
        kw = {k.arg for k in node.keywords}
        if kw - {"file", "flush"}:       # sep= / end= 改了行形状，交人工
            manual = True
            continue
        if not node.args:
            continue
        seg = []
        for i_a, a in enumerate(node.args):
            if i_a:
                seg.append(re.escape(" "))      # 多参 print 的默认分隔符是一个空格
            if isinstance(a, ast.JoinedStr):
                for v in a.values:
                    seg.append(re.escape(v.value) if isinstance(v, ast.Constant)
                               and isinstance(v.value, str) else r".+")
            elif isinstance(a, ast.Constant) and isinstance(a.value, str):
                seg.append(re.escape(a.value))
            else:
                seg.append(r".+")               # 整体是一个表达式 → 通配，不算"没有依据"
        for b in "".join(seg).split(re.escape("\n")):
            if b.strip():
                pats.append(re.compile(b))
    return pats, manual


def judge(py, txt):
    """返回 (报红行, 进入判据的行数, 豁免计数, 是否交人工)。"""
    pats, manual = print_templates(py)
    ex, fails, judged = {}, [], 0
    for ln in txt.splitlines():
        if not ln.strip():
            continue
        hit = next((name for name, pat in EXEMPT if pat.match(ln)), None)
        if hit:
            ex[hit] = ex.get(hit, 0) + 1
            continue
        if manual:
            continue
        if not pats:
            return [], 0, ex, True
        judged += 1
        if not any(p.search(ln) for p in pats):
            fails.append(ln)
    return fails, judged, ex, manual


CASES = [
    ("字面读数对得上", 'print("抖动反例：1x")', "抖动反例：1x", 0, False),
    ("手写的一行必须红", 'print("抖动反例：1x")', "抖动反例：1x\n滞后反例：代码里没有这句", 1, False),
    ("循环里的插值读数不算违规",
     'for s, d in sorted(edges):\n    print(f"  {s:24s} -> {d}")',
     "  demoapp.api              -> demoapp.config", 0, False),
    ("插值开场的表格行不算违规",
     'print(f"30 天错误预算 = {w30} x {bad:.3f} = {budget:.1f} 分钟不可用")\n'
     'print(f"{name:11} {long_m:5} {short_m:4} {br:6}x | {consumed:6.2f}m={pct:4.0f}%")',
     "30 天错误预算 = 43200 x 0.001 = 43.2 分钟不可用\npage-快档        60    5   14.4x |   0.86m=   2%",
     0, False),
    ("三类豁免都不进分母", 'print("ok")', "$ python3 x.py\n==== 样本 A ====\nEXIT=0\nok", 0, False),
    ("多参 print 按单空格拼接成形", 'print("抖动反例", 1)', "抖动反例 1", 0, False),
    ("end= 改了行形状 → 整块交人工", 'print("a", end="")', "手写的一行没人打印", 0, True),
    ("没有一句 print 的块交人工", "x = 1", "随便一行读数", 0, True),
]


def selftest():
    bad = []
    for name, py, txt, want_fails, want_manual in CASES:
        fails, judged, ex, manual = judge(py, txt)
        if manual != want_manual:
            bad.append(f"{name}：交人工期望 {want_manual}，实测 {manual}")
            continue
        if len(fails) != want_fails:
            bad.append(f"{name}：期望报红 {want_fails} 行，实测 {len(fails)} 行 {fails}")
    _, _, ex, _ = judge('print("ok")', "$ x\n==== A ====\nEXIT=0\nok")
    if sum(ex.values()) != 3:
        bad.append(f"豁免计数：期望 3 行，实测 {ex}")
    if bad:
        for b in bad:
            print("  ✗ " + b)
        print(f"复跑闸自检未通过：{len(bad)} 条")
        return 1
    print("复跑闸自检通过：两侧极性（坏样本必红 / 插值真读数必不红）+ 八条桩 + 豁免计数。")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    verbose = "--verbose" in sys.argv
    pairs = judged_all = blind = 0
    fails_all, ex_all, manual_blocks = [], {}, []
    for f in MD:
        cs = chunks(f.read_text(encoding="utf-8"))
        for i in range(len(cs) - 1):
            (l1, t1), (l2, t2) = cs[i], cs[i + 1]
            if (l1, l2) != ("python", "text") or not t2.strip():
                continue
            pairs += 1
            fails, judged, ex, manual = judge(t1, t2)
            for k, v in ex.items():
                ex_all[k] = ex_all.get(k, 0) + v
            if manual:
                manual_blocks.append(f.name)
                blind += sum(1 for ln in t2.splitlines()
                             if ln.strip() and not any(pat.match(ln) for _, pat in EXEMPT))
                continue
            judged_all += judged
            fails_all += [(f.name, ln) for ln in fails]
            if verbose:
                print(f"  [{f.name}] 判 {judged} 行 / 豁免 {ex}")
    print(f"[覆盖] python→text 相邻对 {pairs} 组；进入判据的读数行 {judged_all} 行；"
          f"整块交人工 {len(manual_blocks)} 组"
          + (f"（{', '.join(sorted(set(manual_blocks)))}）" if manual_blocks else "")
          + f"，这些块里的读数行 {blind} 行没进判据（盲区，不是通过）"
          + "；豁免 " + "、".join(f"{k} {v} 行" for k, v in sorted(ex_all.items())))
    if pairs == 0 or judged_all == 0:
        print("复跑闸未通过：覆盖集为空——没有读数被量到，这不叫通过")
        return 1
    if fails_all:
        print(f"复跑闸报红 {len(fails_all)} 行：同段代码里没有任何 print 会产出这一行")
        for name, ln in fails_all:
            print(f"  ✗ [{name}] 「{ln[:76]}」")
        return 1
    print(f"复跑闸通过：{judged_all} 行读数逐行都能由同块某条 print 的输出模板匹配。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
