from PIL import Image
from pathlib import Path

src = Path("vibe_images")
dst = Path("docs/assets")
dst.mkdir(exist_ok=True)

for p in sorted(src.glob("*.png")):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    # part openers 1536x1024 -> max width 1600 already OK; keep as is
    out = dst / (p.name.split("_")[0] + ".webp")
    im.save(out, "WEBP", quality=82, method=6)
    print(f"{p.name} {w}x{h} -> {out.name} {out.stat().st_size // 1024}KB")
