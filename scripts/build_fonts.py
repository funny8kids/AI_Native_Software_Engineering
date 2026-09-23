"""Build self-hosted subset woff2 fonts from local Noto CJK TTCs.

Collects the union of all characters actually used by the site (markdown,
html chrome) and subsets Noto Serif/Sans CJK SC Regular+Bold to woff2.
Zero-CDN: output lands in docs/vendor/fonts/ and is referenced by theme.css.

Run from repo root:  python3 scripts/build_fonts.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "vendor" / "fonts"
FONTS = Path("/usr/share/fonts/opentype/noto")

# CJK punctuation + symbols always kept (UI chrome, captions, quotes)
SAFETY = (
    "，。、；：？！「」『』（）《》〈〉【】〔〕—…·～￥％"
    "‘’“”・ー々℃℉①②③④⑤⑥⑦⑧⑨⑩⑪⑫Ⓐ→←↑↓↔⇒✓✗□■△▲○●◎◇◆"
    "＋－×÷＝≠＜＞≤≥±∓∈∋⊂⊃∪∩∧∨¬∀∃∴∵"
)
ASCII = "".join(chr(c) for c in range(0x20, 0x7F))


def collect_charset() -> str:
    chars = set(ASCII) | set(SAFETY)
    for pattern in ("**/*.md", "*.html"):
        for p in DOCS.glob(pattern):
            if p.is_file():
                chars |= set(p.read_text(encoding="utf-8", errors="ignore"))
    return "".join(sorted(chars))


def build(src: Path, face_index: int, out_name: str, text: str) -> None:
    import subprocess
    import sys

    tmp = OUT / "charset.txt"
    tmp.write_text(text, encoding="utf-8")
    out = OUT / out_name
    cmd = [
        sys.executable, "-m", "fontTools.subset",
        str(src),
        f"--font-number={face_index}",
        f"--text-file={tmp}",
        f"--output-file={out}",
        "--flavor=woff2",
        "--no-hinting",
        "--desubroutinize",
        "--drop-tables+=GSUB,GPOS",
        "--name-IDs=1,2",
    ]
    subprocess.run(cmd, check=True)
    size = out.stat().st_size
    print(f"{out_name}: {size/1024:.0f} KB")
    tmp.unlink()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    charset = collect_charset()
    print(f"charset: {len(charset)} unique chars")
    builds = [
        (FONTS / "NotoSerifCJK-Regular.ttc", 2, "noto-serif-sc-400.woff2"),
        (FONTS / "NotoSerifCJK-Bold.ttc", 2, "noto-serif-sc-700.woff2"),
        (FONTS / "NotoSansCJK-Regular.ttc", 2, "noto-sans-sc-400.woff2"),
        (FONTS / "NotoSansCJK-Bold.ttc", 2, "noto-sans-sc-700.woff2"),
    ]
    for src, idx, name in builds:
        build(src, idx, name, charset)
    print("done")


if __name__ == "__main__":
    main()
