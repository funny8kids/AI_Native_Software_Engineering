"""把卷首艺术图的 PNG 原件压成站内用的 webp。

原件目录 vibe_images/ 刻意不进版本库（16MB），所以**这台机器之外跑不动这个脚本**——
它一旦找不到原件就必须响亮地失败，而不是 glob 到空集合后"成功"退出 0：
那会让下一次同步以为重压过了，实际上一张都没动。
"""
from PIL import Image
from pathlib import Path
import sys

src = Path("vibe_images")
dst = Path("docs/assets")

if not src.is_dir():
    sys.exit(f"中止：原件目录 {src}/ 不存在（它不入库，只在生成那台机器上）——"
             f"没有原件就没有可压的东西，退出非 0 而不是空跑成功")
pngs = sorted(src.glob("*.png"))
if not pngs:
    sys.exit(f"中止：{src}/ 里一张 PNG 也没有——空输入不等于成功")

dst.mkdir(exist_ok=True)

for p in pngs:
    im = Image.open(p).convert("RGB")
    w, h = im.size
    # part openers 1536x1024 -> max width 1600 already OK; keep as is
    out = dst / (p.name.split("_")[0] + ".webp")
    im.save(out, "WEBP", quality=82, method=6)
    print(f"{p.name} {w}x{h} -> {out.name} {out.stat().st_size // 1024}KB")
