#!/usr/bin/env python3
"""加粗邻接静态预扫：把 marked 会拒绝落地的 ** span 找出来。

危险形状：开侧紧跟 ASCII 引号/百分号/空白/反引号；闭侧紧跟 ASCII 标点或反引号或空白。
本件是预扫不是闸：它有假阳（对 ch27 报过一处 HEAD 上早已活着、第九条守卫每轮判绿的句子），
所以口径是"只指路、不当闸"——真正量这一族的是 scripts/check_render_leaks.py（浏览器实跑）。

不传参数时**自己从仓库派生文件全集**（`docs/**/*.md` ＋ 根目录 `*.md`，与第三条守卫同一口径）。
这一条是第十七轮补的：在那之前不带参数的这一跑会枚举到 0 个文件，然后照样打印"无可疑形状"——
零对象的通过读数比没有读数更坏，它会被读成"扫过了"。现在枚举为空直接退出 1。
"""
import pathlib
import re
import sys

RISKY = set("\"'`%$&*+,.:;!=?/\\|<>~ ")  # ASCII 标点集合（中文标点不算）


def scan(path):
    bad = []
    for no, ln in enumerate(open(path, encoding="utf-8"), 1):
        if ln.startswith("```"):
            continue
        for m in re.finditer(r"\*\*(.+?)\*\*", ln):
            body = m.group(1)
            if not body:
                bad.append((no, "空加粗", ln.strip()[:80]))
                continue
            first, last = body[0], body[-1]
            if first.isspace() or (ord(first) < 128 and first in RISKY):
                bad.append((no, f"开侧危险字符 {first!r}", body[:60]))
            if last.isspace() or (ord(last) < 128 and last in RISKY):
                bad.append((no, f"闭侧危险字符 {last!r}", body[-60:]))
            if ln[m.end():m.end() + 2].startswith("**"):
                bad.append((no, "四个星号连成一串", ln[max(0, m.start() - 10):m.end() + 10]))
        if ln.count("**") % 2:
            bad.append((no, "本行 ** 个数为奇数", ln.strip()[:80]))
    return bad


def derive_files(paths):
    """不带参数 = 量全集，不是量空集。全集口径与 scripts/check_markdown.py 的 files() 一致。"""
    if paths:
        return [str(pathlib.Path(x)) for x in paths]
    root = pathlib.Path(__file__).resolve().parent.parent
    return [str(x) for x in sorted((root / "docs").rglob("*.md")) + sorted(root.glob("*.md"))]


def main(paths):
    rc = 0
    targets = derive_files(paths)
    if not targets:
        print("加粗邻接预扫：一个 .md 都没枚举到——这是没扫，不是扫过")
        return 1
    print(f"[覆盖] 本次预扫 {len(targets)} 个 .md 文件")
    for p in targets:
        for no, why, snip in scan(p):
            print(f"  {p.split('/')[-1]}:{no}  {why}  「{snip}」")
            rc = 1
    print("加粗邻接预扫（只指路、不当闸）：", "有可疑形状" if rc else "无可疑形状")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
