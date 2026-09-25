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
FENCE = re.compile(r"^(`{3,}|~{3,})")
ICODE = re.compile(r"(`+)(?!`).+?\1(?!`)")


def visible_markdown(text):
    """只留 Docsify 真的会渲染成链接的那些行。

    代码块与行内代码里的 `[x](y.md)` / `href="y"` 是示例正文，渲染成字面量而不是链接；
    把它们当引用校验，等于逼作者别在书里写示例（实测两处假死链都出自示例）。
    闭合口径与第三条守卫一致：同种字符、长度不短于开栏、行尾无内容。
    """
    keep, fence = [], None
    for line in text.splitlines():
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            keep.append(line)
        else:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                    and line.rstrip() == m.group(0):
                fence = None
    if fence is not None:
        raise SystemExit("围栏未闭合——第三条守卫管的事，这里不重复判，但拒绝在半途读数上下结论")
    return "\n".join(ICODE.sub("", ln) for ln in keep)


def targets(text, markdown=True):
    if markdown:
        text = visible_markdown(text)
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


def selftest():
    """排除集的两种死法都要红：把示例当链接（过窄），把正文链接也放掉（过宽）。"""
    fails = []
    in_fence = "正文。\n\n```python\nlink = '[a](./nope.md)'\nx = '<link href=\"nope.css\">'\n```\n"
    in_icode = "示例草稿正文：`模板在 [附录 D](./nope.md)`，其余是话。\n"
    prose = "真引用：[第 9 章](./ch14-第9章-契约先行.md)。\n"
    wide = "正文里还有 [坏链](./does-not-exist.md)。\n"
    for name, txt, want in (("代码块内不计", in_fence, []),
                            ("行内代码内不计", in_icode, []),
                            ("正文链接要计", prose, ["./ch14-第9章-契约先行.md"]),
                            ("正文坏链要计", wide, ["./does-not-exist.md"])):
        got = targets(txt)
        if got != want:
            fails.append(f"{name}：期望 {want}，实测 {got}")
    # 嵌套围栏：四反引号包住三反引号示例，只有外层闭合才算出块
    nested = "````markdown\n```python\nf = '[b](./nope.md)'\n```\n````\n之后 [c](./ok.md)\n"
    if targets(nested) != ["./ok.md"]:
        fails.append(f"嵌套围栏：期望 ['./ok.md']，实测 {targets(nested)}")
    # 未闭合围栏必须拒绝读数，不能悄悄把后半篇当代码块豁免掉
    try:
        visible_markdown("```python\nf = 1\n[a](./b.md)\n")
        fails.append("未闭合围栏：应当拒绝执行，却返回了读数")
    except SystemExit:
        pass
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        print(f"死链守卫自检未通过：{len(fails)} 条")
        return 1
    print("死链守卫自检通过：排除集两侧（示例不计 / 正文要计）+ 嵌套闭合 + 未闭合拒读。")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    base = "http://127.0.0.1:8080"
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    bad, checked = [], set()
    for f in sorted(DOCS.rglob("*")):
        if f.suffix not in (".md", ".html") or not f.is_file():
            continue
        for raw in targets(f.read_text(), f.suffix == ".md"):
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
