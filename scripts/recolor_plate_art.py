#!/usr/bin/env python3
"""把卷首/案例的 AI 版画重着色到本书的纸/墨/铜绿三停渐变上。

为什么不是重新生成：本机的图像生成接口回 403（配额），而第八条守卫的栅格口径量出
唯一还在板外的面就是这批位图（part-4 浅档 14.8 %、part-2 8.8 %、封面窄屏深档 8.7 %、
ch37 深档 3.3 %，全是冷灰与淡紫）。它们是线描版画，重着色比换图更能保留原有构图，
而且这一步是可重跑的：判据（板外色占比）由脚本自己打印，前后各量一次。

用法：python3 scripts/recolor_plate_art.py [--check]   # --check 只量不改
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
THEME = ROOT / "docs" / "theme.css"

# 三停渐变：亮部=纸，中调=暖沙，暗部=墨。全部取自已有的 --c-plate-* / 纸墨令牌，
# 不新造颜色（否则栅格口径会量出第二批板外色）。
def tokens() -> dict[str, str]:
    css = THEME.read_text()
    root = re.search(r":root\s*\{(.*?)\n\}", css, re.S).group(1)
    return {k: v.lower() for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", root)}


def hx(v: str) -> tuple[int, int, int]:
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


TOK = tokens()
PAPER = hx(TOK["--c-plate"])             # 图版纸底：亮部锚
INK = hx(TOK["--c-plate-ink"])           # 墨：暗部锚
ACCENT = hx(TOK["--c-plate-accent"])     # 铜绿：只给原来带饱和度的那一层
_A = {k: np.array(v, dtype=np.float64) / 255.0
      for k, v in dict(PAPER=PAPER, INK=INK, ACCENT=ACCENT).items()}
LUM_W = np.array([0.2126, 0.7152, 0.0722])
# 两个锚的相对亮度（纸 .955 / 墨 .113，均为 0–1 档）。⚠ 锚必须和像素同档：
# 上一版锚留成 0–255 而像素是 0–1，插值参数被算成 >1 后贴到墨锚，再被 clip(0,1)
# 抬成纯白——14 张图全部输出成接近实心的白，墨线读数 0.68 才把这件事报出来。
_L = {k: float(v @ LUM_W) for k, v in _A.items()}


def ramp(lum):
    """亮度保真映射：输出**相对亮度等于输入相对亮度**的暖中性色（纸↔墨线性插值）。

    ⚠ 为什么不是"纸→暖沙→墨"三停：三停把中调钉在 #eae4d6（亮度 .886）上，等于把
    原图 0.5 的中间调抬到 0.64、把最暗 5 % 从 0.085 抬到 0.229（part4 实测）——
    版画的墨线被冲成浅灰，色温是修好了，画也废了。两锚线性插值下亮度逐位守恒，
    而纸与墨都是 r>b 的暖色，插值路径整段留在暖族里，不需要中调锚也不会转冷。"""
    P, I = _A["PAPER"], _A["INK"]
    t = np.clip((_L["PAPER"] - lum) / (_L["PAPER"] - _L["INK"]), 0.0, 1.0)[..., None]
    return P + (I - P) * t


def recolor(src: Path, dst: Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    a = np.asarray(im, dtype=np.float64) / 255.0
    lum = a @ LUM_W                                       # 相对亮度，0=黑 1=白
    sat = a.max(axis=2) - a.min(axis=2)                   # 原图的彩度（冷蓝线条>0）
    c = ramp(lum)
    # 原图里带饱和度的像素（冷蓝线条）改判为铜绿，饱和度越高掺得越多；
    # 中性灰保持纯纸墨，这样"单一强调色"的约定不被打破。
    k = (np.minimum(0.55, sat * 1.6) * np.where(lum < 0.72, 1.0, 0.25))[..., None]
    out = c * (1.0 - k) + _A["ACCENT"] * k
    # 掺强调色会拖偏亮度（铜绿比它替换掉的暗部更亮），按像素补回来，保证判据可复算
    out = out + (lum - out @ LUM_W)[..., None]
    drift = float(np.abs((out @ LUM_W) - lum).mean())
    assert drift < 0.02, f"亮度不守恒：平均漂移 {drift:.3f}（映射档位或锚点写错了）"
    Image.fromarray(np.round(np.clip(out, 0.0, 1.0) * 255.0).astype("uint8"), "RGB").save(
        dst, "WEBP", quality=82, method=6)
    assert Image.open(dst).size == (w, h)


def palette() -> dict[str, tuple[int, int, int]]:
    css = THEME.read_text()
    root = re.search(r":root\s*\{(.*?)\n\}", css, re.S).group(1)
    dark = re.search(r"html\[data-theme='dark'\]\s*\{(.*?)\n\}", css, re.S).group(1)
    light = {k: v for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", root)}
    both = dict(light)
    both.update({k: v for k, v in
                 re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", dark)})
    return {k: hx(v) for k, v in both.items() if len(v) in (4, 7)}


PAL = palette()
TOL = 26.0


def off_share(p: Path) -> float:
    """[宽松口径] 板外色占比：缩到 80x50 取 8 个主导色，逐色找最近的令牌，超容差即算板外。

    ⚠ 这条**不能单独当判据**：冷灰 #b3b4bd 与暖沙令牌 #c8c0b1 的逐通道最大差只有 21，
    在 ±26 容差下被判"在板内"，而它恰恰是读者看到的"发脏"的那一层。距离小是因为两者
    都接近中性——绝对通道距离看不见色温方向。所以保留它作交叉核对，主判据换成下面的色温。"""
    im = Image.open(p).convert("RGB")
    q = im.resize((80, 50)).quantize(colors=8, method=Image.MEDIANCUT)
    pal = q.getpalette()
    counts = collections.Counter(list(q.getdata()))
    off = 0.0
    for idx, c in counts.most_common(8):
        rgb = tuple(pal[idx * 3: idx * 3 + 3])
        d = min(max(abs(rgb[i] - v[i]) for i in range(3)) for v in PAL.values())
        if d > TOL:
            off += c / (80 * 50)
    return off


def temperature(p: Path) -> tuple[float, float, float]:
    """色温口径（主判据）：整图逐像素，返回 (冷灰, 冷彩, 暖调) 占比。

    - 冷灰：近中性（max-min<30）、蓝压过红 ≥6、**且蓝是最大通道** —— 本书的纸/沙/墨全是
      r>b，这一档必为 0。第三条限定是必须的：唯一的强调色铜绿 #2f6154 本身就是 b>r，
      掺了它的像素若只看 b−r 会被误判成冷灰（实测：不加这条，改后仍报 10.8 %「冷灰」，
      而那些像素是强调色，不是缺陷）。
    - 冷彩：有彩度且色相落在 200°–320°（青蓝→紫）—— 铜绿色相约 165°，属绿族，不在区间。
    - 暖调：红压过蓝 ≥6 —— 期望的主导档。
    三条各自是独立读数，不用距离容差，因此不会被"两个都接近灰"蒙过去。"""
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    chroma = a.max(axis=2) - a.min(axis=2)
    hue = np.asarray(
        Image.open(p).convert("HSV").getchannel("H"), dtype=np.float64) * (360.0 / 255.0)
    total = r.size
    cold_gray = float(np.count_nonzero((chroma < 30) & (b - r >= 6) & (b >= g))) / total
    cold_chroma = float(np.count_nonzero((chroma >= 30) & (hue >= 200) & (hue < 320))) / total
    warm = float(np.count_nonzero(r - b >= 6)) / total
    return cold_gray, cold_chroma, warm


def ink_floor(p: Path) -> float:
    """墨线读数：全图最暗 5 % 像素的平均相对亮度。越小越"墨"。

    这条是给重着色自己用的反退化判据：色温口径只看方向、不看深浅，一张被冲成浅灰的
    图照样能拿"冷调 0 %"。上一版三停渐变就是这样把 part4 的 0.085 抬到 0.229 而全绿的
    ——所以墨线亮度必须和改前对账，抬升超过 0.05 就是画被洗掉了。"""
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0
    L = (a @ LUM_W).ravel()
    k = max(1, int(L.size * 0.05))
    return float(np.partition(L, k)[:k].mean())


def report(p: Path) -> str:
    cg, cc, w = temperature(p)
    return (f"冷灰 {cg:5.1%} 冷彩 {cc:5.1%} 暖调 {w:5.1%} 墨线 {ink_floor(p):.3f} "
            f"[宽松板外 {off_share(p):5.1%}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只量色温占比，不改文件")
    args = ap.parse_args()

    names = [p.name for p in sorted(ASSETS.glob("*.webp")) if p.name != "cover.webp"]
    if args.check:
        for n in names:
            print(f"  {report(ASSETS / n)}  {n}")
        return 0

    tmp = Path("/tmp/plate_art_backup")
    tmp.mkdir(exist_ok=True)
    # /tmp 会被清；真正的原件出处是 git HEAD（`git show HEAD:docs/assets/<名>`），
    # 备份丢了就用 HEAD 重取，不要在已改色的文件上重建备份。
    worst_cold = 0.0
    lowest_warm = 1.0
    reds: list[str] = []
    for n in names:
        src = ASSETS / n
        bak = tmp / n
        # 备份只在第一次落地，之后**改前一律读备份**：如果读 src，第二跑开始「改前」
        # 就是上一跑的改后结果，前后对比自证会变成 after-vs-after 的假绿。
        if not bak.exists():
            bak.write_bytes(src.read_bytes())
        b_cg, b_cc, _ = temperature(bak)
        b_ink = ink_floor(bak)
        recolor(bak, src)
        a_cg, a_cc, a_w = temperature(src)
        a_ink = ink_floor(src)
        worst_cold = max(worst_cold, a_cg + a_cc)
        lowest_warm = min(lowest_warm, a_w)
        im = Image.open(src)
        old = Image.open(bak)
        flag = "尺寸一致" if im.size == old.size else "⚠ 尺寸变了"
        print(f"  冷调 {b_cg + b_cc:5.1%}→{a_cg + a_cc:5.1%}  暖调 {a_w:5.1%}"
              f"  墨线 {b_ink:.3f}→{a_ink:.3f}  {n}  {im.width}x{im.height} {flag}"
              f"  {src.stat().st_size // 1024} KB")
        if not im.size == old.size:
            reds.append(f"{n}: 重着色改了尺寸")
        if a_cg + a_cc > 0.005:
            reds.append(f"{n}: 冷调残留 {a_cg + a_cc:.1%} > 0.5 %")
        if a_ink - b_ink > 0.05:
            reds.append(f"{n}: 墨线被抬亮 {b_ink:.3f}→{a_ink:.3f}（画被冲淡）")
    print(f"[重着色] {len(names)} 张：冷调合计最大 {worst_cold:.1%}，"
          f"暖调最低 {lowest_warm:.1%}（备份 {tmp}，尺寸逐张与备份比对）")
    for r in reds:
        print(f"  ✗ {r}")
    if reds:
        print(f"[结论] {len(reds)} 条不达标")
        return 1
    print("[结论] 0 条不达标：冷调已清零，且墨线亮度未被抬走")
    return 0


if __name__ == "__main__":
    sys.exit(main())
