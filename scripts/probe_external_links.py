#!/usr/bin/env python3
"""外链可达性探针：从全站正文派生枚举，逐条直连，打印可誊进台账的 markdown 表。

为什么要有这一支：`public-evidence.md`「外链可达性台账」早期是一人手抄的链接清单，
抄的那一份会在第一个新链接落地当天少测几条（第十七轮实测：手抄清单 17 条，
从正文派生同一口径量到 89 条）。所以枚举、请求、计数三件事都搬进这条命令，
台账只誊它打印的表，条数不另住一处。

用法：python3 scripts/probe_external_links.py            # 枚举 + 逐条请求 + 打表
      python3 scripts/probe_external_links.py --enumerate-only   # 不开网，只打印枚举结果

退出码：404／410／5xx = 1（这是引用写错了，与读者所在网络无关）；
        仅"网络不可达／超时" = 0，但那几条会单列，不许被读成通过。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import pathlib
import re
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from itertools import zip_longest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FENCE = re.compile(r"^\s{0,3}(```|~~~)")
URL = re.compile(r"https?://[^\s|｜<>\"'`\)\]（）]+[^\s|｜<>\"'`\)\]（）.,;:!?]")
# 正文里的示意地址：nginx / prometheus 配置片段、书稿里的虚构端点，它们不是引用，不测。
SCHEMATIC = re.compile(
    r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|backend|\$entry|prompt\.example\.invalid)"
)
DEAD = {404, 410}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def enumerate_urls() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in sorted(DOCS.rglob("*.md")):
        rel = str(path.relative_to(DOCS))
        in_fence = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for url in URL.findall(line):
                out.setdefault(url, set()).add(rel)
    return out


def fetch(url: str, timeout: int) -> tuple[int | None, str]:
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, url
    except Exception as exc:  # 网络失败要照实分类，不许被读成通过
        return None, f"{type(exc).__name__}: {str(exc)[:40]}"


def probe(url: str) -> dict:
    status, info = fetch(url, 15)
    if status is not None:
        return {"url": url, "status": status, "final": info, "first": "", "retry": ""}
    first = info
    status2, info2 = fetch(url, 30)
    return {"url": url, "status": status2, "final": info2 if status2 is not None else "", "first": first, "retry": info2}


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enumerate-only", action="store_true", help="只枚举，不发请求")
    args = parser.parse_args()

    urls = enumerate_urls()
    schematic = sorted(u for u in urls if SCHEMATIC.match(u))
    tested = sorted(u for u in urls if not SCHEMATIC.match(u))
    print(f"[枚举] docs/**/*.md 围栏外去重 URL {len(urls)} 条："
          f"内网／示意 {len(schematic)} 条不测，实测 {len(tested)} 条")
    for u in schematic:
        print(f"  [未测·示意] {u}")
    if args.enumerate_only:
        return 0

    # 按主机轮转排队，不按 URL 字典序：字典序会把同域地址排成相邻的一串，
    # 并发 6 就在同一瞬间全打在同一个主机上——这等于探针自己制造限流（本轮实测过）。
    by_host: dict[str, list[str]] = {}
    for u in tested:
        by_host.setdefault(urlsplit(u).netloc, []).append(u)
    queue = [u for group in zip_longest(*by_host.values()) for u in group if u]
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        results = list(pool.map(probe, queue))

    ok200 = [r for r in results if r["status"] == 200]
    dead = [r for r in results if r["status"] in DEAD or (r["status"] or 0) >= 500]
    unreachable = [r for r in results if r["status"] is None]
    other = [r for r in results if r["status"] not in (200, None) and r not in dead]
    moved = [r for r in ok200 if r["final"] and r["final"] != r["url"]]
    recovered = [r for r in ok200 if r["first"]]

    print()
    print("| 链接 | 状态 | 最终地址（与左列不同时才填） | 出现在 |")
    print("|---|---|---|---|")
    for r in sorted(results, key=lambda x: x["url"]):
        state = str(r["status"])
        if r["status"] is None:
            state = f"不可达（首跑 {r['first']}；重跑 {r['retry']}）"
        elif r["status"] != 200:
            state = f"{r['status']}"
        target = r["final"] if r["final"] and r["final"] != r["url"] else ""
        where = "、".join(sorted(urls[r["url"]]))
        print(f"| {cell(r['url'])} | {cell(state)} | {cell(target)} | {cell(where)} |")

    print()
    print(f"[读数] 实测 {len(results)} 条：200 = {len(ok200)}；死链(404/410/5xx) = {len(dead)}；"
          f"其他非 200 = {len(other)}；本机不可达 = {len(unreachable)}；"
          f"200 但经重定向 = {len(moved)}；首跑超时、重跑才回 200 = {len(recovered)}")
    for r in dead:
        print(f"  [死链] {r['url']} → {r['status']}")
    for r in other:
        print(f"  [非200] {r['url']} → {r['status']}")
    for r in unreachable:
        print(f"  [本机不可达] {r['url']} → 首跑 {r['first']} ／ 重跑 {r['retry']}")
    for r in moved:
        print(f"  [重定向] {r['url']} → {r['final']}")
    return 1 if dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
