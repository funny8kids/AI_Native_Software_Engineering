#!/usr/bin/env python3
"""第五条守卫·交互闸：命中测试 + 真实点击，把"点得动"变成每次改动后的强制闸。

为什么必须有这条守卫（2026-09-24 事故）：封面 section.cover 是
position:fixed + 100vh + z-index:999，Docsify 收起封面时只摘掉 show 类、节点仍留在
DOM，于是非封面路由上它依旧铺满整个视口——正文看得见，但每一次点击都落在它身上。
用户报"怎么点击都没有反应"时，此前所有"浏览器已验证"的结论都来自 DOM/几何读数，
看不见遮挡类缺陷。所以本守卫只认两类证据：
  1) elementFromPoint 命中测试——坐标上真正接住事件的元素是谁；
  2) CDP Input 域的真实鼠标点击——点击后路由/主题/滚动是否确实变化。
正文里覆在图与宽表之上的滚动暗示层（.scroll-veil，2026-09-24 新增）两类证据都用：
命中测试逐点判它穿不穿得透，再对可见的暗示层真点一次、用捕获阶段的监听读回事件真正的接收者。

用法：
    python3 scripts/check_interactions.py                 # 全量：62 条路由 × 1280/390 两档 + 点击链
    python3 scripts/check_interactions.py --limit 8       # 冒烟：只跑前 8 条路由
    python3 scripts/check_interactions.py --mutate        # 变异自检：证明本守卫会报红（退出码 1）
    python3 scripts/check_interactions.py --mutate M3     # 只跑某一条变异（每条会打印自己的耗时）

约定：自带一次性本地服务器（无需手工起 http.server），自带无头 Chrome，
零 CDN、零外部依赖。退出码 0 = 全绿，1 = 有具名失败。
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import CDP, free_port, safe_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# 每页 5 个采样点（视口相对坐标）：正文中心、侧边栏下部、顶栏下方正文、
# 右下角浮动按钮区、顶栏。这五点覆盖"用户会点的所有层"。
SAMPLE_POINTS = [(0.50, 0.50), (0.15, 0.80), (0.70, 0.13), (0.94, 0.94), (0.50, 0.06)]

# 控件分组 -> CSS 选择器。分组是"读者能点的东西"的完整清单，缺一组就是漏判。
CONTROL_GROUPS = [
    ("封面入口", ".cover a"),
    ("侧边栏链接", ".sidebar li a"),
    ("顶栏链接", ".app-nav a"),
    ("浮动按钮", ".float-btn"),
    ("翻页控件", ".pagination-item"),
    ("本页目录", ".page-toc a"),
    ("抽屉开关", ".sidebar-toggle"),
]

# 一次求值完成：5 点命中 + 七组控件逐个命中测试。返回 JSON。
PROBE_JS = r"""
(function (pts, groups) {
  var W = innerWidth, H = innerHeight;
  function desc(el) {
    if (!el) return 'null';
    var t = el.tagName.toLowerCase();
    var id = el.id ? '#' + el.id : '';
    var cls = (typeof el.className === 'string' && el.className.trim())
      ? '.' + el.className.trim().split(/\s+/).join('.') : '';
    return t + id + cls;
  }
  function chain(el) {
    var out = [];
    while (el && out.length < 4) { out.push(desc(el)); el = el.parentElement; }
    return out.join(' < ');
  }
  function onLayout(el) {
    for (var e = el; e && e !== document.documentElement; e = e.parentElement) {
      var cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    }
    // pointer-events:none 是"设计上当下不可点"（如返回顶部按钮淡出中），
    // 不是遮挡。把它算作一次命中失败，守卫就会在正常的过渡期里报假红。
    if (getComputedStyle(el).pointerEvents === 'none') return false;
    return parseFloat(getComputedStyle(el).opacity) > 0.05;
  }
  // theme.css 开了 scroll-behavior:smooth，默认 scrollIntoView 是动画：
  // 紧接着量的矩形是动画前的位置，命中测试就会指到别的元素上（实测假红两处）。
  // 读数必须来自落定后的几何，所以这里强制 instant。
  function settle(el) { el.scrollIntoView({ block: 'center', behavior: 'instant' }); }
  var hits = pts.map(function (p) {
    var x = Math.round(W * p[0]), y = Math.round(H * p[1]);
    var el = document.elementFromPoint(x, y);
    return {
      at: [x, y],
      hit: chain(el),
      underCover: !!(el && el.closest && el.closest('section.cover')),
      coverShown: !!(document.querySelector('section.cover.show')),
    };
  });
  var controls = [];
  function centreIn(el) {
    var r = el.getBoundingClientRect();
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    return r.width >= 2 && r.height >= 2 && cx > 1 && cy > 1 && cx < W - 1 && cy < H - 1;
  }
  groups.forEach(function (g) {
    var name = g[0], nodes = [].slice.call(document.querySelectorAll(g[1]));
    var tested = 0, off = 0, hidden = 0;
    nodes.forEach(function (el) {
      if (!onLayout(el)) { hidden++; return; }
      // 判定用"中心点在视口内"，不能用 clamp：把 y=910 的点的坐标 clamp 到 898，
      // 命中测试就指到了相邻的那条链接上（实测假红：目标与遮罩的描述完全同形）。
      if (!centreIn(el)) {
        settle(el);                                     // 读者会滚到它面前再点
        if (!centreIn(el)) { off++; return; }            // 抽屉外/视口外：该档不该要求它可点
      }
      var r = el.getBoundingClientRect();
      var x = Math.round(r.left + r.width / 2);
      var y = Math.round(r.top + r.height / 2);
      var hit = document.elementFromPoint(x, y);
      tested++;
      if (!(hit && (hit === el || el.contains(hit)))) {
        var hr = hit ? hit.getBoundingClientRect() : null;
        controls.push({
          group: name, target: chain(el), at: [x, y], blockedBy: chain(hit),
          targetText: (el.innerText || el.getAttribute('href') || '').trim().slice(0, 24),
          targetRect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
          blockedText: hit ? (hit.innerText || hit.getAttribute('href') || '').trim().slice(0, 24) : '',
          blockedRect: hr ? [Math.round(hr.left), Math.round(hr.top), Math.round(hr.width), Math.round(hr.height)] : null,
        });
      }
    });
    controls.push({ group: name, summary: true, present: nodes.length,
                    tested: tested, offscreen: off, hidden: hidden });
  });
  // ---- 滚动暗示层（.scroll-frame / .scroll-veil）：它盖在正文与表格之上，必须穿透 ----
  // 判据不能看 opacity：提示层有 .18s 淡入，正文刚渲染完时淡入还没走完，会把
  // "有暗示层、正在淡入"报成"暗示层不存在"。所以节点存在性按 DOM 算，
  // 可点性（要不要真点一次）才按淡入完成后的计算值算，且只用作候选。
  var frames = [].slice.call(document.querySelectorAll('.scroll-frame'));
  var veilEls = 0, needScroll = 0, veils = [];
  frames.forEach(function (fr) {
    var sc = fr.querySelector('.mermaid-block, .table-scroll');
    if (!sc) return;
    var over = sc.scrollWidth - sc.clientWidth;
    var fi = -1;
    if (over > 2) { needScroll++; fi = needScroll - 1; }   // 跨页定位用序号，不用坐标
    [].slice.call(fr.querySelectorAll('.scroll-veil')).forEach(function (v) {
      veilEls++;
      if (over <= 2) return;                       // 不需要滚 → 不该有可见暗示，也不用来点
      var cs = getComputedStyle(v), r = v.getBoundingClientRect();
      var x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
      var hit = document.elementFromPoint(x, y);
      var side = /(^|\s)left(\s|$)/.test(v.className) ? 'left' : 'right';
      // "这一侧此刻该不该显示"只问状态类，不问 computed opacity：提示层有 .18s 淡入，
      // 正文刚渲染完时 opacity 还在过渡（实测 0.00x），拿它当候选条件会让真点这一步
      // 永远 0 次执行（第一版就是这样：516 点命中、0 次真点）。
      // 第二版改用"坐标在视口内"当候选条件，同样 0 次真点——量测时的坐标不能沿用：
      // 同一次求值里控件那一段 settle() 滚过侧边栏，正文里暗示层的 y 已经换人了
      // （实测 ch37 那条的 y=7345，远超 900 视口）。所以这里只交状态类 + 容器序号，
      // 真点前重新定位再量坐标。
      veils.push({ side: side, at: [x, y], pe: cs.pointerEvents, overflow: Math.round(over),
                   fi: fi, fade: parseFloat(cs.opacity),
                   on: fr.classList.contains(side === 'left' ? 'has-left' : 'has-right'),
                   hit: chain(hit), eats: !!(hit && (hit === v || v.contains(hit))),
                   inView: x > 1 && y > 1 && x < W - 1 && y < H - 1 });
    });
  });
  return JSON.stringify({
    viewport: [W, H],
    hash: location.hash,
    title: (document.querySelector('.markdown-section h1') || {}).innerText || '',
    veils: veils, needScroll: needScroll, veilEls: veilEls,
    hits: hits,
    controls: controls,
    overflow: [].slice.call(document.querySelectorAll('.sidebar li a')).filter(function (a) {
      return a.scrollWidth > a.clientWidth + 1;
    }).map(function (a) { return a.innerText.trim(); }),
  });
})(%s, %s)
"""

# 真实点击的接收者只能从事件本身读：给 document 挂一个捕获阶段监听，把这次点击的
# target 描述存到全局，点完再取。只挂一次（重复挂载会让同一次点击写三遍读数）。
VEIL_SPY_ARM = r"""(function () {
  if (window.__ainseVeilArmed) return 1;
  window.__ainseVeilArmed = 1;
  document.addEventListener('click', function (e) {
    var t = e.target, d = (t.tagName || '').toLowerCase();
    var cls = (typeof t.className === 'string' ? t.className.trim() : '');
    window.__ainseVeilSpy = d + (cls ? '.' + cls.split(/\s+/)[0] : '');
  }, true);
  return 1;
})()"""


def serve(directory: Path):
    """在临时端口上提供 directory，返回 (base_url, shutdown)。"""

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # 守卫的输出只讲判定，不讲访问日志
            pass

    # 浏览器对同一主机并发开 6 条连接；串行的 TCPServer 会把字体/图片/多个 .md 的
    # 请求排成队，慢起来够把 wait_for 拖成超时，再被误读成站点卡死。
    httpd = socketserver.ThreadingTCPServer(
        ("127.0.0.1", free_port()), functools.partial(Quiet, directory=str(directory)))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", httpd.shutdown


def js_route_list(base: str) -> list[str]:
    """路由集合直接问浏览器：侧边里去重后的文件型链接就是读者能走到的全部页面。"""
    with CDP(1280, 900) as b:
        b.navigate(f"{base}/#/")
        b.wait_for("document.querySelector('.sidebar li a')", 30)
        hrefs = b.js(
            """JSON.parse(JSON.stringify(
                 [].slice.call(document.querySelectorAll('.sidebar li a'))
                   .map(function (a) { return a.getAttribute('href') || ''; })
                   .filter(function (h) { return h && !/[?&]id=/.test(h); })
               ))"""
        )
        seen, out = set(), []
        for h in hrefs:
            path = h[1:] if h.startswith("#") else h
            if path not in seen:
                seen.add(path)
                out.append(path)
        return out


WALK_MARK_JS = """(function () {
  function d(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }
  [].slice.call(document.querySelectorAll('[data-ainse-walk]')).forEach(function (x) {
    x.removeAttribute('data-ainse-walk');
  });
  var target = %s, needle = %s;
  var anchors = [].slice.call(document.querySelectorAll('.sidebar li a'));
  // 用"解码后相等"挑入口，和点击后的哈希判定同一口径：Docsify 在不同页面态下
  // 会把中文路径写成原文或百分号编码两种形式，字面属性选择器会挑不到（实测 78 个入口 0 命中）。
  var hits = anchors.filter(function (a) { return d(a.getAttribute('href') || '') === d(target); });
  if (!hits.length) {
    return JSON.stringify({ count: 0, near: anchors.map(function (a) { return a.getAttribute('href'); })
      .filter(function (h) { return needle && h.indexOf(needle) > -1; }).slice(0, 3) });
  }
  hits[0].setAttribute('data-ainse-walk', '1');
  return JSON.stringify({ count: hits.length, text: (hits[0].innerText || '').trim().slice(0, 24) });
})()"""


class Suite:
    """一次浏览器会话跑完：逐路由命中测试 + 真实点击链。失败以具名条目累积。"""

    def __init__(self, base: str, routes: list[str], widths: list[tuple[int, int]],
                 limit: int | None, chain: bool = True):
        self.base = base
        self.routes = routes[:limit] if limit else routes
        self.widths = widths
        self.chain = chain
        self.failures: list[str] = []
        self.counters = {"routes": 0, "hitpoints": 0, "controls": 0, "clicks": 0,
                         "veil_nodes": 0, "veil_points": 0, "veil_clicks": 0, "veil_on": 0}
        self.console: list[str] = []
        # 每档视口最多真点两处暗示层：目标是"证明这层不吃点击"，不是遍历 90 个容器
        self.veil_targets: list[tuple[str, list, str, int]] = []

    VEIL_CLICK_MAX = 2

    def fail(self, what: str) -> None:
        self.failures.append(what)

    # ---------- 逐路由命中测试 ----------
    def sweep(self) -> None:
        with CDP(self.widths[0][0], self.widths[0][1]) as b:
            b.navigate(f"{self.base}/#/")
            if not b.wait_for("document.querySelector('.sidebar li a')", 30):
                self.fail("站点首屏未渲染（侧边栏无链接），后续判定全部失效")
                return
            for w, h in self.widths:
                b.set_viewport(w, h, mobile=w < 700)
                clicks0, points0 = self.counters["veil_clicks"], self.counters["veil_points"]
                for route in self.routes:
                    self.probe_route(b, route, w, h)
                print(f"  · 命中测试 {w}x{h}：{self.counters['routes']} 页 / "
                      f"{self.counters['controls']} 个控件，累计失败 {len(self.failures)}", flush=True)
                if self.chain:
                    self.click_chain(b, w, h)
                    print(f"  · 真实点击链 {w}x{h}：{self.counters['clicks']} 次，"
                          f"累计失败 {len(self.failures)}", flush=True)
                cand = len(self.veil_targets)
                on0 = self.counters["veil_on"]
                self.veil_click_through(b, w, h)
                got = self.counters["veil_clicks"] - clicks0
                pts = self.counters["veil_points"] - points0
                print(f"  · 暗示层穿透 {w}x{h}：节点 {self.counters['veil_nodes']} 个、"
                      f"命中测试 {pts} 点（其中该侧有状态类 {self.counters['veil_on']} 点）、"
                      f"真点 {got}/{cand} 处（接收者都不是暗示层）", flush=True)
                # 有对象可量却一次真点都没跑＝这一判据只剩命中测试半条腿。
                # 上一版正是这个状态（候选条件用了淡入中的 opacity，516 点命中、0 次点击），
                # "全绿"里藏着一段从不执行的代码。
                if pts and not got:
                    self.fail(f"[{w}x{h}] 暗示层命中测试量到 {pts} 点、该侧有状态类 "
                              f"{on0} 点，真实点击却 0 次——穿透判据只剩几何半条腿，"
                              f"本档结论不成立（候选 {cand} 处）")
            self.check_console_errors(b)

    def goto(self, b: CDP, route: str, w: int, h: int) -> bool:
        b.js(f"location.hash = {json.dumps(route)}")
        ok = b.wait_for(
            "document.querySelector('.markdown-section') "
            "&& document.querySelector('.markdown-section').innerText.trim().length > 50",
            20,
        )
        if not ok:
            self.fail(f"[{w}x{h}] {route}：正文在 20s 内没有渲染出来（卡死）")
        return ok

    def probe_route(self, b: CDP, route: str, w: int, h: int) -> dict | None:
        is_cover = route.lstrip("#") in ("", "/")
        if is_cover:
            b.js("location.hash = '#/'")
            b.wait_for("document.querySelector('section.cover.show')", 20)
        elif not self.goto(b, route, w, h):
            return None
        rep = json.loads(b.js(PROBE_JS % (json.dumps(SAMPLE_POINTS), json.dumps(CONTROL_GROUPS))))
        self.counters["routes"] += 1
        on_cover = sum(1 for h in rep["hits"] if h["underCover"])
        for hit in rep["hits"]:
            self.counters["hitpoints"] += 1
            if is_cover:
                continue
            if hit["underCover"]:
                self.fail(
                    f"[{w}x{h}] {route}：坐标 {hit['at']} 被封面接走（{hit['hit']}）——"
                    f"cover.show={hit['coverShown']}，整页不可点击"
                )
        if is_cover and (on_cover < 4 or not rep["hits"][0]["coverShown"]):
            self.fail(
                f"[{w}x{h}] {route}：封面应当接住整屏，实测 5 点只有 {on_cover} 点落在封面上"
            )
        by_group: dict[str, list] = {}
        for c in rep["controls"]:
            if c.get("summary"):
                by_group[c["group"]] = c
                self.counters["controls"] += c["tested"]
                continue
            self.fail(
                f"[{w}x{h}] {route}：{c['group']}「{c['targetText']}」中心 {c['at']} "
                f"(rect {c['targetRect']}) 点不到，被「{c['blockedText']}」(rect {c['blockedRect']}) "
                f"{c['blockedBy']} 挡住"
            )
        for name, summ in by_group.items():
            if summ["tested"] == 0 and summ["present"] > 0 and self.must_be_hittable(name, w, is_cover):
                self.fail(
                    f"[{w}x{h}] {route}：{name} 存在 {summ['present']} 个，但 0 个通过命中测试"
                    f"（不在布局 {summ['hidden']}、在视口外 {summ['offscreen']}）"
                    f"——该档宽度下这一组必须可点"
                )
        if not is_cover and rep["overflow"]:
            self.fail(
                f"[{w}x{h}] {route}：侧边栏有 {len(rep['overflow'])} 条标题被裁切："
                + "、".join(rep["overflow"][:4])
            )
        # —— 滚动暗示层：命中测试逐点判"穿不穿得透"，并把可点候选交给真实点击
        self.counters["veil_nodes"] += rep["veilEls"]
        if rep["needScroll"] and not rep["veilEls"]:
            self.fail(
                f"[{w}x{h}] {route}：{rep['needScroll']} 个容器要横向滚动，页内却有 0 个"
                f" .scroll-veil 节点——读者无从知道右边还有内容"
            )
        for v in rep["veils"]:
            self.counters["veil_points"] += 1
            if v["eats"]:
                self.fail(
                    f"[{w}x{h}] {route}：{v['side']} 侧暗示层在 {v['at']} 挡住了命中测试"
                    f"（overflow={v['overflow']}px，接住点击的是 {v['hit']}）——它吃掉点击"
                )
            if v["pe"] != "none":
                self.fail(
                    f"[{w}x{h}] {route}：{v['side']} 侧暗示层 pointer-events={v['pe']}"
                    f"——覆盖在表格与图上的层必须只看不拦"
                )
            if v["on"]:
                self.counters["veil_on"] += 1
                # 候选只按「该侧此刻该显示」选，不按坐标在不在视口内选：命中测试跑之前
                # 控件那一段会 settle() 滚侧边栏，正文里暗示层的 y 早就不是点的时候的 y 了。
                # 真点时重新定位＋滚到跟前（见 veil_click_through），坐标现量。
                if len(self.veil_targets) < self.VEIL_CLICK_MAX:
                    self.veil_targets.append((route, v["fi"], v["side"], v["overflow"]))
        return rep

    VEIL_ANCHOR_JS = r"""(function (fi, side) {
      var n = 0;
      var frames = [].slice.call(document.querySelectorAll('.scroll-frame'));
      for (var i = 0; i < frames.length; i++) {
        var fr = frames[i];
        var sc = fr.querySelector('.mermaid-block, .table-scroll');
        if (!sc) continue;
        if (sc.scrollWidth - sc.clientWidth <= 2) continue;
        if (n++ !== fi) continue;
        var v = [].slice.call(fr.querySelectorAll('.scroll-veil')).filter(function (x) {
          return new RegExp('(^|\\s)' + side + '(\\s|$)').test(x.className);
        })[0];
        if (!v) return JSON.stringify({missing: 'veil'});
        v.scrollIntoView({block: 'center', behavior: 'instant'});
        var r = v.getBoundingClientRect(), W = innerWidth, H = innerHeight;
        var x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
        return JSON.stringify({
          at: [x, y], inView: x > 1 && y > 1 && x < W - 1 && y < H - 1,
          on: fr.classList.contains(side === 'left' ? 'has-left' : 'has-right'),
          overflow: Math.round(sc.scrollWidth - sc.clientWidth), sl: Math.round(sc.scrollLeft)
        });
      }
      return JSON.stringify({missing: 'frame'});
    })"""

    def veil_click_through(self, b: CDP, w: int, h: int) -> None:
        """真实点击暗示层覆盖的坐标，用捕获阶段的事件监听取回**事件真正的接收者**。

        命中测试（elementFromPoint）说"穿透"仍只是几何读数：CSS 改了 pointer-events、
        或层叠上下文变了，只有派发出去的那一次点击会给出答案。所以这里既真点、又核对
        接收者不是 .scroll-veil——两条证据同向才算通过。

        坐标不能沿用命中测试那一次：Docsify 换页会重画正文，控件那一段还会滚动，
        沿用旧坐标＝点在一块可能根本不存在暗示层的地方。所以按容器序号重新定位、
        滚到跟前、重新量中心，再点。
        """
        if not self.veil_targets:
            return
        for route, fi, side, overflow in self.veil_targets:
            if not self.goto(b, route, w, h):
                continue
            anchor = json.loads(b.js(f"{self.VEIL_ANCHOR_JS}({fi}, {json.dumps(side)})"))
            if anchor.get("missing"):
                self.fail(f"[{w}x{h}] {route}：真点前重定位第 {fi} 个横向滚动容器的 {side} 侧暗示层"
                          f"失败（{anchor['missing']} 不在）——候选失效，本条判定未执行")
                continue
            if not anchor["on"] or anchor["overflow"] <= 2:
                self.fail(f"[{w}x{h}] {route}：第 {fi} 个容器需横向滚动 {anchor['overflow']}px"
                          f"（scrollLeft={anchor['sl']}），{side} 侧暗示层状态类却没生效"
                          f"——读者看不到这一侧的滚动暗示")
                continue
            if not anchor["inView"]:
                self.fail(f"[{w}x{h}] {route}：{side} 侧暗示层滚到跟前仍不在视口内"
                          f"（中心 {anchor['at']}）——无法真点，本条判定未执行")
                continue
            x, y = anchor["at"]
            b.js(VEIL_SPY_ARM)
            b.js("window.__ainseVeilSpy = null; 1")
            b.click(x, y)
            self.counters["clicks"] += 1
            time.sleep(0.25)
            spy = b.js("window.__ainseVeilSpy")
            if spy is None:
                self.fail(f"[{w}x{h}] {route}：真点 {side} 侧暗示层 ({x},{y}) 后监听器没收到任何"
                          f"点击事件——点击没进入文档树，判定为无读数")
            elif "scroll-veil" in spy:
                self.fail(f"[{w}x{h}] {route}：真点 {side} 侧暗示层 ({x},{y})（该容器需横向滚动 "
                          f"{anchor['overflow']}px）后事件接收者是 {spy}——暗示层吃掉了读者的点击")
            else:
                self.counters["veil_clicks"] += 1
        self.veil_targets = []

    @staticmethod
    def must_be_hittable(group: str, w: int, is_cover: bool) -> bool:
        """判定该档宽度 + 该页型下哪组控件必须真的可点——防止"全部跳过"被当成"全部通过"。"""
        if group == "封面入口":
            return is_cover
        if is_cover:
            return False  # 封面在场时侧边栏/顶栏/正文按设计退出布局
        if group == "浮动按钮":
            return True
        if group == "抽屉开关":
            return w < 768
        if group == "本页目录":
            return w >= 1600
        if group == "侧边栏链接":
            return w >= 1024
        return True  # 顶栏链接、翻页控件

    def box_diagnosis(self, b: CDP, selector: str, needle: str = "") -> str:
        """量不到坐标时必须把"为什么"落到失败条目里，而不是只说"找不到"。
        区分三件事：节点根本不在 DOM 里 / 在但祖先 display:none / 有尺寸但在视口外。
        needle（纯 ASCII 片段）用来把"同一条路由在 DOM 里到底长什么样"一起带回来。
        """
        sel = json.dumps(selector)
        rep = b.js(
            f"(function(){{var e=document.querySelector({sel});"
            f"var near=[];if({json.dumps(needle)}){{near=[].slice.call(document.querySelectorAll('.sidebar li a'))"
            f".filter(function(a){{return (a.getAttribute('href')||'').indexOf({json.dumps(needle)})>-1;}})"
            f".map(function(a){{return a.getAttribute('href');}}).slice(0,3);}}"
            f"if(!e)return JSON.stringify({{missing:true, anchors:"
            f"document.querySelectorAll('.sidebar li a').length, near:near}});"
            f"var n=e,hidden=null;"
            f"while(n&&n!==document.body){{var cs=getComputedStyle(n);"
            f"if(cs.display==='none'||cs.visibility==='hidden'){{hidden=n.tagName+'.'+cs.display;break;}}"
            f"n=n.parentElement;}}"
            f"e.scrollIntoView({{block:'center',behavior:'instant'}});"
            f"var r=e.getBoundingClientRect();"
            f"return JSON.stringify({{missing:false,hidden:hidden,near:near,rect:[Math.round(r.left),Math.round(r.top),"
            f"Math.round(r.width),Math.round(r.height)]}});}})()"
        )
        return json.dumps(rep, ensure_ascii=False)

    def anchor_box(self, b: CDP, selector: str) -> list | None:
        """等元素真的有可点尺寸、且落在**它自己那层滚动框的可见口**里，再返回中心坐标。

        三件事都必须等：Docsify 换页时节点先存在、后布局，量早了拿到 0x0；
        "有尺寸"不等于"看得见"——侧栏里的第 40 条链接有尺寸但在视口外，
        直接点它的坐标就是点空白（实测报成 "中心 (150,-1485) 落在视口外"）。
        滚动一律 behavior:'instant'：theme.css 开了 smooth，动画中的矩形不可信。

        第二层（2026-09-24 补）：**视口内有像素不等于点得到**。getBoundingClientRect
        不受 overflow 裁剪影响，所以一条被 .sidebar（fixed，top=60，overflow-y:auto）
        卷到裁剪边界之上的链接，照样能报出 top=16 这种"在视口内"的矩形；
        而 elementFromPoint(150,31) 接到的是压在上面的 fixed 顶栏（z=200）。
        判据必须按被判定对象自己的分辨率来——可点区的界是**滚动口的界**，不是屏幕的界。
        """
        w, h = b.width, b.height
        sel = json.dumps(selector)
        pred = (
            f"(function(){{var e=document.querySelector({sel});if(!e)return false;"
            f"function clipBox(n){{var bx={{t:0,l:0,r:innerWidth,b:innerHeight}};"
            f"while(n&&n!==document.body){{var c=getComputedStyle(n);"
            f"if(/(auto|scroll|hidden|clip)/.test(c.overflowY)||/(auto|scroll|hidden|clip)/.test(c.overflowX)){{"
            f"var q=n.getBoundingClientRect();"
            f"if(q.width>0&&q.height>0){{bx.t=Math.max(bx.t,q.top);bx.l=Math.max(bx.l,q.left);"
            f"bx.r=Math.min(bx.r,q.right);bx.b=Math.min(bx.b,q.bottom);}}}}n=n.parentElement;}}return bx;}}"
            f"function ok(r){{var cb=clipBox(e);"
            f"return r.width>2&&r.height>2&&r.top>=cb.t-1&&r.bottom<=cb.b+1"
            f"&&r.left>=cb.l-1&&r.right<=cb.r+1&&r.left>=0&&r.top>=0"
            f"&&r.right<={w}&&r.bottom<={h};}}"
            f"var r=e.getBoundingClientRect();"
            f"if(!ok(r)){{e.scrollIntoView({{block:'center',behavior:'instant'}});"
            f"r=e.getBoundingClientRect();}}return ok(r);}})()"
        )
        if not b.wait_for(pred, 12):
            return None
        raw = b.js(
            f"""(function(){{var e=document.querySelector({json.dumps(selector)});
              if(!e)return null;var r=e.getBoundingClientRect();
              return JSON.stringify([r.left+r.width/2,r.top+r.height/2]);}})()"""
        )
        # 判定通过到取坐标之间节点仍可能被换页换掉：这里返回 None 交调用方重钉，
        # 不能 json.loads(None) 抛崩整轮守卫
        return json.loads(raw) if raw else None

    # ---------- 真实点击链 ----------
    def click_chain(self, b: CDP, w: int, h: int) -> None:
        b.js("location.hash = '#/'")
        b.wait_for("document.querySelector('section.cover.show')", 20)
        self.click_target(b, w, h, ".cover a[href='#/manuscript/README']",
                          expect_hash="#/manuscript/README", label="封面·开始阅读")
        # 顶栏在两档都存在且可点。先前这里写着"390 下 .app-nav 被 Docsify 移动端样式
        # 设成 display:none"，本轮查证为误读：theme.css 里那条 display:none 在
        # @media print 内（实测 390 计算样式 display:flex，fixed 60px 横条）。
        # 390 下顶栏是横向滚动的（5 项 428px / 可视 366px），第 5 项「搜索」中心点在视口外，
        # 命中测试按 offscreen 跳过；所以该档点的是第 3 项，中心点始终在屏内。
        if w >= 768:
            self.click_target(b, w, h, ".app-nav a[href='#/guide']",
                              expect_hash="#/guide", label="顶栏·阅读指南")
        else:
            self.click_target(b, w, h, ".sidebar-toggle", label="抽屉开关·展开",
                              read="document.body.className")
            self.click_target(b, w, h, ".sidebar li a[href='#/guide']",
                              expect_hash="#/guide", label="抽屉·阅读指南")
            self.click_target(b, w, h, ".sidebar-toggle", label="抽屉开关·收起",
                              read="document.body.className")
            # 抽屉路径之后停在 #/guide，再真点顶栏才是"点了确实换页"的读数
            self.click_target(b, w, h, ".app-nav a[href='#/manuscript/README']",
                              expect_hash="#/manuscript/README", label="顶栏·全书总览（390）")
        self.click_target(b, w, h, ".pagination-item--next", expect_hash="any", label="翻页·下一章")
        if w < 768:
            self.click_target(b, w, h, ".sidebar-toggle", label="抽屉开关",
                              read="document.body.className")
        # 用"第一条正文链接"而不是 `li:not(.active) > a`：后者在 subMaxLevel 注入
        # ?id= 子链接后会命中当前页的锚点（名义上叫"换章"，点的其实是本页目录），
        # 语义漂移会让失败读数难以解释。
        self.click_target(b, w, h, ".sidebar li > a[href^='#/manuscript/']",
                          expect_hash="any", label="侧边栏·换章")
        if w < 768:
            self.click_target(b, w, h, ".sidebar-toggle", label="抽屉开关·收起",
                              read="document.body.className")
        self.click_target(b, w, h, "#btn-theme", label="主题切换",
                          read="document.documentElement.getAttribute('data-theme')")
        self.click_target(b, w, h, "#btn-theme", label="主题切换·切回浅色",
                          read="document.documentElement.getAttribute('data-theme')")
        b.js("var c=document.querySelector('.content'); c.scrollTop = 3000; c.scrollTop")
        time.sleep(0.4)
        self.click_target(b, w, h, "#btn-back-top", label="返回顶部",
                          read="document.querySelector('.content').scrollTop", expect_zero=True)
        if w >= 1600:
            self.click_target(b, w, h, ".page-toc a", expect_hash="id=", label="本页目录·首条")

    # ---------- 钉住"要点的这一个" ----------
    MARK_ATTR = "data-ainse-click"

    def wait_dom_settled(self, b: CDP, timeout: float = 6.0, quiet: float = 0.35) -> bool:
        """等侧边栏停止重画再动手。

        Docsify 换页后不是一次画完：正文先出现，`subMaxLevel` 的 `?id=` 子链接
        要等标题渲染完再注入，于是侧边栏在几百毫秒内被换掉一整轮。
        本轮实测：打标 + 命中确认都通过之后，这点坐标已被新侧边栏的第一条占去，
        期望 #/guide?id=… 实测 #/manuscript/README。
        判据用签名（侧边栏长度 + 正文长度）连续 quiet 秒不变，不用"等一个固定时长"。
        """
        sig_js = ("(function(){var s=document.querySelector('.sidebar');"
                  "var m=document.querySelector('.markdown-section');"
                  "return (s?s.innerHTML.length:-1)+':'+(m?m.innerText.length:-1);})()")
        deadline = time.time() + timeout
        last, since = None, time.time()
        while time.time() < deadline:
            cur = b.js(sig_js)
            if cur == last and time.time() - since >= quiet:
                return True
            if cur != last:
                last, since = cur, time.time()
            time.sleep(0.12)
        return False

    def mark_target(self, b: CDP, selector: str) -> dict | None:
        """给 selector 命中的第一个元素打标，返回它的 href/文本。

        为什么必须打标：Docsify 每次换页都会重画侧边栏，而
        `.sidebar li:not(.active) > a` 这类**相对**选择器在"等尺寸"的几秒里
        会换人——本轮实测就出现"量到的是 README?id=… 那条，落到点上却是 ch01"。
        打标后所有读数与点击都只认这个节点；节点被重画掉就找不到（返回 None），
        由调用方重新打标，绝不带着旧坐标去点新元素。
        """
        sel = json.dumps(selector)
        attr = self.MARK_ATTR
        raw = b.js(
            f"""(function () {{
              var all = document.querySelectorAll('[{attr}]');
              for (var i = 0; i < all.length; i++) all[i].removeAttribute('{attr}');
              var el = document.querySelector({sel});
              if (!el) return null;
              el.setAttribute('{attr}', '1');
              return JSON.stringify({{href: el.getAttribute('href') || '',
                                      text: (el.innerText || '').trim().slice(0, 24)}});
            }})()"""
        )
        return json.loads(raw) if raw else None

    def marked_ready(self, b: CDP, attr: str | None = None) -> dict | None:
        """点前最后一次确认：标记节点仍在文档里、中心在视口内、
        且该中心的 elementFromPoint 命中它自己或它的后代。

        只确认"节点存在 + 有尺寸"是不够的——本轮实测：翻页后 Docsify 异步重画侧边栏，
        量到的是旧节点（href 还是 #/guide?id=…），点下去落在新侧边栏的第一条上
        （# 变成 #/manuscript/README），报成"期望 A 实测 B"的假缺陷。
        命中确认与坐标读必须在同一次 JS 里，否则又是一次跨调用的漂移。
        """
        attr = attr or self.MARK_ATTR
        raw = b.js(
            f"""(function () {{
              // clip：JS 的 slice 按 UTF-16 码元切，切在 emoji 的代理对中间就送回一个
              // 孤立代理位。2026-09-24 实测的现场：挡路元素是顶栏，它的 innerText 是
              // 「主页\\n📖 阅读指南\\n📚 全书总览\\n🗺 四案例时间线\\n🔎 搜索」（34 个码元），
              // 而这里切 20 个，末位正好是 🔎 的前半 0xd83d ——守卫在打印自己那条唯一
              // 真失败时崩了（UnicodeEncodeError），退出码 1 的理由还是错的。
              // 判据交不出去等于这一轮白跑，所以两端都要成对地切。
              function clip(s, k) {{
                s = (s == null ? '' : String(s)).trim().slice(0, k);
                var c = s.charCodeAt(s.length - 1);
                if (c >= 0xD800 && c <= 0xDBFF) s = s.slice(0, -1) + '…';
                return s;
              }}
              var el = document.querySelector('[{attr}]');
              if (!el) return JSON.stringify({{ready: false, why: '节点已被侧边栏重画掉'}});
              if (!document.contains(el)) return JSON.stringify({{ready: false, why: '节点已脱离文档'}});
              var r = el.getBoundingClientRect();
              var x = r.left + r.width / 2, y = r.top + r.height / 2;
              if (!(r.width > 2 && r.height > 2)) {{
                return JSON.stringify({{ready: false, why: '尺寸 ' + r.width + 'x' + r.height}});
              }}
              if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) {{
                return JSON.stringify({{ready: false, why: '中心 (' + x + ',' + y + ') 出视口'}});
              }}
              var top = document.elementFromPoint(x, y);
              if (!top) return JSON.stringify({{ready: false, why: 'elementFromPoint 为空'}});
              // 只认"它自己或它的后代"接到这一点：命中祖先不算，
              // 因为事件的捕获路径止于命中节点，目标 <a> 上的处理器根本不会触发
              // （pointer-events:none 遮在链接上正是这种情形，必须报出来）。
              if (!(top === el || el.contains(top))) {{
                var tr = top.getBoundingClientRect();
                var tcs = getComputedStyle(top);
                // 现场带上祖先链：一个 fixed 侧栏里的链接量到 y<顶栏高度，只有两种可能
                // ——祖先的 position/transform 改变了包含块，或者这一刻根本不是那套布局。
                // 不记这条链，下一轮还是要靠猜。（2026-09-24 的 ch10 就是这个状态）
                var anc = [], an = el;
                for (var k = 0; an && k < 5; k++) {{
                  var ar = an.getBoundingClientRect(), ac = getComputedStyle(an);
                  anc.push(an.tagName.toLowerCase() + (an.className && typeof an.className === 'string'
                    ? '.' + an.className.trim().split(/\\s+/)[0] : '')
                    + '@' + ac.position + '[' + [ar.left, ar.top, ar.width, ar.height].map(Math.round).join(',') + ']'
                    + (ac.transform === 'none' ? '' : ' tf=' + ac.transform.slice(0, 24)));
                  an = an.parentElement;
                }}
                return JSON.stringify({{ready: false, blocked: true, x: x, y: y,
                  href: el.getAttribute('href') || '', text: clip(el.innerText, 24),
                  targetRect: [r.left, r.top, r.width, r.height].map(Math.round),
                  blockerRect: [tr.left, tr.top, tr.width, tr.height].map(Math.round),
                  blockerBox: tcs.position + ' z=' + tcs.zIndex,
                  ancestors: anc,
                  view: [innerWidth, innerHeight, Math.round(scrollY)],
                  why: '该点被「' + clip(top.innerText || top.tagName, 20) + '」(' + top.tagName.toLowerCase()
                  + (top.className && typeof top.className === 'string'
                  ? '.' + top.className.split(' ')[0] : '') + ') 挡在前面'}});
              }}
              return JSON.stringify({{ready: true, x: x, y: y, href: el.getAttribute('href') || '',
                                      text: clip(el.innerText, 24)}});
            }})()"""
        )
        return json.loads(raw) if raw else None

    def click_target(self, b: CDP, w: int, h: int, selector: str, *, expect_hash: str | None = None,
                     label: str, read: str | None = None, expect: str | None = None,
                     expect_zero: bool = False) -> None:
        g = None
        blocked = None
        blocked_key = None
        last_why = ""
        for _ in range(6):
            self.wait_dom_settled(b)
            if self.mark_target(b, selector) is None:
                last_why = "选择器当前无命中元素"
                time.sleep(0.35)
                continue
            if self.anchor_box(b, f"[{self.MARK_ATTR}]") is None:
                # 标记节点在等待尺寸的途中被换页换掉：不是站点缺陷，重钉一轮
                last_why = "打标后在等可点尺寸期间被 Docsify 重画掉"
                time.sleep(0.35)
                continue
            g = self.marked_ready(b) or {}
            if g.get("ready"):
                break
            last_why = g.get("why", "无读数")
            if g.get("blocked"):
                key = f"{g.get('x')},{g.get('y')},{g.get('why')}"
                blocked = g
                g = None
                # 重钉只为对付 Docsify 的换页漂移。同一坐标 + 同一遮挡者连读两次
                # ⇒ 漂移假设已被否证，是稳定遮挡：再钉四轮只是把一条真缺陷拖成几分钟，
                # 整轮变异自检会因为超时跑不完（实测 M2 单条 >20 分钟）。
                if key == blocked_key:
                    break
                blocked_key = key
            else:
                g = None
            time.sleep(0.35)  # 上一轮量完又被重画：重新钉、重新确认
        if g is not None:
            x, y, href, text = g["x"], g["y"], g["href"], g["text"]
            note = ""
        elif blocked is not None:
            # 命中测试判它点不到，但只用命中测试下结论就是"以读数冒充交互"——
            # 仍按读者视角真点一次，把两种证据并成一条失败项。
            x, y, href, text = blocked["x"], blocked["y"], blocked["href"], blocked["text"]
            note = f"（命中测试：{blocked['why']}）"
        else:
            self.fail(f"[{w}x{h}] 点击链：{label}（选择器 {selector}）连续 6 轮打标后仍不稳定——"
                      f"最后一轮原因：{last_why}；现场 {self.box_diagnosis(b, selector)}")
            return
        before_hash = b.js("location.hash")
        before = b.js(read) if read else None
        b.click(x, y)
        self.counters["clicks"] += 1
        changed = False
        if expect_hash is not None:
            if expect_hash == "id=":
                ok = b.wait_for("location.hash.indexOf('id=') > -1", 10)
                detail = f"路由仍是 {b.js('location.hash')}"
            elif expect_hash == "any" and not href.startswith("#/"):
                ok = b.wait_for(f"location.hash !== {json.dumps(before_hash)}", 10)
                detail = f"路由没变（仍是 {before_hash}）"
            else:
                target = href if expect_hash == "any" else expect_hash
                ok = b.wait_for(self.hash_eq_js(target), 10)
                detail = f"期望 {target}，实测 {b.js('location.hash')}"
            changed = ok
            if not ok:
                self.fail(
                    f"[{w}x{h}] 点击链：真实点击 {label}「{text}」于 ({x:.0f},{y:.0f}) 后{detail}{note}"
                )
                return
            # 哈希变了不等于页面换好了：Docsify 摘掉 cover.show、重排正文都在其后，
            # 立刻量下一个控件会拿到 0x0 的矩形（本轮实测踩过）。
            b.wait_for(
                "document.querySelector('.markdown-section') "
                "&& document.querySelector('.markdown-section').innerText.trim().length > 50 "
                "&& !document.querySelector('section.cover.show')",
                20,
            )
        if read:
            if expect_zero:
                zero = b.wait_for(f"({read}) < 50", 6)
                changed = changed or zero
                if not zero:
                    self.fail(f"[{w}x{h}] 点击链：真实点击 {label} 后未回到顶部（{read} = {b.js(read)}）{note}")
                elif note:
                    self.fail(f"[{w}x{h}] 点击链：{label}{note}，但真点后 {read} 回到顶部——"
                              f"命中测试与真实点击结论冲突，需复核探针")
                return
            time.sleep(0.6)
            after = b.js(read)
            changed = changed or (after != before)
            if after == before:
                self.fail(f"[{w}x{h}] 点击链：真实点击 {label} 后状态没变（{read} 仍是 {before!r}）{note}")
            elif note:
                self.fail(f"[{w}x{h}] 点击链：{label}{note}，但真点后 {read} = {after!r} 确实变了——"
                          f"命中测试与真实点击结论冲突，需复核探针")
            elif expect is not None and expect not in str(after):
                self.fail(f"[{w}x{h}] 点击链：{label} 点击后 {read} = {after!r}，不含 {expect!r}")
            return
        if note and not changed and expect_hash is None:
            self.fail(f"[{w}x{h}] 点击链：{label}{note}，真点后无可断言状态变化，判定为点不动")

    @staticmethod
    def hash_eq_js(href: str) -> str:
        """比较哈希必须两侧同口径：
        - 侧边栏的文件型 href 是原文（含中文），而 location.hash 是浏览器编码后的 %E4%B8%AD…；
        - 但 Docsify 给锚点（?id=）写进 href 的本身就是百分号编码，方向正好相反。
        所以两边都 decode 再比：decodeURIComponent 对无 % 的串是恒等，对畸形串抛错就退回原串。
        （实测锚点点击会因这个口径报成"期望 X，实测 X"这种自相矛盾的失败。）
        """
        return (
            "(function(){function d(s){try{return decodeURIComponent(s);}catch(e){return s;}}"
            f"return d(location.hash) === d({json.dumps(href)});}})()"
        )

    def walk_routes_by_click(self) -> None:
        """用真实点击走完全部内容路由：逐条点侧边栏，验证每条都真的换页且不卡死。

        封面路由（#/）刻意不在遍历清单里：点它会打开封面、让侧边栏按设计退出布局，
        之后每一条都只能在 (0,0) 上空点——实测这会把 1 个前置问题放大成 61 条假失败。
        封面的可达与可点由 sweep 的 is_cover 分支 + click_chain 的「封面·开始阅读」覆盖。
        """
        # 归一化后再判定：js_route_list 交回来的是去掉前导 # 的路径（"/"、"guide"…），
        # 所以 COVER 的判据只能是"剥掉 # 和 / 之后为空"，不能靠字面量清单。
        routes = [r for r in self.routes if r.lstrip("#/").strip() != ""]
        if not routes:
            self.fail("点击遍历：内容路由枚举为空——口径失效，本项无法给出结论")
            return
        with CDP(1280, 900) as b:
            b.navigate(f"{self.base}/#/")
            if not b.wait_for("document.querySelector('section.cover.show')", 30):
                self.fail("点击遍历：封面没出现，走查无法开始")
                return
            self.click_target(b, 1280, 900, ".cover a[href='#/manuscript/README']",
                              expect_hash="#/manuscript/README", label="走查起点·封面开始阅读")
            if b.js("!!document.querySelector('section.cover.show')") or b.js("location.hash") == "#/":
                self.fail("点击遍历：真实点击后仍没能离开封面，后续点击无意义——中止，"
                          "不把 1 个前置问题放大成逐路由假失败")
                return
            for route in routes:
                href = route if route.startswith("#") else "#" + route
                needle = "".join(c for c in route if ord(c) < 128)[:24]
                self.wait_dom_settled(b)  # 侧边栏还在重画时打标，点下去的是别的链接
                marked = json.loads(b.js(WALK_MARK_JS % (json.dumps(href), json.dumps(needle))))
                if not marked["count"]:
                    self.fail(f"点击遍历：侧边栏里没有指向 {href} 的链接（枚举口径与点击口径不一致）"
                              f"—— 现场同类 href：{marked['near']}")
                    continue
                anchor = ".sidebar li a[data-ainse-walk]"
                box = self.anchor_box(b, anchor)
                if box is None:
                    self.fail(f"点击遍历：{href} 的侧边栏入口量不到可点坐标 —— "
                              f"{self.box_diagnosis(b, anchor, needle)}")
                    continue
                ready = self.marked_ready(b, "data-ainse-walk") or {}
                if not ready.get("ready"):
                    # 现场全带上：anchor_box 与 marked_ready 是两次 JS 往返，
                    # 只看一句「被挡在前面」分不出真遮挡与换页期间的坐标漂移。
                    self.fail(f"点击遍历：{href} 的入口虽在布局里，但这一点被别的东西吃掉——"
                              f"不点（避免把点到邻居当成到站）：{ready.get('why', '无读数')}｜"
                              f"取标={box and [round(box[0]), round(box[1])]} 复核点=({ready.get('x')},{ready.get('y')}) "
                              f"目标矩形={ready.get('targetRect')} 挡路矩形={ready.get('blockerRect')} "
                              f"挡路定位={ready.get('blockerBox')} 视口/滚动={ready.get('view')} "
                              f"祖先链={ready.get('ancestors')}")
                    continue
                if b.js("!!document.querySelector('section.cover.show')"):
                    self.fail(f"点击遍历：走到 {href} 时封面又盖住页面，中止以避免连锁假失败")
                    return
                before = b.js("location.hash")
                b.click(box[0], box[1])
                self.counters["clicks"] += 1
                if not b.wait_for(self.hash_eq_js(href), 10):
                    who = b.js(
                        "(function(){var e=document.querySelector('.sidebar li a[data-ainse-walk]');"
                        "if(!e)return JSON.stringify({gone:true});"
                        "var r=e.getBoundingClientRect();"
                        "var t=document.elementFromPoint(Math.round(r.left+r.width/2),Math.round(r.top+r.height/2));"
                        "return JSON.stringify({inDom:document.contains(e),rect:[Math.round(r.left),Math.round(r.top),"
                        "Math.round(r.width),Math.round(r.height)],href:(e.getAttribute('href')||'').slice(0,60),"
                        "receiver:t?t.tagName+'.'+(t.className||''):'null'});})()"
                    )
                    self.fail(f"点击遍历：真实点击 {href} 没到站（点击前 {before}，10s 后 "
                              f"{b.js('location.hash')}）—— 现场 {who}")
                    continue
                if not b.wait_for(
                    "document.querySelector('.markdown-section') "
                    "&& document.querySelector('.markdown-section').innerText.trim().length > 50",
                    20,
                ):
                    self.fail(f"点击遍历：{href} 点击后正文 20s 未渲染（卡死）")
                # 事件按所在路由逐页收：等到最后统一 drain 只会得到一条没有出处的
                # "Uncaught (in promise) @ mermaid.min.js"，落不到章上。
                self.collect_console(b, href)
                if self.counters["clicks"] % 20 == 0:
                    print(f"  · 点击遍历：已走 {self.counters['clicks']} 次，累计失败 {len(self.failures)}",
                          flush=True)
            self.check_console_errors(b)

    def collect_console(self, b: CDP, context: str) -> None:
        """把 CDP 抛出的异常/console.error 按"当时所在的路由"入账。

        等页面渲染完再多留 0.8s：mermaid 是异步排版，异常往往在正文出现之后才落地。
        """
        time.sleep(0.8)
        for ev in b.drain_events({"Runtime.exceptionThrown", "Log.entryAdded", "Runtime.consoleAPICalled"}):
            m = ev["method"]
            p = ev.get("params", {})
            msg = None
            if m == "Runtime.exceptionThrown":
                d = p.get("exceptionDetails", {})
                # 只抄 text 会得到 "Uncaught (in promise)" 这种没法定位的行，
                # 必须把异常自身的 description 和出处一起落进失败条目。
                exc = d.get("exception") or {}
                where = f"{d.get('url') or ''}:{d.get('lineNumber')}:{d.get('columnNumber')}"
                detail = safe_text(exc.get("description") or exc.get("value") or d.get("text") or "", 400)
                msg = f"未捕获异常：{safe_text(d.get('text'))} @ {where} —— {detail.strip()}"
            elif m == "Log.entryAdded":
                e = p.get("entry", {})
                if e.get("level") == "error":
                    msg = f"控制台 error：{safe_text(e.get('text', ''), 180)}"
            elif m == "Runtime.consoleAPICalled" and p.get("type") in ("error", "assert"):
                args = ",".join(safe_text(a.get("value", a.get("description", "")), 80) for a in p.get("args", []))
                msg = f"console.error：{safe_text(args, 180)}"
            if msg:
                self.console.append(f"[{context}] {msg}")

    def report_console(self) -> None:
        for line in sorted(set(self.console)):
            self.fail(f"控制台错误：{line}")

    def check_console_errors(self, b: CDP) -> None:
        self.collect_console(b, b.js("location.hash"))
        self.report_console()


def run(base: str, *, limit: int | None, widths, walk: bool, chain: bool = True) -> list[str]:
    routes = js_route_list(base)
    if not routes:
        return ["侧边栏一条路由都没有——枚举口径失效，本守卫无法给出任何结论"]
    suite = Suite(base, routes, widths, limit, chain)
    suite.sweep()
    if walk:
        suite.walk_routes_by_click()
    suite.counters["total_routes"] = len(routes)
    print(
        "  实测：路由 {} 条（枚举自侧边栏）× 视口 {}；命中点 {} 个、控件 {} 个、真实点击 {} 次".format(
            len(routes),
            " / ".join(f"{w}x{h}" for w, h in widths),
            suite.counters["hitpoints"],
            suite.counters["controls"],
            suite.counters["clicks"],
        )
    )
    return suite.failures


# 每条变异额外做一次"子进程退出码复核"：报红≠闸会拦。
# 只用 --limit/--no-chain 的那一档跑，几秒就够（点击链已被本轮的早退优化排除）。
RC_PROBE_ARGS = ["--limit", "4", "--no-chain", "--no-walk", "--widths", "1280"]


# ---------------------------------------------------------------- 变异自检
MUTATIONS = [
    (
        "M1 复活封面遮罩（Docsify 只摘 show 类、节点留在 DOM）",
        lambda files: files["theme.css"].__setitem__(
            "__tail__", "\nsection.cover:not(.show){display:flex !important;}\n"
        ),
        ("被封面接走", "section.cover"),
    ),
    (
        "M2 注入全屏透明遮罩层",
        lambda files: files["index.html"].__setitem__(
            "</body>",
            '<div id="hijack" style="position:fixed;inset:0;z-index:9999;"></div></body>',
        ),
        ("div#hijack",),
    ),
    (
        "M3 让主题按钮吃掉点击（pointer-events:none）",
        lambda files: files["theme.css"].__setitem__(
            "__tail__", "\n#btn-theme{pointer-events:none;}\n"
        ),
        ("真实点击 主题切换", "0 个通过命中测试"),
    ),
    (
        "M4 让侧边栏链接点不动（点击后路由不变）",
        lambda files: files["theme.css"].__setitem__(
            "__tail__", "\n.sidebar li a{pointer-events:none;}\n"
        ),
        ("这一点被别的东西吃掉", "没到站", "0 个通过命中测试"),
    ),
    (
        "M5 让滚动暗示层吃掉点击（pointer-events:auto）",
        lambda files: files["theme.css"].__setitem__(
            "__tail__", "\n.scroll-veil{pointer-events:auto;}\n"
        ),
        ("侧暗示层在", "侧暗示层 pointer-events", "暗示层吃掉了读者的点击"),
    ),
]


def mutate(name: str, text: str, files: dict) -> str:
    """把 files 里的补丁写回文本：index.html 用替换，theme.css 用追加。"""
    if name == "index.html":
        for old, new in files["index.html"].items():
            text = text.replace(old, new)
        return text
    return text + files["theme.css"].get("__tail__", "")


def run_mutations(widths, only: str | None = None) -> int:
    src = {"theme.css": (DOCS / "theme.css").read_text(), "index.html": (DOCS / "index.html").read_text()}
    bad = 0
    # 每条变异的耗时单独落盘：整轮跑 40 分钟时，"没跑完"和"跑完但没捕获"
    # 在日志里长得一样（都是缺一条结论）。有了耗时才能点名是哪一条慢。
    for label, apply, needles in MUTATIONS:
        if only and not label.upper().startswith(only.upper()):
            continue
        files = {"theme.css": {}, "index.html": {}}
        apply(files)
        tmp = Path(tempfile.mkdtemp(prefix="ainse-mut-"))
        t0 = time.monotonic()
        try:
            for f in DOCS.rglob("*"):
                rel = f.relative_to(DOCS)
                if f.is_dir():
                    (tmp / rel).mkdir(parents=True, exist_ok=True)
                else:
                    dst = tmp / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if str(rel) in src:
                        dst.write_text(mutate(str(rel), src[str(rel)], files))
                    else:
                        shutil.copy2(f, dst)
            base, shutdown = serve(tmp)
            try:
                failures = run(base, limit=4, widths=widths, walk=True)
                # 报红 ≠ 会拦住：判定到退出码之间还有一层映射，没验证过的映射
                # 在 CI 里等于没有闸。用同一条被改坏的站点起一个子进程，要它 rc=1。
                probe = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--base", base] + RC_PROBE_ARGS,
                    capture_output=True, text=True, timeout=900)
                rc = probe.returncode
            finally:
                shutdown()
            # needle 是"该变异的机制名"：只认点名机制的片段，
            # 泛词（如"被""点击遍历"）会被任何一条无关失败满足 ⇒ 假绿。
            hits = {n: [f for f in failures if n in f] for n in needles}
            caught = [n for n, fs in hits.items() if fs]
            dt = time.monotonic() - t0
            if failures and caught and rc != 1:
                bad += 1
                print(f"  [变异 {label}] 耗时 {dt:.0f}s -> 报了 {len(failures)} 条失败、"
                      f"命中机制判据「{caught[0]}」，但子进程退出码 = {rc} 而非 1——"
                      f"这条缺陷拦不住下一次改动", flush=True)
            elif failures and caught:
                n = caught[0]
                print(f"  [变异 {label}] 耗时 {dt:.0f}s -> 报红 {len(failures)} 条，"
                      f"命中机制判据「{n}」{len(hits[n])} 条，子进程退出码复核 rc={rc}，"
                      f"示例：{safe_text(hits[n][0], 150)}", flush=True)
            elif failures:
                bad += 1
                print(f"  [变异 {label}] 耗时 {dt:.0f}s -> 只报了无关失败（示例 {safe_text(failures[0], 150)}），"
                      f"未命中机制判据 {list(needles)}——该变异未被本守卫按机制捕获", flush=True)
            else:
                bad += 1
                print(f"  [变异 {label}] 耗时 {dt:.0f}s -> 全绿！守卫失明，需要修判据", flush=True)
        except BaseException as e:
            # 单条变异崩溃不能带走整轮：否则日志里只剩上一行的尾巴，
            # 看上去像"跑太久被砍"，实际是探针自己抛错。
            bad += 1
            print(f"  [变异 {label}] 耗时 {time.monotonic() - t0:.0f}s -> "
                  f"执行崩溃：{type(e).__name__}: {str(e)[:200]}", flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return bad


WIDTH_HEIGHTS = {1280: 900, 1440: 900, 1600: 990, 390: 844}


def parse_widths(spec: str) -> list[tuple[int, int]]:
    """--widths 1280,390 → [(1280,900),(390,844)]；高度按档查表，查不到用 900。"""
    out = []
    for raw in spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        w, _, h = raw.partition("x")
        out.append((int(w), int(h) if h else WIDTH_HEIGHTS.get(int(w), 900)))
    if not out:
        raise SystemExit("--widths 解析为空——空覆盖集会伪装成「跑过了」")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, help="只跑前 N 条路由（冒烟用）")
    ap.add_argument("--mutate", nargs="?", const="all", default=None, metavar="前缀",
                    help="变异自检：证明本守卫会报红（退出码 1）；可只跑某一条，如 --mutate M3")
    ap.add_argument("--base", help="对已运行的站点做检查（默认自带临时服务器）")
    ap.add_argument("--no-walk", action="store_true", help="跳过 62 条路由的真实点击遍历")
    ap.add_argument("--no-chain", action="store_true", help="跳过真实点击链（只做命中测试）")
    ap.add_argument("--widths", default="1280,390",
                    help="逗号分隔的视口档，如 1280 或 1280,1440,390x844")
    args = ap.parse_args()

    widths = parse_widths(args.widths)
    if args.mutate:
        only = None if args.mutate == "all" else args.mutate
        picked = [lab for lab, _, _ in MUTATIONS
                  if only is None or lab.upper().startswith(only.upper())]
        if not picked:
            # 前缀打错会"0 条变异、结论：全部变异被捕获、退出码 0"——假绿。
            print(f"变异前缀「{only}」没有命中任何一条变异。已有：" +
                  "、".join(m[0].split()[0] for m in MUTATIONS))
            return 1
        print(f"变异自检（{len(picked)} 条，每条都必须让守卫报红，且子进程退出码 = 1）：")
        bad = run_mutations([(1280, 900)], only)
        print(f"结论（{len(picked)} 条已跑）："
              + ("每条被跑到的变异都被按机制捕获、退出码复核为 1。"
                 if bad == 0 else f"{bad} 条变异未被捕获/未跑完/退出码不是 1。"))
        return 0 if bad == 0 else 1

    if args.base:
        failures = run(args.base.rstrip("/"), limit=args.limit, widths=widths,
                       walk=not args.no_walk, chain=not args.no_chain)
    else:
        base, shutdown = serve(DOCS)
        try:
            failures = run(base, limit=args.limit, widths=widths,
                           walk=not args.no_walk, chain=not args.no_chain)
        finally:
            shutdown()

    if failures:
        print(f"\n交互闸失败 {len(failures)} 条：")
        for f in failures[:60]:
            print("  ✗ " + safe_text(f))
        if len(failures) > 60:
            print(f"  …另有 {len(failures) - 60} 条")
        return 1
    # 报"0 处点不动"之前先交代本轮跑了哪些阶段：
    # 带 --no-chain 冒烟时的"全绿"不许长得像全量全绿。
    skipped = [n for n, on in (("真实点击链", not args.no_chain),
                              ("逐路由点击遍历", not args.no_walk),
                              ("全部路由（本轮只跑 --limit 指定的前几条）", not args.limit)) if not on]
    scope = "（全量）" if not skipped else "（部分：" + "、".join(skipped) + " 已跳过，不构成全量结论）"
    print(f"\n交互闸通过{scope}：0 处遮挡、0 处点不动、0 次点击后状态不变、0 条控制台错误。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
