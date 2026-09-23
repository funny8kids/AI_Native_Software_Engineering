#!/usr/bin/env python3
"""死链守卫：把 docs 里每一条本地引用换成真实 HTTP 请求。

用法：
    python3 -m http.server 8080 --directory docs &     # 或任意端口
    python3 scripts/check_links.py [--base http://127.0.0.1:8080]

解析口径：
- Markdown 链接/图片、HTML 的 href/src、Docsify 的 /manuscript/x.md 根相对路径。
- 锚点（#…）只校验宿主文件存在；外链（http/https/mailto）交 public-evidence.md 的可达性台账。
- 尖括号包裹的链接与 `<>` 路由（九部分卷首）同样解析。
"""
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

MD_LINK = re.compile(r"!\[[^\]]*\]\((<?[^)\s]+>?)\)|\[([^\]]*)\]\((<?[^)\s]+>?)\)")
HTML_ATTR = re.compile(r"(?:href|src)\s*=\s*[\"']([^\"']+)[\"']", re.I)


def targets(text):
    out = []
    for m in MD_LINK.finditer(text):
        out.append((m.group(1) or m.group(3)).strip())
    out += [m.strip() for m in HTML_ATTR.findall(text)]
    return out


def normalize(raw):
    raw = raw.strip().strip("<>").split(" ")[0]
    if raw.startswith(("http://", "https://", "mailto:", "data:", "#", "?")) or raw.startswith("?id="):
        return None  # 纯查询串（如导航栏搜索入口 ?q=）交给浏览器语义，不当文件校验
    path, _, _frag = raw.partition("#")
    path = path.split("?")[0]
    path = urllib.parse.unquote(path)
    if not path:
        return None
    return path


def resolve(path, base_dir):
    if path.startswith("/"):
        return DOCS / path.lstrip("/")
    return (base_dir / path).resolve()


def main():
    base = "http://127.0.0.1:8080"
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    bad, checked = [], set()
    for f in sorted(DOCS.rglob("*")):
        if f.suffix not in (".md", ".html") or not f.is_file():
            continue
        for raw in targets(f.read_text()):
            path = normalize(raw)
            if path is None:
                continue
            target = resolve(path, f.parent if f.suffix == ".md" else DOCS)
            try:
                rel = target.relative_to(DOCS)
            except ValueError:
                bad.append((f.name, raw, "跳出 docs/ 目录"))
                continue
            url = base + "/" + urllib.parse.quote(str(rel).replace("\\", "/"))
            if url in checked:
                continue
            checked.add(url)
            try:
                code = urllib.request.urlopen(url, timeout=10).getcode()
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception as e:  # noqa: BLE001
                bad.append((f.name, raw, f"请求失败 {type(e).__name__}"))
                continue
            if code != 200:
                bad.append((f.name, raw, f"HTTP {code}"))
    print(f"本地引用去重后 {len(checked)} 条 URL。")
    if bad:
        print("死链：")
        for src, link, why in bad:
            print(f" - {src} -> {link} ({why})")
        return 1
    print("死链 = 0。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
