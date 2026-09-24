#!/usr/bin/env python3
"""第八条守卫·配色闸：颜色只有 token 一个出处，且每一对前景/底色**合成后**真的看得清。

为什么需要第八条：前七条量的是"有没有、看不看得见、点不点得动"，量不到"看得清不清"。
2026-09-24 的实测就是例子——浅档曾是纯白 #FFFFFF + 高饱和靛蓝，命中测试、几何、字号
全部通过，读者只有一句"不够高级"。而"高级"不能靠感觉收口，得换成可判的三件事：

① token 纪律（静态）：theme.css 里除两个令牌块之外不得出现字面量色值；例外只有两类
   （mask-image 的黑白遮罩、@media print 的强制黑白）。代码高亮**不是**例外——曾经它是，
   那段豁免让深档一整块八字面量代码色合法存在，改版全程没报过红。
   书稿 markdown 里全部 mermaid `style/classDef/linkStyle` 指令行同理（条数由本闸自己
   打印，注释里不复述，免得变成一条会腐烂的静态计数）：mermaid 不认
   `var()`（实测写 var() 的那条 style 会让整张图渲染失败），所以图版只能带字面量——
   那这些字面量就必须逐个等于 theme.css 里 --c-plate-* 令牌的值，否则就是第二个事实源。
   同一条纪律再往下一层：index.html 的 JS 兜底色、以及 docs/assets 下位图版画的
   **锚点回执**（张数由本闸自己打印，注释里不复述：位图会增删，写死的计数第一天就旧了。
   位图是派生件，DOM 侧只有一个 <img> 盒子，浏览器口径量不到它里面，只能拿重着色
   脚本自己落的回执对账）。执行这条纪律的脚本是 scripts/sync_plate_literals.py——
   守卫只判"字面值 ≠ 令牌值"，判不了"谁来把它对齐"。
   还有一层是对比度**看不见**的：图版底色族（由书稿 fill 现算出的那些 --c-plate-*）两两
   之间的可辨性。对比度只看亮度，两档只要都"够亮"就一律 1.0x:1 永远绿，而它们是图例的
   词表——撞在一起就等于少一档。这里用 CIELAB 的 ΔE 判（族内两两 ≥4、每档离纸底 ≥4），
   并把换算钉在四个公开已知答案上（lab_selftest，对不上直接中止）。
② 正文对比度（浏览器）：逐页逐文本节点取前景色，沿祖先链**逐层 alpha 合成**出真正的底色，
   再算 WCAG 对比度；正文 ≥4.5:1，大字（≥24px，或 ≥18.66px 且加粗）≥3:1。
   不合成就算 = 假绿：顶栏、渐隐层、封面高光都是半透明的。
③ 图版对比度（浏览器）：图里的文字不能用"卡片底色"当背景——黑节点上的白字会被算成
   白纸上白字。这里用 elementsFromPoint 从字形中心往下找**真正垫在它后面的那一层**
   （节点的 rect/path 或卡片底），合成后再判 ≥3:1。
④ 键盘焦点环（浏览器）：焦点指示是"非文本对比度"（WCAG 1.4.11 ≥3:1），前三个房间都量不到
   它——它判的是像素而不是声明。真按 Tab 逐站取视口像素：环宽、环色是否就是全站那一个强调色、
   环在四侧里至少两侧画得出来、控件留在自己祖先滚动口内的比例、环对邻边的对比度。

外加三条自证：真点 #btn-theme 并断言 data-theme 与令牌值同时翻转（否则"换了档"是假的）；
覆盖集与独立口径（TreeWalker 数文本节点）对账，空集或漏量即中止；焦点判据先过
focus_selftest()（一支干净记录不许报红、九支坏记录各报自己那一条）。

用法：
    python3 scripts/check_palette.py                        # 全量：62 条路由 × 1280/1440/390 × 浅/深
    python3 scripts/check_palette.py --mutate               # 变异自检：P1–P19 各自要能被打红
    python3 scripts/check_palette.py --screenshot DIR       # 供人工逐项复核的截图
    python3 scripts/check_palette.py --report               # 打印对比度最低的若干对前景/底色

约定：零 CDN、零外部依赖，自带一次性本地服务器。退出码 0 = 全绿。
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import CDP, free_port  # noqa: E402
from check_legibility import dismiss_cover, same_landing  # noqa: E402  # 揭幕那条链只写一份，五条闸共用

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SIDEBAR = DOCS / "_sidebar.md"
THEME = DOCS / "theme.css"

MIN_TEXT_RATIO = 4.5      # 正文
MIN_LARGE_RATIO = 3.0     # 大字（≥24px，或 ≥18.66px 且 bold）与图内文字
NARROW = 768
VIEWPORTS = [(1280, 900, False), (1440, 900, False), (390, 844, True)]


# ============================== 静态：token 纪律 ==============================

def parse_tokens(css: str) -> tuple[dict[str, str], dict[str, str]]:
    """取出 :root 与 html[data-theme='dark'] 两个块的令牌表。"""
    def block(pat: re.Pattern) -> dict[str, str]:
        m = pat.search(css)
        if not m:
            raise SystemExit("找不到主题令牌块——令牌块改名会让本闸静默失明，先修口径")
        body = m.group(1)
        return {k.strip(): v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body)}

    light = block(re.compile(r":root\s*\{(.*?)\n\}", re.S))
    dark = block(re.compile(r"html\[data-theme='dark'\]\s*\{(.*?)\n\}", re.S))
    if not light or not dark:
        raise SystemExit("令牌块解析出空表——口径可疑，中止")
    return light, dark


LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)")


def strip_comments(css: str) -> str:
    """注释里的色值是说明文字不是样式。用等量换行占位，保证去注释后行号与原文对齐。"""
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)


def token_line_spans(css: str) -> list[tuple[int, int]]:
    """两个令牌块的 1-based 起止行号（含）。strip_comments 保留行数，所以去注释后的
    第 i 行就是原文第 i 行——可以直接按行号排除，不需要重新对齐。"""
    lines = css.splitlines()

    def start_line(pat: str) -> int | None:
        rx = re.compile(pat)
        for idx, line in enumerate(lines, 1):
            if rx.search(line):
                return idx
        return None

    spans = []
    for head in (r"^:root\s*\{", r"^html\[data-theme='dark'\]\s*\{"):
        s = start_line(head)
        if s is None:
            continue
        for idx in range(s, len(lines) + 1):
            if lines[idx - 1].startswith("}"):
                spans.append((s, idx))
                break
    if len(spans) != 2:
        raise SystemExit(f"只定位到 {len(spans)} 个令牌块（需要 2 个）——口径可疑，中止")
    return spans


def scan_literal_colors(theme_text: str) -> list[str]:
    """判据①·上半：theme.css 规则里不许有字面量色值（三类例外除外）。"""
    body = strip_comments(theme_text)
    spans = token_line_spans(theme_text)
    fails = []
    for i, line in enumerate(body.splitlines(), 1):
        if not LITERAL.search(line):
            continue
        if any(s <= i <= e for s, e in spans):
            continue
        if "mask-image" in line:
            continue    # 遮罩通道里的 #000 是「不透」不是颜色，收进令牌反而读错语义
        # @media print 的豁免已撤（2026-09-24）：豁免等于在闸上留一个"往里塞什么
        # 都不判"的房间，而 `.token` 那段豁免就是这么让深档八个字面量合法活了一整轮。
        # 打印档改成 --c-print-paper / --c-print-ink 两个令牌（两档同值），规则侧回到零字面量。
        fails.append(f"[theme.css:{i}] 规则里出现字面量色值 {LITERAL.findall(line)} —— "
                     f"请收进 :root / 深色令牌块：{line.strip()[:100]}")
    return fails


MERMAID_DIR = re.compile(r"^\s*(?:style|classDef|linkStyle)\b")
DIR_COLOR = re.compile(r"\b(fill|stroke|color)\s*:\s*(#[0-9a-fA-F]{3,8})")


def scan_mermaid_palette(docs_dir: Path, light: dict[str, str]) -> tuple[list[str], int]:
    """判据①·下半：书稿里 mermaid 指令行的字面量必须等于 --c-plate-* 令牌值。"""
    allowed = {v.strip().lower() for k, v in light.items() if k.startswith("--c-plate")}
    if len(allowed) < 10:
        raise SystemExit(f"--c-plate-* 令牌只有 {len(allowed)} 个色值——图版口径可疑，中止")
    fails, seen = [], 0
    for f in sorted(docs_dir.rglob("*.md")):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if not MERMAID_DIR.match(line):
                continue
            for prop, hexv in DIR_COLOR.findall(line):
                seen += 1
                if hexv.lower() not in allowed:
                    fails.append(f"[{f.relative_to(docs_dir)}:{i}] {prop}:{hexv} 不在图版令牌里"
                                 f"（唯一出处是 theme.css 的 --c-plate-*）")
    if seen < 100:
        raise SystemExit(f"只数到 {seen} 条 mermaid 颜色指令（<100）——口径可疑，中止")
    return fails, seen


# ============================== 静态：图版底色族的可辨性 ==============================

MERMAID_FILL = re.compile(r"\bfill\s*:\s*(#[0-9a-fA-F]{3,8})")
MIN_BAND_DELTA = 4.0     # 同族两档之间（相邻大块的可辨阈约 2.3；图例跨页跨图，翻倍留余量）
MIN_PAPER_DELTA = 4.0    # 一档离纸底：离纸这么近的不算一档，只算"没上色"


def _srgb_lin(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def to_lab(hexv: str) -> tuple[float, float, float]:
    """sRGB → CIELAB(D65)。底纹之间"差得出来吗"是感知问题，对比度（只算亮度）答不了。"""
    v = hexv.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise SystemExit(f"to_lab 只接 3/6 位十六进制，收到 {hexv!r}——口径可疑，中止")
    r, g, b = (int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
    R, G, B = _srgb_lin(r), _srgb_lin(g), _srgb_lin(b)
    X = R * .4124564 + G * .3575761 + B * .1804375
    Y = R * .2126729 + G * .7151522 + B * .0721750
    Z = R * .0193339 + G * .1191920 + B * .9503041
    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (8456 / 24389) * t + 16 / 116
    fx, fy, fz = f(X / .9504560), f(Y / 1.0), f(Z / 1.0887540)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    """ΔE76。取欧氏而不是 CIEDE2000：这条判据只管"两档差没差开"，不做人眼实验级评分，
    多一套常就多一处会写错的地方；阈值按本函数自己的口径标定（见 lab_selftest）。"""
    x, y = to_lab(a), to_lab(b)
    return sum((p - q) ** 2 for p, q in zip(x, y)) ** 0.5


def lab_selftest() -> None:
    """把色度学换算钉在六个**外部可查**的已知答案上；对不上就中止，而不是让一条判据带着错尺跑全站。

    锚必须来自量具之外，否则是自证循环：sRGB 三原色与中灰的 CIELAB 值是印刷在案的公开数
    （#ff0000→53.24, 80.09, 67.20 等），白/黑是定义值。这条自证也不是装饰——本闸立项前的
    一次性量具把 D65 白点 Z 写成 .089903（那是 XYZ 矩阵的系数不是白点），b* 被整体放大，
    同族 ΔE 全部虚高，"哪几对塌陷"的结论方向对、数值全废；而当时没有任何锚会为此停下。
    顺带记一次：第一版锚里我凭记忆写的 "#f0f0f0 L*=94.73" 被这条自证判成不对（真值 94.80），
    自证第一次跑就抓住的是**我自己**——这正是它要在的理由。
    """
    anchors = [
        ("纯白 L*", to_lab("#ffffff"), (100.0, 0.0, 0.0)),
        ("纯黑 L*", to_lab("#000000"), (0.0, 0.0, 0.0)),
        ("中灰 #808080（公开值 L* 53.59）", to_lab("#808080"), (53.59, 0.0, 0.0)),
        ("sRGB 红 #ff0000（公开 Lab 53.24, 80.09, 67.20）", to_lab("#ff0000"), (53.24, 80.09, 67.20)),
        ("sRGB 绿 #00ff00（公开 Lab 87.73, -86.18, 83.18）", to_lab("#00ff00"), (87.73, -86.18, 83.18)),
        ("sRGB 蓝 #0000ff（公开 Lab 32.30, 79.19, -107.86）", to_lab("#0000ff"), (32.30, 79.19, -107.86)),
    ]
    bad = [f"{name} 量得 ({got[0]:.2f}, {got[1]:.2f}, {got[2]:.2f})，已知答案 ({w[0]:.2f}, {w[1]:.2f}, {w[2]:.2f})"
           for name, got, w in anchors if max(abs(g - x) for g, x in zip(got, w)) > 0.05]
    if abs(delta_e("#ffffff", "#000000") - 100.0) > 0.05:
        bad.append(f"白↔黑 ΔE 量得 {delta_e('#ffffff', '#000000'):.2f}，定义值 100.00")
    if bad:
        raise SystemExit("第八条的色度学锚点不对，分色族判据不能开机：\n  " + "\n  ".join(bad))


# 「不算一档」的角色令牌：它们承担纸底、描边、连线、图内文字，不是分色底纹。
BAND_ROLES = ("--c-plate", "--c-plate-edge", "--c-plate-ink", "--c-plate-line",
              "--c-plate-accent", "--c-plate-onblack")


def band_names(toks: dict[str, str]) -> list[str]:
    """分色族**按令牌名枚举**，不按面值反查。

    这是 P12 变异用脚打出来的口径：第一版成员集合是"书稿 fill 的字面值 ∩ --c-plate-* 的值"，
    于是任何改令牌值的动作都让那一档**从分母里消失**而不是撞在一起——深档把红档挪到橙档旁边，
    浅档的字面值没变，那条 fill 就不属于任何档了，判据对着坏样本闭嘴（报红 0 条）。
    归属判据的分母必须来自被判定对象自己的身份（令牌名），不能来自它当下的读数。
    """
    return sorted(k for k in toks
                  if k.startswith("--c-plate") and k not in BAND_ROLES and not k.endswith("-line"))


def fill_literals(docs_dir: Path) -> dict[str, int]:
    """书稿里真正被 paint 的 fill 字面量 → 次数（豁免名单的过堂证据）。"""
    used: dict[str, int] = {}
    for f in sorted(docs_dir.rglob("*.md")):
        for line in f.read_text().splitlines():
            if not MERMAID_DIR.match(line):
                continue
            for hexv in MERMAID_FILL.findall(line):
                v = hexv.lower()
                used[v] = used.get(v, 0) + 1
    return used


def themes_for_band(light: dict[str, str], dark: dict[str, str]) -> list[tuple[str, dict[str, str]]]:
    """分色族在哪些主题下被量：浅档必量；深档只在它真的覆盖了某一档时才量。

    图版按设计是"固定彩版"（mermaid 的 style 不认 var()，深档过去不覆盖任何 plate 令牌），
    所以常态只有一档主题。但只要有人给深档加了覆盖，那一档就必须重量——P12 坏样本走的就是这支。
    """
    out: list[tuple[str, dict[str, str]]] = [("浅档", light)]
    overridden = [k for k in band_names(light) if k in dark]
    if overridden:
        out.append(("深档（覆盖了 " + " ".join(overridden) + "）", {**light, **dark}))
    return out


def scan_band_separation(docs_dir: Path, light: dict[str, str],
                         dark: dict[str, str]) -> tuple[list[str], int, int, str]:
    """判据①·第五层：图版底色族两两可辨、且每档离纸底可辨。

    暴露这条洞的正是 2026-09-25 的提亮轮：那次把每一档都往纸底推，同族分离度掉了 7 对
    （node↔amber 从 3.84 到 3.19，而这二档在同图共存的有 20 张），浏览器口径全程不红——
    它只判前景/底色的对比度，而对比度只看亮度，两档同为"亮"时读数一律 1.0x:1，永远绿。
    """
    fails: list[str] = []
    names = band_names(light)
    if len(names) < 5:
        raise SystemExit(f"分色族只数到 {len(names)} 档（{names}）——不足 5 档，口径可疑，中止")
    if "--c-plate" not in light:
        raise SystemExit("theme.css 里没有 --c-plate 纸底令牌——离纸底的判据无从算起，中止")

    # 豁免名单自己过堂：角色令牌一旦真的被书稿当分色底纹用过，而没有任何"档"与它同值，
    # 那个颜色就是画在图上却没人量可辨性的漏洞——名单会腐烂，所以每次现查。
    used = fill_literals(docs_dir)
    light_band_vals = {light[k].strip().lower() for k in names}
    for role in BAND_ROLES:
        v = light.get(role)
        if v is None:
            continue
        v = v.strip().lower()
        if v in used and v not in light_band_vals:
            fails.append(f"[分色族] 角色豁免名单里的 {role} = {v} 被书稿当 fill paint 过 "
                         f"{used[v]} 次，却没有同值的档接管它——这一层色不在可辨性判据的分母里。"
                         f"要么把它改成真正的档，要么改书稿")

    themes = themes_for_band(light, dark)
    pairs = 0
    tight_pair: tuple[float, str] | None = None
    tight_paper: tuple[float, str] | None = None
    for label, toks in themes:
        short = label.split("（")[0]          # 读数里只留"浅档/深档"，覆盖清单已经打进失败正文
        paper = toks["--c-plate"].strip().lower()
        bands = sorted((k, toks[k].strip().lower()) for k in names)
        for i, (name, v) in enumerate(bands):
            d = delta_e(v, paper)
            if tight_paper is None or d < tight_paper[0]:
                tight_paper = (d, f"{short}/{name}")
            if d < MIN_PAPER_DELTA:
                fails.append(f"[分色族·{label}] {name} = {v} 离纸底 {paper} 只有 ΔE {d:.2f} < "
                             f"{MIN_PAPER_DELTA}——离纸这么近不算一档，读者看不出这里上了色")
            for w_name, w in bands[i + 1:]:
                pairs += 1
                dd = delta_e(v, w)
                if tight_pair is None or dd < tight_pair[0]:
                    tight_pair = (dd, f"{short}/{name}↔{w_name}")
                if dd < MIN_BAND_DELTA:
                    fails.append(f"[分色族·{label}] {name}（{v}）与 {w_name}（{w}）"
                                 f"ΔE {dd:.2f} < {MIN_BAND_DELTA}——两档在读者眼里是同一档，图例等于少一档；"
                                 f"改 theme.css 的令牌后跑 scripts/sync_plate_literals.py 再重出题图")
    return (fails, len(names), pairs, "×".join(lbl for lbl, _ in themes),
            tight_pair, tight_paper)


def scan_raster_anchor(docs_dir: Path, light: dict[str, str]) -> tuple[list[str], int]:
    """判据①·第四层：位图资产的**锚点回执**必须等于当前令牌。

    docs/assets 下那批 AI 版画 webp 是派生件——它们的纸/墨/铜绿三个锚是 `recolor_plate_art.py`
    重着色当时从 theme.css 读的。第八条的浏览器口径对 `<img>` 只看到一个盒子，量不到里面，
    所以"令牌改了、位图没跟着重跑"这件事在 DOM 里不可见。做法：重着色成功后由脚本自己
    落一张回执（人不手编），这里逐键判相等；缺回执、少键、多未知键、值不等、张数不等
    一律报红。张数不进本注释——它由这里算出来并打印，写死就是第一天就旧了的计数。
    2026-09-25 提亮轮暴露这条洞时，SVG 题图有 `plate_engine --check` 当场报 26 条板外色，
    而位图这边没有任何执行者。
    """
    led = docs_dir / "assets" / "plate-art-anchor.json"
    keys = ("--c-plate", "--c-plate-ink", "--c-plate-accent")
    if not led.is_file():
        return ([f"[assets/plate-art-anchor.json] 没有锚点回执——位图是否按当前令牌重跑过，"
                 f"无从核对（跑一次 python3 scripts/recolor_plate_art.py 由它自己写）"], 0)
    rec = json.loads(led.read_text())
    anchors = rec.get("anchors", {})
    fails = []
    for k in keys:
        if k not in anchors:
            fails.append(f"[plate-art-anchor.json] 锚点回执缺 {k}——重着色脚本没记它，或回执被手编")
        elif k not in light:
            fails.append(f"[plate-art-anchor.json] 锚点回执里的 {k} 在 theme.css 查无此令牌")
        elif anchors[k].strip().lower() != light[k].strip().lower():
            fails.append(f"[plate-art-anchor.json] 锚点回执的 {k} = {anchors[k]} ≠ theme.css 的 "
                         f"{light[k]}——位图停在旧锚，重跑 recolor_plate_art.py")
    for k in sorted(set(anchors) - set(keys)):
        fails.append(f"[plate-art-anchor.json] 锚点回执多了 {k}——脚本已经不写它了，删掉或补上读取方")
    n = len([p for p in (docs_dir / "assets").glob("*.webp") if p.name != "cover.webp"])
    if rec.get("recolored") != n:
        fails.append(f"[plate-art-anchor.json] 锚点回执记 {rec.get('recolored')} 张，"
                     f"docs/assets 下实有 {n} 张位图（除 cover.webp）——新落的图没重着色")
    return fails, n


# ============================== 静态：图版令牌 ↔ JS 兜底表 ==============================

FALLBACK_BLOCK = re.compile(r"var AINSE_FIG_FALLBACK\s*=\s*\{(.*?)\};", re.S)
QUOTED_NAME = re.compile(r"'(--c-[\w-]+)'")


def scan_fig_fallback(index_text: str, light: dict[str, str]) -> tuple[list[str], int, int]:
    """判据①·第三层：index.html 里的兜底色值必须等于 theme.css 的令牌值。

    取不到 CSS 变量时 ainseToken() 会退回这张表；表一漂移，图上就会出现一套没人看过
    的第二配色。同时要求「代码读到的每一个令牌名，表里都有对应项」——漏一项会静默变成
    transparent，等于给图版开了个没底的洞。"""
    m = FALLBACK_BLOCK.search(index_text)
    if not m:
        raise SystemExit("index.html 里找不到 AINSE_FIG_FALLBACK 兜底表——口径可疑，中止")
    table = dict(re.findall(r"'(--c-[\w-]+)'\s*:\s*'([^']+)'", m.group(1)))
    if len(table) < 10:
        raise SystemExit(f"兜底表只有 {len(table)} 项（<10）——口径可疑，中止")
    refs = set(QUOTED_NAME.findall(index_text.replace(m.group(0), "")))
    if len(refs) < 8:
        raise SystemExit(f"只发现 {len(refs)} 处令牌读取（<8）——口径可疑，中止")
    fails = []
    for name in sorted(refs):
        if name not in table:
            fails.append(f"[index.html] 代码读取 {name} 但兜底表没有这一项——取不到值时会变成 transparent")
        elif name not in light:
            fails.append(f"[index.html] 兜底表与代码都写了 {name}，theme.css 里却没有这个令牌")
        elif table[name].strip().lower() != light[name].strip().lower():
            fails.append(f"[index.html] {name} 兜底值 {table[name]} ≠ theme.css 的 {light[name]}——两张配色在漂移")
    for name, val in sorted(table.items()):
        if name in refs:
            continue
        if name not in light or light[name].strip().lower() != val.strip().lower():
            fails.append(f"[index.html] 兜底表里的 {name}:{val} 没人读、也与令牌不符——删掉或补上读取方")
    return fails, len(refs), len(table)


# ============================== 静态：index.html 里"手抄令牌"的完整清单 ==============================
#
# 上一条判据只盯得住 AINSE_FIG_FALLBACK 这一块——它按表里的名字逐项对账。表外的抄件它是瞎的。
# 实测到的第二个抄件就住在表外：`<meta name="theme-color" content="#efeae0">`。这一格是提亮**前**
# --c-desk 的值（现值 #f7f5f0），而运行时 applyTheme 每次换档都会把 DOM 里的它改成
# ainseToken('--c-desk')——所以"页面看起来是对的"与"源码字节是对的"是两件事：首屏渲染之前
# 浏览器读的是源码里那个旧值，标签栏/地址栏先闪一下上一个配色。这与位图那条（P11）同形：
# 令牌有抄件、抄件没有闸。
# 补法不能是"再加一行 if"——那正是我记忆里反复出现的失效方式（清单会漏第三个读者）。所以判据
# 从文件派生：把 index.html 的每一个 #rgb/#rrggbb 都找出来，落在"已登记宿主"的字符区间之外的，
# 一律报「未登记」。登记宿主目前有两个：兜底表整块（按名字逐条判）、meta theme-color（按令牌名判
# --c-desk）。第三条抄件落地那天，要么在这里登记它抄哪个令牌，要么把它改成读 var()。

HEX_IN_TEXT = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
META_THEME_COLOR = re.compile(
    r'<meta\s+name="theme-color"\s+content="(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))"')
# 抄件 ↔ 令牌的对应表：新登记一个宿主就是往这里加一行，而不是往判据里加一个 if。
INDEX_TOKEN_HOSTS = (("meta[name=theme-color] content", META_THEME_COLOR, "--c-desk"),)


def strip_comments(text: str) -> str:
    """把 // 行注释与 /* */ 块注释换成等长空格（偏移必须原样保留：登记表是按字符区间认宿主的）。

    为什么要剔：index.html 的注释里写着 mermaid 默认主题的冷灰（#eee #999 #333 #707070）和
    一句"标签还按背景明暗自动配成 #333"——那是**说明文字**，不是令牌的抄件。不剔注释，这条闸
    上线第一天就会把注释报成红，而人对假红的反应是把闸放宽。"""
    out = list(text)
    n = len(text)
    i = 0

    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        two = text[i:i + 2]
        if two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
        elif two == "<!--":
            j = text.find("-->", i + 4)
            j = n if j < 0 else j + 3
            blank(i, j)
            i = j
        elif two == "//" and (i == 0 or text[i - 1] not in ":/"):
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        else:
            i += 1
    return "".join(out)


def scan_index_literals(index_text: str, light: dict[str, str]) -> tuple[list[str], int, int]:
    """index.html 的每个色字面量要么住在已登记的宿主里，要么就是第二个事实源。

    返回（失败清单，在场宿主数，枚举到的字面量总数，表外未登记数）。总数是覆盖率读数：
    它少于登记表项数就说明枚举口径自己瞎了（正则不匹配 ≠ 文件干净），直接中止。"""
    code = strip_comments(index_text)
    fails: list[str] = []
    spans: list[tuple[int, int]] = []
    fb = FALLBACK_BLOCK.search(code)
    if not fb:
        raise SystemExit("index.html 里找不到 AINSE_FIG_FALLBACK 兜底表——抄件登记无从起，中止")
    spans.append(fb.span())
    for label, pattern, token in INDEX_TOKEN_HOSTS:
        m = pattern.search(code)
        if not m:
            fails.append(f"[index.html] 登记的抄件宿主「{label}」在文件里找不到了——"
                         f"它抄的是 {token}；宿主没了就把这一行删掉，别让它变成一条空转的判据")
            continue
        spans.append(m.span())
        want = light.get(token)
        if want is None:
            fails.append(f"[index.html] 抄件宿主「{label}」指向的 {token} 在 theme.css 里没有——无从对账")
        elif m.group(1).strip().lower() != want.strip().lower():
            ln = code.count("\n", 0, m.start()) + 1
            fails.append(f"[index.html:{ln}] 抄件宿主「{label}」写的 {m.group(1)} ≠ 浅档 {token} 的 "
                         f"{want}——令牌动过而这个抄件没跟着动（首屏读的是源码值，不是运行时改出来的 DOM 值）")
    registered = 1 + sum(1 for l, p, t in INDEX_TOKEN_HOSTS if p.search(code))
    found = 0
    stray = 0
    for m in HEX_IN_TEXT.finditer(code):
        found += 1
        if any(a <= m.start() < b for a, b in spans):
            continue
        stray += 1
        ln = code.count("\n", 0, m.start()) + 1
        tail = code[m.start():m.start() + 70].split("\n")[0].strip()
        fails.append(f"[index.html:{ln}] 出现未登记的色抄件 {m.group(0)}（{tail!r}）——"
                     f"它既不在兜底表也不在已登记的宿主里：要么在 INDEX_TOKEN_HOSTS 登记它抄哪个令牌，"
                     f"要么改成运行时读 var()")
    # 枚举口径自证：登记在册的每一格都该被 HEX_IN_TEXT 数到。数到 0 不是"文件干净"，是正则瞎了。
    # 下界由文件自己算出来（兜底表项数 + 在场宿主数），不写死常数——写死的计数第一天就旧。
    entries = len(re.findall(r"'--c-[\w-]+'\s*:", fb.group(1)))
    if found < entries + registered - 1:
        raise SystemExit(f"index.html 只枚举到 {found} 处色字面量，少于兜底表的 {entries} 项 + "
                         f"表外宿主 {registered - 1} 个——HEX_IN_TEXT 或宿主正则不匹配了，"
                         f"这条闸不能拿「没找到」当「没问题」")
    return fails, registered, found, stray


CLEAN_INDEX = """<html>
  <meta name="theme-color" content="#f7f5f0">
  <script>
    // mermaid 的 neutral 主题把 mainBkg / nodeBorder 写成冷灰（#eee #999 #333 #707070）
    var AINSE_FIG_FALLBACK = {
      '--c-desk': '#f7f5f0', '--c-accent': '#2b7159'
    };
    /* 块注释里出现的 #123456 也不该被算成抄件 */
    function t(n) { return ainseToken(n); }
  </script>
</html>
"""


def index_literal_selftest() -> None:
    """抄件登记闸的自证：合成干净件不许报红（假阳对照，剔注释这一步就死在这里），
    四支坏件各报自己那一条：抄件停在旧值／表外冒出一个抄件／登记宿主消失／令牌在 theme.css 查无。

    干净件里**必须**带一行注释里的色和一块块注释：真 index.html 的注释里正好有 mermaid 那四个
    冷灰，不测这一支等于没测 strip_comments()——而漏测的下一步就是拿假阳去放宽判据。"""
    light = {"--c-desk": "#f7f5f0", "--c-accent": "#2b7159", "--c-plate": "#fbf8f1"}
    bad: list[str] = []
    ok_fails, hosts, found, stray = scan_index_literals(CLEAN_INDEX, light)
    if ok_fails:
        bad.append(f"干净件被报红：{ok_fails[0]}")
    if hosts < 2 or stray != 0 or found != 3:
        bad.append(f"干净件的覆盖率读数就不对（宿主 {hosts} 个 / 枚举 {found} 处 / 表外 {stray} 处，"
                   f"期望 2 / 3 / 0）")
    cases = [
        ("meta 停在提亮前的值", CLEAN_INDEX.replace('content="#f7f5f0"', 'content="#efeae0"'),
         light, "抄件宿主"),
        ("表外冒出一个抄件", CLEAN_INDEX.replace("function t(n)", "var TINT = '#123456';\n    function t(n)"),
         light, "未登记"),
        ("登记的宿主消失了", CLEAN_INDEX.replace('  <meta name="theme-color" content="#f7f5f0">\n', ""),
         light, "找不到了"),
        ("宿主指向的令牌查无此名", CLEAN_INDEX, {"--c-accent": "#2b7159"}, "theme.css 里没有"),
    ]
    for name, text, lk, needle in cases:
        got = scan_index_literals(text, lk)[0]
        if not any(needle in f for f in got):
            bad.append(f"坏样本「{name}」没有报出「{needle}」：{got[:1]}")
    try:
        scan_index_literals(CLEAN_INDEX.replace("AINSE_FIG_FALLBACK", "AINSE_OTHER_TABLE"), light)
        bad.append("兜底表整块消失却没有中止——口径无从校起时不能报 0 条")
    except SystemExit:
        pass
    if bad:
        raise SystemExit("抄件登记闸自证未过（它还不具备自己声称的能力）：\n  " + "\n  ".join(bad))


# ============================== 浏览器：对比度 ==============================

PROBE_JS = r"""
(function (MIN_TEXT, MIN_LARGE) {
  function num(s) { return parseFloat(s) || 0; }
  function parse(str) {
    if (!str) return null;
    var m = /^rgba?\(([^)]+)\)$/.exec(String(str).trim());
    if (!m) return null;                       // oklab()/color() 之类读不到就明说
    var p = m[1].split(/[\s,\/]+/).filter(function (x) { return x !== ''; }).map(Number);
    if (p.length < 3 || p.some(isNaN)) return null;
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  }
  function over(fg, bg) {                      // 上层 fg 合成到下层 bg（都是 {r,g,b,a}）
    var a = fg.a + bg.a * (1 - fg.a);
    if (a === 0) return {r: 0, g: 0, b: 0, a: 0};
    return {r: (fg.r * fg.a + bg.r * bg.a * (1 - fg.a)) / a,
            g: (fg.g * fg.a + bg.g * bg.a * (1 - fg.a)) / a,
            b: (fg.b * fg.a + bg.b * bg.a * (1 - fg.a)) / a, a: a};
  }
  function lum(c) {
    function ch(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  }
  function ratio(a, b) {
    var l1 = lum(a), l2 = lum(b);
    if (l1 < l2) { var t = l1; l1 = l2; l2 = t; }
    return (l1 + 0.05) / (l2 + 0.05);
  }
  function css(c) { return 'rgb(' + [c.r, c.g, c.b].map(Math.round).join(',') + ')'; }

  // 沿祖先链把 background-color 一层层合成出来（含元素自己的 opacity）
  function backdrop(el, opacityChain) {
    var layers = [], e = el, op = opacityChain;
    while (e) {
      var cs = getComputedStyle(e);
      if (cs.opacity !== undefined) op = op * (parseFloat(cs.opacity) || 1);
      var c = parse(cs.backgroundColor);
      if (c && c.a > 0) { layers.push({r: c.r, g: c.g, b: c.b, a: Math.min(c.a, 1)}); if (c.a >= 1) break; }
      e = e.parentElement;
    }
    var base = (e && e.nodeType === 9) || !e
      ? parse(getComputedStyle(document.documentElement).backgroundColor) || {r: 255, g: 255, b: 255, a: 1}
      : {r: 255, g: 255, b: 255, a: 1};
    var out = {r: base.r, g: base.g, b: base.b, a: 1};
    for (var i = layers.length - 1; i >= 0; i--) out = over(layers[i], out);
    return {color: out, opacity: op};
  }

  // 图里的文字：先按 DOM 找真正垫着它的那一层（节点形状），找不到再退回命中测试，
  // 最后才退到卡片底。为什么不能只用 elementsFromPoint：它在视口外返回空数组，
  // 而书里最长的图都在折叠以下——那样会把「深底白字」误读成「纸底白字」。
  function shapeOf(g) {
    if (!g) return null;
    var kids = g.children || [];
    for (var i = 0; i < kids.length; i++) {
      var k = kids[i], tag = (k.tagName || '').toLowerCase();
      if (tag !== 'rect' && tag !== 'circle' && tag !== 'ellipse' &&
          tag !== 'polygon' && tag !== 'path') continue;
      var cs = getComputedStyle(k);
      var f = parse(cs.fill);
      if (f && cs.fill !== 'none') {
        // 形状自己可以是半透明（边标签底板 opacity:0.5），alpha 必须带进合成
        var o = parseFloat(cs.opacity);
        f.a = f.a * (isNaN(o) ? 1 : Math.max(0, Math.min(1, o)));
        return f;
      }
    }
    return null;
  }
  function smallGroupShape(t, card) {
    // 时序图的参与者、状态图的状态框：文字与形状是同级的两块，父层只有它们几个孩子。
    // 孩子数一限，就不会把远处某个大容器里的矩形当成自己的底。
    var e = t.parentElement, hops = 0;
    while (e && e !== card && hops < 4) {
      if ((e.children || []).length <= 3) {
        var s = shapeOf(e);
        if (s) return s;
      }
      e = e.parentElement; hops++;
    }
    return null;
  }
  function svgBackdrop(t, card) {
    var r = t.getBoundingClientRect();
    // g.edgeLabel：连线上的标签有自己的底板矩形（fill=edgeLabelBackground、opacity .5），
    // 不算进去就会拿卡片底当背景——同一页里两类底板的颜色并不相同
    var g = t.closest ? t.closest('g.node, g.node-circle, g[class*="section"], g[class*="edgeLabel"]') : null;
    var shape = shapeOf(g) || shapeOf(g && g.firstElementChild);
    if (!shape) shape = smallGroupShape(t, card);
    if (shape) return {color: over(shape, backdrop(card, 1).color), via: '形状'};
    // orphan：文字明明在某个节点/分区/边标签组里，却没找到该组的形状——
    // 这一条读数是拿纸色替那块底板算的，不可信。甘特刻度与图标题没有节点组，
    // 落回卡片底是诚实的，不算 orphan。
    var orphan = !!g;
    if (!r.width || !r.height) return {color: backdrop(card, 1).color, via: '卡片底', orphan: orphan};
    var pts = [[r.left + r.width / 2, r.top + r.height / 2],
               [r.left + 2, r.top + r.height / 2],
               [r.right - 2, r.top + r.height / 2]];
    for (var k = 0; k < pts.length; k++) {
      if (pts[k][1] < 0 || pts[k][1] > innerHeight) continue;   // 视口外，命中测试不可信
      var stack = document.elementsFromPoint(pts[k][0], pts[k][1]) || [];
      for (var i = 0; i < stack.length; i++) {
        var el = stack[i];
        if (el === t || t.contains(el)) continue;
        // 卡片本身与它以上的页面外壳不参与命中：卡底（暖纸）已经是下面所有合成的基准，
        // 让 markdown-section 在命中测试里胜出，等于拿深档的纸去判一张暖纸上的字
        // （甘特图刻度在深档实测被读成 墨字/#1a1815 = 1.04:1 的假红）。
        if (el === card || (card && card.contains(el) === false && el.contains(card))) continue;
        var tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (/^(text|tspan|div|span|p|foreignobject)$/.test(tag)) continue;
        var cs = getComputedStyle(el);
        // 只有真正的形状才用 fill 画出面积。g/svg 上的 fill 是从父层继承来的
        // 「将来给孩子的字色」，从来不被单独绘制——拿它当底色就是把字本身当成纸
        // （甘特图刻度与标题实测被读成 1:1 的假红）。
        if (/^(rect|circle|ellipse|polygon|path)$/.test(tag)) {
          var fill = parse(cs.fill);
          if (fill && cs.fill !== 'none') return {color: over({r: fill.r, g: fill.g, b: fill.b, a: 1},
                                                backdrop(card, 1).color), via: '命中'};
        }
        var bg = parse(cs.backgroundColor);
        if (bg && bg.a > 0) return {color: over(bg, backdrop(card, 1).color), via: '命中'};
      }
    }
    // 视口内命中测试走不通时，最后沿祖先链找真正被画出来的那一层（HTML 标签自带的底板）
    var e2 = t, hops2 = 0;
    while (e2 && e2 !== card && hops2 < 6) {
      var b2 = parse(getComputedStyle(e2).backgroundColor);
      if (b2 && b2.a > 0) return {color: over(b2, backdrop(card, 1).color), via: '标签底'};
      e2 = e2.parentElement; hops2++;
    }
    return {color: backdrop(card, 1).color, via: '卡片底', orphan: orphan};
  }

  function push(list, rec) { list.push(rec); }
  function classify(el, cs, bg, opacity) {
    var fg = parse(cs.color);
    if (!fg) return null;
    fg = {r: fg.r, g: fg.g, b: fg.b, a: 1};
    var eff = over(fg, bg);                    // 前景按祖先 opacity 压淡后再比
    var fs = num(cs.fontSize);
    var bold = (parseInt(cs.fontWeight, 10) || 400) >= 700;
    var large = fs >= 24 || (fs >= 18.66 && bold);
    return {fg: css(eff), bg: css(bg), size: +fs.toFixed(1), large: large,
            ratio: +ratio(eff, bg).toFixed(2), opacity: +opacity.toFixed(2)};
  }

  var out = {hash: location.hash, theme: document.documentElement.getAttribute('data-theme') || '',
             tokens: {}, text: [], svg: [], walker: 0, sampled: 0, sampledMd: 0, pseudo: 0,
             navShown: false,
             figs: {blocks: 0, svgs: 0, raw: 0}, orphans: 0, uncovered: {}, via: {}};
  var sampledSet = (typeof WeakSet === 'function') ? new WeakSet() : null;
  var cs = getComputedStyle(document.documentElement);
  ['--c-desk', '--c-bg', '--c-text', '--c-accent', '--c-plate'].forEach(function (k) {
    out.tokens[k] = (cs.getPropertyValue(k) || '').trim();
  });

  var sel = '.markdown-section h1, .markdown-section h2, .markdown-section h3, .markdown-section h4,' +
            '.markdown-section h5, .markdown-section p, .markdown-section li, .markdown-section td,' +
            '.markdown-section th, .markdown-section a, .markdown-section strong, .markdown-section em,' +
            '.markdown-section code, .markdown-section kbd, .markdown-section span, .markdown-section small,' +
            '.markdown-section summary, .markdown-section dt, .markdown-section dd, .markdown-section figcaption,' +
            '.markdown-section blockquote,' +
            '.sidebar-nav a, .sidebar-nav li > strong, .app-nav a, .page-toc a, .page-footer p,' +
            '.pagination-item, .cover h1, .cover p, .cover blockquote, .part-opener h1,' +
            '.part-opener .part-thesis, .part-opener .part-kicker, .home-part-card strong,' +
            '.home-part-card span, .home-part-card .part-idx, .mermaid-block figcaption, .figure-caption';
  var nodes = document.querySelectorAll(sel);

  [].forEach.call(nodes, function (el) {
    // 只看"自己这一层直接写着字"的节点：父与子各算一次会把同一对颜色重复计账
    var own = '';
    for (var i = 0; i < el.childNodes.length; i++) {
      if (el.childNodes[i].nodeType === 3) own += el.childNodes[i].nodeValue;
    }
    own = own.trim();
    if (!own) return;
    // 图里的文字不参与正文口径：`.markdown-section span` 会连带命中 foreignObject 里的
    // .nodeLabel，而祖先链上没有一层有 background-color（形状是它的**同级** rect，不是父层），
    // 于是黑节点上的白字被拿卡片底算成 1.06:1 的假红。图内文字由下面的图形口径逐条判，
    // 那条会去找真正被画出来的那一层。跳过要说得出对象在别处量过：覆盖集自证查的是
    // sampledSet，图形口径同样往里记账，漏量会直接以 miss: 现形。
    if (el.closest && el.closest('svg')) return;
    var st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') return;
    var r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var bd = backdrop(el, 1);
    if (bd.opacity < 0.05) return;             // 整条链全透明：读者根本看不见，不参与判据
    var rec = classify(el, st, bd.color, bd.opacity);
    if (!rec) return;
    out.sampled++;
    if (sampledSet) sampledSet.add(el);
    if (el.closest && el.closest('.markdown-section')) out.sampledMd++;
    push(out.text, {tag: el.tagName.toLowerCase(),
                    cls: (typeof el.className === 'string' ? el.className.split(' ')[0] : ''),
                    txt: own.slice(0, 20), fg: rec.fg, bg: rec.bg, size: rec.size,
                    large: rec.large, ratio: rec.ratio});
  });

  // 伪元素里生成的字。这类文字不是 DOM 文本节点，上面那条枚举口径永远看不见它，
  // TreeWalker 也数不到它——窄屏顶栏第一行的书名（.app-nav::before）就是新增的一处正文。
  // 它在场却没被量到 = 伪元素口径失明；封面页整条顶栏 display:none，不参与这条自证。
  var navEl = document.querySelector('.app-nav');
  out.navShown = !!(navEl && getComputedStyle(navEl).display !== 'none'
                       && navEl.getBoundingClientRect().width > 0);
  [].forEach.call(document.querySelectorAll('.app-nav, .markdown-section'), function (el) {
    ['::before', '::after'].forEach(function (pe) {
      var pst = getComputedStyle(el, pe);
      if (pst.display === 'none' || pst.visibility === 'hidden') return;
      var raw = pst.content || '';
      if (raw === 'none' || raw === 'normal' || raw === '""' || raw === "''") return;
      var txt = raw.replace(/^[\"']|[\"']$/g, '').trim();
      if (!txt) return;                        // 纯装饰（图标字体/渐变条）没有字，不参与文字判据
      var r = el.getBoundingClientRect();
      if (!r.width || !r.height) return;
      var bd = backdrop(el, 1);
      if (bd.opacity < 0.05) return;
      var rec = classify(el, pst, bd.color, bd.opacity);
      if (!rec) return;
      out.pseudo++; out.sampled++;
      push(out.text, {tag: 'pseudo' + pe, cls: (typeof el.className === 'string' ? el.className.split(' ')[0] : ''),
                      txt: txt.slice(0, 20), fg: rec.fg, bg: rec.bg, size: rec.size,
                      large: rec.large, ratio: rec.ratio});
    });
  });

  // 图内文字
  [].forEach.call(document.querySelectorAll('.mermaid-block'), function (block) {
    // 自证：容器在、图没渲染出来时，下面的取样只会安静地交出空集——
    // 那和「这一页本来没图」读数一模一样。先各计一笔，交给 Python 侧判红。
    out.figs.blocks++;
    if (block.querySelector('svg')) out.figs.svgs++;
    [].forEach.call(block.querySelectorAll('svg text, svg tspan, svg .nodeLabel, svg foreignObject div, svg foreignObject span'), function (t) {
      var own = (t.textContent || '').trim();
      if (!own) return;
      var tag = t.tagName ? t.tagName.toLowerCase() : '';
      if (tag === 'text') {
        // <text> 自己带孩子时，真正被画出来的是 <tspan>（时序图参与者即如此：
        // text.actor 从 .actor 规则继承了盒子底色，tspan 才被上成字色）。
        // 量父层等于量一个永远不画的颜色。
        if (t.querySelector('tspan')) return;
      }
      if (tag === 'tspan' && t.parentElement && /text/.test(t.parentElement.tagName.toLowerCase())) {
        // tspan 的 fill 多数继承自 <text>，只量 <text> 一层，避免同一句话计 5 次
        var kids = [].filter.call(t.parentElement.childNodes, function (n) { return n.nodeType === 1; });
        if (kids.length && kids[0] !== t) return;
      }
      var st = getComputedStyle(t);
      // 只有 SVG 文字才用 fill 上色。流程图 style 行会把 fill 内联到 g.node 上，
      // foreignObject 里的 HTML 标签「继承」到一个永远不画的颜色——照 fill 读数会把
      // 黑字误读成节点底色（实测 1.12:1 的假红），HTML 标签只认 color。
      var isSvg = (typeof SVGElement !== 'undefined') && (t instanceof SVGElement);
      if (!isSvg) {
        // HTML 标签（foreignObject 里的 div>span）只量真正持有文字的那一层：
        // 外层 div 的 color 是从页面继承来的，笔画全在内层 span 上，
        // 深档读它会拿页面的浅色字去比节点底（边标签实测 236,230,218 / 240,235,223 = 1.04:1 的假红）。
        var owns = false;
        for (var ci = 0; ci < t.childNodes.length; ci++) {
          if (t.childNodes[ci].nodeType === 3 && (t.childNodes[ci].nodeValue || '').trim()) owns = true;
        }
        if (!owns) return;
      }
      var col = parse(isSvg ? (st.fill !== 'none' ? st.fill : st.color) : st.color);
      var bd = svgBackdrop(t, block);
      if (!col || !bd) return;
      var bgc = bd.color;
      var eff = over({r: col.r, g: col.g, b: col.b, a: 1}, bgc);
      out.sampled++; out.sampledMd++;
      if (sampledSet) sampledSet.add(t);
      out.via[bd.via] = (out.via[bd.via] || 0) + 1;
      if (bd.orphan) out.orphans++;
      push(out.svg, {txt: own.slice(0, 20), fg: css(eff), bg: css(bgc), via: bd.via,
                     size: +(parseFloat(st.fontSize) || 16).toFixed(1),
                     ratio: +ratio(eff, bgc).toFixed(2)});
    });
  });
  // 没被插件接手过的图：mermaid 源码还以 <code> 躺在正文里。
  // 内联脚本整体语法坏掉时 .mermaid-block 一个都不会生成，blocks 也是 0——
  // 只有这一路分母能区分「这页本来没图」和「脚本死了，图全没了」。
  // ⚠ 只认 `pre > code`：正文里的行内 `` `flowchart TD` `` 之类是**句子**不是图，
  // 曾被下面的兜底判据误认成滞留源码（DIAGNOSIS 实测 1 张假红）。
  out.figs.raw = [].filter.call(
    document.querySelectorAll('.markdown-section pre > code.lang-mermaid, ' +
                              '.markdown-section pre > code.language-mermaid'),
    function (c) { return !c.closest('.mermaid-block'); }).length;

  // 独立口径：TreeWalker 逐条回查正文里每个可见文本节点有没有被量到（覆盖集自证）
  var mdRoot = document.querySelector('.markdown-section') || document.body;
  var walker = document.createTreeWalker(mdRoot, NodeFilter.SHOW_TEXT, null);
  var n = 0, node;
  function mark(pe, prefix) {
    var key = prefix + pe.tagName.toLowerCase() + '.' +
              (typeof pe.className === 'string' ? pe.className.split(' ')[0] : '');
    out.uncovered[key.slice(0, 44)] = (out.uncovered[key.slice(0, 44)] || 0) + 1;
  }
  while ((node = walker.nextNode())) {
    if (!(node.nodeValue || '').trim()) continue;
    var pe = node.parentElement;
    if (!pe) continue;
    var ps = getComputedStyle(pe);
    if (ps.display === 'none' || ps.visibility === 'hidden') continue;
    var pr = pe.getBoundingClientRect();
    if (!pr.width || !pr.height) continue;
    n++;
    if (!sampledSet) continue;
    // 回查一：这个文本节点所在的那一层，被选择器口径量到过吗？
    var anc = pe, found = null;
    while (anc && anc !== mdRoot.parentElement) {
      if (sampledSet.has(anc)) { found = anc; break; }
      anc = anc.parentElement;
    }
    if (!found) { mark(pe, 'miss:'); continue; }
    // 回查二：量到过祖先，但中间夹了一层改了 color/background-color 的元素——
    // 那一层的对比度和祖先不同，量祖先等于没量它。
    var fcs = getComputedStyle(found), probe = pe;
    while (probe && probe !== found) {
      var pcs = getComputedStyle(probe);
      if (pcs.color !== fcs.color || pcs.backgroundColor !== fcs.backgroundColor) {
        mark(probe, 'mid:');
        break;
      }
      probe = probe.parentElement;
    }
  }
  out.walker = n;
  return JSON.stringify(out);
})
"""

def parse_viewports(spec: str) -> list[tuple[int, int, bool]]:
    out = []
    for raw in [s.strip() for s in spec.split(",") if s.strip()]:
        w = int(raw)
        if not 320 <= w <= 2560:
            raise SystemExit(f"视口宽度 {w} 不在 320–2560——口径可疑，中止")
        out.append((w, 844 if w < NARROW else 900, w < NARROW))
    if not out:
        raise SystemExit("--viewports 解析出 0 档——口径可疑，中止")
    return out


def routes_two_ways(b: CDP, base: str) -> list[str]:
    """两条独立口径互证：DOM 侧边栏链接 vs _sidebar.md 里的链接，归一化后必须相等。

    口径照搬 check_legibility.py 已修好的那一版，三个坑都是它先踩过的：
    ① 正则与侧边栏实际写法不符（本站是 `](/x.md)` 与 `](</x.md>)`，没有 `#` 前缀）
       会枚举出 0 条，看着像「DOM 全独有」的口径坏掉；
    ② Docsify 会为**当前页标题**自动生成 `?id=` 锚点混进同一批 `<a>`，
       锚点不是路由，但不能整条丢掉——按 `?` 截断让它塌回所在页。
       因此必须从 `#/` 进入而不是 `#/README`：后者让标题锚塌成一条 `README` 路由，
       而侧边栏里主页写的是 `/`，DOM 口径就凭空多出一条（实测 63 vs 62）。
    ③ 两条口径必须做同样的归一化，否则是过滤不对称而不是清单不一致。
    """
    b.navigate(f"{base}/#/")
    b.wait_for("document.querySelectorAll('.sidebar li a').length > 30", 25)
    hrefs = json.loads(b.js(
        "JSON.stringify([].map.call(document.querySelectorAll('.sidebar li a'),"
        "function(a){return a.getAttribute('href')||''}))"))

    def norm(x: str) -> str:
        return unquote((x or "")).lstrip("#").removesuffix(".md").strip("/")

    page_hrefs = [h.split("?")[0] for h in hrefs or [] if h.startswith("#/")]
    dom = list(dict.fromkeys(page_hrefs))
    md = []
    for target in re.findall(r"\]\(<([^>]+)>\)|\]\(([^)>]+)\)", SIDEBAR.read_text()):
        t = (target[0] or target[1]).strip()
        if not t or t.startswith("http"):
            continue
        md.append("#" + (t if t.startswith("/") else "/" + t))
    dom_u, md_u = {norm(x) for x in dom}, {norm(x) for x in md}
    if dom_u != md_u:
        raise SystemExit(f"两条枚举口径不一致（DOM {len(dom)} / _sidebar.md {len(md)}）："
                         f"只在 DOM={sorted(dom_u - md_u)[:4]} 只在 md={sorted(md_u - dom_u)[:4]}"
                         f"——中止，先修口径")
    pages = [norm(x) for x in dom]
    if len(pages) < 30:
        raise SystemExit(f"枚举到 {len(pages)} 条正文路由（<30）——口径可疑，中止")
    print(f"[枚举] 两条口径互证一致：DOM {len(dom)} / _sidebar.md {len(md)}，"
          f"交回采样 {len(pages)} 条（含首页 `#/`；正文压在封面下，由 dismiss_cover 真点揭幕之后再量）")
    return pages


def serve(directory: Path):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    httpd = socketserver.ThreadingTCPServer(
        ("127.0.0.1", free_port()), functools.partial(Quiet, directory=str(directory)))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", httpd.shutdown


def settle(b: CDP) -> None:
    b.js("(function(){return (window.ainseMermaidChain || Promise.resolve())"
         ".then(function(){return 1;}).catch(function(){return 1;});})()",
         await_promise=True, timeout=60)
    time.sleep(0.2)


def read_page(b: CDP) -> dict:
    # PROBE_JS 是 `(function (MIN_TEXT, MIN_LARGE) {…})`，参数在调用点接上
    expr = "%s(%s, %s)" % (PROBE_JS, MIN_TEXT_RATIO, MIN_LARGE_RATIO)
    return json.loads(b.js(expr, timeout=120))


# ============================== 浏览器口径：键盘焦点环（非文本对比度） ==============================
#
# 对比度的老口径（前景/底色）只看**字**，看不见"这个控件被聚焦了没有"。全站此前只有
# `.search input` 一处有 :focus 样式，其余控件的环全靠浏览器默认——2026-09-25 立此条时
# 真按 Tab 逐控件取证，搜索框那条唯一的指示是 1px 边框换色，环所在像素 #a2bfb1 对邻边
# #faf8f3 = 1.86:1，过不了 WCAG 1.4.11 的 3:1；修法是全站一条 2px 铜绿环（theme.css）。
# 这一轮把取证跑成判据时，Tab 本身又交出来三个缺陷，每一个都只在"真按键 + 真取像素"下现形：
# ① 窄屏关着的抽屉仍留在 Tab 顺序里——390 档从 ☰ 起连按，20+ 站停在 x<0 的侧栏链接上，
#    四侧环像素全部落在画面外（修法：`.sidebar` 收起时 visibility:hidden，见 theme.css）。
# ② 窄屏顶栏是一条 overflow-x:auto 的横滚带，Chrome **不会**为键盘焦点横向滚动它
#    （focusin 里 scroll 事件计数为空；同一条带用 scrollIntoView 手工滚就有效）——
#    走到最右的「🔎 搜索」时链接停在 x=375..440，滚动口右沿 378，环被裁到只剩一侧
#    （修法：index.html 补一次横向揭示，只碰焦点所在的横滚带）。
# ③ Chrome 会把**溢出可滚的容器**收进 Tab 顺序（`.mermaid-block`、`.table-scroll`：
#    实测无 tabindex 属性、tabIndex===-1，却被 Tab 走到），而逐标签点名的焦点环选择器
#    追不上这类停靠点（修法：theme.css 用裸 :focus-visible）。
# 取样必须**真按键**：`el.focus()` 实测也会让 :focus-visible 成立（输入模态是残留状态），
# 所以 fv=True 不能证明键盘用户看得见环，只有 Tab 走出来的顺序才是用户走的那条路。
# 读数还必须等两件事落定：环本身（theme.css 有 `transition: all`，不等 0.55s 读到的是
# 起点值 3px/currentColor，会把"作者环已生效"误读成"还在用 UA 环"），和焦点揭示引起的
# 滚动（theme.css 开了 scroll-behavior:smooth，实测 0.6s 内还会读到动画中途的 rect）。

MIN_FOCUS_RATIO = 3.0            # WCAG 1.4.11：非文本（界面组件与焦点指示）对比度下限
MIN_FOCUS_WIDTH = 2.0            # 环宽下限（px）：1px 环在 100% 缩放下常被视觉忽略
FOCUS_TABS = 8                   # 每页每档走几站
FOCUS_SETTLE = 0.55              # 环的 transition 取证
FOCUS_SCROLL_WAIT = 2.4          # 滚动落定的上限；到点仍不稳定即报"中途 rect"
MIN_SIDES = 2                    # 环至少几侧在像素上在场（实测合法的贴边最差 3 侧）
MIN_VISIBLE = 0.98               # 控件矩形至少几成落在自己的祖先滚动口内（裁一侧即不合格）
# 逐档地板：8 站里至少几个是**不同控件**。实测（2026-09-25，样本面 8 次走查）7 次走到 8 个
# （等于 Tab 次数上限，说明真实焦点顺序比 8 站长），1 次走到 7 个（390/dark/README 有一站回到
# 已走过的控件）。地板定 6 而不是 8：留出"重复一站"的余量，但 Tab 若在同一个控件上转圈、
# 或整片停靠点被 visibility:hidden 摘掉，这一条立刻红。抬高 FOCUS_TABS 时记得回来重量。
FOCUS_MIN_STOPS = {"1280": 6, "390": 6}
RING_TOL = 8                     # 像素与令牌色的单通道容差（PNG 无损，容差只吸收合成/AA）

# 焦点走查的样本面。为什么不跟着对比度跑全部 62 条路由：一站 = 真按一次 Tab + 等滚动落定 +
# 等 transition 落定 + 取一次视口像素，实测每站 0.76s（一次走查 8 站 6.1s）。全样本面要
# 62×3×2 = 372 次走查 ≈ 38 分钟纯走查，而**读数是同构的**——顶栏、抽屉、正文链接、图框、
# 搜索框这几类停靠点在任意一条路由上都齐了。所以按"停靠点类别"取样而不是按路由：
# README（顶栏 + 正文链接 + 图框 + 宽表）与首页（封面揭幕后的那一屏）。
# 视口只走 768 断点两侧各一档（1280 / 390）：抽屉收起、顶栏横滚这两支都活在这两侧。
FOCUS_SAMPLE = {"pages": {"README", ""}, "views": {1280, 390},
                "themes": {"light", "dark"}}

FOCUS_PROBE_JS = r"""
(function () {
  var a = document.activeElement;
  if (!a || a === document.body || a === document.documentElement) return null;
  var cs = getComputedStyle(a), r = a.getBoundingClientRect();
  function d(e) { return e.tagName.toLowerCase() + '.' +
                  String(e.className || '').trim().split(/\s+/).slice(0, 2).join('.'); }
  // 祖先滚动口：只要 overflow 不是 visible 就会裁掉焦点环。控件被裁在口外＝读者看不见环，
  // 而这正是计算样式读不出来的那类缺陷（上面②）。面积比按"还留在口内的比例"算。
  var clip = 1, clipBy = '';
  for (var p = a.parentElement; p && p !== document.documentElement; p = p.parentElement) {
    var pc = getComputedStyle(p);
    if (pc.overflowX === 'visible' && pc.overflowY === 'visible') continue;
    var q = p.getBoundingClientRect();
    var iw = Math.min(r.right, q.right) - Math.max(r.left, q.left);
    var ih = Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top);
    var f = (iw > 0 && ih > 0 ? iw * ih : 0) / Math.max(1, r.width * r.height);
    if (f < clip) { clip = f; clipBy = d(p) + '{' + pc.overflowX + ',' + pc.overflowY + '}'; }
  }
  // 停靠点自己是不是滚动容器：上面③那一类。读数要能证明这一类真被走到过。
  var scroller = (a.scrollWidth > a.clientWidth + 2 || a.scrollHeight > a.clientHeight + 2)
    && /(auto|scroll|hidden)/.test(cs.overflowX + ' ' + cs.overflowY);
  return {tag: a.tagName.toLowerCase(),
          cls: String(a.className || '').trim().split(/\s+/).slice(0, 2).join('.'),
          txt: (a.textContent || a.getAttribute('placeholder') || a.getAttribute('aria-label') || '')
                 .trim().replace(/\s+/g, ' ').slice(0, 18),
          fv: a.matches(':focus-visible'), style: cs.outlineStyle, width: cs.outlineWidth,
          ring: cs.outlineColor, offset: cs.outlineOffset, color: cs.color,
          clip: clip, clipBy: clipBy, scroller: !!scroller,
          rect: [r.left, r.top, r.width, r.height],
          vh: innerHeight, vw: innerWidth};
})()
"""


def rgb_of(css: str) -> tuple[int, int, int] | None:
    """把两种色写法换成三元组：计算样式给的是 rgb(a)(...)，PIL 取像素给的是 #rrggbb。
    解不出来返回 None——调用方据此跳过该侧，不能拿 None 去比距离。"""
    s = (css or "").strip()
    m = re.match(r"rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", s)
    if m:
        v = m.group(1)
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    return None


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    v = h.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise SystemExit(f"焦点环的强调色令牌不是 3/6 位十六进制：{h!r}——口径可疑，中止")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def contrast_rgb(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """WCAG 相对亮度比，直接吃**像素**（这里判的是画出来的东西，不是声明值）。"""
    def lum(c):
        r, g, bl = (_srgb_lin(v / 255) for v in c)
        return .2126 * r + .7152 * g + .0722 * bl
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


def tab_stop(b: CDP) -> None:
    """真按一次 Tab（CDP Input 域）。与用户按键走同一条命中测试路径。"""
    for t in ("rawKeyDown", "keyUp"):
        b.call("Input.dispatchKeyEvent", {
            "type": t, "key": "Tab", "code": "Tab",
            "windowsVirtualKeyCode": 9, "nativeVirtualKeyCode": 9,
            "text": "\t" if t == "rawKeyDown" else ""})


def focus_walk(b: CDP, tmp_dir: Path | None = None) -> tuple[list[dict], str, int]:
    """从当前页的焦点起点开始走 FOCUS_TABS 站，逐站取计算样式 + **环所在像素**。

    返回（记录表，本档的强调色令牌，落在 body/documentElement 上的站数）。强调色是从
    **页面当前计算样式**读的而不是从静态 theme.css 抄的：浅/深两档的 --c-accent 不是一个值，
    抄一份就会拿浅档色去判深档的环。

    记录里每条是判据的输入；像素来自一次视口截图（deviceScaleFactor=1，CSS px 与像素 1:1）。
    为什么非要像素：计算样式读得出"作者声明了什么"，读不出"这一圈有没有被祖先 overflow 裁掉、
    有没有被更上层的元素盖住"——那正是焦点环最常见的死法（上面②③两条实测都是这么死的）。
    """
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("焦点环判据要取图像素，但没有 PIL——这条判据不能降级成只读计算样式")
    shots = tmp_dir or Path(tempfile.mkdtemp(prefix="ainse-pal-focus-"))
    shots.mkdir(parents=True, exist_ok=True)
    accent = (b.js("getComputedStyle(document.documentElement)"
                   ".getPropertyValue('--c-accent').trim()") or "").strip()
    if not accent:
        raise SystemExit("页面上读不到 --c-accent——焦点环判据没有参照色，中止")
    b.js("document.activeElement && document.activeElement.blur();")
    recs: list[dict] = []
    nulls = 0
    for i in range(FOCUS_TABS):
        tab_stop(b)
        # 先等滚动落定（焦点揭示走的是 smooth 滚动），再等 transition 落定，最后才取读数。
        # 中途取到的 rect 属于动画路上，四侧采样会集体指到空白处（实测读到过 y 在动画中途的站）。
        deadline = time.time() + FOCUS_SCROLL_WAIT
        r = b.js(FOCUS_PROBE_JS)
        prev = None
        while r and time.time() < deadline:
            if prev is not None and r["rect"] == prev:
                break
            prev, r = r["rect"], b.js(FOCUS_PROBE_JS)
            time.sleep(0.12)
        time.sleep(FOCUS_SETTLE)
        r = b.js(FOCUS_PROBE_JS)
        if not r:
            nulls += 1
            continue
        # 落定自证：settle 之后再读一次 rect，两次不等＝还在滚动，这一站的几何不可信
        again = b.js(FOCUS_PROBE_JS)
        rec = dict(r, tab=i, stable=bool(again) and again["rect"] == r["rect"])
        x, y, w, h = r["rect"]
        off = float(re.sub(r"[^0-9.\-]", "", r["offset"] or "0") or 0)
        wd = float(re.sub(r"[^0-9.\-]", "", r["width"] or "0") or 0)
        png = shots / f"tab{i:02d}.png"
        b.screenshot(str(png))
        im = Image.open(png).convert("RGB")
        mid_x, mid_y = int(round(x + w / 2)), int(round(y + h / 2))
        d = off + wd / 2                      # 环带的中心离边框盒多远
        pts = {"左": (int(round(x - d)), mid_y), "右": (int(round(x + w + d)), mid_y),
               "上": (mid_x, int(round(y - d))), "下": (mid_x, int(round(y + h + d)))}
        out_d = off + wd + 2.0                # 环外侧 2px：环垫在哪层底上
        outs = {"左": (int(round(x - out_d)), mid_y), "右": (int(round(x + w + out_d)), mid_y),
                "上": (mid_x, int(round(y - out_d))), "下": (mid_x, int(round(y + h + out_d)))}
        rec["ring_px"], rec["adj_px"] = {}, {}
        for k in pts:
            for name, table in (("ring_px", pts), ("adj_px", outs)):
                px = table[k]
                rec[name][k] = ("#%02x%02x%02x" % im.getpixel(px)
                                if 0 <= px[0] < im.width and 0 <= px[1] < im.height else None)
        recs.append(rec)
    if not tmp_dir:
        shutil.rmtree(shots, ignore_errors=True)
    return recs, accent, nulls


def judge_focus(recs: list[dict], accent_hex: str, label: str,
                min_stops: int = FOCUS_MIN_STOPS["1280"]) -> list[str]:
    """纯函数：把 focus_walk 的记录换成失败清单。可注入，所以能喂任何样本——
    四支"真浏览器里今天不犯"的分支（环宽／邻边／遍历／不可分辨）由 focus_selftest()
    用合成记录各自走一次，一条干净记录做假阳对照。"""
    accent = hex_to_rgb(accent_hex)
    fails: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    distinct = 0
    non_accent_text = 0
    for rec in recs:
        who = f"{rec['tag']}.{rec['cls']}「{rec['txt']}」"
        key = (rec["tag"], rec["cls"], rec["txt"])
        if key not in seen:
            seen.add(key)
            distinct += 1
        if rgb_of(rec["color"]) != accent:
            non_accent_text += 1
        if not rec.get("stable", True):
            fails.append(f"[焦点环·{label}] {who} 两次读数 rect 不等——滚动还没落定就取了样，"
                         f"这一站的像素不算数")
            continue
        if not rec["fv"]:
            fails.append(f"[焦点环·{label}] {who} 被 Tab 走到了却不匹配 :focus-visible——"
                         f"这一站的环不存在")
            continue
        if rec["style"] in ("none", "hidden"):
            fails.append(f"[焦点环·{label}] {who} outline-style:{rec['style']}——没有环")
            continue
        wd = float(re.sub(r"[^0-9.]", "", rec["width"] or "0") or 0)
        if wd < MIN_FOCUS_WIDTH:
            fails.append(f"[焦点环·{label}] {who} 环宽 {rec['width']} < {MIN_FOCUS_WIDTH}px")
        if rgb_of(rec["ring"]) != accent:
            fails.append(f"[焦点环·{label}] {who} 环色 {rec['ring']} ≠ 强调色令牌 "
                         f"rgb{accent}——焦点指示必须走全站那一个强调色，"
                         f"跟着 currentColor 走会随控件字色变化，深色字在深底上就看不见；"
                         f"停在 auto 则是选择器没覆盖到这一类停靠点（滚动容器就是漏掉的一类）")
            continue
        # 偏移为负时环画进控件自己肚子里：采样锚（off+width/2 与 off+width+2）全部落到边框盒
        # 内侧，"几侧在场"与"邻边对比度"两读数量的是控件自己的墨色而不是环垫着的那层底——
        # 所以这一支直接拒掉，不留给下游去"判"一个几何上无意义的数。
        off = float(re.sub(r"[^0-9.\-]", "", rec["offset"] or "0") or 0)
        if off < 0:
            fails.append(f"[焦点环·{label}] {who} 焦点环偏移 outline-offset {rec['offset']} 为负——"
                         f"环落在控件自己的肚子里，不是一圈包裹控件的指示；"
                         f"且邻边锚点因此落进控件内容，这一站的像素读数无从判")
            continue
        hit = [k for k, v in (rec["ring_px"] or {}).items()
               if v and rgb_of(v) and max(abs(a - b) for a, b in
                                          zip(accent, rgb_of(v))) <= RING_TOL]
        if len(hit) < MIN_SIDES:
            clip = rec.get("clip", 1)
            fails.append(f"[焦点环·{label}] {who} 声明了环但**像素上只数到 {len(hit)} 侧**"
                         f"（<{MIN_SIDES}）：环带采样 {rec['ring_px']}，期望 rgb{accent}±{RING_TOL}，"
                         f"控件留在祖先滚动口内的比例 {clip:.0%}"
                         + (f"，裁它的是 {rec['clipBy']}" if rec.get("clipBy") else "")
                         + "——读者看不见这一圈的焦点")
            continue
        if rec.get("clip", 1) < MIN_VISIBLE:
            fails.append(f"[焦点环·{label}] {who} 只有 {rec['clip']:.0%} 落在自己的祖先滚动口内"
                         f"（<{MIN_VISIBLE:.0%}，裁它的是 {rec.get('clipBy') or '?'}）——"
                         f"焦点停靠点被 overflow 裁在口外，键盘用户滚不动也看不到")
        worst = None
        for k in hit:
            adj = (rec["adj_px"] or {}).get(k)
            if not adj or not rgb_of(adj):
                continue
            rr = contrast_rgb(accent, rgb_of(adj))
            if worst is None or rr < worst[0]:
                worst = (rr, k, adj)
        if worst and worst[0] < MIN_FOCUS_RATIO:
            fails.append(f"[焦点环·{label}] {who} 环对{worst[1]}侧邻边 {worst[2]} 只有 "
                         f"{worst[0]:.2f}:1 < {MIN_FOCUS_RATIO}:1（{len(hit)}/4 侧环在像素上在场）")
    if distinct < min_stops:
        fails.append(f"[焦点环·{label}] Tab {FOCUS_TABS} 次只走到 {distinct} 个不同控件"
                     f"（<{min_stops}）——遍历没跑起来，本页焦点读数作废")
    if recs and non_accent_text == 0:
        fails.append(f"[焦点环·{label}] 走到的 {len(recs)} 站字色全都等于强调色——"
                     f"「环色=强调色」这条判据在这里与「环色=currentColor」不可分辨，读数不作数")
    return fails


def focus_selftest() -> None:
    """焦点判据的自证：一支干净记录不许报红（假阳对照），七支坏记录各报自己那一条（极性对照），
    外加两支只在纯函数这一侧走到的分支（遍历站数／字色与环同色）。
    这些坏样本在今天的真页面上都不犯，所以它们只能在这里走到——不在这里走，就等于没有判据。"""
    def rec(**kw):
        base = {"tag": "A", "cls": "anchor", "txt": "示例链接", "fv": True, "stable": True,
                "style": "solid", "width": "2px", "offset": "2px", "ring": "rgb(43, 113, 89)",
                "color": "rgb(110, 103, 92)", "clip": 1.0, "clipBy": "", "scroller": False,
                "rect": [100, 100, 80, 30], "vw": 1280, "vh": 900,
                "ring_px": {k: "#2b7159" for k in ("左", "右", "上", "下")},
                "adj_px": {k: "#fbf8f2" for k in ("左", "右", "上", "下")}}
        return dict(base, **kw)

    cases = [
        ("干净记录", rec(), []),
        ("环宽 1px", rec(width="1px"), ["环宽"]),
        ("环色跟 currentColor", rec(ring="rgb(110, 103, 92)"), ["环色"]),
        ("环没画出来", rec(ring_px={k: "#fbf8f2" for k in ("左", "右", "上", "下")}),
         ["像素上只数到"]),
        ("环画在自己肚子里", rec(offset="-2px"), ["偏移"]),
        ("环对邻边 1.86:1", rec(adj_px={k: "#a2bfb1" for k in ("左", "右", "上", "下")}),
         ["邻边"]),
        ("控件被裁在滚动口外", rec(clip=0.05, clipBy="ul{auto,auto}"), ["祖先滚动口"]),
        ("不匹配 :focus-visible", rec(fv=False), ["focus-visible"]),
    ]
    bad: list[str] = []
    for name, r, expect in cases:
        got = judge_focus([r] * max(1, len(expect)), "2b7159", "自证", min_stops=1)
        for needle in expect:
            if not any(needle in f for f in got):
                bad.append(f"坏样本「{name}」没有报出「{needle}」：{got[:1]}")
        if expect and not got:
            bad.append(f"坏样本「{name}」零报红")
        if not expect and got:
            bad.append(f"干净记录「{name}」被报红：{got[0]}")
    # 多站样本必须每站一个**不同控件**：站数判据按 (tag, cls, 文本) 去重，六条同文本的
    # 记录只算一站——假阳对照第一次跑就报了这条红，暴露的是取样口径而不是页面缺陷。
    clean = judge_focus([rec(txt=f"第{i}站") for i in range(6)], "2b7159", "自证", min_stops=6)
    if clean:
        bad.append(f"六站干净记录被报红：{clean[0]}")
    thin = judge_focus([rec(txt="同一条") for _ in range(3)], "2b7159", "自证", min_stops=6)
    if not any("遍历没跑起来" in f for f in thin):
        bad.append("只走到 1 个控件却没过「遍历没跑起来」")
    same = judge_focus([rec(txt=f"第{i}站", color="rgb(43, 113, 89)") for i in range(6)],
                       "2b7159", "自证", min_stops=6)
    if not any("不可分辨" in f for f in same):
        bad.append("全部站字色=强调色却没报「不可分辨」")
    if bad:
        raise SystemExit("焦点判据自证未过（这条闸还没有能力报它该报的红）：\n  "
                         + "\n  ".join(bad))


def focus_worst(recs: list[dict], accent_hex: str):
    """读数（不是判据）：这批站里最紧的一条"环对邻边"对比度，和最小可见占比。
    和分色族那行同理——过/不过是一个比特，余量才告诉下一轮还剩多少可花。"""
    accent = hex_to_rgb(accent_hex)
    ratio = who = None
    clip = 1.0
    for rec in recs:
        clip = min(clip, rec.get("clip", 1))
        for k, v in (rec["ring_px"] or {}).items():
            adj = (rec["adj_px"] or {}).get(k)
            if not v or not adj or not rgb_of(v) or not rgb_of(adj):
                continue
            if max(abs(a - b) for a, b in zip(accent, rgb_of(v))) > RING_TOL:
                continue
            r = contrast_rgb(accent, rgb_of(adj))
            if ratio is None or r < ratio:
                ratio, who = r, f"{rec['tag']}.{rec['cls']}「{rec['txt']}」{k}侧 邻边 {adj}"
    return ratio, who, clip


def focus_sample_ok(path: str, w: int, theme: str, sample: dict) -> bool:
    return path in sample["pages"] and w in sample["views"] and theme in sample["themes"]


# ============================== 浏览器口径：声明 vs 生效 ==============================
#
# 前面所有颜色口径问的都是"画出来的这个像素对那个像素够不够亮"。这一节问的是另一个问题：
# **theme.css 里写的那条声明，页面算出来还是它吗？** 2026-09-25 焦点走查第一次跑到搜索框那一站
# 报红（环下侧邻边 #eee，1.60:1），顺着像素查下来才是这件事的真身：docsify 的搜索插件在运行时
# 往 <head> 追加一条 <style>（docs/vendor/search.min.js 里的 Docsify.dom.style），它排在主题表
# 之后，同特异度即赢——theme.css 的 `.search{padding…border-bottom…}` 与 `.search input{padding
# …font-size…}` 三条声明从来没有生效过，页面上画的是插件的 6px / #eee / .6em 7px / 16px。
# 这条清单上的每一行都是"两个宿主"实测点过名的属性：选择器带元素名（div.search）是**承重**的，
# 谁把它"简化"回 .search，这里就会红（变异 P17 走的就是这一支）。
# 为什么不拿静态扫描代替：文件里两条声明都写得清清楚楚，输赢只在计算值上。
EFFECT_LEDGER = (
    ("div.search", "borderBottomColor", "--c-border"),
    ("div.search input", "borderTopColor", "--c-border-strong"),
    ("div.search input", "backgroundColor", "--c-bg"),
    ("div.search input", "color", "--c-text"),
)

EFFECT_PROBE_JS = """(() => {
  var root = getComputedStyle(document.documentElement);
  return %s.map(function (row) {
    var e = document.querySelector(row[0]);
    return {sel: row[0], prop: row[1], token: row[2],
            got: e ? getComputedStyle(e)[row[1]] : null,
            want: (root.getPropertyValue(row[2]) || '').trim()};
  });
})()""" % repr([list(r) for r in EFFECT_LEDGER])


def judge_effect(rows: list[dict], label: str) -> list[str]:
    """纯函数：算出来的值必须等于**同一页**上那个令牌的值。"""
    fails: list[str] = []
    for r in rows:
        if r["got"] is None:
            fails.append(f"[生效对账·{label}] 页面上找不到 {r['sel']}——这一行没有读者，"
                         f"判据在这一页退化成空转")
            continue
        if not r["want"]:
            fails.append(f"[生效对账·{label}] 令牌 {r['token']} 在这一页读出来是空——"
                         f"参照物不存在，{r['sel']}.{r['prop']} 的读数作废")
            continue
        a, b = rgb_of(r["want"]), rgb_of(r["got"])
        if b is None:
            fails.append(f"[生效对账·{label}] {r['sel']} 的 {r['prop']} 读成 {r['got']!r}，"
                         f"不是可比较的颜色")
            continue
        if a != b:
            fails.append(f"[生效对账·{label}] {r['sel']} 的 {r['prop']} 算出来是 {r['got']}，"
                         f"而 theme.css 让它等于令牌 {r['token']}（{r['want']}）——"
                         f"这条声明被别的宿主赢了，页面上画的不是作者写的值")
    return fails


def effect_selftest() -> None:
    """生效对账的自证：同一个色的两种写法不许报红（假阳对照），换色、缺节点、空令牌各报自己那一条。"""
    def row(**kw):
        base = dict(sel="div.search", prop="borderBottomColor", token="--c-border",
                    got="rgb(236, 230, 219)", want="#ece6db")
        base.update(kw)
        return base
    bad: list[str] = []
    clean = judge_effect([row()], "自证")
    if clean:
        bad.append(f"hex 与 rgb() 同源却被报红：{clean[0]}")
    for name, r, needle in (
            ("被别的宿主赢了", row(got="rgb(238, 238, 238)"), "被别的宿主赢了"),
            ("节点不存在", row(got=None), "没有读者"),
            ("参照令牌读空", row(want=""), "读出来是空"),
            ("读成非颜色", row(got="none"), "不是可比较的颜色")):
        got = judge_effect([r], "自证")
        if not any(needle in f for f in got):
            bad.append(f"坏样本「{name}」没报出「{needle}」：{got[:1]}")
    if bad:
        raise SystemExit("生效对账自证未过：\n  " + "\n  ".join(bad))


def audit(base: str, pages: list[str], themes: list[str],
          shot_dir: Path | None = None, report: bool = False,
          viewports: list[tuple[int, int, bool]] | None = None,
          focus: dict | None = None) -> tuple[list[str], dict]:
    """逐页逐主题量对比度。返回（不达标清单，自证统计）。
    focus=None 时用 FOCUS_SAMPLE；变异自检传一份更小的样本（只需真走到那一条判据）。"""
    if "dark" in themes and "light" not in themes:
        raise SystemExit("只跑深档就没有浅档基线，"
                         "「深档真的换了色」无法自证——请带上 light 一起跑")
    if themes[0] != "light":
        raise SystemExit("主题顺序必须以 light 开头，否则深档找不到同页同视口的基线")
    fs = focus or FOCUS_SAMPLE
    fails: list[str] = []
    worst: list[tuple[float, str]] = []
    stats = {"pages": 0, "sampled": 0, "walker": 0, "uncovered": 0, "figBlocks": 0,
             "figSvgs": 0, "figRaw": 0, "clicks": 0, "svg": 0, "text": 0, "orphan": 0,
             "pseudo": 0, "pseudoMobilePages": 0, "via": {},
             "focusWalks": 0, "focusStops": 0, "focusScroller": 0, "focusNulls": 0,
             "focusWorst": None, "focusWho": "", "focusClip": 1.0,
             "focusSecs": 0.0, "focusDistinct": [], "effectRows": 0}
    for w, h, mobile in (viewports or VIEWPORTS):
        with CDP(w, h) as b:
            b.set_viewport(w, h, mobile=mobile)
            route_list = pages if pages != ["ALL"] else routes_two_ways(b, base)
            light_tokens: dict[str, dict] = {}
            for theme in themes:
                for path in route_list:
                    disp = path or "首页(封面之下)"
                    label = f"{w}px/{theme}/{disp}"
                    b.navigate(f"{base}/#/{quote(path)}")
                    why = dismiss_cover(b, path)
                    if why:
                        fails.append(f"[{label}] {why}")
                        continue
                    ok = b.wait_for(
                        "document.querySelector('.markdown-section') && "
                        "document.querySelector('.markdown-section').textContent.length > 40", 25)
                    b.wait_for("!document.querySelector('section.cover.show')", 15)
                    settle(b)
                    if not ok:
                        fails.append(f"[{label}] 正文未渲染，本页读数作废")
                        continue
                    d = read_page(b)
                    # 落点自证只比 `?` 之前的页面部分：揭幕那次真点会把 hash 写成 `#/?id=/`。
                    got = unquote((d["hash"] or "").lstrip("#")).split("?")[0].strip("/")
                    if not same_landing(got, path):
                        fails.append(f"[{label}] 实际落在 {d['hash']!r}——读数作废")
                        continue

                    want = "dark" if theme == "dark" else ""
                    figs = d.get("figs") or {}
                    stats["figBlocks"] += figs.get("blocks", 0)
                    stats["figSvgs"] += figs.get("svgs", 0)
                    stats["figRaw"] += figs.get("raw", 0)
                    # 自证一：换档必须是真点按钮点出来的，不是脚本改属性
                    if d["theme"] != want:
                        if not b.js("!!document.getElementById('btn-theme')"):
                            fails.append(f"[{label}] 页面上没有 #btn-theme——换档不是用户能做的动作")
                            continue
                        b.js("document.getElementById('btn-theme').click()")
                        stats["clicks"] += 1
                        settle(b)
                        d = read_page(b)
                    if d["theme"] != want:
                        fails.append(f"[{label}] 点了 #btn-theme 但 data-theme 仍是 "
                                     f"{d['theme']!r}（期望 {want!r}）——这一档读数不可用")
                        continue

                    # 自证二：与同页同视口的浅档读数对账，令牌必须真的换了
                    if theme == "light":
                        light_tokens[path] = dict(d["tokens"])
                    else:
                        ref = light_tokens.get(path)
                        if ref is None:
                            fails.append(f"[{label}] 缺浅档基线，无法自证深档换了色")
                            continue
                        changed = [k for k in d["tokens"]
                                   if k != "--c-plate" and d["tokens"][k] != ref.get(k)]
                        if not changed:
                            fails.append(f"[{label}] data-theme 翻了但令牌一个都没变——"
                                         f"深档只是挂了个属性，配色根本没落地")
                            continue
                        if d["tokens"].get("--c-plate") != ref.get("--c-plate"):
                            fails.append(f"[{label}] 图版底色跟着主题翻了（浅 {ref.get('--c-plate')} → "
                                         f"深 {d['tokens'].get('--c-plate')}）——全书的图约定是同一张纸")
                            continue

                    # 生效对账：作者写在 theme.css 里的声明，页面算出来必须还是它
                    rows = b.js(EFFECT_PROBE_JS, timeout=60) or []
                    stats["effectRows"] += len(rows)
                    if not rows:
                        fails.append(f"[{label}] 生效对账交出 0 行——账本没翻开，"
                                     f"这一页没有这项检查")
                    else:
                        fails.extend(judge_effect(rows, label))

                    # 图全没渲染出来时，图内取样交出空集——那和「这页本来没图」的
                    # 读数一模一样。用容器数与源码残留数当分母，把这条静默通道堵死。
                    if figs.get("raw", 0):
                        fails.append(f"[{label}] 页面上还有 {figs['raw']} 张图停在 mermaid 源码状态——"
                                     f"渲染脚本没接手，这一页的图版判据不存在")
                        continue
                    if figs.get("blocks", 0) and not figs.get("svgs", 0):
                        fails.append(f"[{label}] {figs['blocks']} 个 .mermaid-block 容器，"
                                     f"渲染出的 svg 是 0 张——图全坏了")
                        continue

                    # 自证三：覆盖集不能是空集，也不能整片漏量
                    unc = d.get("uncovered") or {}
                    unc_total = sum(unc.values())
                    stats["pages"] += 1
                    stats["sampled"] += d["sampled"]
                    stats["walker"] += d["walker"]
                    stats["uncovered"] += unc_total
                    stats["svg"] += len(d["svg"])
                    stats["text"] += len(d["text"])
                    stats["pseudo"] += d.get("pseudo", 0)
                    if mobile and d.get("navShown"):
                        stats["pseudoMobilePages"] += 1
                        if not d.get("pseudo"):
                            fails.append(f"[{label}] 390 档顶栏在场、书名（.app-nav::before）却没被量到——"
                                         f"伪元素判据这一页是瞎的（不中止本页其余判据）")
                    for k, v in (d.get("via") or {}).items():
                        stats["via"][k] = stats["via"].get(k, 0) + v
                    if d["sampled"] == 0:
                        fails.append(f"[{label}] 一个文本节点都没量到——覆盖集为空，不算通过")
                        continue
                    if d["walker"] == 0:
                        fails.append(f"[{label}] 独立口径 TreeWalker 数到 0 个可见文本节点——"
                                     f"两口径同时失明，读数作废")
                        continue
                    if unc_total > max(8, 0.08 * d["walker"]):
                        top = sorted(unc.items(), key=lambda kv: -kv[1])[:5]
                        fails.append(f"[{label}] 独立口径 {d['walker']} 个可见文本节点，"
                                     f"其中 {unc_total} 个没被量到（漏量选择器 {top}）"
                                     f"——有整片内容不在判据里")
                        continue
                    for key, cnt in sorted(unc.items(), key=lambda kv: -kv[1]):
                        if cnt >= 15:
                            fails.append(f"[{label}] 单类漏量 {cnt} 处（{key}）——像是一整类元素漏了")

                    # 图内文字的底色必须落到它自己的节点形状上；一半以上只能按卡片底算，
                    # 就等于在拿纸色替深色节点做判据——那条读数是假的。
                    orphans = d.get("orphans", 0)
                    stats["orphan"] += orphans
                    if len(d["svg"]) >= 10 and orphans > 0.1 * len(d["svg"]):
                        fails.append(f"[{label}] 图内文字 {orphans}/{len(d['svg'])} 条明明在节点/分区组里，"
                                     f"却没找到自己的形状——只能拿卡片底算，这一页的图版判据不可信")

                    if shot_dir:
                        b.screenshot(str(shot_dir / f"{w}_{theme}_{path.replace('/', '_')}.png"))

                    for t in d["text"]:
                        need = MIN_LARGE_RATIO if t["large"] else MIN_TEXT_RATIO
                        worst.append((t["ratio"], f"{label} {t['tag']}/{t['cls']}「{t['txt']}」"))
                        if t["ratio"] < need:
                            fails.append(f"[{label}] 正文对比度 {t['ratio']}:1 < {need}:1 "
                                         f"（<{t['tag']} class={t['cls']}「{t['txt']}」 "
                                         f"{t['size']}px 前景 {t['fg']} 底色 {t['bg']}）")
                    for s in d["svg"]:
                        worst.append((s["ratio"], f"{label} 图内文字「{s['txt']}」"))
                        if s["ratio"] < MIN_LARGE_RATIO:
                            fails.append(f"[{label}] 图内文字对比度 {s['ratio']}:1 < {MIN_LARGE_RATIO}:1"
                                         f"（「{s['txt']}」 {s['size']}px 前景 {s['fg']} 底色 {s['bg']}）")

                    # 焦点环走查放在本页所有对比度读数**之后**：Tab 会把控件滚进视口、
                    # 留下焦点态，先走再量的话那一批正文读数量的就不是读者打开页面时的那一屏。
                    if focus_sample_ok(path, w, theme, fs):
                        t0 = time.monotonic()
                        recs, accent, nulls = focus_walk(b)
                        stats["focusWalks"] += 1
                        stats["focusSecs"] += time.monotonic() - t0
                        stats["focusStops"] += len(recs)
                        stats["focusNulls"] += nulls
                        stats["focusScroller"] += sum(1 for r in recs if r.get("scroller"))
                        distinct = len({(r["tag"], r["cls"], r["txt"]) for r in recs})
                        stats["focusDistinct"].append(f"{distinct}@{label}")
                        fails += judge_focus(recs, accent, label,
                                             min_stops=FOCUS_MIN_STOPS["390" if mobile else "1280"])
                        ratio, who, clip = focus_worst(recs, accent)
                        if ratio is not None and (stats["focusWorst"] is None
                                                  or ratio < stats["focusWorst"]):
                            stats["focusWorst"], stats["focusWho"] = ratio, f"{label} {who}"
                        stats["focusClip"] = min(stats["focusClip"], clip)
    if report:
        worst.sort()
        print("[对比度最低的前 25 对]")
        for r, who in worst[:25]:
            print(f"  {r:>6}:1  {who}")
    if "dark" in themes and stats["clicks"] == 0:
        fails.append("[自证] 全程一次 #btn-theme 都没点过——「真点按钮」这条没有执行，"
                     "等于没判")
    if fs["pages"] and stats["focusWalks"] == 0:
        fails.append(f"[自证] 焦点环走查一次都没跑（样本面 {sorted(fs['pages'])} × "
                     f"{sorted(fs['views'])} × {sorted(fs['themes'])}）——没有任何一格走到这条判据，"
                     f"绿读数不含焦点")
    if stats["focusWalks"] and stats["focusStops"] == 0:
        fails.append("[自证] 焦点环走查跑了但一站都没记录——Tab 没落进任何控件，读数作废")
    if stats["effectRows"] != len(EFFECT_LEDGER) * stats["pages"]:
        fails.append(f"[自证] 生效对账读到 {stats['effectRows']} 行，而有效页次 {stats['pages']} 次 × "
                     f"{len(EFFECT_LEDGER)} 行 = {len(EFFECT_LEDGER) * stats['pages']}——"
                     f"账本有的页次没翻开，那里的绿读数不含生效对账")
    return fails, stats


# ============================== 变异自检 ==============================

MUT_PAGES = ["", "README", "manuscript/ch09-第4章-AI原生工程栈"]
# 390 档必须一起跑：窄屏顶栏第一行的书名只在 @media (max-width:768px) 里被 ::before
# 生成出来。只在 1280 跑变异，等于「伪元素判据」这一类对象从来没有过一次 RED——
# 绿读数证明不了它会报红。
MUT_VIEWS = [(1280, 900, False), (390, 844, True)]
# 变异模式下的焦点走查样本：一格就够——P15/P16 打的两条支都是全站生效的 CSS 声明，
# 任何一次真按键走查都能证明判据会红；全样本面（README + 首页 × 1280/390 × 浅/深）
# 由日常全量跑覆盖，逐条变异各付 8 次走查的钱只是把同一件事量八遍。
MUT_FOCUS = {"pages": {"README"}, "views": {1280}, "themes": {"light"}}

CH09 = "manuscript/ch09-第4章-AI原生工程栈.md"
# 变异样本里的色值与锚点**一律从当前 theme.css / 当前书稿现取**，不写死。理由是同一件事
# 实测过两遍：P4 的坏形状是「深档被指回浅档值」，浅档一提亮（2026-09-25 那一轮），写死的
# 旧浅档值让样本自己不再等于基线，判据对着不坏的样本闭嘴（报成"变异存活"的假红）；
# 同一轮把 --c-plate-node 从 #f1ece1 移到 #f1ebde 时，写死的 ANCHOR_D1/D2 又当场取不到锚
# （好在 apply_mutation 的 hits!=1 会中止，不会假绿，但那已经是整轮变异跑到最后一步）。
_LIGHT0, _DARK0 = parse_tokens(THEME.read_text())
# 探针在深/浅两档各读一次、再逐键比是否换了色的令牌（--c-plate 单独判「不许跟档翻」）。
PROBE_OFFPLATE = ("--c-desk", "--c-bg", "--c-text", "--c-accent")
_missing = [k for k in PROBE_OFFPLATE if k not in _LIGHT0]
if _missing:
    raise SystemExit(f"P4 的变异载荷取不到浅档令牌 {_missing}——口径可疑，中止")
P4_CSS = ('  <link rel="stylesheet" href="theme.css">\n'
          "  <style>/* 变异 P4 */ html[data-theme='dark']{"
          + "".join(f"{k}:{_LIGHT0[k]};" for k in PROBE_OFFPLATE) + "}</style>")


def _anchor(pattern: str, label: str) -> str:
    m = re.search(pattern, (DOCS / CH09).read_text(), re.M)
    if not m:
        raise SystemExit(f"{label} 的锚点在 {CH09} 里找不到（正则：{pattern!r}）"
                         "——书稿那一行改过了，载荷必须跟着改，不能沿用旧字面值")
    return m.group(0)


ANCHOR_D1 = _anchor(r"^  P4 -\.反馈约束\.-> P1\n"
                    r"  style P1 fill:#[0-9a-fA-F]{6},stroke:#[0-9a-fA-F]{6},color:#[0-9a-fA-F]{6}$", "P2")
ANCHOR_D2 = _anchor(r'^  F4\["决策与约束无记录"\] --> P4\["支柱四 · 文档即代码"\]\n'
                    r"  style P1 fill:#[0-9a-fA-F]{6},stroke:#[0-9a-fA-F]{6},color:#[0-9a-fA-F]{6}$", "P5")
_PAPER = _LIGHT0["--c-plate"].lower()
_D1_COLOR = re.search(r"color:(#[0-9a-fA-F]{6})", ANCHOR_D1).group(1).lower()
if _D1_COLOR == _PAPER:
    raise SystemExit(f"P2 需要「图内文字色 ≠ 纸底色」，两者现在都是 {_PAPER}——坏样本不坏，中止")
# 坏样本＝把标签字色指到纸底色上：真实缺陷就是"白纸上白字"。
P2_NEW = ANCHOR_D1.replace(f"color:{_D1_COLOR}", f"color:{_PAPER}")
# 同理，P11 的锚串也从当前令牌现拼（写死会让浅档一改色就找不到锚、表现为假红）。
for _k in ("--c-plate", "--c-plate-node"):
    if _k not in _LIGHT0:
        raise SystemExit(f"P11 的变异载荷取不到浅档令牌 {_k}——口径可疑，中止")
if _LIGHT0["--c-plate"].lower() == _LIGHT0["--c-plate-node"].lower():
    raise SystemExit("P11 需要「纸底」与「节点底」是两个不同的色，否则坏样本不坏")
P11_OLD = f'"--c-plate": "{_LIGHT0["--c-plate"].lower()}"'
P11_NEW = f'"--c-plate": "{_LIGHT0["--c-plate-node"].lower()}"'
# P12 的坏样本要"两档撞在一起但仍是两个可区分的值"：直接把某档指到另一档的原值＝同色，
# 同色在分色族口径里是"一桶漆两个名字"（--c-plate-ink 与 --c-plate-black 今天就同为 #1e1c19，
# 那是有意的共用），会被并成一档而不报红——所以取**两档的中点色**：仍是独立的一档，但离橙档
# 近到越不过地板。打在深档覆盖上而不是浅档：改浅档值会立刻让书稿字面值板外，先被 mermaid
# 那条判据吃掉，看不出分色族判据在不在工作。
for _k in ("--c-plate-red", "--c-plate-orange"):
    if _k not in _LIGHT0:
        raise SystemExit(f"P12 的变异载荷取不到浅档令牌 {_k}——口径可疑，中止")
if _LIGHT0["--c-plate-red"].lower() == _LIGHT0["--c-plate-orange"].lower():
    raise SystemExit("P12 需要「红档」与「橙档」是两个不同的色，否则坏样本不坏")
if "--c-plate-red" in _DARK0:
    raise SystemExit("P12 假设图版令牌在深档不覆盖（覆盖就得换打法）——先看这条前提还成不成立")


def _mid(a: str, b: str) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{(int(a[i:i + 2], 16) + int(b[i:i + 2], 16)) // 2:02x}" for i in (0, 2, 4))


P12_RED = _mid(_LIGHT0["--c-plate-red"], _LIGHT0["--c-plate-orange"])
if P12_RED in (_LIGHT0["--c-plate-red"].lower(), _LIGHT0["--c-plate-orange"].lower()):
    raise SystemExit(f"P12 的中点色 {P12_RED} 与某一档重合——两档会被并成一桶漆，坏样本不坏")
if delta_e(P12_RED, _LIGHT0["--c-plate-orange"]) >= MIN_BAND_DELTA:
    raise SystemExit(f"P12 的中点色 {P12_RED} 离橙档还有 ΔE "
                     f"{delta_e(P12_RED, _LIGHT0['--c-plate-orange']):.2f}，够辨，坏样本不坏")
# 追加一条**新的**深档块是没用的：parse_tokens 用 .search 只认第一个 html[data-theme='dark']
# 块，追加的那条根本进不了读数——变异会以"量具看不见"的原因存活。所以必须打进既有块里。
_DARK_BODY = re.search(r"html\[data-theme='dark'\]\s*\{(.*?)\n\}", THEME.read_text(), re.S).group(1)
_DARK_LINES = [ln for ln in _DARK_BODY.splitlines() if ln.strip().startswith("--")]
if len(_DARK_LINES) < 10:
    raise SystemExit(f"深档块只数到 {len(_DARK_LINES)} 行令牌——锚不稳，P12 中止")
P12_OLD = _DARK_LINES[-1]
P12_NEW = P12_OLD + "\n  --c-plate-red: " + P12_RED + ";"


def _mix(a: str, b: str, t: float) -> str:
    """a→b 的线性混合色（sRGB 通道级，够用了：这里只用来造坏样本）。"""
    A, B = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(
        f"{round(int(A[i:i + 2], 16) + t * (int(B[i:i + 2], 16) - int(A[i:i + 2], 16))):02x}"
        for i in (0, 2, 4))


# P13＝豁免名单腐烂：书稿把一个**角色色**当分色底纹 paint 了，而没有任何"档"与它同值。
# 这一支不会自己出现——今天 8 个 fill 字面量全部落在档内，是判据成立的前提，不是永远的事实。
_FILL_IN_USE = set(fill_literals(DOCS))
_edge = _LIGHT0.get("--c-plate-edge")
_band_vals0 = {_LIGHT0[k].lower() for k in band_names(_LIGHT0)}
if _edge is None:
    raise SystemExit("P13 需要 --c-plate-edge 作为「角色色」样本——令牌改名了，先看判据口径")
if _edge.lower() in _band_vals0:
    raise SystemExit(f"P13 的 { _edge } 同时是某个档的值，豁免与分色撞了，坏样本不坏")
if _edge.lower() in _FILL_IN_USE:
    raise SystemExit(f"P13 的角色色 {_edge} 已经被书稿 paint 过——基线就该是红的，先修基线")
P13_OLD = ANCHOR_D1
P13_FILL = re.search(r"fill:(#[0-9a-fA-F]{6})", ANCHOR_D1).group(1)
P13_NEW = ANCHOR_D1.replace(f"fill:{P13_FILL}", f"fill:{_edge}")

# P14＝离纸底那一支：把某档朝纸底混合到"技术上不同、读者看不出上了色"。
# 同 P12 打在深档覆盖上：改浅档值会顺带把书稿字面值打出板外，红的不是这条判据。
P14_TOKEN = P14_NEW_VAL = ""
for _k in band_names(_LIGHT0):
    _v = _LIGHT0[_k].lower()
    _others = [_LIGHT0[o].lower() for o in band_names(_LIGHT0) if o != _k]
    for _i in range(1, 20):
        _c = _mix(_v, _PAPER, _i * 0.05)
        if delta_e(_c, _PAPER) >= MIN_PAPER_DELTA:
            continue
        # 只打"离纸底"这一支：混合色必须仍与所有别的档够辨，否则两条判据一起红，分不清是谁
        if all(delta_e(_c, o) >= MIN_BAND_DELTA for o in _others) and _c not in _FILL_IN_USE:
            P14_TOKEN, P14_NEW_VAL = _k, _c
        break
    if P14_TOKEN:
        break
if not P14_TOKEN:
    raise SystemExit("没有一个档能「离纸底越界、离同档仍够辨」——P14 造不出只打这一支的坏样本，"
                     "先复核 MIN_PAPER_DELTA / MIN_BAND_DELTA 两个地板各是多少")
P14_OLD = _DARK_LINES[-1]
P14_NEW = P14_OLD + f"\n  {P14_TOKEN}: {P14_NEW_VAL};"

# P15/P16 打的是焦点环那两条支。锚从 theme.css 现读并数次数（hits!=1 时 apply_mutation 会中止，
# 但更早在这里停下能省掉一整轮白跑的变异）：全站有两条 `outline: 2px solid var(--c-accent)`
# ——裸 :focus-visible 一条、.search input 一条，锚必须带上前导换行才只命中前者。
_RING_BLOCK = ("\n:focus-visible {\n"
               "  outline: 2px solid var(--c-accent);\n"
               "  outline-offset: 2px;")
_theme_text = THEME.read_text()
if _theme_text.count(_RING_BLOCK) != 1:
    raise SystemExit(f"P15/P16 的焦点环锚在 theme.css 里出现 "
                     f"{_theme_text.count(_RING_BLOCK)} 次（需要恰好 1 次）——"
                     "选择器改形状了，载荷必须跟着改")
_alt = _LIGHT0.get("--c-plate-edge")
if _alt is None:
    raise SystemExit("P15 需要一个合法的令牌色当坏环色，但 --c-plate-edge 查无此键")
if _alt.lower() == _LIGHT0["--c-accent"].lower():
    raise SystemExit(f"P15 的坏环色 {_alt} 与强调色同值——坏样本不坏，换一个令牌")
P15_NEW = _RING_BLOCK.replace("var(--c-accent)", "var(--c-plate-edge)")
# 把偏移改成负值＝环画进控件自己的肚子里。第一版把它预期成"像素上什么都没有"，实测不成立：
# 环仍然画得出来（在场侧数照旧过），塌掉的是**邻边**锚点——它落到了控件自己的墨色上。
# 所以这一支现在由具名的「偏移」判据直接拒，不把几何问题解释成对比度问题（见 P16 的注释）。
P16_NEW = _RING_BLOCK.replace("outline-offset: 2px;", "outline-offset: -18px;")

# P17 打的是生效对账那一条：把容器选择器的元素名去掉（div.search → .search），声明一个字没改，
# 但插件的 `.search{border-bottom:1px solid #eee}` 与它同特异度、又排在后面，于是页面算出来
# 就换成了 #eee。静态口径看这条 CSS 完全合规（值仍是令牌），只有读计算值才发现它没赢。
_SEARCH_BLOCK = "\ndiv.search {\n  padding: 12px 16px 16px;"
if _theme_text.count(_SEARCH_BLOCK) != 1:
    raise SystemExit(f"P17 的搜索容器锚在 theme.css 里出现 {_theme_text.count(_SEARCH_BLOCK)} 次"
                     "（需要恰好 1 次）——选择器形状改了，载荷必须跟着改")
if _LIGHT0.get("--c-border", "").lower() == "#eeeeee":
    raise SystemExit("P17 依赖「插件的 #eee ≠ 我们的 --c-border」，两者现在同值，坏样本不坏")
P17_NEW = _SEARCH_BLOCK.replace("\ndiv.search {", "\n.search {")

# P18/P19 打的是"抄件登记"这一条：它不问颜色够不够亮，只问"这格字面量抄的是哪个令牌、抄对没有"。
# 两个坏形状各一支：抄件停在另一个值（真发生过——提亮时 meta theme-color 就是漏网的那一格），
# 以及表外凭空多出一格没人认领的抄件（登记清单自己会漏，所以判据从文件派生而不是写死白名单）。
_index_text = (DOCS / "index.html").read_text()
_META_ANCHOR = '<meta name="theme-color" content="'
_META_BAD_TO = _LIGHT0.get("--c-plate")
if _META_BAD_TO is None:
    raise SystemExit("P18 需要一个与 --c-desk 不同的合法令牌值当旧抄件，但 --c-plate 查无此键")
if _META_BAD_TO.lower() == _LIGHT0.get("--c-desk", "").lower():
    raise SystemExit(f"P18 的坏抄件 {_META_BAD_TO} 与 --c-desk 同值——坏样本不坏，换一个令牌")
P18_OLD = _META_ANCHOR + _LIGHT0["--c-desk"] + '">'
if _index_text.count(_META_ANCHOR) != 1:
    raise SystemExit(f"meta theme-color 的锚在 index.html 里出现 "
                     f"{_index_text.count(_META_ANCHOR)} 次（需要恰好 1 次）——宿主形状改了，载荷跟着改")
P18_NEW = _META_ANCHOR + _META_BAD_TO + '">'
# 表外那一格：插在兜底表之前——它必须在表的字符区间之外，否则会被当成"已登记的宿主"而静默存活。
_TABLE_ANCHOR = "    var AINSE_FIG_FALLBACK = {\n"
if _index_text.count(_TABLE_ANCHOR) != 1:
    raise SystemExit(f"兜底表的锚在 index.html 里出现 {_index_text.count(_TABLE_ANCHOR)} 次"
                     "（需要恰好 1 次）——P19 的表外抄件没有落点")
P19_OLD = _TABLE_ANCHOR
P19_NEW = ("    var AINSE_UNREGISTERED_TINT = '#123456';  // 故意留下的第二套配色\n"
           + _TABLE_ANCHOR)

MUTATIONS = [
    ("P1 正文灰到看不清（--c-text-3 提到接近纸色）", "theme.css",
     "  --c-text-3:     #6e675c;", "  --c-text-3:     #ded9cf;", "正文对比度"),
    ("P2 图内文字与节点同色（标签改成图版卡底色）", CH09,
     ANCHOR_D1, P2_NEW, "图内文字对比度"),
    ("P3 规则里塞回一个硬编码色（token 纪律）", "theme.css",
     "", "\n.markdown-section h2 { color: #1a1d23; }\n", "字面量色值"),
    # 坏样本要真坏：先前用「补一个不闭合的 /*」吃掉深档令牌块是**空操作**——
    # 注释在下一处已有的 */ 就闭合了（实测只吃掉 97 个字符的说明文字，45 条令牌全部存活），
    # 于是判据没抓到红其实是样本根本没坏。这里换成真实世界的那个 bug 形状：
    # 深档块原样在位，但页面里更靠后的一段同名规则把四个非图版令牌指回浅档值
    # （同特异度、后来者胜）——data-theme 会翻，颜色一点不换。
    # 打在 index.html 而不是 theme.css：截空 theme.css 的令牌块会让静态口径直接中止
    # （那是量具坏了，不是判据抓到红），而且会顺带触发 P3 的「字面量色值」针。
    ("P4 深档令牌被更靠后的同名规则指回浅档值（只挂属性不换色）", "index.html",
     '  <link rel="stylesheet" href="theme.css">', P4_CSS, "令牌一个都没变"),
    ("P5 mermaid 用了图版之外的色（第二个事实源）", CH09,
     ANCHOR_D2, ANCHOR_D2.split("\n")[0] + "\n" +
     "  style P1 fill:#eef2ff,stroke:#4f46e5,color:#1a1d23",
     "不在图版令牌里"),
    ("P6 JS 兜底色与令牌漂移（第二套配色）", "index.html",
     "'--c-plate-ink': '#1e1c19'", "'--c-plate-ink': '#1a1d23'", "兜底值"),
    # 取样器交空集 ≠ 没有图：拿一次「渲染脚本自己死了」的坏样本证明这条分母真的会报红
    ("P7 取色函数抛错，图全停在源码状态（空集自证）", "index.html",
     "      var t = ainseToken;", "      var t = ainseTokenUndefined;",
     "停在 mermaid 源码状态"),
    # 撤掉 @media print 豁免之后，必须有一个"就打在豁免原址"的正对照：
    # 否则没人知道那个房间是真的封了，还是只是暂时没人往里放东西。
    ("P8 把字面量色塞回 @media print（豁免原址的正对照）", "theme.css",
     "  body { background: var(--c-print-paper); color: var(--c-print-ink); }",
     "  body { background: #fff; color: #000; }", "字面量色值"),
    # 伪元素口径的正对照：把窄屏书名指到一个合法令牌上，但它恰好是发丝线色。
    # 不打字面量色（那会被 P3 的 token 纪律先吃掉，看不出伪元素判据有没有在工作）。
    ("P9 窄屏顶栏书名换成发丝线色（::before 生成的字）", "theme.css",
     "    letter-spacing: .12em;\n    color: var(--c-text-2);",
     "    letter-spacing: .12em;\n    color: var(--c-border);", "pseudo::before"),
    # 首页从 2026-09-25 起进采样面，靠的是"真点封面那条「全书架构」揭幕"。
    # 这条链一旦哑掉（读者到不了正文），本闸必须报红而不是静默少测一页——
    # 所以给"首页在场"这个新事实配一个会因它而拒绝执行的读者。
    ("P10 封面上那条「全书架构」入口改名（首页正文无从抵达）", "_coverpage.md",
     "[全书架构](README.md)", "[全书结构总览](README.md)", "正文无从揭幕"),
    # 位图是派生件，DOM 侧只看到一个 <img> 盒子——令牌改了而位图没跟着重跑，第八条的
    # 浏览器口径量不到。这条给「锚点回执」判据配一个坏样本，且故意打成一个**合法的图版色**
    # （--c-plate-node）：如果判据只查"值在不在图版色板里"，这条会存活；它必须逐键等于
    # 当前令牌值才算抓住"纸底停在旧锚"这件事。
    ("P11 位图锚点回执的纸底停在图版另一色（派生件没跟着重跑）", "assets/plate-art-anchor.json",
     P11_OLD, P11_NEW, "锚点回执"),
    # 分色族判据的坏样本：两档没撞成同色（撞了会被并成一桶漆，本来就可辨），只是近到越不过
    # 地板。这条同时把"深档一旦覆盖图版令牌就必须各量一遍"这个分支跑到：不覆盖时只量浅档。
    ("P12 红档在深档被挪到橙档旁边（同族两档越不过可辨地板）", "theme.css",
     P12_OLD, P12_NEW, "分色族"),
    # 分色族这条判据有两个分支，各配一个坏样本；只配一个的话另一个分支是"没人走过的红支"，
    # 与没有判据等价。（P12 用脚打出来的第一版口径失明：成员按面值派生，改值即掉出分母。）
    ("P13 书稿把角色色 edge 当分色底纹 paint（豁免名单腐烂）", CH09,
     P13_OLD, P13_NEW, "角色豁免"),
    ("P14 一档被深档覆盖到贴着纸底（读者看不出这里上了色）", "theme.css",
     P14_OLD, P14_NEW, "离纸底"),
    # 焦点环两支各配一个坏样本。走查在变异模式里只跑 README×1280×light 一次（约 8s）：
    # 这两条 CSS 是全站生效的，任何一格真停靠点都能证明判据会红；全样本面留给日常全量跑。
    ("P15 焦点环改用另一个合法令牌色（不再跟着全站强调色）", "theme.css",
     _RING_BLOCK, P15_NEW, "环色"),
    ("P16 焦点环偏移成负值（环画进控件自己肚子里，锚点落进控件内容）", "theme.css",
     _RING_BLOCK, P16_NEW, "偏移"),
    # P16 走过的第一版预期是「像素上只数到 N 侧」，实测不成立：offset:-2px 时环仍然画得出来，
    # 只是画在边框盒内侧——四侧采样照旧命中环色，倒是**邻边**锚点落到了控件自己的墨色上
    # （报出来的是 2.92:1 与 1.00:1 两条"环对邻边"红）。那是判据在替作者解释几何，不是判据
    # 在判几何；所以给"偏移为负"单独一条具名拒判，像素读数在这支之后不再采信。
    # 「像素上只数到」那一支（声明了环、像素上一圈都没有）今天在真页面上不犯，
    # 它只有 focus_selftest 的合成记录走过——记在这里，免得日后把它当成有真题背书。
    # 生效对账的坏样本：不是改颜色，是改**选择器形状**——这正是这条判据存在的理由
    # （颜色口径全都看不出问题：值仍然是令牌）。
    ("P17 搜索容器选择器去掉元素名（同特异度，插件的 #eee 把它赢了）", "theme.css",
     _SEARCH_BLOCK, P17_NEW, "被别的宿主赢了"),
    # 抄件登记这一条的两个分支：值不等（P18）与清单漏一格（P19）。少了任一支，
    # 那条判据就只在另一支上被走过——而"清单会漏第三个读者"正是它存在的理由。
    ("P18 meta theme-color 停在另一个令牌的值（首屏标签栏色是上一版配色）", "index.html",
     P18_OLD, P18_NEW, "抄件宿主"),
    ("P19 兜底表外冒出一格没人认领的色抄件（登记清单漏了第三个读者）", "index.html",
     P19_OLD, P19_NEW, "未登记"),
]


def copy_docs(tmp: Path) -> None:
    for f in sorted(DOCS.rglob("*")):
        rel = f.relative_to(DOCS)
        if f.is_dir():
            (tmp / rel).mkdir(parents=True, exist_ok=True)
            continue
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(f.read_bytes())


def apply_mutation(tmp: Path, mut) -> None:
    _name, fname, old, new, _needle = mut
    text = (DOCS / fname).read_text()
    if old:
        hits = text.count(old)
        if hits != 1:
            raise SystemExit(f"变异 {mut[0]} 的锚点在 {fname} 里出现 {hits} 次（需要恰好 1 次）——"
                             f"歧义锚会把变异打到别处，表现为「未被捕获」的假红")
        text = text.replace(old, new, 1)
    else:
        text = text + new
    (tmp / fname).write_text(text)


def mutation_fails(tmp: Path) -> list[str]:
    fails = static_fails(tmp / "theme.css", tmp)[0]
    base, shutdown = serve(tmp)
    try:
        aud, _ = audit(base, MUT_PAGES, ["light", "dark"], viewports=MUT_VIEWS, focus=MUT_FOCUS)
    finally:
        shutdown()
    return fails + aud


def run_mutations() -> int:
    bad = 0
    for mut in MUTATIONS:
        label, fname, _, _, needle = mut
        tmp = Path(tempfile.mkdtemp(prefix="ainse-pal-mut-"))
        t0 = time.monotonic()
        fails: list[str] = []
        try:
            copy_docs(tmp)
            apply_mutation(tmp, mut)
            fails = mutation_fails(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        hit = [f for f in fails if needle in f]
        print(f"  [变异 {label}]\n    目标 {fname} → 耗时 {time.monotonic() - t0:.0f}s，"
              f"报红 {len(fails)} 条，命中「{needle}」{len(hit)} 条")
        if hit:
            print(f"    示例：{hit[0][:160]}")
        elif fails:
            print(f"    其它失败：{fails[:2]}")
        else:
            print("    且无任何失败——这条判据对着坏样本闭嘴了")
        if not hit:
            bad += 1
    return bad


def static_fails(theme_path: Path = THEME, docs_dir: Path = DOCS) -> tuple:
    lab_selftest()
    focus_selftest()
    effect_selftest()
    index_literal_selftest()
    light, dark = parse_tokens(theme_path.read_text())
    fails = scan_literal_colors(theme_path.read_text())
    md_fails, seen = scan_mermaid_palette(docs_dir, light)
    index_path = docs_dir / "index.html"
    if not index_path.is_file():
        raise SystemExit(f"{index_path} 不存在——兜底表口径无从校起，中止")
    index_text = index_path.read_text()
    fb_fails, refs, entries = scan_fig_fallback(index_text, light)
    lit_fails, hosts, found, stray = scan_index_literals(index_text, light)
    ras_fails, raster = scan_raster_anchor(docs_dir, light)
    band_fails, bands, pairs, band_themes, tight_pair, tight_paper = scan_band_separation(docs_dir, light, dark)
    return (fails + md_fails + fb_fails + lit_fails + ras_fails + band_fails,
            seen, refs, entries, raster, bands, pairs, band_themes, tight_pair, tight_paper,
            hosts, found, stray)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutate", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--screenshot", metavar="DIR")
    ap.add_argument("--themes", default="light,dark")
    ap.add_argument("--viewports", default="")
    ap.add_argument("--pages", default="ALL")
    args = ap.parse_args()

    themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    views = parse_viewports(args.viewports) if args.viewports else VIEWPORTS
    pages = ["ALL"] if args.pages == "ALL" else [p.strip() for p in args.pages.split(",")]

    if args.mutate:
        print("[变异自检] 十九条变异各打红一条判据（P3/P8 同属 token 纪律、P18/P19 同属抄件登记，共十七条），"
              "且必须按各自的机制打红")
        bad = run_mutations()
        print(f"[变异自检] {'全部命中' if bad == 0 else str(bad) + ' 条变异存活——判据有失明'}")
        return 0 if bad == 0 else 1

    shot = Path(args.screenshot) if args.screenshot else None
    if shot:
        shot.mkdir(parents=True, exist_ok=True)

    light, dark = parse_tokens(THEME.read_text())
    (static, seen, refs, entries, raster, bands, pairs, band_themes, tight_pair, tight_paper,
     hosts, found, stray) = static_fails()
    print(f"[静态] 浅档令牌 {len(light)} 个 / 深档覆盖 {len(dark)} 个；"
          f"mermaid 颜色指令 {seen} 条，全部等于 --c-plate-* 令牌值：{not any('不在图版令牌里' in f for f in static)}")
    print(f"[静态] index.html 读取的令牌 {refs} 个 / 兜底表 {entries} 项，"
          f"逐项与令牌相等：{not any('兜底' in f for f in static)}")
    print(f"[静态] index.html 枚举到 {found} 处色字面量 / 抄件宿主 {hosts} 个在场，"
          f"宿主之外未登记 {stray} 处："
          f"{not any('抄件' in f for f in static)}")
    print(f"[静态] 位图派生件 {raster} 张（除 cover.webp），锚点回执逐键等于当前令牌："
          f"{not any('锚点回执' in f for f in static)}")
    print(f"[静态] 分色族 {bands} 档（按令牌名枚举，非按面值）× {band_themes} = {pairs} 对，"
          f"两两 ΔE≥{MIN_BAND_DELTA}、离纸底 ΔE≥{MIN_PAPER_DELTA}："
          f"{not any('分色族' in f for f in static)}")
    # 余量而不是只报过/没过：地板是 4.0，贴着地板过与宽裕地过不是一回事——
    # 下一次提亮只会往"更亮＝更贴纸底"走，看得见余量才知道还剩多少可花。
    if tight_pair and tight_paper:
        print(f"       最紧的一对 ΔE {tight_pair[0]:.2f}（{tight_pair[1]}，地板 {MIN_BAND_DELTA}）；"
              f"最贴纸底的一档 ΔE {tight_paper[0]:.2f}（{tight_paper[1]}，地板 {MIN_PAPER_DELTA}）")
    for f in static[:20]:
        print("  ✗", f)

    base, shutdown = serve(DOCS)
    try:
        t0 = time.monotonic()
        fails, stats = audit(base, pages, themes, shot, args.report, views)
        dur = time.monotonic() - t0
    finally:
        shutdown()

    print(f"[浏览器] 有效读数 {stats['pages']} 页次，正文/图形样本 {stats['text']}+{stats['svg']} 个，"
          f"独立口径 {stats['walker']} 个可见文本节点（未覆盖 {stats['uncovered']}），"
          f"伪元素生成的字 {stats['pseudo']} 条（顶栏在场的 390 页次 {stats['pseudoMobilePages']}），"
          f"真点换档 {stats['clicks']} 次，图 {stats['figSvgs']}/{stats['figBlocks']} 张渲染出 svg"
          f"（滞留源码 {stats['figRaw']} 张、找不到形状 {stats['orphan']} 条），"
          f"图内底色来源 {stats['via']}，耗时 {dur:.0f}s")
    print(f"[焦点环] 真按 Tab 走查 {stats['focusWalks']} 次 × {FOCUS_TABS} 站 = "
          f"{stats['focusStops']} 站读数（每站取一次视口像素；其中溢出可滚的停靠点 "
          f"{stats['focusScroller']} 站、Tab 落空 {stats['focusNulls']} 次），"
          f"样本面 {sorted(FOCUS_SAMPLE['pages'])} × "
          f"{sorted(FOCUS_SAMPLE['views'])} × {sorted(FOCUS_SAMPLE['themes'])}")
    if stats["focusWorst"] is not None:
        print(f"       环对邻边最紧的一站 {stats['focusWorst']:.2f}:1（地板 {MIN_FOCUS_RATIO}:1）"
              f"：{stats['focusWho']}；最小可见占比 {stats['focusClip']:.0%}"
              f"（地板 {MIN_VISIBLE:.0%}）")
    print(f"       每次走查 {stats['focusSecs'] / max(1, stats['focusWalks']):.1f}s，"
          f"逐次走到的不同控件数 {' '.join(stats['focusDistinct'])}"
          f"（地板 FOCUS_MIN_STOPS {FOCUS_MIN_STOPS}）")
    print(f"[生效对账] {len(EFFECT_LEDGER)} 行 × {stats['pages']} 页次 = {stats['effectRows']} 行读数"
          f"（读的是计算值：theme.css 写了不等于页面算出来还是它）")
    for f in fails[:40]:
        print("  ✗", f)
    if len(fails) > 40:
        print(f"  …另有 {len(fails) - 40} 条")
    total = len(static) + len(fails)
    print(f"[结论] 静态 {len(static)} 条 + 浏览器 {len(fails)} 条 = {total} 处配色不达标"
          + ("" if total == 0 else " —— 退出码 1"))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
