#!/usr/bin/env python3
"""第九条守卫·渲染泄漏闸：源码里写了 markdown 语法，页面上必须真的变成样式。

为什么立这条（2026-09-24 验收时实测到）：`ch26-第21章` 第 24 行写着
`**"那天晚上，对账系统和监控系统同时失明。"**`，DOM 里 `hasStrong=false`、
可见文本原样带着两颗星号。前八条量的是"图在不在、点不点得动、看得清不清"，
没有一条量"语法有没有真的落地"；第三条 `check_markdown.py` 只看源码结构
（围栏成对、HTML 块不吞语法），它对着同一份源码也是全绿的。
**源码合法 ≠ 渲染成功**，这一格必须由浏览器补上。

失效机理（从 `docs/vendor/docsify.min.js` 里内嵌的 marked 15.0.12 读出正则，
再用 39 条写法在浏览器里逐条实测校准，静态预测 33/33 命中）：
`_punctuation` 只列 ASCII 符号，所以**中文标点、全角引号、破折号对 marked 来说是"字"**；
`strong.start` 要求 `**` 后面不能是空白，`strong.endAst` 要求 `**` 前面是标点时后面必须也是标点或空白。
由此得到四种"写了不落地"的形状（本轮全站实测到 127 处，全部由这四种形状产生）：
  R1 开侧：`：**"……"**`——前一个字符不是空白/ASCII 标点，后一个又是 ASCII 引号 → 开不出来
  R2 段内落单的 `**`——配对被吃掉一整个，剩下的那颗起不了头也收不了尾
  R3 `。**坑在这里**`——四个 `*` 连成一串，两对的闭合判定同时失败
  R4 `**` 后面紧跟空白（`在** JS 侧**`）——start 的 `(?![\\s])` 直接拒绝
对应的写法纪律已写进 `docs/STYLE_GUIDE.md`「加粗与引号」一节。

口径：
  · 只扫渲染后的可见文本节点，且跳过 <code>/<pre>/<kbd>/<samp>——代码块里的 `**` 是内容不是泄漏。
  · 泄漏形状：`**` `__` `~~` 反引号、`](` 与 `[文字](` （链接没解析）、`<tag>` 字面标签、
    以及 `\n` `\t` 这类被写死的转义。
  · 覆盖集自证：逐页必须走到 >0 个文本节点；路由用两条口径（DOM 侧边栏 / _sidebar.md）互证。
  · 对照：`--selftest` 把上面四种形状各造一条反例（必报）+ 五条修好的正例（必不报），
    一次装进同一页的临时副本，按"最近标题"归因到每一条——
    反例被报说明判据没瞎，正例不被报说明它没把正常加粗也吃掉；两者同页互证。
    对不上就是"什么都能报红"或"什么都不报"，两种松判据都当场抓住。

用法：
    python3 scripts/check_render_leaks.py            # 全量
    python3 scripts/check_render_leaks.py --selftest # 九条对照，一次装一页
    python3 scripts/check_render_leaks.py --report   # 逐页输出走了多少节点、命中多少条
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import socket
import socketserver
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "scripts"))

from cdp import CDP, free_port, safe_text  # noqa: E402
from check_legibility import routes_two_ways, dismiss_cover  # noqa: E402

VIEWPORT = (1280, 900)

# 渲染后仍留在可见文本里的"没吃掉的语法"。
LEAK_RES: list[tuple[str, re.Pattern[str]]] = [
    ("加粗/斜体星号", re.compile(r"\*\*")),
    ("下划线强调", re.compile(r"__\S")),
    ("删除线", re.compile(r"~~\S")),
    ("行内代码反引号", re.compile(r"`")),
    ("链接没解析", re.compile(r"\]\s*\(")),
    ("字面 HTML 标签", re.compile(r"</?[a-zA-Z][a-zA-Z0-9-]*(\s[^<>]{0,80})?>")),
    ("写死的转义符", re.compile(r"\\[ntr]")),
]

PROBE_JS = r"""
(function () {
  var SKIP = 'code, pre, kbd, samp, .mermaid-block, script, style';
  var mdRoot = document.querySelector('.markdown-section');
  var out = {hash: location.hash, walked: 0, hits: [], rootFound: !!mdRoot};
  if (!mdRoot) return JSON.stringify(out);
  var walker = document.createTreeWalker(mdRoot, NodeFilter.SHOW_TEXT, null);
  var n, src = [];
  while ((n = walker.nextNode())) {
    var t = (n.nodeValue || '');
    if (!t.trim()) continue;
    var p = n.parentElement;
    if (!p || p.closest(SKIP)) continue;
    var r = p.getBoundingClientRect();
    if (!r.width || !r.height) continue;          // 没被画出来的不参与（折叠区/模板）
    out.walked++;
    src.push({t: t, tag: p.tagName.toLowerCase(),
              cls: (typeof p.className === 'string' ? p.className.split(' ')[0] : ''),
              head: (function (e) {                    // 最近的标题，给报告用
                var h = e;
                while (h && h !== mdRoot) {
                  var sib = h.previousElementSibling;
                  while (sib) {
                    if (/^H[1-6]$/.test(sib.tagName)) return (sib.innerText || '').trim().slice(0, 24);
                    sib = sib.previousElementSibling;
                  }
                  h = h.parentElement;
                }
                return '';
              })(p)});
  }
  // 结构性反证：源码写了 ** 却一个 <strong> 都没渲染出来，说明整段强调语法没落地
  out.strongs = mdRoot.querySelectorAll('strong').length;
  out.ems = mdRoot.querySelectorAll('em').length;
  out.codes = mdRoot.querySelectorAll('code').length;
  out.src = src;
  return JSON.stringify(out);
})()
"""


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


def classify(text: str) -> list[str]:
    return [name for name, rx in LEAK_RES if rx.search(text)]


def audit(base: str, report: bool = False) -> tuple[list[str], dict]:
    fails: list[str] = []
    stats = {"pages": 0, "walked": 0, "hits": 0, "strongs": 0}
    with CDP(*VIEWPORT) as b:
        routes = routes_two_ways(b, base)
        for path in routes:
            b.navigate(f"{base}/#/{quote(path)}")
            # 首页的正文压在封面下：不揭幕就只能读到封面的字，那一读"0 个文本节点"的
            # 空覆盖判据就会报红（本闸 2026-09-25 就是被第七条的枚举改动推着撞上这条的）。
            why = dismiss_cover(b, path)
            if why:
                fails.append(f"[{path or '首页'}] {why}")
                continue
            if not b.wait_for("document.querySelector('.markdown-section')", 25):
                fails.append(f"[{path or '首页'}] .markdown-section 没出现——这一页没有对象可判，读数作废")
                continue
            b.wait_for("true", timeout=1.2)      # 给 mermaid / 锚点脚本留出落位时间
            d = json.loads(safe_text(b.js(PROBE_JS)))
            if not d.get("rootFound"):
                fails.append(f"[{path}] 探针找不到正文根节点")
                continue
            if d["walked"] == 0:
                fails.append(f"[{path}] 走到 0 个可见文本节点——覆盖集为空，不算通过")
                continue
            stats["pages"] += 1
            stats["walked"] += d["walked"]
            stats["strongs"] += d["strongs"]
            for node in d["src"]:
                kinds = classify(node["t"])
                if not kinds:
                    continue
                stats["hits"] += 1
                snippet = node["t"].strip().replace("\n", " ")[:70]
                fails.append(f"[{path or '首页'}] {'、'.join(kinds)} 泄漏："
                             f"<{node['tag']} class={node['cls']}>「{snippet}」"
                             f"（最近标题：{node['head'] or '—'}）")
            if report:
                print(f"  {path or '首页':<46} 节点 {d['walked']:>5}  "
                      f"strong {d['strongs']:>3}  em {d['ems']:>3}  code {d['codes']:>3}")
    return fails, stats


# ============================== 正/反对照 ==============================

# 每一条都是全站真实踩到过的写法（去掉具体数字与专有名词，避免对照集和正文互相引用）。
# want_leak=True 的必须在页面上留字面星号，False 的必须被 marked 正常吃掉。
FIXTURES: list[tuple[str, str, bool, str]] = [
    ("R1", '运维复盘时把这句话贴在了墙上：**"那天晚上，两个系统同时失明。"**', True,
     "R1 加粗以 ASCII 引号开头（ch26 那一行的原形状）"),
    ("G1", '运维复盘时把这句话贴在了墙上："**那天晚上，两个系统同时失明。**"', False,
     "G1 把引号挪到加粗之外"),
    ("G0", '运维复盘时把这句话贴在了墙上：**「那天晚上，两个系统同时失明。」**', False,
     "G0 全角引号留在加粗内侧——中文标点对 marked 是「字」"),
    ("R2", '源头域的负责人说："这个包是从我们域抽出来的，我们不想当第一批验证者。**', True,
     "R2 段内落单的一个 `**`（ch19:125 原形状）"),
    ("G2", '源头域的负责人说："这个包是从我们域抽出来的，我们不想当第一批验证者。"', False,
     "G2 那颗落单的星号本该是收引号"),
    ("R3", '工具卡的判据是：**要么把码表钉在 runbook 上复跑，要么把判据落在摘要行上。****坑在这里**：默认扫出问题仍然退出零', True,
     "R3 四个星号连成一串（ch27:225 原形状）"),
    ("G3", '工具卡的判据是：**要么把码表钉在 runbook 上复跑，要么把判据落在摘要行上。** **坑在这里**：默认扫出问题仍然退出零', False,
     "G3 两个加粗之间留一个空格"),
    ("R4", '崩溃点其实在** JS 侧**——顶栏文本正好切在代理对的中间', True,
     "R4 `**` 后面紧跟空白（DIAGNOSIS:111 原形状）"),
    ("G4", '崩溃点其实在 **JS 侧**——顶栏文本正好切在代理对的中间', False,
     "G4 空白挪到星号外侧"),
]

TAG_RE = re.compile(r"对照 ([RG]\d)")


def selftest() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ainse-leak-"))
    try:
        for f in sorted(DOCS.rglob("*")):
            rel = f.relative_to(DOCS)
            if f.is_dir():
                (tmp / rel).mkdir(parents=True, exist_ok=True)
            else:
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                (tmp / rel).write_bytes(f.read_bytes())
        page = tmp / "manuscript" / "ch06-第1章-AI原生不是让AI写代码.md"
        block = "\n\n---\n\n## 自检对照小节 Z\n\n" + "\n\n".join(
            f"### 对照 {tag}（{'反' if want else '正'}）\n\n{line}\n"
            for tag, line, want, _ in FIXTURES)
        page.write_text(page.read_text(encoding="utf-8") + block, encoding="utf-8")
        base, shutdown = serve(tmp)
        try:
            with CDP(*VIEWPORT) as b:
                b.navigate(f"{base}/#/")
                b.wait_for("document.querySelectorAll('.sidebar li a').length > 3", 30)
                b.navigate(f"{base}/#/{quote('manuscript/ch06-第1章-AI原生不是让AI写代码')}")
                b.wait_for("document.querySelector('.markdown-section')", 25)
                b.wait_for("true", timeout=1.5)
                d = json.loads(safe_text(b.js(PROBE_JS)))
        finally:
            shutdown()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    if d["walked"] == 0:
        print("  [✗] 对照页走到 0 个文本节点——覆盖集为空，九条对照全部作废")
        return 1
    hits: dict[str, list[str]] = {}
    for n in d["src"]:
        m = TAG_RE.search(n.get("head") or "")
        if m and classify(n["t"]):
            hits.setdefault(m.group(1), []).append(n["t"].strip().replace("\n", " ")[:60])

    rc = 0
    for tag, line, want, why in FIXTURES:
        got = bool(hits.get(tag))
        ok = got == want
        rc |= 0 if ok else 1
        print(f"  [{'✔' if ok else '✗'}] {tag} {'反例必报' if want else '正例必不报'}"
              f"（实测泄漏={got}）  {why}")
        if not ok and hits.get(tag):
            print(f"      意外泄漏：{hits[tag][:2]}")
    stray = {k: v for k, v in hits.items() if k not in {t for t, *_ in FIXTURES}}
    if stray:
        print(f"  [!] 归因到别处的泄漏 {len(stray)} 组：{list(stray)[:3]}")
    bad = sum(1 for _, _, w, _ in FIXTURES if w)
    print(f"自检结论：{len(FIXTURES)} 条对照（反例 {bad}、正例 {len(FIXTURES) - bad}）同页互证，"
          f"页面渲染出 <strong> {d['strongs']} 个 / 走过 {d['walked']} 个节点——"
          "判据既不是「什么都能报红」，也没被放宽。")
    return rc


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    base, shutdown = serve(DOCS)
    try:
        fails, stats = audit(base, report="--report" in sys.argv)
    finally:
        shutdown()
    for f in fails[:60]:
        print("  ✗", f)
    if len(fails) > 60:
        print(f"  …另有 {len(fails) - 60} 条")
    print(f"实测：{stats['pages']} 页 / {stats['walked']} 个可见文本节点 / "
          f"渲染出 <strong> {stats['strongs']} 个 / 泄漏 {stats['hits']} 处")
    if fails:
        print(f"渲染泄漏闸未通过：{len(fails)} 处源码写了语法、页面没吃进去")
        return 1
    print("渲染泄漏闸通过：可见文本里没有未解析的 markdown 标记残留。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
