#!/usr/bin/env python3
"""第八条守卫·配色闸：颜色只有 token 一个出处，且每一对前景/底色**合成后**真的看得清。

为什么需要第八条：前七条量的是"有没有、看不看得见、点不点得动"，量不到"看得清不清"。
2026-09-24 的实测就是例子——浅档曾是纯白 #FFFFFF + 高饱和靛蓝，命中测试、几何、字号
全部通过，读者只有一句"不够高级"。而"高级"不能靠感觉收口，得换成可判的三件事：

① token 纪律（静态）：theme.css 里除两个令牌块之外不得出现字面量色值；例外只有两类
   （mask-image 的黑白遮罩、@media print 的强制黑白）。代码高亮**不是**例外——曾经它是，
   那段豁免让深档一整块八字面量代码色合法存在，改版全程没报过红。
   书稿 markdown 的 160 条 mermaid `style/classDef/linkStyle` 指令行同理：mermaid 不认
   `var()`（实测写 var() 的那条 style 会让整张图渲染失败），所以图版只能带字面量——
   那这些字面量就必须逐个等于 theme.css 里 --c-plate-* 令牌的值，否则就是第二个事实源。
② 正文对比度（浏览器）：逐页逐文本节点取前景色，沿祖先链**逐层 alpha 合成**出真正的底色，
   再算 WCAG 对比度；正文 ≥4.5:1，大字（≥24px，或 ≥18.66px 且加粗）≥3:1。
   不合成就算 = 假绿：顶栏、渐隐层、封面高光都是半透明的。
③ 图版对比度（浏览器）：图里的文字不能用"卡片底色"当背景——黑节点上的白字会被算成
   白纸上白字。这里用 elementsFromPoint 从字形中心往下找**真正垫在它后面的那一层**
   （节点的 rect/path 或卡片底），合成后再判 ≥3:1。

外加两条自证：真点 #btn-theme 并断言 data-theme 与令牌值同时翻转（否则"换了档"是假的）；
覆盖集与独立口径（TreeWalker 数文本节点）对账，空集或漏量即中止。

用法：
    python3 scripts/check_palette.py                        # 全量：62 条路由 × 1280/1440/390 × 浅/深
    python3 scripts/check_palette.py --mutate               # 变异自检：九条判据各自要能被打红
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
    pages = [p for p in (norm(x) for x in dom) if p]
    if len(pages) < 30:
        raise SystemExit(f"枚举到 {len(pages)} 条正文路由（<30）——口径可疑，中止")
    print(f"[枚举] 两条口径互证一致：DOM {len(dom)} / _sidebar.md {len(md)}，"
          f"其中正文页 {len(pages)} 条（首页封面 {len(dom) - len(pages)} 条无正文可判，不参与）")
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


def audit(base: str, pages: list[str], themes: list[str],
          shot_dir: Path | None = None, report: bool = False,
          viewports: list[tuple[int, int, bool]] | None = None) -> tuple[list[str], dict]:
    """逐页逐主题量对比度。返回（不达标清单，自证统计）。"""
    if "dark" in themes and "light" not in themes:
        raise SystemExit("只跑深档就没有浅档基线，"
                         "「深档真的换了色」无法自证——请带上 light 一起跑")
    if themes[0] != "light":
        raise SystemExit("主题顺序必须以 light 开头，否则深档找不到同页同视口的基线")
    fails: list[str] = []
    worst: list[tuple[float, str]] = []
    stats = {"pages": 0, "sampled": 0, "walker": 0, "uncovered": 0, "figBlocks": 0,
             "figSvgs": 0, "figRaw": 0, "clicks": 0, "svg": 0, "text": 0, "orphan": 0,
             "pseudo": 0, "pseudoMobilePages": 0, "via": {}}
    for w, h, mobile in (viewports or VIEWPORTS):
        with CDP(w, h) as b:
            b.set_viewport(w, h, mobile=mobile)
            route_list = pages if pages != ["ALL"] else routes_two_ways(b, base)
            light_tokens: dict[str, dict] = {}
            for theme in themes:
                for path in route_list:
                    label = f"{w}px/{theme}/{path}"
                    b.navigate(f"{base}/#/{quote(path)}")
                    ok = b.wait_for(
                        "document.querySelector('.markdown-section') && "
                        "document.querySelector('.markdown-section').textContent.length > 40", 25)
                    b.wait_for("!document.querySelector('section.cover.show')", 15)
                    settle(b)
                    if not ok:
                        fails.append(f"[{label}] 正文未渲染，本页读数作废")
                        continue
                    d = read_page(b)
                    got = unquote((d["hash"] or "").lstrip("#")).strip("/")
                    if got != path:
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
    if report:
        worst.sort()
        print("[对比度最低的前 25 对]")
        for r, who in worst[:25]:
            print(f"  {r:>6}:1  {who}")
    if "dark" in themes and stats["clicks"] == 0:
        fails.append("[自证] 全程一次 #btn-theme 都没点过——「真点按钮」这条没有执行，"
                     "等于没判")
    return fails, stats


# ============================== 变异自检 ==============================

MUT_PAGES = ["README", "manuscript/ch09-第4章-AI原生工程栈"]
# 390 档必须一起跑：窄屏顶栏第一行的书名只在 @media (max-width:768px) 里被 ::before
# 生成出来。只在 1280 跑变异，等于「伪元素判据」这一类对象从来没有过一次 RED——
# 绿读数证明不了它会报红。
MUT_VIEWS = [(1280, 900, False), (390, 844, True)]

CH09 = "manuscript/ch09-第4章-AI原生工程栈.md"
ANCHOR_D1 = "  P4 -.反馈约束.-> P1\n  style P1 fill:#eae4d6,stroke:#2f6154,color:#1e1c19"
ANCHOR_D2 = '  F4["决策与约束无记录"] --> P4["支柱四 · 文档即代码"]\n' \
            "  style P1 fill:#eae4d6,stroke:#2f6154,color:#1e1c19"

MUTATIONS = [
    ("P1 正文灰到看不清（--c-text-3 提到接近纸色）", "theme.css",
     "  --c-text-3:     #6e675c;", "  --c-text-3:     #ded9cf;", "正文对比度"),
    ("P2 图内文字与节点同色（标签改成图版卡底色）", CH09,
     ANCHOR_D1, "  P4 -.反馈约束.-> P1\n  style P1 fill:#eae4d6,stroke:#2f6154,color:#f5f1e7",
     "图内文字对比度"),
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
     '  <link rel="stylesheet" href="theme.css">',
     '  <link rel="stylesheet" href="theme.css">\n'
     "  <style>/* 变异 P4 */ html[data-theme='dark']{"
     "--c-desk:#efeae0;--c-bg:#fbf8f2;--c-text:#1e1c19;--c-accent:#2f6154}</style>",
     "令牌一个都没变"),
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
        aud, _ = audit(base, MUT_PAGES, ["light", "dark"], viewports=MUT_VIEWS)
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


def static_fails(theme_path: Path = THEME, docs_dir: Path = DOCS) -> tuple[list[str], int, int, int]:
    light, _dark = parse_tokens(theme_path.read_text())
    fails = scan_literal_colors(theme_path.read_text())
    md_fails, seen = scan_mermaid_palette(docs_dir, light)
    index_path = docs_dir / "index.html"
    if not index_path.is_file():
        raise SystemExit(f"{index_path} 不存在——兜底表口径无从校起，中止")
    fb_fails, refs, entries = scan_fig_fallback(index_path.read_text(), light)
    return fails + md_fails + fb_fails, seen, refs, entries


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
        print("[变异自检] 九条判据各自要能被按各自的机制打红")
        bad = run_mutations()
        print(f"[变异自检] {'全部命中' if bad == 0 else str(bad) + ' 条变异存活——判据有失明'}")
        return 0 if bad == 0 else 1

    shot = Path(args.screenshot) if args.screenshot else None
    if shot:
        shot.mkdir(parents=True, exist_ok=True)

    light, dark = parse_tokens(THEME.read_text())
    static, seen, refs, entries = static_fails()
    print(f"[静态] 浅档令牌 {len(light)} 个 / 深档覆盖 {len(dark)} 个；"
          f"mermaid 颜色指令 {seen} 条，全部等于 --c-plate-* 令牌值：{not any('不在图版令牌里' in f for f in static)}")
    print(f"[静态] index.html 读取的令牌 {refs} 个 / 兜底表 {entries} 项，"
          f"逐项与令牌相等：{not any('兜底' in f for f in static)}")
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
