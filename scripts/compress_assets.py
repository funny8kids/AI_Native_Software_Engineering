from PIL import Image
from pathlib import Path

root = Path("docs/assets")
for p in root.glob("*.png"):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    max_w = 1600
    if w > max_w:
        nh = int(h * max_w / w)
        im = im.resize((max_w, nh), Image.Resampling.LANCZOS)
    out = p.with_suffix(".webp")
    im.save(out, "WEBP", quality=82, method=6)
    print(f"{p.name}: {w}x{h} -> {out.name} {out.stat().st_size // 1024}KB")

# remove heavy PNGs after successful webp
for p in root.glob("*.png"):
    webp = p.with_suffix(".webp")
    if webp.exists() and webp.stat().st_size > 1000:
        p.unlink()
        print(f"removed {p.name}")
