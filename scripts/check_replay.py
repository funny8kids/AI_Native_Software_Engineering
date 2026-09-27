#!/usr/bin/env python3
"""第十一条守卫：声称「本机实跑」的读数块，每一行都要有打印依据。

判据分两支，两支的量的是两种形状，盲区各自打印：

**甲支（成对）**：对每个**在文档里真紧邻**的「```python 块 + ```text 块」对，把 python 块里
每条 print 编译成一个**输出正则**（字面段转义、f-string 插值段换成 `.+`），text 块的非空行
必须匹配其中至少一条。匹配不到 = 作者手写的"输出"，A 档口径当场失效。
 adjacency 的口径在 2026-09-27 第二十四轮改过一次：旧实现先把别种语言的围栏整块丢掉再判相邻，
于是「python → bash → text」这种排布里 python 与 text 会被错配成一对，当时实测全站 4 处、
错配进来的判据行也全都绿着——**匹配上不等于配对对**。那 4 个数字是改动当时的一次量测，
不是今天的读数；今天的读数只看本闸打印的那两行覆盖率。现在按文档实际围栏序取邻居。

**乙支（同围栏回显）**：手稿里还有一大类读数压根不成对——命令与输出写在同一个围栏里
（第一行 `$ cmd`，往下是输出），而这类围栏的语言是 ```bash，甲支的解析面以前连看都看不到。
乙支判的是**新鲜度**：回显命令必须整条命中白名单 `python3 scripts/check_<名>.py [单面长选项]
[ | head|tail -n N ]`，命中就把这条守卫**现在**跑一遍（不带 shell，argv 直调），输出非空行
与贴出来的非空行**逐字相等**才算过；台账涨一行而忘了重跑贴件，这一支当场红。

乙支为什么只收这一种形状（界要写清楚，别当成"够用就行"）：
① **不许执行书里写的任意命令**——全站含 `$ ` 回显的围栏与命令各有多少、其中多少条带写入或进程
副作用（git / rm / cp / install / curl 之类），全部由本闸那行覆盖率读数自己打印；把它们塞进
bash 执行等于让守卫自己跑稿件里的命令。白名单只放"本仓库 scripts/ 下那支具名守卫"，
它们的只读性是各自的契约。
② **不判历史取证读数**——`$ python3 scripts/check_figures.py` 那种"故意撞红、临时件读数后即删"
的贴件，现跑必然不等（现场已经不在了），它 honest 地写在正文里，但机器分不清"当时"与"现在"。
这种读数需要一枚可机检的历史标记才能进判据，本轮先不判，打印成「输出在别处」这一格。

豁免（分类计数、全部打印，不做静默豁免）：`$ ` 命令回显 / 以三个等号开头的分节标签 /
`EXIT=`·`退出码`·`rc` 开头的退出码行（由 shell 产生，不在 python 里）。
整块交人工：多参 print、带 sep=/end= 的 print、语法不可解析的块——宁可交人工也不猜。

用法：python3 scripts/check_replay.py [--verbose] [--selftest]
"""
import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MD = sorted((ROOT / "docs" / "manuscript").glob("*.md"))
ANY = re.compile(r"^```([a-zA-Z0-9_-]*)[ \t]*$")
CLOSE = re.compile(r"^```[ \t]*$")
ECHO = re.compile(r"^\$\s+(.*)$")
GUARD_CMD = re.compile(r"^python3 scripts/check_([a-z_]+)\.py( --[a-z-]+)?"
                       r"( \| (head|tail) -n ([1-9]\d*))?$")
SELF = "check_replay"
ECHO_LANGS = {"bash", "sh", "shell", "console", "zsh", "text", ""}
EXEMPT = [("命令回显", re.compile(r"^\$\s")),
          ("分节标记", re.compile(r"^={3,}\s\S.*")),
          ("退出码行", re.compile(r"^(EXIT=|退出码|rc[ =])"))]


def fences(text):
    """按 CommonMark 口径取全部围栏，保序返回 (lang, body)；语言小写，未标注记成空串。"""
    out, i, lines = [], 0, text.splitlines()
    while i < len(lines):
        m = ANY.match(lines[i])
        if m:
            lang, body, i = m.group(1).lower(), [], i + 1
            closed = False
            while i < len(lines):
                if CLOSE.match(lines[i]):
                    closed = True
                    i += 1
                    break
                body.append(lines[i])
                i += 1
            if not closed:
                raise SystemExit("围栏开了没关（%s 块）——不在半途读数上下结论" % (lang or "未标注"))
            out.append((lang, "\n".join(body)))
            continue
        i += 1
    return out


def chunks(text):
    """兼容旧调用：只取 python / text 两种块（甲支要的是真紧邻，故由 pairs() 直接走 fences）。"""
    return [(l, b) for l, b in fences(text) if l in ("python", "text")]


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
    """甲支判据：返回 (报红行, 进入判据的行数, 豁免计数, 是否交人工)。"""
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


def run_guard(cmd, runner=None):
    """乙支执行面：整条命令已由 GUARD_CMD 白名单收住，argv 直调、不经 shell。
    runner 可注入（纯函数化：判据=比较，执行=参数），自检不必真跑守卫。"""
    m = GUARD_CMD.match(cmd)
    argv = ["python3", f"scripts/check_{m.group(1)}.py"]
    if m.group(2):
        argv.append(m.group(2).strip())
    lines = runner(argv) if runner else _spawn(argv)
    how, n = m.group(4), m.group(5)
    if how:
        n = int(n)
        lines = lines[:n] if how == "head" else lines[-n:]
    return [ln for ln in lines if ln.strip()]


def _spawn(argv):
    r = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
    return (r.stdout + r.stderr).splitlines()


def echo_judge(cmd, pasted, runner=None):
    """乙支判据（纯比较）：返回 (状态, 报红行)。状态 ∈ {判, 自指, 形状不判, 非守卫, 输出在别处}。"""
    if not pasted:
        return "输出在别处", []
    if SELF in cmd:
        return "自指", []
    if not GUARD_CMD.match(cmd):
        return ("形状不判", []) if "scripts/check_" in cmd else ("非守卫", [])
    got = run_guard(cmd, runner)
    fails = [] if got == pasted else [(pasted, got)]
    return "判", fails


def echo_blocks(text):
    """取每个围栏里的 (回显命令, 其后贴出的非空输出行)，命令到下一条回显为止。"""
    out = []
    for lang, body in fences(text):
        if lang not in ECHO_LANGS:
            continue
        lines = body.splitlines()
        for k, ln in enumerate(lines):
            m = ECHO.match(ln)
            if not m:
                continue
            nxt = next((j for j in range(k + 1, len(lines)) if ECHO.match(lines[j])), len(lines))
            pasted = [x for x in lines[k + 1:nxt] if x.strip()]
            out.append((m.group(1).strip(), pasted))
    return out


def pair_scan(md_files):
    """甲支：真紧邻的 python→text 对。返回 (报红, 覆盖计数)。"""
    pairs = judged_all = blind = 0
    fails_all, ex_all, manual_files = [], {}, []
    for f in md_files:
        cs = fences(f.read_text(encoding="utf-8"))
        for i in range(len(cs) - 1):
            (l1, t1), (l2, t2) = cs[i], cs[i + 1]
            if (l1, l2) != ("python", "text") or not t2.strip():
                continue
            pairs += 1
            fails, judged, ex, manual = judge(t1, t2)
            for k, v in ex.items():
                ex_all[k] = ex_all.get(k, 0) + v
            if manual:
                manual_files.append(f.name)
                blind += sum(1 for ln in t2.splitlines()
                             if ln.strip() and not any(p.match(ln) for _, p in EXEMPT))
                continue
            judged_all += judged
            fails_all += [(f.name, ln) for ln in fails]
    return fails_all, {"甲对": pairs, "甲判": judged_all, "甲交人工": len(manual_files),
                       "甲盲区行": blind, "豁免": ex_all}


def echo_scan(md_files, runner=None, skip_pairs=True):
    """乙支：同围栏回显的现跑对账。返回 (报红, 覆盖计数)。"""
    cnt = {"回显": 0, "判": 0, "等": 0, "不等": 0, "自指": 0, "形状不判": 0,
           "非守卫": 0, "输出在别处": 0, "贴出行": 0}
    fails = []
    for f in md_files:
        for cmd, pasted in echo_blocks(f.read_text(encoding="utf-8")):
            cnt["回显"] += 1
            st, fl = echo_judge(cmd, pasted, runner)
            cnt[st] += 1
            if st == "判":
                cnt["贴出行"] += len(pasted)
                if fl:
                    cnt["不等"] += 1
                    fails.append((f.name, cmd, fl[0][0]))
                else:
                    cnt["等"] += 1
    return fails, cnt


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

CMD_CASES = [
    # (命令, 现跑输出, 贴出的输出, 期望状态, 期望报红)
    ("python3 scripts/check_tier_ledger.py",
     ["[覆盖] 台账 59 行", "台账闸通过：59 行"], ["[覆盖] 台账 59 行", "台账闸通过：59 行"],
     "判", False),
    ("python3 scripts/check_tier_ledger.py",
     ["[覆盖] 台账 60 行"], ["[覆盖] 台账 59 行"],               # 台账涨了没重跑贴件
     "判", True),
    ("python3 scripts/check_tier_ledger.py --print | head -n 1",
     ["第一行", "第二行"], ["第一行"],                            # head 由本闸自己截
     "判", False),
    ("python3 scripts/check_tier_ledger.py --print | tail -n 1",
     ["第一行", "第二行"], ["第二行"],
     "判", False),
    ("git push origin main", ["Everything up-to-date"], ["Everything up-to-date"],
     "非守卫", False),
    ("python3 scripts/check_tier_ledger.py --print | awk -F'\\t' '{print $2}'",
     ["x"], ["x"], "形状不判", False),
    ("python3 scripts/check_replay.py", ["[覆盖] ..."], ["[覆盖] ..."], "自指", False),
    ("python3 scripts/check_figures.py", [], [], "输出在别处", False),
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
    # 乙支：执行面全部注入，自检一条命令都不真跑
    for cmd, live, pasted, want_st, want_red in CMD_CASES:
        st, fl = echo_judge(cmd, pasted, runner=lambda a, live=live: list(live))
        if st != want_st:
            bad.append(f"乙支「{cmd[:40]}」：状态期望 {want_st}，实测 {st}")
        if bool(fl) != want_red:
            bad.append(f"乙支「{cmd[:40]}」：报红期望 {want_red}，实测 {bool(fl)}")
    # 相邻口径：中间夹一个 bash 围栏就不许配成一对
    doc = "```python\nprint('x')\n```\n```bash\necho hi\n```\n```text\nx\n```"
    cs = fences(doc)
    n = sum(1 for i in range(len(cs) - 1)
            if (cs[i][0], cs[i + 1][0]) == ("python", "text"))
    if n:
        bad.append(f"相邻口径：夹着 bash 围栏的两块被配成了 {n} 对")
    if bad:
        for b in bad:
            print("  ✗ " + b)
        print(f"复跑闸自检未通过：{len(bad)} 条")
        return 1
    print("复跑闸自检通过：甲支两侧极性（坏样本必红 / 插值真读数必不红）+ 八条桩 + 豁免计数；"
          "乙支八条命令桩（等／不等／截断／四类交人工）全部注入执行，不真跑守卫；相邻口径带桩。")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    verbose = "--verbose" in sys.argv
    pfails, pc = pair_scan(MD)
    efails, ec = echo_scan(MD)
    print(f"[甲·成对] python→text 真紧邻对 {pc['甲对']} 组；进入判据的读数行 {pc['甲判']} 行；"
          f"整块交人工 {pc['甲交人工']} 组，这些块里的读数行 {pc['甲盲区行']} 行没进判据"
          "（盲区，不是通过）；豁免 "
          + "、".join(f"{k} {v} 行" for k, v in sorted(pc['豁免'].items())))
    print(f"[乙·同围栏] 含 $ 回显的命令 {ec['回显']} 条：现跑对账 {ec['判']} 条"
          f"（逐字相等 {ec['等']}／不等 {ec['不等']}，贴出行合计 {ec['贴出行']} 行）、"
          f"输出在别处 {ec['输出在别处']} 条（回显下面同围栏里没有行：多半是成对块的另一半，"
          "也可能是块末的一句命令或一行注释——这一格里藏着「故意撞红后删掉现场」的历史取证读数）、"
          f"形状不判 {ec['形状不判']} 条（守卫命令但管道里有白名单外环节）、"
          f"自指 {ec['自指']} 条、非守卫命令 {ec['非守卫']} 条（含带写入的那一类，一条码都不跑）")
    if verbose:
        for name, cmd, pairs_ in efails:
            print(f"  [{name}] {cmd}")
            for pasted, got in pairs_:
                print("      贴出：", " ⏎ ".join(pasted[:6]))
                print("      现跑：", " ⏎ ".join(got[:6]))
    if pc["甲对"] == 0 or pc["甲判"] == 0:
        print("复跑闸未通过：甲支覆盖集为空——没有读数被量到，这不叫通过")
        return 1
    if ec["判"] == 0:
        print("复跑闸未通过：乙支覆盖集为空——同围栏回显一条都没进判据，这一支已经形同装饰")
        return 1
    if pfails or efails:
        if pfails:
            print(f"甲支报红 {len(pfails)} 行：同段代码里没有任何 print 会产出这一行")
            for name, ln in pfails:
                print(f"  ✗ [{name}] 「{ln[:76]}」")
        if efails:
            print(f"乙支报红 {len(efails)} 条：贴出来的输出与这条守卫现在跑出来的不等（读数陈旧，或命令不是原样）")
            for name, cmd, _ in efails:
                print(f"  ✗ [{name}] $ {cmd}")
        return 1
    print(f"复跑闸通过：甲支 {pc['甲判']} 行逐行可由同块某条 print 的输出模板匹配；"
          f"乙支 {ec['等']} 条现跑逐字相等。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
