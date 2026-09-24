#!/usr/bin/env python3
"""章节题图（plate）引擎：用代码画铜版线描，不用图像生成。

为什么不用图像生成接口：本机 ImageGen 稳定回 403（配额），而 14 张位图卷首已经证明
"先生成冷色图、再事后重着色"这条路要背两笔债——生成结果不可控（冷灰、淡紫），
重着色只能改色不能改构图。题图改成代码画之后：

1. 颜色只有 `tokens()` 这一个出处，直接读 theme.css 的 :root 令牌 → 板外色恒为 0，
   不需要"改完再验"，因为画不出板外的颜色。
2. 矢量 → 390px 窄屏与 1440px 宽屏同一份文件，不重编码、不失真、不占位图体积。
3. 构图可复算：同一 seed 出同一张图，改引擎能整批重跑（位图改不动就只能重抽）。
4. 版式统一由引擎保证（页边、留白、线宽档位、强调色用量），42 张不会画成 42 种脾气。

刀法约定（第一版被自己否掉的三件事，写在这里防止回退）：
- 线宽只许四档：hair 0.8 / main 1.3 / emph 2.1 / struct 2.8。混档会画成 CAD。
- 大面积实体一律用排线（hatch）而不是实心墨：第一版闸门用了 dense 排线，渲出来
  是一块近黑色砖，把整张纸的重量都吃掉了。
- 强调色（铜绿）每张只用**一处**，且只描边不填充大面积。

用法：
    python3 scripts/plate_engine.py                 # 渲染全部母题 + 出 PNG 预览
    python3 scripts/plate_engine.py --only strata   # 只出某个母题
    python3 scripts/plate_engine.py --check         # 只自检已落盘文件（板外色/文字节点）
"""
from __future__ import annotations

import argparse
import math
import random
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "docs" / "theme.css"
OUT = ROOT / "docs" / "assets" / "plates"
PROBE_DIR = Path("/tmp/plates_probe")   # 试版目录：不进仓库、不进发货资产

W, H = 1200, 460          # 题图幅面：12:5 横幅
M = 40                    # 页边
HAIR, MAIN, EMPH, STRUCT = 0.8, 1.3, 2.1, 2.8

# 描边按"页面实际显示宽 / 画布宽"预放大。670 是实测值不是估的：
# CDP 量 .chapter-plate img 的 getBoundingClientRect().width，1280 与 1440 两档同为 670px
# （正文栏有 max-width，视口加宽并不加宽图），390 档 340px。
# 不预放大的后果在 1280 截图里看得见：0.8 档发丝线落在 0.447 CSS px，整张图像蒙了层灰。
# 若正文栏宽度改版，重量这条读数并重画：python3 scripts/plate_engine.py --emit
DISPLAY_W = 670
BOOST = round(DISPLAY_W / W, 3)          # 0.558：页面缩放系数，供核对
INK_BOOST = round(1 / BOOST, 3)          # 1.792：描边预放大


def pw(x: float) -> float:
    """pattern / 字面描边：按页面缩放预放大后取两位。"""
    return round(x * INK_BOOST, 2)



def tokens() -> dict[str, str]:
    css = THEME.read_text()
    root = re.search(r":root\s*\{(.*?)\n\}", css, re.S).group(1)
    return {k: v.lower()
            for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", root)}


TOK = tokens()


def t(name: str) -> str:
    if name not in TOK:
        raise KeyError(f"theme.css 没有令牌 {name}——题图不允许自带颜色")
    return TOK[name]


PAPER = t("--c-plate")
EDGE = t("--c-plate-edge")
NODE = t("--c-plate-node")
LINE = t("--c-plate-line")
INK = t("--c-plate-ink")
ACCENT = t("--c-plate-accent")
PALETTE = {PAPER, EDGE, NODE, LINE, INK, ACCENT}


class Engraver:
    """刻刀：直线画成带极细抖动的折线，曲线走 Catmull-Rom，都不许绝对直。"""

    def __init__(self, rng: random.Random, amp: float = 0.9):
        self.rng = rng
        self.amp = amp

    def _j(self, v: float, scale: float = 1.0) -> float:
        return v + self.rng.uniform(-self.amp, self.amp) * scale

    def line(self, x1, y1, x2, y2, bow: float = 1.0) -> str:
        length = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(length / 52))
        pts = []
        for i in range(n + 1):
            u = i / n
            s = 0.0 if i in (0, n) else bow
            pts.append(f"{self._j(x1 + (x2 - x1) * u, s):.1f},"
                       f"{self._j(y1 + (y2 - y1) * u, s):.1f}")
        return "M" + " L".join(pts)

    def thread(self, x0, y0, x1, y1, sag: float = 5.0) -> str:
        """一根有自重的线：中点下垂，比直线像"织出来的东西"。"""
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + self._j(sag, .4)
        return (f"M{self._j(x0):.1f},{self._j(y0):.1f} "
                f"Q{mx:.1f},{my:.1f} {self._j(x1):.1f},{self._j(y1):.1f}")

    def poly(self, pts, close: bool = False, bow: float = 1.0) -> str:
        segs = [self.line(a[0], a[1], b[0], b[1], bow) for a, b in zip(pts, pts[1:])]
        if not segs:
            return ""
        d = segs[0] + "".join(f" {seg[1:]}" for seg in segs[1:])
        if close:
            d += " " + self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], bow)[1:]
        return d

    def smooth(self, pts, close: bool = False, jitter: float = 0.6) -> str:
        """Catmull-Rom → 三次贝塞尔：有机轮廓不用折线。"""
        p = [(self._j(x, jitter), self._j(y, jitter)) for x, y in pts]
        if close:
            p = [p[-1]] + p + [p[0], p[1]]
        else:
            p = [p[0]] + p + [p[-1]]
        d = f"M{p[1][0]:.1f},{p[1][1]:.1f}"
        for i in range(1, len(p) - 2):
            c1 = (p[i][0] + (p[i + 1][0] - p[i - 1][0]) / 6,
                  p[i][1] + (p[i + 1][1] - p[i - 1][1]) / 6)
            c2 = (p[i + 1][0] - (p[i + 2][0] - p[i][0]) / 6,
                  p[i + 1][1] - (p[i + 2][1] - p[i][1]) / 6)
            d += (f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} "
                  f"{p[i + 1][0]:.1f},{p[i + 1][1]:.1f}")
        return d

    def circle(self, cx, cy, r, a0=0.0, a1=360.0) -> str:
        seg = max(16, int(r / 4.5))
        pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / seg)),
                cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / seg)))
               for i in range(seg + 1)]
        return self.poly(pts, close=(abs(a1 - a0 - 360) < .01), bow=0.25)

    def ellipse(self, cx, cy, rx, ry, rot=0.0) -> str:
        pts = []
        for i in range(28):
            a = math.tau * i / 28
            x, y = rx * math.cos(a), ry * math.sin(a)
            xr = x * math.cos(rot) - y * math.sin(rot)
            yr = x * math.sin(rot) + y * math.cos(rot)
            pts.append((cx + xr, cy + yr))
        return self.smooth(pts, close=True, jitter=.45)

    def rect(self, x, y, w, h, bow: float = 1.0) -> str:
        return self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                         close=True, bow=bow)

    def sample(self, d: str, n: int = 90) -> list[tuple[float, float]]:
        """把路径上的数字坐标取出来当采样点——只用于求交，不用于绘制。"""
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", d)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) < 2:
            return pts
        out = []
        for i in range(n):
            u = i / (n - 1) * (len(pts) - 1)
            k = min(int(u), len(pts) - 2)
            f = u - k
            out.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f,
                        pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f))
        return out

    def weave(self, over: str, under: str, gap: float = 9.0, cap: int = 40) -> list[str]:
        """压线：在交点处用一小段纸色线把"下面那根"擦断，再画上面那根。
        这是线描版画里表现交织的唯一办法，没有它，织面就只是一张网格。
        ⚠ 交点必须聚类后再画：不聚类的版本在 9 股绳结上吐出 1 200 个擦除段，
        单张 SVG 从 13 KB 涨到 135 KB，而且擦得太碎，看着像断线不像交织。"""
        pts = []
        a, b = self.sample(over), self.sample(under)
        for ax, ay in a:
            for bx, by in b:
                if math.hypot(ax - bx, ay - by) < gap:
                    if not any(math.hypot(ax - px, ay - py) < gap * 1.6 for px, py in pts):
                        pts.append((ax, ay))
                    break
        pts = pts[:cap]
        return [f'<path d="M{px:.1f},{py:.1f} l0.1,0.1" stroke="{PAPER}" '
                f'stroke-width="{gap * 1.5}" stroke-linecap="round" fill="none"/>'
                for px, py in pts]


def s(d: str, stroke=LINE, width=MAIN, fill="none", cap="round", dash=None,
      opacity=None) -> str:
    op = f' opacity="{opacity}"' if opacity is not None else ""
    # 虚线的段长与描边同比放大，否则加粗后"线"变"点"、间隙反而成了主角
    extra = ""
    if dash:
        seg = " ".join(str(pw(float(v))) for v in str(dash).split())
        extra = f' stroke-dasharray="{seg}"'
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{pw(width)}" '
            f'stroke-linecap="{cap}" stroke-linejoin="round"{extra}{op}/>')


def tone(x, y, w, h, pattern="hatch", opacity=None) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{pattern})" stroke="none"{f" opacity={opacity}" if opacity else ""}/>'


def defs() -> str:
    """底纹：瓦片间距是**空间量**（不随页面缩放补偿），描边是**线的粗细**（要补）。
    只补描边不补间距，深档与浅档、桌面与手机上的灰度才一致。"""
    return f"""<defs>
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M30 0 L0 0 0 30" fill="none" stroke="{EDGE}" stroke-width="{pw(0.7)}" opacity="0.7"/>
    </pattern>
    <pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <path d="M0 0 V7" stroke="{LINE}" stroke-width="{pw(0.8)}" opacity="0.5"/>
    </pattern>
    <pattern id="hatch-soft" width="11" height="11" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <path d="M0 0 V11" stroke="{LINE}" stroke-width="{pw(0.75)}" opacity="0.34"/>
    </pattern>
    <pattern id="hatch-rev" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
      <path d="M0 0 V8" stroke="{LINE}" stroke-width="{pw(0.8)}" opacity="0.42"/>
    </pattern>
    <pattern id="cross" width="8" height="8" patternUnits="userSpaceOnUse">
      <path d="M0 8 L8 0 M0 0 L8 8" stroke="{LINE}" stroke-width="{pw(0.75)}" opacity="0.42"/>
    </pattern>
    <pattern id="stipple" width="10" height="10" patternUnits="userSpaceOnUse">
      <circle cx="2.5" cy="2.5" r="{pw(0.85)}" fill="{LINE}" opacity="0.5"/>
      <circle cx="7.5" cy="7.5" r="{pw(0.85)}" fill="{LINE}" opacity="0.34"/>
    </pattern>
    <pattern id="brick" width="34" height="16" patternUnits="userSpaceOnUse">
      <path d="M0 0 H34 M0 8 H34 M0 16 H34 M17 0 V8 M0 8 V16 M34 8 V16"
            fill="none" stroke="{LINE}" stroke-width="{pw(0.8)}" opacity="0.55"/>
    </pattern>
    <pattern id="water" width="26" height="10" patternUnits="userSpaceOnUse">
      <path d="M0 6 Q6.5 1 13 6 T26 6" fill="none" stroke="{LINE}" stroke-width="{pw(0.85)}" opacity="0.5"/>
    </pattern>
  </defs>"""


def frame(en: Engraver) -> str:
    """单线页框 + 四角刻痕 + 左下比例尺：让每张读起来像同一本画册的版。"""
    o = en.rect(M, M, W - 2 * M, H - 2 * M, bow=0.4)
    k = 12
    ticks = "".join(
        f'<path d="M{x} {y} h{dx} M{x} {y} v{dy}" stroke="{INK}" stroke-width="{pw(1.6)}" '
        f'stroke-linecap="round" fill="none"/>'
        for x, y, dx, dy in (
            (M, M, k, k), (W - M, M, -k, k), (M, H - M, k, -k), (W - M, H - M, -k, -k)))
    rule = "".join(s(en.line(64, H - 62, 64 + 6 * i, H - 62), INK if i % 5 == 0 else LINE,
                     EMPH if i % 5 == 0 else HAIR + .3) for i in range(11))
    return (f'<path d="{o}" fill="none" stroke="{LINE}" stroke-width="{pw(1.2)}"/>{ticks}{rule}'
            f'{s(en.line(64, H - 68, 64, H - 56), LINE, HAIR + .3)}'
            f'{s(en.line(124, H - 68, 124, H - 56), LINE, HAIR + .3)}')


# --------------------------------------------------------------------------- 母题

def m_strata(en: Engraver, rng) -> str:
    """探沟剖面：不等厚地层 + 一条断层把层错开 + 铜绿卡住最薄那层（考古／读依赖）。"""
    x0, x1, top = 92, W - 92, 96
    fault = 690                                          # 断层位置
    drop = 22                                            # 右盘下沉量
    th = [26, 44, 18, 58, 34, 52]                        # 不等厚：真实的地层不是等分
    fills = ["hatch-soft", "stipple", "hatch", "", "cross", "hatch-soft"]
    edges = [top]
    for h in th:
        edges.append(edges[-1] + h)
    bottom = edges[-1]
    out = [f'<rect x="{x0}" y="{top}" width="{x1 - x0}" height="{bottom + drop - top}" '
           f'fill="url(#grid)" opacity="0.55"/>']
    for i, (h, f) in enumerate(zip(th, fills)):
        y0, y1 = edges[i], edges[i + 1]
        for (ax0, ax1, oy0, oy1) in ((x0, fault, y0, y1), (fault, x1, y0 + drop, y1 + drop)):
            out.append(s(en.line(ax0, oy0, ax1, oy0), INK if h > 45 else LINE,
                         EMPH if h > 45 else MAIN))
            if f:
                out.append(f'<path d="M{ax0},{oy0} L{ax1},{oy0} L{ax1},{oy1} L{ax0},{oy1} Z" '
                           f'fill="url(#{f})" stroke="none"/>')
    out.append(s(en.line(x0, bottom, fault, bottom), INK, EMPH))
    out.append(s(en.line(fault, bottom + drop, x1, bottom + drop), INK, EMPH))
    # 断面：断层的两壁 + 错动记号（长度只在剖面内，不扎出去）
    out.append(s(en.line(fault, top, fault, bottom + drop), INK, EMPH))
    out.append(s(en.line(fault + 8, top + 12, fault + 8, bottom + drop), LINE, HAIR + .3,
                 opacity=.7))
    for yy in (top + 58, top + 148, top + 226):
        out.append(s(en.line(fault - 15, yy, fault + 21, yy + 13), LINE, HAIR + .3))
    # 顶面侵蚀线 + 地层里的残片
    out.append(s(en.smooth([(x0, top - 9), (x0 + 180, top - 15), (x0 + 420, top - 6),
                            (fault - 40, top - 14), (x1 - 120, top - 5), (x1, top - 13)]),
                 INK, MAIN))
    for cx, cy, w, h in ((180, top + 30, 76, 20), (430, top + 128, 104, 17),
                         (760, top + 152, 82, 22), (980, top + 58, 66, 18)):
        out.append(s(en.rect(cx, cy, w, h, .6), LINE, MAIN, NODE))
        out.append(s(en.line(cx + 7, cy + h / 2, cx + w - 7, cy + h / 2), LINE, HAIR + .2))
    # 铜绿：卡住最薄那一层（18px——"没人敢删的那段"）
    by = edges[2] + th[2] / 2
    bx0, bx1 = 356, 566
    for x in (bx0, bx1):
        out.append(s(en.line(x, by - 33, x, by + 33), ACCENT, MAIN))
    out.append(s(en.line(bx0, by - 33, bx1, by - 33), ACCENT, MAIN))
    out.append(s(en.line(bx0, by + 33, bx1, by + 33), ACCENT, MAIN))
    for x in range(bx0 + 13, bx1, 19):
        out.append(s(en.line(x, by + 25, x, by + 33), ACCENT, HAIR + .3))
    return "".join(out)


def m_loom(en: Engraver, rng) -> str:
    """织机：左半是织好的布（经线×纬线压线交织 +  shuttle 走的那根纬是铜绿），
    右半是还没上机的散经（各自下垂、长短不齐）。
    ⚠ 这一版替换掉的是"乱麻理直"：程序画的绳结在纸上读起来像一坨断线（交织要靠
    压线擦断，9 股绳的交点擦下来 1200 段，图重 135 KB 还画不像）。织布用的是同一套
    线，但经纬正交、交点可控，"散乱→成物"的比喻反而更准。"""
    out = []
    cx0, cx1 = 92, 566                                   # 布面
    ty, by_ = 116, 344
    warp_x = [cx0 + 8 + i * 27 for i in range(18)]
    weft_y = [ty + 10 + j * 24 for j in range(10)]
    out.append(f'<rect x="{cx0}" y="{ty}" width="{cx1 - cx0}" height="{by_ - ty}" '
               f'fill="url(#hatch-soft)" stroke="none" opacity="0.5"/>')
    for x in warp_x:                                     # 经线
        out.append(s(en.thread(x, ty, x, by_, sag=2.5), LINE, MAIN))
    for j, y in enumerate(weft_y):                       # 纬线：隔一根压一次
        for k, x in enumerate(warp_x):
            if (j + k) % 2 == 0:
                out.append(f'<path d="M{x:.1f},{y:.1f} l0.1,0.1" stroke="{PAPER}" '
                           f'stroke-width="7.5" stroke-linecap="round" fill="none"/>')
        col = ACCENT if j == 5 else (INK if j % 4 == 0 else LINE)
        out.append(s(en.thread(cx0, y, cx1, y + rng.uniform(-2, 2), sag=3), col,
                     EMPH if j == 5 else MAIN))
    out.append(s(en.line(cx0 - 7, ty - 6, cx0 - 7, by_ + 6), INK, EMPH))   # 布边
    out.append(s(en.line(cx0 - 1, ty - 6, cx1, ty - 6), INK, MAIN))
    out.append(s(en.line(cx0 - 1, by_ + 6, cx1, by_ + 6), INK, MAIN))
    # 梭子：停在布面上的那枚铜绿梭（当前正在走的一根纬）
    shx, shy = 392, weft_y[5]
    out.append(s(en.smooth([(shx - 40, shy), (shx, shy - 13), (shx + 40, shy),
                            (shx, shy + 13)], close=True), ACCENT, EMPH, PAPER))
    out.append(s(en.circle(shx - 26, shy, 4), ACCENT, MAIN, NODE))
    out.append(s(en.line(shx + 40, shy, cx1, shy), ACCENT, EMPH))
    # 钢筘：把布与散经分开的排齿
    rx = 618
    out.append(s(en.rect(rx, 104, 54, 258, .5), INK, EMPH, NODE))
    out.append(f'<rect x="{rx}" y="104" width="54" height="258" fill="url(#brick)" stroke="none"/>')
    for y in weft_y:
        out.append(s(en.line(rx - 2, y, rx + 56, y), PAPER, 3.0))
    # 散经：出了钢筘就没人管了——间距乱、下垂深、有断头
    for i, y in enumerate(weft_y):
        x_end = W - 96 - rng.choice([0, 0, 42, 78])
        out.append(s(en.thread(rx + 54, y, x_end, y + rng.uniform(-16, 16),
                               sag=rng.uniform(8, 26)), LINE, MAIN))
    for x in (cx1 - 26, cx1 - 68):                      # 断经头：只从布的右缘伸出
        out.append(s(en.thread(x, rng.uniform(150, 200), x + rng.uniform(20, 44),
                               rng.uniform(240, 330), sag=12), LINE, HAIR + .5))
    return "".join(out)


def m_gate(en: Engraver, rng) -> str:
    """水闸：砖石闸体（排线不是实心墨）+ 拱形闸口 + 过闸水流 + 铜绿手轮（契约／边界）。"""
    out = []
    gx, gy, gw, gh = 470, 104, 156, 268
    for i in range(8):
        y = 128 + i * 30
        out.append(s(en.thread(92, y, gx - 6, y + rng.uniform(-4, 4), sag=3), LINE, MAIN))
    out.append(f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" fill="url(#brick)" stroke="none"/>')
    out.append(s(en.rect(gx, gy, gw, gh, .5), INK, EMPH))
    out.append(s(en.rect(gx - 14, gy - 18, gw + 28, 22, .5), LINE, MAIN, NODE))
    out.append(s(en.smooth([(gx + 46, gy + gh - 10), (gx + 44, gy + 140), (gx + 78, gy + 108),
                            (gx + 112, gy + 140), (gx + 110, gy + gh - 10)]), INK, EMPH, PAPER))
    # 闸杆 + 铜绿手轮（全部收在页框内）
    out.append(s(en.line(gx + gw / 2, gy - 18, gx + gw / 2, gy - 44), INK, EMPH))
    wy, wr = gy - 62, 18
    out.append(s(en.circle(gx + gw / 2, wy, wr), ACCENT, EMPH))
    out.append(s(en.circle(gx + gw / 2, wy, 6), ACCENT, MAIN, NODE))
    for a in (0, 90, 180, 270):
        out.append(s(en.line(gx + gw / 2 + wr * math.cos(math.radians(a)),
                             wy + wr * math.sin(math.radians(a)),
                             gx + gw / 2 + 6 * math.cos(math.radians(a)),
                             wy + 6 * math.sin(math.radians(a))), ACCENT, MAIN))
    out.append(s(en.line(gx + gw / 2 - 44, gy - 44, gx + gw / 2 + 44, gy - 44), ACCENT, MAIN))
    out.append(f'<rect x="{gx + gw}" y="158" width="{W - 96 - gx - gw}" height="176" '
               f'fill="url(#water)" stroke="none"/>')
    for i in range(5):
        y = 176 + i * 36
        out.append(s(en.thread(gx + gw, y, W - 96, y + rng.uniform(-5, 5), sag=6), LINE, MAIN))
    # 越界的那一条：撞在铜绿界线上被拦回
    out.append(s(en.line(gx + gw + 40, 300, W - 156, 300), ACCENT, EMPH, dash="12 8"))
    out.append(s(en.smooth([(W - 156, 300), (W - 132, 290), (W - 118, 266), (W - 124, 240)]),
                 ACCENT, EMPH))
    out.append(s(en.circle(W - 124, 232, 7), ACCENT, MAIN, NODE))
    return "".join(out)


def m_caliper(en: Engraver, rng) -> str:
    """游标卡尺：横梁刻度 + 定钳/动钳从两侧夹住工件 + 铜绿公差带（度量／验收）。"""
    out = []
    bx, by, bw, bh = 150, 118, 900, 30
    ox, oy, orr = 556, 262, 76
    out.append(s(en.rect(bx, by, bw, bh, .5), INK, EMPH, NODE))
    out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="url(#hatch-soft)" '
               f'stroke="none"/>')
    for i in range(25):
        x = bx + 18 + i * 35
        long = i % 5 == 0
        out.append(s(en.line(x, by + bh, x, by + bh + (26 if long else 15)),
                     INK if long else LINE, EMPH if long else HAIR + .35))
    # 工件先画，钳口压在上面才有"夹住"的关系
    out.append(f'<circle cx="{ox}" cy="{oy + 9}" r="{orr}" fill="url(#stipple)" stroke="none"/>')
    out.append(f'<circle cx="{ox}" cy="{oy}" r="{orr}" fill="url(#cross)" stroke="none"/>')
    out.append(s(en.circle(ox, oy, orr), INK, EMPH))
    out.append(s(en.circle(ox, oy, orr - 16), LINE, HAIR + .35, opacity=.55))
    fx = ox - orr - 7                                    # 定钳内侧面
    out.append(s(en.poly([(fx - 52, by + bh), (fx - 52, oy + 44), (fx, oy + 30),
                          (fx, by + bh)], close=True, bow=.4), INK, EMPH, NODE))
    out.append(f'<path d="M{fx - 52},{by + bh} L{fx - 52},{oy + 44} L{fx},{oy + 30} L{fx},{by + bh} Z" '
               f'fill="url(#hatch-soft)" stroke="none"/>')
    sx = ox + orr + 7                                    # 动钳内侧面
    out.append(s(en.rect(sx - 4, by - 14, 76, bh + 26, .5), LINE, EMPH, NODE))
    out.append(s(en.circle(sx + 34, by + bh / 2, 8), LINE, MAIN, PAPER))
    out.append(s(en.poly([(sx, by + bh), (sx, oy + 30), (sx + 52, oy + 44),
                          (sx + 52, by + bh)], close=True, bow=.4), INK, EMPH, NODE))
    out.append(f'<path d="M{sx},{by + bh} L{sx},{oy + 30} L{sx + 52},{oy + 44} L{sx + 52},{by + bh} Z" '
               f'fill="url(#hatch-soft)" stroke="none"/>')
    # 铜绿：深度尺插进孔心 + 上下两道公差带夹住直径
    out.append(s(en.line(ox, by - 26, ox, oy), ACCENT, EMPH))
    out.append(s(en.rect(ox - 30, by - 44, 60, 18, .4), ACCENT, EMPH, PAPER))
    out.append(s(en.circle(ox, oy, 6), ACCENT, MAIN, NODE))
    for yy in (oy - orr, oy + orr):
        out.append(s(en.line(ox - 134, yy, ox + 134, yy), ACCENT, MAIN, dash="9 7"))
        for x in (ox - 134, ox + 134):
            out.append(s(en.line(x, yy - 9, x, yy + 9), ACCENT, MAIN))
    for x in (fx - 52, ox, sx + 52):
        out.append(s(en.line(x, oy + orr + 28, x, H - 92), LINE, HAIR + .3, dash="5 6"))
    return "".join(out)


def m_radar(en: Engraver, rng) -> str:
    """回波屏：同心刻度 + 扫掠扇形（排线不是实心）+ 三个亮点 + 右侧标尺（可观测）。"""
    cx, cy, R = 336, 232, 152
    out = [f'<rect x="92" y="86" width="490" height="300" fill="url(#grid)" opacity="0.5"/>']
    for i in range(1, 5):
        out.append(s(en.circle(cx, cy, R * i / 4), LINE, EMPH if i == 4 else MAIN, opacity=.9))
    for a in (0, 90, 180, 270):
        out.append(s(en.line(cx + (R + 14) * math.cos(math.radians(a)),
                             cy + (R + 14) * math.sin(math.radians(a)),
                             cx + (R - 26) * math.cos(math.radians(a)),
                             cy + (R - 26) * math.sin(math.radians(a))), LINE, HAIR + .4,
                     opacity=.65))
    out.append(s(en.circle(cx, cy, 5), INK, EMPH, INK))
    # 扫掠扇形：用排线铺，不用实心
    wedge = (f"M{cx},{cy} L{cx + R * math.cos(math.radians(-62)):.1f},"
             f"{cy + R * math.sin(math.radians(-62)):.1f} "
             f"A{R},{R} 0 0 1 {cx + R * math.cos(math.radians(-8)):.1f},"
             f"{cy + R * math.sin(math.radians(-8)):.1f} Z")
    out.append(f'<path d="{wedge}" fill="url(#hatch-soft)" stroke="none"/>')
    out.append(s(en.line(cx, cy, cx + R * math.cos(math.radians(-40)),
                         cy + R * math.sin(math.radians(-40))), INK, EMPH))
    for (px, py, rr, ph) in ((438, 148, 8, True), (268, 300, 6, False), (372, 268, 5, False)):
        out.append(s(en.circle(px, py, rr), ACCENT, EMPH, NODE))
        out.append(s(en.circle(px, py, rr + 13), ACCENT, HAIR + .4, opacity=.55))
        if ph:
            out.append(s(en.circle(px, py, rr + 24), ACCENT, HAIR + .3, opacity=.3))
    # 右侧标尺 + 一条被标出的趋势
    x0 = 636
    out.append(s(en.line(x0, 108, x0, 366), INK, EMPH))
    for i in range(12):
        y = 112 + i * 23
        out.append(s(en.line(x0, y, x0 + (34 if i % 3 == 0 else 17), y),
                     INK if i % 3 == 0 else LINE, EMPH if i % 3 == 0 else HAIR + .3))
    bx, by, bw, bh = x0 + 62, 140, W - 96 - x0 - 62, 200
    out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="url(#stipple)" stroke="none"/>')
    out.append(s(en.rect(bx, by, bw, bh, .5), LINE, MAIN))
    pts = [(bx + bw * i / 6, by + bh - (28 + 22 * i + (14 if i == 5 else 0))) for i in range(7)]
    out.append(s(en.poly(pts, bow=.5), INK, EMPH))
    for (px, py) in pts:
        out.append(s(en.circle(px, py, 4.6), LINE, MAIN, PAPER))
    out.append(s(en.line(bx, by + bh - 66, bx + bw, by + bh - 66), ACCENT, EMPH, dash="10 7"))
    return "".join(out)


def m_contour(en: Engraver, rng) -> str:
    """等高线：一圈圈收敛的界 + 上山的路（迁移切片）+ 罗盘（目标架构／演进）。"""
    cx, cy = 372, 236
    out = []
    rings = []
    for i in range(8):
        r = 30 + i * 24
        pts = []
        for k in range(14):
            a = math.tau * k / 13
            wob = 1 + 0.11 * math.sin(3 * a + i * .8) + 0.05 * math.cos(5 * a - i * .5)
            pts.append((cx + r * math.cos(a) * wob * 1.2, cy + r * math.sin(a) * wob * .8))
        d = en.smooth(pts, close=True)
        rings.append(d)
        out.append(f'<path d="{d}" fill="url(#hatch-soft)" stroke="none" opacity="{0.9 - i * 0.1:.2f}"/>'
                   if i % 2 == 0 else "")
        out.append(s(d, INK if i in (0, 7) else LINE, EMPH if i in (0, 7) else MAIN))
    out.append(s(en.circle(cx, cy, 10), ACCENT, EMPH, NODE))
    out.append(s(en.line(cx - 30, cy, cx + 30, cy), ACCENT, MAIN))
    out.append(s(en.line(cx, cy - 30, cx, cy + 30), ACCENT, MAIN))
    # 上山的路：从右下角一级一级台阶到山顶
    p = [(1096, 366), (980, 352), (906, 316), (806, 312), (736, 268), (640, 250), (556, 226)]
    for a, b in zip(p, p[1:]):
        out.append(s(en.line(a[0], a[1], b[0], b[1], .6), INK, EMPH))
    for (px, py) in p:
        out.append(s(en.circle(px, py, 7), LINE, MAIN, PAPER))
    out.append(s(en.circle(p[-1][0], p[-1][1], 14), ACCENT, EMPH))
    # 罗盘
    ox, oy = 1058, 128
    out.append(s(en.circle(ox, oy, 32), LINE, MAIN))
    out.append(s(en.circle(ox, oy, 24), LINE, HAIR + .3, opacity=.7))
    for a in range(0, 360, 45):
        L = 42 if a % 90 == 0 else 36
        out.append(s(en.line(ox + 24 * math.cos(math.radians(a)), oy + 24 * math.sin(math.radians(a)),
                             ox + L * math.cos(math.radians(a)), oy + L * math.sin(math.radians(a))),
                     INK if a % 90 == 0 else LINE, EMPH if a == 270 else MAIN))
    out.append(s(en.smooth([(ox, oy - 20), (ox + 7, oy), (ox, oy + 20), (ox - 7, oy)], close=True),
                 ACCENT, MAIN, NODE))
    return "".join(out)


def m_sieve(en: Engraver, rng) -> str:
    """筛子：倒进来的东西里只有一小部分被接住，其余穿筛而下（AI 产出／验收）。

    构图按三条横带铺满 12:5 版面（进料带／筛面／穿筛与积料带）。第一版把漏斗画在正中、
    右侧另起一张小剖面，1280 截图里左右各空着一片纸，读起来像没画完的示意图而不是版画。
    铜绿只给"过得了孔径的那一颗"：全书的立场是接住错误比写得快更难。"""
    out = []
    sx0, sx1, sy = 150, 1050, 252                        # 筛面：横贯版面的那一条界
    ax, ay, aw, ah = 812, 92, 236, 126                   # 右上小剖面（落料要停在它之前）
    # ── 进料带：左上漏斗 + 沿筛面铺开的落料
    fx, fy0, fy1 = 292, 96, 186
    out.append(s(en.line(fx - 104, fy0, fx - 20, fy1), INK, EMPH))
    out.append(s(en.line(fx + 104, fy0, fx + 20, fy1), INK, EMPH))
    out.append(s(en.line(fx - 20, fy1, fx + 20, fy1), INK, MAIN))
    out.append(s(en.line(fx - 112, fy0, fx + 112, fy0), LINE, HAIR + .4, dash="7 6", opacity=.8))
    out.append(f'<rect x="{fx - 100}" y="{fy0 + 6}" width="200" height="34" '
               f'fill="url(#hatch-soft)" stroke="none" opacity="0.7"/>')
    # 落料：从漏斗口向右铺开，越往右越稀、越小（写得快 ≠ 排得满）
    for i in range(46):
        t = i / 45
        px = fx + rng.uniform(-70, 70) + t * (ax - 26 - fx)   # 停在右上小剖面之前
        py = fy1 + rng.uniform(-42, 34) + t * 14
        if py > sy - 14:
            py = sy - 14 - rng.uniform(0, 26)
        r = rng.uniform(3.0, 8.2) * (1 - .38 * t)
        out.append(s(en.circle(px, py, r), LINE, MAIN, NODE if i % 3 else PAPER))
    # ── 筛面：斜纹带 + 等距筛孔 + 铜绿标出的那一段口径
    out.append(f'<rect x="{sx0}" y="{sy}" width="{sx1 - sx0}" height="14" fill="url(#cross)" '
               f'stroke="none"/>')
    out.append(s(en.line(sx0, sy, sx1, sy), INK, EMPH))
    out.append(s(en.line(sx0, sy + 14, sx1, sy + 14), LINE, MAIN))
    for x in range(sx0 + 26, sx1 - 10, 52):
        out.append(s(en.line(x, sy + 3, x, sy + 11), LINE, HAIR + .35, opacity=.7))
    out.append(s(en.rect(604, sy - 3, 96, 20, .5), ACCENT, EMPH))
    # 留在筛面上的大块（被拦下）
    for (px, w, h) in ((382, 30, 24), (452, 22, 18), (866, 34, 26), (944, 20, 16)):
        out.append(s(en.rect(px, sy - h, w, h, .5), LINE, MAIN, NODE))
    out.append(s(en.rect(516, sy - 21, 26, 21, .5), LINE, MAIN, PAPER))
    # ── 穿筛而下：细流 + 底部积料
    for i in range(15):
        x = sx0 + 30 + i * 60
        out.append(s(en.thread(x, sy + 18, x + rng.uniform(-8, 8), 352, sag=4),
                     LINE, HAIR + .45, opacity=.8))
    out.append(f'<path d="M{sx0 - 6},352 L{sx1 + 6},352 L{sx1 - 18},392 L{sx0 + 18},392 Z" '
               f'fill="url(#stipple)" stroke="none"/>')
    out.append(s(en.line(sx0 - 6, 352, sx1 + 6, 352), INK, MAIN))
    out.append(s(en.smooth([(sx0 + 18, 392), ((sx0 + sx1) // 2, 378), (sx1 - 18, 392)]),
                 LINE, MAIN))
    # ── 右上小剖面：卡住靠的是尺寸，不是运气
    out.append(s(en.rect(ax, ay, aw, ah, .5), LINE, MAIN))
    out.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="url(#grid)" '
               f'stroke="none" opacity="0.55"/>')
    out.append(s(en.line(ax + 62, ay + 8, ax + 62, ay + ah - 8), INK, MAIN))
    out.append(s(en.line(ax + 128, ay + 8, ax + 128, ay + ah - 8), INK, MAIN))
    out.append(s(en.circle(ax + 95, ay + 42, 20), ACCENT, EMPH))       # 过得了的那颗
    out.append(s(en.circle(ax + 95, ay + 94, 27), LINE, MAIN, NODE))   # 过不了的那颗
    out.append(s(en.line(ax + 40, ay + 42, ax + 150, ay + 42), ACCENT, HAIR + .4, dash="6 5"))
    return "".join(out)


def m_truss(en: Engraver, rng) -> str:
    """桁架：一根根斜杆把载荷传到墩上，其中一根被铜绿标成"这一根不能拆"（依赖／承重）。"""
    out = []
    y0, y1 = 168, 288
    xs = [110 + i * 98 for i in range(10)]
    out.append(s(en.line(xs[0], y0, xs[-1], y0), INK, EMPH))
    out.append(s(en.line(xs[0], y1, xs[-1], y1), INK, EMPH))
    for i, x in enumerate(xs):
        out.append(s(en.line(x, y0, x, y1), LINE, MAIN))
        if i < len(xs) - 1:
            d = en.line(x, y1, xs[i + 1], y0) if i % 2 == 0 else en.line(x, y0, xs[i + 1], y1)
            out.append(s(d, LINE, MAIN + .15))
    # 载荷：桥面上三个砝码（越靠跨中越重）
    for i, (cx, hh) in enumerate(((260, 26), (560, 44), (860, 30))):
        out.append(s(en.rect(cx - 34, y0 - hh - 12, 68, hh, .5), LINE, MAIN, NODE))
        out.append(f'<rect x="{cx - 34}" y="{y0 - hh - 12}" width="68" height="{hh}" '
                   f'fill="url(#hatch-soft)" stroke="none"/>')
        for k in range(3):
            out.append(s(en.line(cx - 22 + k * 22, y0 - 10, cx - 22 + k * 22, y0 + 6),
                         INK, HAIR + .4))
    # 墩与地面线
    for x in (xs[1], xs[4], xs[7]):
        out.append(s(en.poly([(x - 30, y1), (x + 30, y1), (x + 20, 356), (x - 20, 356)],
                             close=True, bow=.5), INK, EMPH, NODE))
        out.append(f'<path d="M{x - 30},{y1} L{x + 30},{y1} L{x + 20},356 L{x - 20},356 Z" '
                   f'fill="url(#hatch)" stroke="none"/>')
    out.append(s(en.line(96, 356, W - 96, 356), INK, EMPH))
    for i in range(16):
        x = 100 + i * 62
        out.append(s(en.line(x, 356, x - 13, 370), LINE, HAIR + .4))
    # 铜绿：被标出的那根斜杆 + 它的两个节点
    i = 4
    out.append(s(en.line(xs[i], y0, xs[i + 1], y1), ACCENT, EMPH))
    for (px, py) in ((xs[i], y0), (xs[i + 1], y1)):
        out.append(s(en.circle(px, py, 8), ACCENT, EMPH, PAPER))
    out.append(s(en.circle(xs[i] + (xs[i + 1] - xs[i]) / 2, (y0 + y1) / 2, 20), ACCENT,
                 HAIR + .4, dash="6 5"))
    return "".join(out)


def m_spillway(en: Engraver, rng) -> str:
    """溢洪道：水位涨到堰顶才自己泄，不需要谁去下令（容量／自动降级）。"""
    out = []
    crest_x, crest_y = 520, 190
    # 上游水体：波纹 + 库底
    out.append(f'<rect x="96" y="{crest_y - 4}" width="{crest_x - 96}" height="176" '
               f'fill="url(#water)" stroke="none"/>')
    out.append(s(en.line(96, crest_y - 6, crest_x, crest_y - 6), INK, EMPH))
    out.append(s(en.line(96, crest_y + 6, 96, 366), INK, EMPH))
    out.append(s(en.line(96, 366, crest_x + 210, 366), INK, EMPH))
    # 堰体（砖纹）+ 堰顶铜绿标线
    out.append(f'<rect x="{crest_x}" y="{crest_y - 26}" width="120" height="{366 - crest_y + 26}" '
               f'fill="url(#brick)" stroke="none"/>')
    out.append(s(en.poly([(crest_x, crest_y - 26), (crest_x + 120, crest_y - 26),
                          (crest_x + 150, 366), (crest_x + 96, 366)], close=True, bow=.5),
                 INK, EMPH))
    out.append(s(en.line(crest_x - 4, crest_y - 26, crest_x + 124, crest_y - 26), ACCENT, EMPH))
    # 跌水：抛物线水舌 + 雾化区
    for i in range(7):
        x0 = crest_x + 120 + i * 12
        out.append(s(en.smooth([(x0, crest_y - 20), (x0 + 46 + i * 6, crest_y + 30 + i * 8),
                                (x0 + 78 + i * 9, crest_y + 108 + i * 12),
                                (x0 + 96 + i * 10, 358)]), LINE, MAIN))
    out.append(f'<ellipse cx="{crest_x + 250}" cy="344" rx="132" ry="26" fill="url(#stipple)" '
               f'stroke="none"/>')
    # 下游消力池
    out.append(s(en.line(crest_x + 150, 366, W - 96, 366), INK, EMPH))
    for i in range(4):
        y = 322 - i * 26
        out.append(s(en.thread(crest_x + 300 + i * 40, y, W - 100, y + 12, sag=8),
                     LINE, HAIR + .5, opacity=.8))
    # 水位标尺：三条线，只有最上面那条越过了堰顶
    gx = 168
    out.append(s(en.line(gx, 104, gx, 348), INK, EMPH))
    for i in range(11):
        y = 112 + i * 22
        out.append(s(en.line(gx, y, gx + (30 if i % 5 == 0 else 15), y),
                     INK if i % 5 == 0 else LINE, EMPH if i % 5 == 0 else HAIR + .3))
    out.append(s(en.line(gx - 12, crest_y - 26, gx + 250, crest_y - 26), ACCENT, MAIN,
                 dash="10 7"))
    out.append(s(en.line(gx - 12, crest_y - 26, gx - 12, crest_y - 8), ACCENT, EMPH))
    return "".join(out)


MOTIFS = {
    "strata": m_strata, "loom": m_loom, "gate": m_gate,
    "radar": m_radar, "caliper": m_caliper, "contour": m_contour,
    "sieve": m_sieve, "truss": m_truss, "spillway": m_spillway,
}



# --------------------------------------------------------------------------- 台账
# 章 → 母题。规则：**只给九个部分的首章出题图**，一幅一个母题，不重复。
# 为什么不给 42 章都配：母题只有九个，硬配会让第七个"分层"和第一个"分层"长得一样，
# 读者读到第三次就发现题图是贴纸而不是画——那时它开始扣审美分。
PLATES: dict[str, tuple[str, int, str]] = {
    "ch06": ("sieve", 3, "筛子：AI 写得快不是本事，写错了能被接住才是"),
    "ch10": ("strata", 11, "探沟剖面：地层不会自己说话，断层要人标出来"),
    "ch13": ("contour", 7, "等高线：目标架构不是一个点，是一圈一圈收敛的界"),
    "ch17": ("loom", 5, "织机：把缠在一起的三件事分成经线和纬线"),
    "ch21": ("truss", 9, "桁架：新功能必须落在既有的承重结构上"),
    "ch24": ("gate", 13, "水闸：过闸的口径是定出来的，不是涨出来的"),
    "ch28": ("caliper", 17, "卡尺：治理靠可判定的尺寸，不靠形容词"),
    "ch33": ("spillway", 23, "溢洪道：水位到了堰顶自己泄，不需要谁下令"),
    "ch38": ("radar", 29, "回波屏：四个案例是同一台仪器的四次回波"),
}

def render(motif: str, seed: int = 11) -> str:
    rng = random.Random(f"{motif}:{seed}")
    en = Engraver(rng)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">
  <title>{motif} — 章节题图（铜版线描；颜色取自 theme.css 图版令牌，无外部资源）</title>
  {defs()}
  <rect width="{W}" height="{H}" fill="{PAPER}"/>
  <g>{frame(en)}</g>
  <g>{MOTIFS[motif](en, rng)}</g>
</svg>
"""


def check(svg_text: str, name: str) -> list[str]:
    """自检：颜色必须逐个等于令牌值；不得含文字节点（<img> 里的 SVG 用不了子集字体）。"""
    reds = []
    for c in set(re.findall(r"#[0-9a-fA-F]{3,8}", svg_text)) - PALETTE:
        reds.append(f"{name}: 板外色 {c}")
    try:
        ET.fromstring(svg_text)
    except ET.ParseError as e:
        reds.append(f"{name}: SVG 解析失败 {e}")
    if "<text" in svg_text:
        reds.append(f"{name}: 含 <text> 节点——题图不写字，字由 HTML 图注承担")
    return reds


def preview(svg: Path, dst: Path) -> None:
    dst.parent.mkdir(exist_ok=True)
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                    f"--screenshot={dst}", f"--window-size={W},{H}", "--hide-scrollbars",
                    "file://" + str(svg)], capture_output=True, timeout=90)



MS = ROOT / "docs" / "manuscript"


def emit_chapter_plates() -> int:
    """按台账出题图并把 <figure> 插进章首（幂等：已有 chapter-plate 的章跳过插入）。"""
    reds: list[str] = []
    for stem, (motif, seed, caption) in sorted(PLATES.items()):
        ch = next(iter(sorted(MS.glob(f"{stem}-*.md"))), None)
        if ch is None:
            reds.append(f"{stem}: 找不到章文件")
            continue
        svg = render(motif, seed)
        reds += check(svg, f"{stem}/{motif}")
        name = f"{stem}-{motif}.svg"
        (OUT / name).write_text(svg)
        text = ch.read_text()
        if "chapter-plate" in text:
            print(f"  {name}  {len(svg) / 1024:.1f} KB  （图注已在位，跳过插入）")
            continue
        lines = text.split("\n")
        # 插到「本章定位／核心命题」引用块之后：题图不抢标题，也不压进正文第一段
        i = 0
        while i < len(lines) and not lines[i].startswith("# "):
            i += 1
        i += 1
        while i < len(lines) and (lines[i].startswith(">") or not lines[i].strip()):
            i += 1
        while i > 0 and not lines[i - 1].strip():
            i -= 1
        ch_no = lines[0].split(" ")[1] if len(lines[0].split(" ")) > 1 else stem
        block = (f'\n<figure class="chapter-plate">\n'
                 f'  <img src="../assets/plates/{name}" alt="{ch_no}题图：{caption.split("：")[0]}"/>\n'
                 f'  <figcaption>题图 · {caption}</figcaption>\n'
                 f'</figure>')
        lines.insert(i, block)
        ch.write_text("\n".join(lines))
        print(f"  {name}  {len(svg) / 1024:.1f} KB  → {ch.name}")
    for r in reds:
        print("  ✗", r)
    return 1 if reds else 0

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只渲染指定母题")
    ap.add_argument("--check", action="store_true", help="只自检已落盘文件")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--emit", action="store_true", help="按台账出题图并插进章首")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if args.emit:
        return emit_chapter_plates()
    if args.check:
        files = sorted(OUT.glob("*.svg"))
        reds = [r for p in files for r in check(p.read_text(), p.name)]
        print(f"[题图自检] {len(files)} 张，{len(reds)} 条不达标")
        for r in reds:
            print("  ✗", r)
        return 1 if reds else 0

    motifs = [args.only] if args.only else sorted(MOTIFS)
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    reds: list[str] = []
    for mo in motifs:
        svg = render(mo)
        reds += check(svg, mo)
        dst = PROBE_DIR / f"probe-{mo}.svg"              # 试版不落进发货目录：assets 里的每个字节都会被站点守卫看见
        dst.write_text(svg)
        line = f"  {dst}  {len(svg) / 1024:.1f} KB"
        if not args.no_preview:
            png = Path("/tmp/plates_png") / f"{mo}.png"
            preview(dst, png)
            line += f"  → {png}"
        print(line)
    for r in reds:
        print("  ✗", r)
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(main())
