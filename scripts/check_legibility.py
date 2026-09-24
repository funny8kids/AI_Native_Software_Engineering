#!/usr/bin/env python3
"""第七条守卫·可读性与滚动暗示闸：图"缩到看得清吗"＋宽内容"看得出还能滚吗"。

为什么需要第七条：第五道（命中测试）与第六道（390 几何）都量"有没有破版"，
量不到两件更贴身的事——
① 图被等比塞进 638px 正文栏后，节点文字的有效字号是多少。2026-09-24 全站体检实测：
   1280 档 41 张图缩放 <0.85，最差 ch37 案例四 viewBox 1491 → 638px（0.428），
   节点「CTO 阿坤」有效字号 6.85px。命中测试与"无横向溢出"读数对它全部无害。
② 需要横向滚动的容器有没有告诉读者"右边还有内容"。同批实测：390 档 175 个需滚容器
   （图最大溢出 1167px、宽表 90 条）暗示覆盖率 0。

本守卫真起 Chrome、真点主题按钮、把滚动容器的状态翻转与命中测试一起量，退出码即结论。

用法：
    python3 scripts/check_legibility.py                # 全量：62 条路由 × 1280/390 × 浅/深
    python3 scripts/check_legibility.py --mutate       # 变异自检：每条判据都要能被按机制打红
    python3 scripts/check_legibility.py --report       # 逐图打印自然字号/缩放/有效字号
    python3 scripts/check_legibility.py --screenshot DIR

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

# 判据口径
MIN_EFFECTIVE_FONT = 11.0   # 有效字号下限（节点自然字号 × 渲染缩放），单位 px
NARROW = 768                # 与 index.html/theme.css 的窄屏分界一致
VIEWPORTS = [(1280, 900, False), (390, 844, True)]


def parse_viewports(spec: str) -> list[tuple[int, int, bool]]:
    """`--viewports 1280,1440,390` → [(宽, 高, 移动端缩放)]。窄于 NARROW 才开移动端模拟：
    开了移动端缩放 Chrome 会按 devicePixelRatio 重排，量到的就不是桌面栏宽了。"""
    out = []
    for raw in [s.strip() for s in spec.split(",") if s.strip()]:
        w = int(raw)
        if not 320 <= w <= 2560:
            raise SystemExit(f"视口宽度 {w} 不在 320–2560——口径可疑，中止")
        out.append((w, 844 if w < NARROW else 900, w < NARROW))
    if not out:
        raise SystemExit("--viewports 解析出 0 档——口径可疑，中止")
    return out

# 变异自检用代表页：必须各自包含每条判据的实物对象，否则"没对象可判"会伪装成"判据有效"。
MUT_PAGES = ["README", "manuscript/ch03-案例时间线", "manuscript/ch05-数字清单",
             "manuscript/ch37-案例四-守夜人科技"]

PROBE_JS = r"""
(async function (MIN_FONT, NARROW) {
  // 提示层带 .18s 淡入淡出：改完 scrollLeft 立刻读 getComputedStyle，读到的是
  // 过渡起点（0），会把"正常淡入的暗示"报成"暗示没出现"。所以每个状态都要等过渡走完再读。
  // 为不让一页 22 张表就睡 22 次，这里分三段：一次把所有容器推到目标态 → 睡一次 → 读全部。
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  var out = {hash: location.hash, theme: document.documentElement.getAttribute('data-theme') || 'light',
             mermaid: [], scrollers: []};

  // ---- ① 每张图：自然字号 → 有效字号 ----
  [].forEach.call(document.querySelectorAll('.mermaid-block'), function (block, bi) {
    var svg = block.querySelector('svg');
    if (!svg) return;
    var vb = (svg.viewBox && svg.viewBox.baseVal.width) || 0;
    var sr = svg.getBoundingClientRect(), br = block.getBoundingClientRect();
    var scale = vb ? sr.width / vb : null;
    var natMin = null, natNode = '';
    [].forEach.call(svg.querySelectorAll('text, foreignObject *'), function (t) {
      var fs = parseFloat(getComputedStyle(t).fontSize) || 0;
      if (!fs) return;
      var txt = (t.textContent || '').trim();
      if (!txt) return;                       // 空 text 节点（占位/图标字体）不算可读性对象
      if (natMin === null || fs < natMin) { natMin = fs; natNode = txt.slice(0, 16); }
    });
    out.mermaid.push({
      i: bi, viewBoxW: Math.round(vb), svgW: Math.round(sr.width), blockW: Math.round(br.width),
      scale: scale === null ? null : +scale.toFixed(3),
      natMin: natMin, effMin: (natMin && scale) ? +(natMin * scale).toFixed(2) : null,
      node: natNode,
      isWide: !!block.querySelector('.mermaid.is-wide, .mermaid[data-is-wide="1"]'),
      leftClipped: sr.left < br.left - 1.5,
      overflows: block.scrollWidth - block.clientWidth
    });
  });

  // ---- ② 每个需要横向滚动的容器：有没有暗示、状态会不会翻转、暗示挡不挡点击 ----
  function veilState(frame) {
    var l = frame.querySelector('.scroll-veil.left, .scroll-veil-l');
    var r = frame.querySelector('.scroll-veil.right, .scroll-veil-r');
    function op(el) { return el ? parseFloat(getComputedStyle(el).opacity) : null; }
    function pe(el) { return el ? getComputedStyle(el).pointerEvents : null; }
    return { l: !!l, r: !!l && !!r, opL: op(l), opR: op(r),
             peL: pe(l), peR: pe(r),
             wL: l ? Math.round(l.getBoundingClientRect().width) : 0 };
  }
  function hitTest(frame, x, y) {
    var el = document.elementFromPoint(x, y);
    if (!el) return {hit: null};
    var inside = frame.contains(el) || el === frame;
    return {tag: el.tagName.toLowerCase(),
            cls: (typeof el.className === 'string' ? el.className.split(' ')[0] : ''),
            veil: /scroll-veil/.test(String(el.className) + ' ' + (el.parentElement && el.parentElement.className || '')) || /scroll-veil/.test(String(el.className)),
            inside: inside};
  }
  var list = [];
  [].forEach.call(document.querySelectorAll('.mermaid-block, .table-scroll'), function (sc) {
    var over = sc.scrollWidth - sc.clientWidth;
    if (over <= 2) return;                    // 不需要滚 → 无判据对象
    var frame = sc.closest('.scroll-frame');
    var rec = {sel: sc.className.split(' ')[0], overflow: Math.round(over),
               framed: !!frame, scroller: null};
    out.scrollers.push(rec);
    if (frame) {
      rec.scroller = {left: veilState(frame)};   // 初始态：已经稳定，可直接读
      list.push({sc: sc, frame: frame, rec: rec});
    }
  });
  for (const it of list) {
    it.sc.scrollLeft = it.sc.scrollWidth;
    it.sc.dispatchEvent(new Event('scroll', {bubbles: true}));
  }
  await sleep(400);
  for (const it of list) {
    var max = it.sc.scrollWidth - it.sc.clientWidth;
    it.rec.reachedEnd = it.sc.scrollLeft >= max - 1;
    it.rec.scroller.right = veilState(it.frame);
    var fr = it.frame.getBoundingClientRect();
    // 命中测试：右缘渐隐层中心那点，必须仍点得到滚动容器里的内容
    it.rec.hit = hitTest(it.frame, Math.round(fr.right - 8), Math.round(fr.top + fr.height / 2));
    it.sc.scrollLeft = 0;
    it.sc.dispatchEvent(new Event('scroll', {bubbles: true}));
  }
  await sleep(400);
  for (const it of list) it.rec.scroller.back = veilState(it.frame);
  return JSON.stringify(out);
})(%s, %s)
""" % (MIN_EFFECTIVE_FONT, NARROW)


def routes_two_ways(cdp: CDP, base: str) -> list[str]:
    """两条独立口径枚举路由，互证不一致就中止。

    本轮探针犯的第二个谎就是拿一条坏掉的枚举（正则与侧边栏实际写法不符）跑出 0 条路由，
    然后把 248 次"零读数"当成"全站干净"。所以这里宁可中止也不返回空。
    """
    cdp.navigate(f"{base}/#/")
    if not cdp.wait_for("document.querySelectorAll('.sidebar li a').length > 3", 30):
        raise SystemExit("路由枚举失败：侧边栏没挂出链接——没有对象可判，不算通过")
    hrefs = json.loads(cdp.js(
        "JSON.stringify([].slice.call(document.querySelectorAll('.sidebar li a'))"
        ".map(function(a){return a.getAttribute('href');}))"))
    def norm(h):
        p = unquote(h[1:]).removesuffix(".md").strip("/")
        return p

    # 侧边栏里混着两类链接：整页路由，和 Docsify 为**当前页标题**自动生成的站内锚点
    # （实测首页多出 4 条 `#/?id=九部分地图` 之类，把 DOM 口径从 62 撑到 66）。锚点不是路由，
    # 但也不能按"有没有 ?"整条丢掉——`#/manuscript/ch05?id=x` 的页面部分仍是一条真路由。
    # 所以只截掉 `?` 之后再去重：本页标题锚会塌回它所在的那一页（首页的塌成 `#/`）。
    # ⚠ 两条口径必须做**同样的**归一化：上一版只把 DOM 侧的空页面路径（= 首页封面）滤掉，
    # md 侧留着 `1:- [主页](/)`，于是互证报出"只在 md=['']"——那是过滤不对称，不是清单不一致。
    page_hrefs = [h.split("?")[0] for h in hrefs or [] if h and h.startswith("#/")]
    dom = list(dict.fromkeys(page_hrefs))
    md = []
    for target in re.findall(r"\]\(<([^>]+)>\)|\]\(([^)>]+)\)", SIDEBAR.read_text()):
        t = (target[0] or target[1]).strip()
        if not t or t.startswith("http"):
            continue
        md.append("#" + (t if t.startswith("/") else "/" + t))

    dn, mn = {norm(x) for x in dom}, {norm(x) for x in md}
    if dn != mn:
        raise SystemExit(f"两条枚举口径不一致（DOM {len(dom)} / _sidebar.md {len(md)}）："
                         f"只在 DOM={sorted(dn - mn)[:4]} 只在 md={sorted(mn - dn)[:4]}")
    if not dom:
        raise SystemExit("枚举到 0 条路由——判据没有对象，中止")
    # 交回给采样循环的是**已解码的纯路径**（"README"、"manuscript/ch03-案例时间线"）：
    # 带着 `#` 或 %E4… 原样交回去，导航时会被二次转义成 %23，整趟就打在同一个坏页上。
    # 首页（`#/`，norm 后为空）跳过：它是封面版面，没有 .markdown-section，
    # 本闸两类判据（图字号、滚动暗示）在它身上都没有判据对象——跳过要说，不能算通过。
    pages = [norm(x) for x in dom if norm(x)]
    if len(pages) < 30:
        raise SystemExit(f"枚举到 {len(pages)} 条正文路由（<30）——口径可疑，中止")
    print(f"[枚举] 两条口径互证一致：DOM {len(dom)} / _sidebar.md {len(md)}，"
          f"其中正文页 {len(pages)} 条（首页封面 {len(dom) - len(pages)} 条不参与本闸）")
    return pages


FENCE_RE = re.compile(r"^( {0,3})(`{3,})")


def renderable_mermaid_fences(text: str) -> int:
    """按 CommonMark 的**嵌套**规则数：这一页真正会被渲染成图的 mermaid 围栏有几条。

    上一版是 `re.findall(r\"^```mermaid\\b\", text, re.M)`——只看行首字样，不看那条围栏
    当下是不是已经在别的围栏内部。STYLE_GUIDE 与 FIGURE_LIST 各有一段「图注模板」用四反引号
    的 `````markdown` 把示例源码包起来（```` ```mermaid ```` 在里面是给人读的文本，
    Docsify 永远不会把它变成图），朴素口径把这两条例外也数进"应有图数"，于是全站体检报出
    8 条"有图没画出来"——缺陷在量具，不在书。
    规则：围栏只有遇到**同种字符、长度不短于自己、且后面没内容**的另一条才算闭合。
    """
    count, open_len = 0, 0
    for line in text.splitlines():
        m = FENCE_RE.match(line)
        if not m:
            continue
        fence, rest = m.group(2), line[m.end():]
        if open_len:
            if len(fence) >= open_len and not rest.strip():
                open_len = 0
            continue
        if len(fence) == 3 and rest.strip().lower() == "mermaid":
            count += 1
        open_len = len(fence)
    return count


def fence_counts(paths: list[str]) -> dict[str, int]:
    """独立口径：每页 markdown 里会渲染的 mermaid 围栏数，用来证明"图真的画出来了"。"""
    out = {}
    for p in paths:
        f = DOCS / (p + ".md")
        out[p] = renderable_mermaid_fences(f.read_text()) if f.is_file() else -1
    return out


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
    """等作图串行队列排空：主题切换/首绘都走那条链，没排空就量到上一态的 svg。"""
    b.js("(function(){return (window.ainseMermaidChain || Promise.resolve())"
         ".then(function(){return 1;}).catch(function(){return 1;});})()",
         await_promise=True, timeout=60)
    time.sleep(0.25)


def audit(base: str, pages: list[str], themes: list[str],
          shot_dir: Path | None = None, report: bool = False,
          viewports: list[tuple[int, int, bool]] | None = None) -> list[str]:
    fails: list[str] = []
    counts = fence_counts(pages)
    for w, h, mobile in (viewports or VIEWPORTS):
        with CDP(w, h) as b:
            b.set_viewport(w, h, mobile=mobile)
            route_list = pages if pages != ["ALL"] else routes_two_ways(b, base)
            counts = fence_counts(route_list)
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
                    d = json.loads(b.js(PROBE_JS, await_promise=True, timeout=90))
                    # 落点自证：URL 二次转义（# → %23）会让整趟采样打在同一个坏页面上
                    got = unquote((d["hash"] or "").lstrip("#")).strip("/")
                    if got != path:
                        fails.append(f"[{label}] 实际落在 {d['hash']!r}——读数作废")
                        continue
                    # 主题自证：必须真点按钮，且断言 data-theme 真的翻了
                    want = "dark" if theme == "dark" else ""
                    cur = d["theme"] if d["theme"] != "light" else ""
                    if cur != want:
                        clicked = b.js("(function(){var x=document.getElementById('btn-theme');"
                                       "if(x){x.click();return 1;}return 0;})()")
                        settle(b)
                        d = json.loads(b.js(PROBE_JS, await_promise=True, timeout=90))
                        cur = d["theme"] if d["theme"] != "light" else ""
                        if cur != want:
                            fails.append(f"[{label}] 主题没落地（期望 {want!r} 实得 {d['theme']!r}，"
                                         f"按钮存在={bool(clicked)}）——这一档读数不可用")
                            continue
                    if shot_dir:
                        b.screenshot(str(shot_dir / f"{w}_{theme}_{path.replace('/', '_')}.png"))

                    # —— 覆盖自证：渲染出来的图必须等于该页的围栏数
                    n_fence = counts.get(path, -1)
                    if n_fence < 0:
                        fails.append(f"[{label}] 找不到 {path}.md，独立口径缺失")
                    elif len(d["mermaid"]) != n_fence:
                        fails.append(f"[{label}] 页内有 {n_fence} 个 mermaid 围栏，"
                                     f"只量到 {len(d['mermaid'])} 张已渲染图——有图没画出来或选择器失效")

                    for m in d["mermaid"]:
                        if report:
                            print(f"  · [{label}] 图#{m['i']} viewBox={m['viewBoxW']} 渲染={m['svgW']} "
                                  f"缩放={m['scale']} 自然字号={m['natMin']} 有效={m['effMin']} "
                                  f"节点「{m['node']}」is-wide={m['isWide']} 溢出={m['overflows']}")
                        if m["effMin"] is None:
                            if m["natMin"] is None:
                                fails.append(f"[{label}] 图#{m['i']} 量不到任何文字节点——"
                                             f"可读性判据对它失明（无对象不算通过）")
                            continue
                        if m["effMin"] < MIN_EFFECTIVE_FONT:
                            fails.append(f"[{label}] 图#{m['i']} 有效字号 {m['effMin']}px"
                                         f"（自然 {m['natMin']}px × 缩放 {m['scale']}，"
                                         f"viewBox {m['viewBoxW']} → {m['svgW']}px），"
                                         f"低于 {MIN_EFFECTIVE_FONT}px 下限；最密节点「{m['node']}」")
                        if m["overflows"] > 2 and m["leftClipped"]:
                            fails.append(f"[{label}] 图#{m['i']} 撑宽到 {m['svgW']}px 后图左缘 "
                                         f"x 仍在容器外——居中溢出滚不回来（应左对齐）")
                        if m["overflows"] > 2 and not m["isWide"]:
                            fails.append(f"[{label}] 图#{m['i']} 溢出 {m['overflows']}px 但宿主没挂号"
                                         f" is-wide——左对齐靠的是它")

                    for s in d["scrollers"]:
                        if not s["framed"]:
                            fails.append(f"[{label}] {s['sel']} 需要横向滚动 {s['overflow']}px，"
                                         f"但没有 .scroll-frame 承载暗示——读者无从知道右边还有内容")
                            continue
                        ini, rgt = s["scroller"]["left"], s["scroller"]["right"]
                        if not (ini["l"] and ini["r"]):
                            fails.append(f"[{label}] {s['sel']} 的滚动层缺左或右渐隐（{ini}）")
                            continue
                        if not s["reachedEnd"]:
                            fails.append(f"[{label}] {s['sel']} 滚不到右缘（scrollLeft 未到底）——"
                                         f"状态翻转判据失效")
                            continue
                        if ini["opR"] is None or ini["opR"] < 0.5:
                            fails.append(f"[{label}] {s['sel']} 起始态右暗示不可见"
                                         f"（opacity={ini['opR']}）——暗示等于没给")
                        if rgt["opR"] is not None and rgt["opR"] > 0.5:
                            fails.append(f"[{label}] {s['sel']} 滚到右缘后右暗示仍在"
                                         f"（opacity={rgt['opR']}）——状态没跟着滚动更新")
                        if rgt["opL"] is not None and rgt["opL"] < 0.5:
                            fails.append(f"[{label}] {s['sel']} 滚到右缘后左渐隐没出现"
                                         f"（opacity={rgt['opL']}）")
                        back = s["scroller"]["back"]
                        if back["opL"] is not None and back["opL"] > 0.5:
                            fails.append(f"[{label}] {s['sel']} 滚回左缘后左渐隐没消失"
                                         f"（opacity={back['opL']}）")
                        for side in ("peL", "peR"):
                            if s["scroller"]["left"][side] != "none":
                                fails.append(f"[{label}] {s['sel']} 渐隐层 {side}="
                                             f"{s['scroller']['left'][side]}——会吃掉点击")
                        hit = s.get("hit") or {}
                        if hit.get("veil"):
                            fails.append(f"[{label}] {s['sel']} 右缘 {s['hit'].get('tag')}"
                                         f".{s['hit'].get('cls')} 挡住了命中测试——内容点不到了")
    return fails


# 每条变异 = (名字, 文件, 锚点, 替换, 期望被打红的判据关键词)
# needle 必须与失败文案同源：A 那条先前写死成"低于 11px 下限"，而失败文案用的是
# MIN_EFFECTIVE_FONT（渲染成 11.0）——变异真的把地板打红了 13 条，自检却因为 needle
# 对不上判成"未被捕获"。常量一改，写死的 needle 就会静默腐烂，所以这里由常量生成。
MUTATIONS = [
    ("A 撤掉可读性地板（抬升比例再打折，桌面宽图缩回不可读）", "index.html",
     "var target = narrow ? Math.max(need, 1) : need;",
     "var target = need * 0.4;", f"低于 {MIN_EFFECTIVE_FONT}px 下限"),
    ("B 不建滚动暗示层（外层 div 换了名字，判据找不到载体）", "index.html",
     "frame.className = 'scroll-frame';", "frame.className = 'scroll-frame-off';", "没有 .scroll-frame"),
    ("C 渐隐层吃掉点击（pointer-events 改成 auto）", "theme.css",
     "  pointer-events: none;\n  z-index: 3;\n",
     "  pointer-events: auto;\n  z-index: 3;\n", "挡住了命中测试"),
    ("D 暗示状态不随滚动更新（去掉 scroll 监听）", "index.html",
     "sc.addEventListener('scroll', sync, {passive: true});", "// 变异 D", "状态没跟着滚动更新"),
    ("E 宽图宿主不挂 is-wide（撑宽后仍居中）", "index.html",
     "host.classList.add('is-wide');", "host.classList.add('is-wide-noop');",
     "没挂号 is-wide"),
]


def apply_mutation(tmp: Path, mut) -> None:
    name, fname, old, new, _ = mut
    text = (DOCS / fname).read_text()
    if old and old not in text:
        raise SystemExit(f"变异 {name} 的锚点在 {fname} 里找不到——自检本身失效，先修这条变异")
    hits = text.count(old)
    if old and hits != 1:
        raise SystemExit(f"变异 {name} 的锚点在 {fname} 里出现 {hits} 次（需要恰好 1 次）——"
                         f"替换只吃第一处，歧义锚会把变异打到别的函数上，表现为「未被捕获」的假红")
    (tmp / fname).write_text(text.replace(old, new, 1) if old else text + new)


def run_mutations() -> int:
    bad = 0
    for mut in MUTATIONS:
        label, _, _, _, needle = mut
        tmp = Path(tempfile.mkdtemp(prefix="ainse-leg-mut-"))
        t0 = time.monotonic()
        try:
            for f in DOCS.rglob("*"):
                rel = f.relative_to(DOCS)
                if f.is_dir():
                    (tmp / rel).mkdir(parents=True, exist_ok=True)
                else:
                    dst = tmp / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(f.read_bytes())
            apply_mutation(tmp, mut)
            base, shutdown = serve(tmp)
            try:
                fails = audit(base, MUT_PAGES, ["light"])
            finally:
                shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        hit = [f for f in fails if needle in f]
        print(f"  [变异 {label}] 耗时 {time.monotonic() - t0:.0f}s → 报红 {len(fails)} 条，"
              f"命中「{needle}」{len(hit)} 条"
              + (f"，示例：{hit[0]}" if hit else (f"，其它失败：{fails[:2]}" if fails else "，且无任何失败")))
        if not hit:
            bad += 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutate", action="store_true")
    ap.add_argument("--report", action="store_true", help="逐图打印自然/有效字号与缩放")
    ap.add_argument("--screenshot", metavar="DIR")
    ap.add_argument("--themes", default="light,dark")
    ap.add_argument("--viewports", default="", help="逗号分隔的宽度档，如 1280,1440,390（默认 1280,390）")
    ap.add_argument("--pages", default="ALL", help="ALL 或逗号分隔的路由路径")
    args = ap.parse_args()

    if args.mutate:
        print(f"变异自检（{len(MUTATIONS)} 条，每条都必须让守卫按机制报红）：")
        bad = run_mutations()
        print("结论：" + ("每条变异都被具名捕获。" if bad == 0 else f"{bad} 条变异未被捕获。"))
        return 0 if bad == 0 else 1

    pages = ["ALL"] if args.pages == "ALL" else [p.strip() for p in args.pages.split(",") if p.strip()]
    themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    vps = parse_viewports(args.viewports) if args.viewports else VIEWPORTS
    shot = Path(args.screenshot) if args.screenshot else None
    if shot:
        shot.mkdir(parents=True, exist_ok=True)
    base, shutdown = serve(DOCS)
    try:
        fails = audit(base, pages, themes, shot, args.report, vps)
    finally:
        shutdown()
    if fails:
        grouped: dict[str, int] = {}
        for f in fails:
            grouped.setdefault(re.sub(r"\d+(\.\d+)?", "N", f), 0)
            grouped[re.sub(r"\d+(\.\d+)?", "N", f)] += 1
        print(f"可读性闸失败 {len(fails)} 条，折叠同形后 {len(grouped)} 类（前 30 类）：")
        for k, n in list(grouped.items())[:30]:
            print(f"  ✗ {'' if n == 1 else f'×{n} '}{k}")
        if len(grouped) > 30:
            print(f"  …另有 {len(grouped) - 30} 类")
        return 1
    print(f"可读性闸通过：{'/'.join(str(v[0]) for v in vps)} 档 × 主题 {'/'.join(themes)}——"
          f"每张图有效字号 ≥ {MIN_EFFECTIVE_FONT}px、宽图左对齐不居中溢出、"
          f"所有需横向滚动的图与表都有随滚动更新的边缘暗示，且暗示层不吃点击。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
