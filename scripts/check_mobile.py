#!/usr/bin/env python3
"""第六条守卫·窄屏几何闸：390 档的"看得见但挤作一团"类缺陷。

为什么命中测试闸（第五条）看不见这类缺陷：2026-09-24 实测，顶栏五项被压扁后每项
在 60px 固定条内折成两行（rect 高 59、中心 y=29），`elementFromPoint` 依旧点在它自己身上
——命中测试全绿，读者看到的却是挤成一团的顶栏。同类：mermaid 被 `max-width:100%`
等比缩到 340px，节点文字 4～5px；以及居中溢出把图左半张推到 `scrollLeft` 够不到的负偏移。
所以本守卫只量几何：行数、是否留在固定条内、图缩放、图左缘、正文层与文档的横向溢出。

用法：
    python3 scripts/check_mobile.py            # 全量：4 个代表页 × 390x844
    python3 scripts/check_mobile.py --mutate   # 变异自检：每条判据都要能被按机制打红
    python3 scripts/check_mobile.py --screenshot DIR   # 顺手存图，供人工看图

约定：自带一次性本地服务器与无头 Chrome，零 CDN、零外部依赖。退出码 0 = 全绿。
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import CDP, free_port  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
W, H = 390, 844

# 代表页：含顶栏 + 至少一张 mermaid + 宽表格；缺一类实物就没有页能触发对应判据。
PAGES = {
    "总览": "README",
    "时间线": "manuscript/ch03-案例时间线",
    "数字清单": "manuscript/ch05-数字清单",
    "部分卷首": "manuscript/part-1-认知",
}
SCALE_MIN = 0.95  # 判"缩成糊图"的口径 = 渲染宽 / viewBox 宽。窄屏下每张图都按自己的
                  # viewBox 定宽（index.html 的 ainseGuardDiagramWidth），所以应当是 1.00。
                  # 用绝对宽度当判据会误伤甘特——302px 的甘特在 390 下天然就该是 302px。

PROBE_JS = r"""
(function (W, H, SCALE_MIN) {
  function lineCount(el) {
    // 真实折行数用 Range 行盒数：computed height 会被 box-sizing 与 padding 骗过
    // （实测 .app-nav a 高 35 = 23.4 行高 + 上下 6px padding，按高度判会全员假红）。
    var rng = document.createRange();
    rng.selectNodeContents(el);
    var tops = {}, n = 0;
    [].forEach.call(rng.getClientRects(), function (r) {
      if (r.width > 0.5) { var k = Math.round(r.top); if (!tops[k]) { tops[k] = 1; n++; } }
    });
    return n;
  }
  function rect(el) {
    var r = el.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
  }
  var nav = document.querySelector('.app-nav');
  var ul = nav && nav.querySelector('ul');
  var navRect = nav ? rect(nav) : null;
  var links = [].slice.call(nav ? nav.querySelectorAll('a') : []).map(function (a) {
    var r = rect(a);
    return { text: (a.innerText || '').trim().slice(0, 12), rect: r, lines: lineCount(a),
             insideBar: !!(navRect && r[1] >= navRect[1] - 1 && r[3] + r[1] <= navRect[3] + navRect[1] + 1) };
  });
  var mermaid = [].slice.call(document.querySelectorAll('.mermaid-block')).map(function (b) {
    var s = b.querySelector('svg');
    var br = rect(b), sr = s ? rect(s) : null;
    var vb = null;
    if (s && s.viewBox && s.viewBox.baseVal.width) { vb = s.viewBox.baseVal.width; }
    return { hasSvg: !!s, blockLeft: br[0], blockW: br[2], svg: sr, viewBoxW: vb,
             scale: (sr && vb) ? +(sr[2] / vb).toFixed(2) : null,
             tooNarrow: !!(sr && vb && sr[2] / vb < SCALE_MIN),
             leftClipped: !!(sr && sr[0] < br[0] - 1) };
  });
  var contentEl = document.querySelector('.content');
  return JSON.stringify({
    hash: location.hash,
    navPresent: !!nav, nav: navRect,
    navPosition: nav ? getComputedStyle(nav).position : null,
    ulWrap: ul ? getComputedStyle(ul).flexWrap : null,
    ulScrollW: ul ? ul.scrollWidth : null, ulClientW: ul ? ul.clientWidth : null,
    ulOverflowX: ul ? getComputedStyle(ul).overflowX : null,
    navJustify: nav ? getComputedStyle(nav).justifyContent : null,
    links: links, mermaid: mermaid,
    // 本站真正的横向滚动容器是 .content（绝对定位的滚动层），不是 documentElement：
    // 只量 documentElement.scrollWidth 会漏判——实测把正文强撑到 1400px，
    // documentElement 读数纹丝不动，破版却发生在 .content 里。
    contentOverflowX: contentEl ? contentEl.scrollWidth - contentEl.clientWidth : null,
    contentBox: contentEl ? rect(contentEl) : null,
    pageOverflowX: document.documentElement.scrollWidth - W
  });
})(%d, %d, %s)
""" % (W, H, SCALE_MIN)


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


def audit(base: str, shot_dir: Path | None = None, report: bool = False) -> list[str]:
    from urllib.parse import quote, unquote
    fails: list[str] = []
    with CDP(W, H) as b:
        b.set_viewport(W, H, mobile=True)
        for label, path in PAGES.items():
            b.navigate(f"{base}/#/{quote(path)}")
            rendered = b.wait_for(
                "document.querySelector('.markdown-section') && "
                "document.querySelector('.markdown-section').textContent.length > 40", 25)
            b.wait_for("!document.querySelector('section.cover.show')", 15)
            time.sleep(1.5)
            if not rendered:
                fails.append(f"[{label}] 正文未渲染，本页读数作废")
                continue
            d = json.loads(b.js(PROBE_JS))
            if unquote((d["hash"] or "").lstrip("#")).strip("/") != path:
                fails.append(f"[{label}] 落在 {d['hash']!r}，应为 {path!r}——读数作废")
                continue
            if shot_dir:
                b.screenshot(str(shot_dir / f"390_{label}.png"))
            if not d["navPresent"]:
                fails.append(f"[{label}] 顶栏不在 DOM 里——判据无对象，不算通过")
                continue
            if not d["links"]:
                fails.append(f"[{label}] 顶栏一个链接都没量到——选择器失效，不算通过")
            for l in d["links"]:
                if l["lines"] != 1:
                    fails.append(f"[{label}] 顶栏「{l['text']}」折成 {l['lines']} 行"
                                 f"（rect {l['rect']}，条 {d['nav']}）")
                if not l["insideBar"]:
                    fails.append(f"[{label}] 顶栏「{l['text']}」跑出固定条"
                                 f"（rect {l['rect']}，条 {d['nav']}，position={d['navPosition']}）")
            if (d["ulScrollW"] or 0) - (d["ulClientW"] or 0) > 1 and d["ulOverflowX"] != "auto":
                fails.append(f"[{label}] 顶栏内容 {d['ulScrollW']}px 超出可视 {d['ulClientW']}px "
                             f"却没有横向滚动（overflow-x={d['ulOverflowX']}），右端项滚不进来")
            if (d["ulScrollW"] or 0) - (d["ulClientW"] or 0) > 1 and d["navJustify"] == "flex-end":
                fails.append(f"[{label}] 顶栏超宽且 justify-content:flex-end——溢出会往左滚不回"
                             f"（实测末项中心 x>{W}）")
            for i, m in enumerate(d["mermaid"]):
                if not m["hasSvg"]:
                    continue
                if report:
                    print(f"  · [{label}] mermaid#{i} viewBox={m['viewBoxW']} "
                          f"渲染={m['svg'] and m['svg'][2]} 缩放={m['scale']} 左缘={m['svg'] and m['svg'][0]}"
                          f"/容器{m['blockLeft']}")
                if m["tooNarrow"]:
                    fails.append(f"[{label}] mermaid#{i} 缩放 {m['scale']}（viewBox {m['viewBoxW']} → "
                                 f"渲染 {m['svg'][2]}px）低于 {SCALE_MIN}，等比缩成糊图")
                if m["leftClipped"]:
                    fails.append(f"[{label}] mermaid#{i} 图左缘 x={m['svg'][0]} 在容器 "
                                 f"{m['blockLeft']} 之外——居中溢出滚不回来")
            if (d["contentOverflowX"] or 0) > 1:
                fails.append(f"[{label}] 正文层 .content 横向溢出 {d['contentOverflowX']}px"
                             f"（box {d['contentBox']}）——出现整页横滚，破版")
            if d["pageOverflowX"] > 1:
                fails.append(f"[{label}] 文档横向溢出 {d['pageOverflowX']}px")
    return fails


# 每条变异 = (名字, 改哪个文件, 锚点, 替换成, 期望被打红的判据名)。
# 锚点缺失即中止，避免"补丁没打上 → 全绿"的假自检；old 为空表示追加。
# 锚点/替换也可以是**等长列表**：一条机制今天由两条规则共同守住时（宽图左对齐＝`.is-wide`
# 通用规则 + 窄屏媒体查询），只删一条会让变异变成"改了但没坏"的假绿（本轮 C 就是这样：
# 删掉媒体查询那条，is-wide 仍把图钉在左缘，报红 0 条）。逐条各自验唯一性。
MUTATIONS = [
    ("A 顶栏允许换行（去掉 ul 的 nowrap）", "theme.css",
     "    flex-wrap: nowrap;\n", "    flex-wrap: wrap;\n", "跑出固定条"),
    ("B 顶栏项可被压扁（去掉 li 不被压缩 + 链接 nowrap）", "theme.css",
     "  .app-nav li { flex: 0 0 auto; }\n\n  .app-nav a {\n    white-space: nowrap;\n",
     "  .app-nav li { flex-shrink: 1; }\n\n  .app-nav a {\n", "折成 2 行"),
    ("C 撤掉宽图左对齐（两条 flex-start 一起删，撑宽后左半张推到负偏移）", "theme.css",
     [".mermaid-block .mermaid.is-wide {\n  justify-content: flex-start;\n}",
      "  .mermaid-block .mermaid {\n    justify-content: flex-start;\n  }"],
     ["/* 变异 C：删掉宽图（is-wide）左对齐 */", "  /* 变异 C：删掉窄屏左对齐 */"],
     "居中溢出滚不回来"),
    ("D 正文强行加宽（造出正文层整页横滚）", "theme.css",
     "", "\n.markdown-section{min-width:1400px !important;}\n", "正文层 .content 横向溢出"),
    ("E 窄屏定宽守卫失配（matchMedia 永不命中，图被等比缩糊）", "index.html",
     "      var narrow = window.matchMedia('(max-width: ' + AINSE_NARROW + 'px)').matches;\n"
     "      var target = narrow ? Math.max(need, 1) : need;",
     "      var narrow = window.matchMedia('(min-width: 4000px)').matches;\n"
     "      var target = narrow ? Math.max(need, 1) : need;", "等比缩成糊图"),
]


def apply_mutation(tmp: Path, mut) -> None:
    name, fname, old, new, _ = mut
    pairs = list(zip(old, new)) if isinstance(old, list) else [(old, new)]
    text = (DOCS / fname).read_text()
    for o, n in pairs:
        if o and o not in text:
            raise SystemExit(f"变异 {name} 的锚点在 {fname} 里找不到——自检本身失效，先修这条变异")
        # 锚点必须唯一：替换只吃第一处，同一段代码在别处出现过时，变异会打到另一个函数上——
        # 表现为「变异未被捕获」的假红（本轮 E 第一次就是这样：锚点命中 ainseGanttWidth 的
        # matchMedia，窄屏定宽守卫原地不动，图当然不糊）。歧义要在打补丁之前中止。
        hits = text.count(o)
        if o and hits != 1:
            raise SystemExit(f"变异 {name} 的锚点在 {fname} 里出现 {hits} 次（需要恰好 1 次）——"
                             f"第一处不一定是你要改的那一处，请把锚点写成整行以消除歧义")
        text = text.replace(o, n, 1) if o else text + n
    (tmp / fname).write_text(text)


def run_mutations() -> int:
    bad = 0
    for mut in MUTATIONS:
        label, _, _, _, needle = mut
        tmp = Path(tempfile.mkdtemp(prefix="ainse-mob-mut-"))
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
                fails = audit(base)
            finally:
                shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        hit = [f for f in fails if needle in f]
        print(f"  [变异 {label}] 耗时 {time.monotonic() - t0:.0f}s -> "
              f"报红 {len(fails)} 条，命中机制判据「{needle}」{len(hit)} 条"
              + (f"，示例：{hit[0]}" if hit else (f"，全部失败：{fails[:2]}" if fails else "，且无其它失败")))
        if not hit:
            bad += 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutate", action="store_true", help="变异自检：每条判据都要能被按机制打红")
    ap.add_argument("--screenshot", metavar="DIR", help="把 390 档截图存到 DIR")
    ap.add_argument("--report", action="store_true", help="逐图打印 viewBox / 渲染宽 / 缩放")
    args = ap.parse_args()

    if args.mutate:
        print(f"变异自检（{len(MUTATIONS)} 条，每条都必须让守卫按机制报红）：")
        bad = run_mutations()
        print("结论：" + ("每条变异都被具名捕获。" if bad == 0 else f"{bad} 条变异未被捕获。"))
        return 0 if bad == 0 else 1

    base, shutdown = serve(DOCS)
    try:
        shot = Path(args.screenshot) if args.screenshot else None
        if shot:
            shot.mkdir(parents=True, exist_ok=True)
        fails = audit(base, shot, args.report)
    finally:
        shutdown()
    if args.screenshot:
        print(f"  截图已存：{args.screenshot}")
    if fails:
        print(f"窄屏几何闸失败 {len(fails)} 条：")
        for f in fails:
            print(f"  ✗ {f}")
        return 1
    print(f"窄屏几何闸通过：{len(PAGES)} 个代表页 × {W}x{H}——"
          f"顶栏无折行/无溢出固定条、mermaid 按各自 viewBox 定宽（无缩糊、无滚不回的居中溢出）、"
          f"正文层与文档均无横向溢出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
