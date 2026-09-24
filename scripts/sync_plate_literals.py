#!/usr/bin/env python3
"""把 theme.css 的图版令牌值同步进两类「按字面值复制」的下游：书稿 mermaid 指令行、index.html 兜底表。

为什么要有这个执行者：2026-09-25 提亮轮改了 10 个 `--c-plate*`，第八条守卫当场把
160 条指令行 / 480 个字面颜色报成板外色，而**修它的那条命令当时不存在**——那一次是
临时写的一段一次性代码。守卫只判「字面值 ≠ 令牌值」，判不了「谁来把它对齐」；
没有稳定的执行者，下一次令牌移动仍然会退化成手改 160 行（手改一定会漏，漏了就有人
去放宽判据）。所以这条脚本是判据的执行者：它自己也是守卫，只在能自证干净时才落盘。

口径与 check_palette.py 完全一致（同一份 MERMAID_DIR / DIR_COLOR / FALLBACK_BLOCK），
否则会出现"脚本说同步好了、守卫仍然报红"的第二套真相。

用法：
    python3 scripts/sync_plate_literals.py --check   # 只量漂移，不写
    python3 scripts/sync_plate_literals.py           # 落盘（写完自动复量一次）
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
THEME = DOCS / "theme.css"
INDEX = DOCS / "index.html"

# 与守卫同源：从 check_palette 直接 import，不复制正则（复制＝两份口径会分叉）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_palette import DIR_COLOR, FALLBACK_BLOCK, MERMAID_DIR, parse_tokens  # noqa: E402


def git_head_theme() -> str:
    r = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:docs/theme.css"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"取不到 HEAD 的 theme.css（{r.stderr.strip()}）——"
                         "旧值表是这条脚本的唯一映射依据，没有它不能同步")
    return r.stdout


def md_drift(old: dict[str, str], new: dict[str, str]) -> tuple[list[tuple[Path, int, str, str]], int]:
    """返回 (待改的 [(文件, 行号, 旧字面值, 新字面值)], 数到的颜色指令总数)。

    映射按**旧值表**做：字面值必须先在 HEAD 的令牌里找到一个出处，才谈得上"它跟着哪个令牌动"。
    旧值表里找不到 ⇒ 这条指令早就飘在板外，交回守卫报错，不由本脚本猜。
    多个令牌共享同一旧值且它们的新值彼此不同 ⇒ 歧义，必须中止而不是挑一个（`--c-plate-ink`
    与 `--c-plate-black` 今天就同为 #1e1c19；一旦哪天它们分道，这里必须喊出来）。
    """
    by_value: dict[str, set[str]] = {}
    for k, v in old.items():
        if k.startswith("--c-plate"):
            by_value.setdefault(v.strip().lower(), set()).add(k)
    todo: list[tuple[Path, int, str, str]] = []
    seen = 0
    for f in sorted(DOCS.rglob("*.md")):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if not MERMAID_DIR.match(line):
                continue
            for _prop, hexv in DIR_COLOR.findall(line):
                seen += 1
                v = hexv.lower()
                keys = by_value.get(v)
                if not keys:
                    continue
                nxt = {new.get(k, "").strip().lower() for k in keys}
                nxt.discard("")
                if len(nxt) != 1:
                    raise SystemExit(f"{f.relative_to(DOCS)}:{i} 的字面值 {v} 对应 {sorted(keys)}，"
                                     f"它们的新值 {sorted(nxt)} 不止一个——映射有歧义，本脚本不猜，"
                                     "请先在书稿里把这两档分开")
                (rep,) = nxt
                if rep != v:
                    todo.append((f, i, v, rep))
    return todo, seen


def fallback_drift(new: dict[str, str]) -> tuple[list[tuple[str, str, str]], int, int]:
    """兜底表按**令牌名**对齐（名是唯一键，不需要旧值表）。返回 ([(名, 表里值, 令牌值)], 读取数, 项数)。"""
    m = FALLBACK_BLOCK.search(INDEX.read_text())
    if not m:
        raise SystemExit("index.html 里找不到 AINSE_FIG_FALLBACK 兜底表——口径可疑，中止")
    table = dict(re.findall(r"'(--c-[\w-]+)'\s*:\s*'([^']+)'", m.group(1)))
    todo = [(name, val.strip().lower(), new[name].strip().lower())
            for name, val in table.items()
            if name in new and new[name].strip().lower() != val.strip().lower()]
    return todo, len(table), len(m.group(1))


def rewrite_md(todo: list[tuple[Path, int, str, str]]) -> int:
    """按 (文件, 行号) 精确替换该行内出现的旧字面值；落盘前自证「除这些行外一行未动」。"""
    by_file: dict[Path, dict[int, list[tuple[str, str]]]] = {}
    for f, i, old, new in todo:
        by_file.setdefault(f, {}).setdefault(i, []).append((old, new))
    changed = 0
    for f, rows in by_file.items():
        before = f.read_text().splitlines(keepends=True)
        after = list(before)
        for i, pairs in rows.items():
            line = after[i - 1]
            for old, new in pairs:
                # 书稿里的字面值是小写；大写写法也接（守卫两边都判小写）
                for pat, rep in ((old, new), (old.upper(), new.upper())):
                    if pat in line:
                        line = line.replace(pat, rep)
                        break
                else:
                    raise SystemExit(f"{f.relative_to(DOCS)}:{i} 声称含 {old} 但替换时找不到——行号已过期")
            after[i - 1] = line
        diff = [n for n, (a, b) in enumerate(zip(before, after), 1) if a != b]
        if sorted(diff) != sorted(rows):
            raise SystemExit(f"{f.relative_to(DOCS)} 实际改了 {len(diff)} 行，映射只有 {len(rows)} 行"
                             "——替换越界，已放弃写入该文件")
        f.write_text("".join(after))
        changed += len(diff)
    return changed


def rewrite_fallback(todo: list[tuple[str, str, str]]) -> int:
    text = INDEX.read_text()
    n = 0
    for name, old, new in todo:
        for a, b in ((f"'{name}': '{old}'", f"'{name}': '{new}'"),
                     (f"'{name}': '{old.upper()}'", f"'{name}': '{new.upper()}'")):
            if a in text:
                text = text.replace(a, b)
                n += 1
                break
        else:
            raise SystemExit(f"兜底表里 {name} 的值 {old} 替换时找不到——表的面与读取口径不一致")
    INDEX.write_text(text)
    return n


def anchor_note(new: dict[str, str]) -> str:
    """位图锚点动没动？动了就必须再跑 recolor_plate_art.py，否则第八条的锚点回执判据会报红。"""
    led = DOCS / "assets" / "plate-art-anchor.json"
    if not led.is_file():
        return "没有锚点回执（第一次跑 recolor_plate_art.py 会写）"
    import json
    rec = json.loads(led.read_text()).get("anchors", {})
    moved = [k for k, v in rec.items() if k in new and new[k].strip().lower() != v.strip().lower()]
    return ("锚点未动，位图无需重跑" if not moved else
            "⚠ 锚点已动 " + " ".join(f"{k}:{rec[k]}→{new[k]}" for k in moved) +
            " —— 必须再跑 python3 scripts/recolor_plate_art.py")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报漂移，不写文件")
    args = ap.parse_args()

    old_light, _ = parse_tokens(git_head_theme())
    new_light, _ = parse_tokens(THEME.read_text())
    md_todo, seen = md_drift(old_light, new_light)
    fb_todo, entries, _ = fallback_drift(new_light)
    moved = [k for k in new_light if old_light.get(k, "").lower() != new_light[k].lower()
             and k.startswith("--c-plate")]
    print(f"[映射] HEAD→工作树：--c-plate* 令牌移动 {len(moved)} 个；"
          f"颜色指令总数 {seen}；兜底表 {entries} 项")
    print(f"[漂移] 书稿指令行待对齐 {len(md_todo)} 行 / 兜底表待对齐 {len(fb_todo)} 项；{anchor_note(new_light)}")
    if not md_todo and not fb_todo:
        print("[结论] 0 处漂移：字面值已与令牌相等（重复跑本脚本必须落在这条上）")
        return 0
    if args.check:
        files = sorted({f.relative_to(DOCS).as_posix() for f, *_ in md_todo})
        print(f"[结论] {len(md_todo) + len(fb_todo)} 处漂移，分布在 {len(files)} 个文件"
              f"（前 6 个：{files[:6]}）—— 去掉 --check 才会落盘")
        return 1
    n_md = rewrite_md(md_todo)
    n_fb = rewrite_fallback(fb_todo)
    print(f"[落盘] 书稿改写 {n_md} 行 / 兜底表改写 {n_fb} 项")
    # 落盘后立刻用同一口径复量：不复量等于"写完就说好了"
    again_md, _ = md_drift(old_light, new_light)
    again_fb, _, _ = fallback_drift(new_light)
    if again_md or again_fb:
        print(f"[结论] ✗ 落盘后仍剩 书稿 {len(again_md)} 行 / 兜底 {len(again_fb)} 项——替换没走完，别提交")
        return 1
    print("[复量] 落盘后 0 处漂移")
    print(f"[结论] 同步完成；{anchor_note(new_light)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
