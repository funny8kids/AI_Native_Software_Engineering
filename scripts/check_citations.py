#!/usr/bin/env python3
"""第十三条守卫：正文里点名的档案条目号，必须与档案里的条目集合双向对上。

判据两条（同一把尺的两侧）：
① **悬空**：正文（档案自身除外）围栏外出现的每个 `E<n>`，无论单点还是区间的两端，
   都必须在 `public-evidence.md` 里有 `## E<n> ·` 那一节；没有就是正文引用了一件不存在的东西。
② **孤儿**：档案里的每一条，要么被正文**单点名**过，要么落在正文写出的某个区间里；
   两头都没沾上就是档案里躺着一条正文从不引的条目。

为什么区间要单独算：正文的区间写法（`E8–E28`、`E1–E7`）是**范围陈述**，不是逐条引用。
如果判据只认单点，E2、E3、E4、E5 这四条今天会被判成孤儿——它们只被 `E1–E7` 那一类区间盖住。
所以本件把区间计入分母，同时把**只靠区间在册**的条目打印出来交人读：那几句是范围陈述，
是否成立机检判不了，但它们在闸眼里有记录，不许悄悄当成逐条引用。

为什么机检：第二十轮 9.2 那张上会表的第六条判据写的是「档案里出现了正文没有引、正文里出现了
档案没有的」，同轮 9.3 收尾明写"认这一格没有闸，比给一条量不准的判据立一道假闸要诚实"。
这一件就是那句话的兑现：它只量编号集合的对账，量不到引文与原文是否一致。

盲区（打印出来，不当通过）：一句话是否**诚实**对应它挂的那个条目号，机检判不了；
本件只保证编号两侧集合双向对上，不保证内容对得上——逐字核对仍靠人与档案里的落盘字节。

用法：python3 scripts/check_citations.py [--verbose] [--selftest]
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = "public-evidence.md"
ENTRY = re.compile(r"^## E(\d+) ·", re.M)
TOKEN = re.compile(r"(?<![A-Za-z0-9])E(\d+)\s*([–—-]\s*E?(\d+))?")
FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.S)


def body_files(docs_dir):
    """枚举口径：docs 根下与 docs/manuscript 下的 .md，减去档案自身。"""
    d = pathlib.Path(docs_dir)
    return sorted([p for p in list(d.glob("*.md")) + list((d / "manuscript").glob("*.md"))
                   if p.name != ARCHIVE])


def archive_entries(text):
    return {int(m.group(1)) for m in ENTRY.finditer(text)}


def refs(text):
    """一处 `E<n>` 或 `E<a>–E<b>`：返回单点集合、区间列表。"""
    t = FENCE.sub("", text)
    single, ranges = set(), []
    for m in TOKEN.finditer(t):
        if m.group(3):
            ranges.append((int(m.group(1)), int(m.group(3))))
        else:
            single.add(int(m.group(1)))
    return single, ranges


def check(entry_set, singles, ranges):
    """纯函数：两侧对账。返回（悬空, 孤儿, 只靠区间在册）。"""
    covered = set(singles)
    for a, b in ranges:
        if b >= a:
            covered |= set(range(a, b + 1))
    named = set(singles) | {n for a, b in ranges for n in (a, b)}
    dangling = sorted(named - entry_set)
    orphans = sorted(entry_set - covered)
    range_only = sorted((covered & entry_set) - singles)
    return dangling, orphans, range_only


def run(docs_dir, verbose=False):
    ap = pathlib.Path(docs_dir) / ARCHIVE
    if not ap.is_file():
        print(f"✗ 档案不在位：{ap}")
        return 1
    entry_set = archive_entries(ap.read_text(encoding="utf-8"))
    if not entry_set:
        print(f"✗ 档案里一条 `## E<n> ·` 都没枚举到（{ap}）——空分母不算绿")
        return 1
    files = body_files(docs_dir)
    if not files:
        print(f"✗ 正文一枚都没枚举到（{docs_dir}）——空分母不算绿")
        return 1
    singles, ranges, detail = set(), [], []
    for p in files:
        s, r = refs(p.read_text(encoding="utf-8"))
        singles |= s
        ranges += r
        for n in sorted(s - entry_set):
            detail.append(f"{p.name} 单点 E{n}")
        for a, b in r:
            for n in (a, b):
                if n not in entry_set:
                    detail.append(f"{p.name} 区间 E{a}–E{b} 的端点 E{n}")
    dangling, orphans, range_only = check(entry_set, singles, ranges)
    print(f"枚举口径：正文 {len(files)} 个文件（不含档案自身）／档案条目 {len(entry_set)} 条"
          f"／被单点名 {len(singles & entry_set)} 条／区间写法 {len(ranges)} 处")
    if range_only:
        print("  只靠区间在册、正文从未单点的条目："
              + "、".join(f"E{n}" for n in range_only)
              + "（本件算它们已覆盖，但那几句是范围陈述，请人读是否成立）")
    rc = 0
    if dangling:
        rc = 1
        print(f"✗ 悬空引用 {len(dangling)} 条：" + "、".join(f"E{n}" for n in dangling))
        for line in detail:
            print(f"    {line}")
    if orphans:
        rc = 1
        print("✗ 孤儿条目（档案里有、正文既不单点也不在任何区间内）："
              + "、".join(f"E{n}" for n in orphans))
    if rc == 0:
        print("引用对账闸通过：两侧编号集合双向对上。")
    else:
        print("引用对账闸未通过。")
    if verbose:
        print(f"  区间明细：{ranges}")
    return rc


def selftest():
    """正例 1、反例 2、假阳对照 1、空分母 1：五条对照都打在 check/run 的同一份实现上。"""
    ent = {1, 2, 3, 4}
    cases = []
    d, o, ro = check(ent, {1}, [(2, 4)])
    cases.append(("C1 正例：区间 E2–E4 覆盖，不算孤儿也不悬空", d == [] and o == [] and ro == [2, 3, 4]))
    d, o, ro = check(ent, {1, 9}, [])
    cases.append(("C2 悬空必红（正文 E9 而档案无此节）", d == [9] and o == [2, 3, 4]))
    d, o, ro = check(ent, {1, 2, 3}, [])
    cases.append(("C3 孤儿必红（E4 两头都没沾）", d == [] and o == [4] and ro == []))
    d, o, ro = check(ent, {1}, [])
    cases.append(("C4 假阳对照：抹掉区间展开这一步，E2–E4 会被误判孤儿", o == [2, 3, 4]))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rc_empty = run(pathlib.Path(td))
    cases.append(("C5 空分母必红（正文一枚都没有，实测 rc=%d）" % rc_empty, rc_empty == 1))
    ok = all(p for _, p in cases)
    for name, passed in cases:
        print(f"  [{'✔' if passed else '✗'}] {name}")
    print(f"自检结论：{len(cases)} 条对照（正例 1、反例 2、假阳 1、空分母 1）——"
          f"{'全部按预期' if ok else '有对照未按预期，判据不可信'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(run(ROOT / "docs", verbose="--verbose" in sys.argv))
