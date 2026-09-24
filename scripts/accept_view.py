#!/usr/bin/env python3
"""打开页面做验收：真起 Chrome，逐页 × 逐视口 × 逐主题截图 + 现场读数。

本机无 X 显示（headful 起不来），所以"打开页面"只能走 headless CDP：
截图是我肉眼读，读数是浏览器现场量——两者都出，不用 DOM 可见性冒充结论。
"""
from __future__ import annotations

import sys, time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import CDP, safe_text

BASE = "http://127.0.0.1:8080"
OUT = Path("/tmp/shots-accept")
OUT.mkdir(exist_ok=True)

PAGES = [
    ("封面", ""),
    ("指南", "guide"),
    ("数字清单", "manuscript/ch05-数字清单"),
    ("Foundry卡", "manuscript/ch36-案例三-暗流资本"),
    ("Sentry卡", "manuscript/ch26-第21章-对账灰度回滚监控"),
    ("宽图章", "manuscript/ch10-第5章-大规模考古画图"),
]
VIEWPORTS = [(1280, 900), (1440, 900), (390, 844)]

READ = """
(() => {
  const s = document.querySelector('.content') || document.scrollingElement;
  const b = document.body;
  const theme = document.documentElement.getAttribute('data-theme') || '?';
  const bg = getComputedStyle(document.querySelector('.markdown-section')||b).backgroundColor;
  const tx = getComputedStyle(document.querySelector('.markdown-section h1')||b).color;
  return JSON.stringify({
    theme, hash: location.hash.slice(0,60),
    hOverflow: s ? s.scrollWidth - s.clientWidth : -1,
    docOverflow: b.scrollWidth - innerWidth,
    sidebar: !!document.querySelector('.sidebar') &&
             getComputedStyle(document.querySelector('.sidebar')).display !== 'none',
    bg, tx,
    title: (document.querySelector('.markdown-section h1')||{}).innerText || '',
    figs: document.querySelectorAll('.mermaid svg').length,
    tables: document.querySelectorAll('.markdown-section table').length
  });
})()
"""


def main():
    with CDP(width=1280, height=900) as c:
        c.navigate(f"{BASE}/#/"); time.sleep(2.0)
        for label, path in PAGES:
            for w, h in VIEWPORTS:
                c.set_viewport(w, h); c.reload(); time.sleep(1.6)
                c.navigate(f"{BASE}/#/{quote(path)}")
                ok = c.wait_for("document.querySelector('.markdown-section')", timeout=25)
                c.wait_for("true", timeout=1)
                time.sleep(1.2)
                for theme in ("light", "dark"):
                    cur = safe_text(c.js("document.documentElement.getAttribute('data-theme')||'light'"))
                    if cur != theme:
                        box = c.js("""(() => {const b=document.querySelector('#btn-theme');
                          if(!b) return null; const r=b.getBoundingClientRect();
                          return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2});})()""")
                        if box:
                            import json as _j
                            p = _j.loads(box); c.click(int(p["x"]), int(p["y"])); time.sleep(0.9)
                    read = safe_text(c.js(READ))
                    shot = OUT / f"{w}_{theme}_{label}.png"
                    c.screenshot(str(shot))
                    print(f"{w:>4} {theme:<5} {label:<10} {read}")
                    if not ok:
                        print("   !! markdown-section 未出现")
    print(f"\n截图目录：{OUT}  共 {len(list(OUT.glob('*.png')))} 张")


if __name__ == "__main__":
    main()
