#!/usr/bin/env python3
"""第四条守卫：整屏遮罩闸。

管的缺陷类别——某个 position:fixed + 占满视口 + 高 z-index 的元素在"不该在场"的
状态下仍参与命中测试，于是页面看得见、点击全部落空。2026-09-24 的封面事故就是它：
Docsify 收起封面只摘掉 show 类、节点留在 DOM 里，而 theme.css 无条件写了
display:flex !important，实测 5/5 采样点命中 .cover。

查的是 CSS 层叠语义，不是字符串在不在：
  1. 枚举 CSS 里所有"占满视口的 fixed 高 z-index 遮罩"规则；
  2. 每个遮罩必须存在一条**同元素、带状态限定**的隐藏规则
     （display:none / visibility:hidden / pointer-events:none）；
  3. 隐藏规则要在层叠里真的赢过基础规则（!important 与特异性都参与比较），否则等于没写。

用法：python3 scripts/check_overlays.py [--css docs/theme.css]
"""

import re
import sys
from pathlib import Path

REQUIRED_MIN_Z = 100
VIEWPORT_W = 1280.0
VIEWPORT_H = 900.0

RULE_RE = re.compile(r'([^{}]+)\{([^{}]*)\}', re.S)
ID_RE = re.compile(r'#[\w-]+')
CLS_RE = re.compile(r'\.[\w-]+|\[[^\]]+\]|::?[\w-]+(?:\([^)]*\))?')
TAG_RE = re.compile(r'(?:^|[\s>+~])([a-zA-Z][\w-]*)')
NOT_RE = re.compile(r':not\(([^)]*)\)')
HAS_RE = re.compile(r':has\(([^)]*)\)')

HIDE_PROPS = {
    'display': lambda v: v.strip() == 'none',
    'visibility': lambda v: v.strip() == 'hidden',
    'pointer-events': lambda v: v.strip() == 'none',
}


def parse(css: str):
    """[(selector, [(prop, value, important), ...])]；按 ';' 切声明，不按行。"""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    rules = []
    for m in RULE_RE.finditer(css):
        sel = m.group(1).strip()
        if sel.startswith('@'):
            continue
        decls = []
        for chunk in m.group(2).split(';'):
            if ':' not in chunk:
                continue
            prop, _, val = chunk.partition(':')
            prop, val = prop.strip().lower(), val.strip()
            important = val.endswith('!important')
            if important:
                val = val[: -len('!important')].strip()
            if prop and val:
                decls.append((prop, val, important))
        if decls:
            rules.append((sel, decls))
    return rules


def specificity(selector: str):
    core = HAS_RE.sub('', selector)
    core = NOT_RE.sub(r'\1', core)
    core = re.sub(r'\[[^\]]*\]', '', core)
    a = len(ID_RE.findall(core))
    b = len(CLS_RE.findall(core))
    c = len(TAG_RE.findall(re.sub(r'::?[\w-]+(?:\([^)]*\))?', '', core)))
    return (a, b, c)


def to_px(value: str):
    m = re.match(r'^(-?[\d.]+)(px|vw|vh|%)$', value.strip())
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2)
    return n if unit == 'px' else n * VIEWPORT_W / 100 if unit == 'vw' else n * VIEWPORT_H / 100


def get(decls, prop):
    for p, v, imp in decls:
        if p == prop:
            return v, imp
    return None, False


def is_overlay(decls):
    if get(decls, 'position')[0] != 'fixed':
        return False
    z, _ = get(decls, 'z-index')
    if not z or not re.match(r'^\d+$', z.strip()) or int(z) < REQUIRED_MIN_Z:
        return False
    if get(decls, 'inset')[0] == '0':
        return True
    spans_w = (get(decls, 'left')[0] == '0' and get(decls, 'right')[0] == '0'
               or (to_px(get(decls, 'width')[0] or '') or 0) >= VIEWPORT_W * 0.99)
    min_h = to_px(get(decls, 'min-height')[0] or '') or 0
    h = to_px(get(decls, 'height')[0] or '') or 0
    spans_h = (get(decls, 'top')[0] == '0' and get(decls, 'bottom')[0] == '0'
               or min_h >= VIEWPORT_H * 0.99 or h >= VIEWPORT_H * 0.99)
    return spans_w and spans_h


def signature(selector: str):
    """剥掉状态限定后的元素签名（标签集 + 类集）。"""
    core = HAS_RE.sub('', selector)
    core = NOT_RE.sub('', core)
    core = re.sub(r'\[[^\]]*\]', '', core)
    core = re.sub(r'::?[\w-]+(?:\([^)]*\))?', '', core)
    return frozenset(TAG_RE.findall(core)), frozenset(re.findall(r'\.([\w-]+)', core))


def state_qualified(selector: str):
    return bool(NOT_RE.search(selector) or HAS_RE.search(selector)
                or re.search(r'\[[^\]]+\]', selector))


def audit(css: Path):
    rules = parse(css.read_text(encoding='utf-8'))
    overlays, problems = [], []

    for sel, decls in rules:
        for one in (s.strip() for s in sel.split(',')):
            if not one or not is_overlay(decls):
                continue
            overlays.append(one)
            tags, classes = signature(one)
            best = None  # ((important, specificity), prop, value, selector)
            for sel2, decls2 in rules:
                for other in (s.strip() for s in sel2.split(',')):
                    if not other or other == one or not state_qualified(other):
                        continue
                    otags, oclasses = signature(other)
                    if otags != tags or not oclasses >= classes:
                        continue
                    for prop, test in HIDE_PROPS.items():
                        val, imp = get(decls2, prop)
                        if not val or not test(val):
                            continue
                        key = (imp, specificity(other))
                        if best is None or key > best[0]:
                            best = (key, prop, val, other)
            base_val, base_imp = get(decls, 'display')
            if best is None:
                problems.append(
                    f'{css}:{one} 是占满视口的 fixed 遮罩（z-index {get(decls, "z-index")[0]}），'
                    f'没有任何"带状态限定"的隐藏规则能盖住它——状态不成立时它会吃掉整页点击。'
                )
                continue
            if base_imp and not best[0][0]:
                problems.append(
                    f'{css}:{one} 的基础规则给 display 加了 !important，'
                    f'而隐藏规则 {best[3]} 没有，层叠上盖不住。'
                )
            if best[0][1] <= specificity(one) and not best[0][0]:
                problems.append(
                    f'{css}:隐藏规则 {best[3]} 特异性不高于 {one} 且无 !important，遮罩关不掉。'
                )
    return overlays, problems


def main():
    args = sys.argv[1:]
    css = Path('docs/theme.css')
    if '--css' in args:
        css = Path(args[args.index('--css') + 1])
    if not css.exists():
        print(f'遮罩闸失败：找不到 {css}（缺文件不视为通过）')
        return 1
    overlays, problems = audit(css)
    if problems:
        for p in problems:
            print('遮罩闸报红：' + p)
        return 1
    if not overlays:
        print(f'遮罩闸失败：{css} 里枚举到 0 个占满视口的 fixed 遮罩。'
              f'0 不是通过——本闸依赖能解析到遮罩才有效，请检查 CSS 写法或解析口径。')
        return 1
    print(f'{css}：枚举到 {len(overlays)} 个占满视口的 fixed 遮罩'
          f'（{", ".join(overlays)}），全部有层叠上能赢的状态化隐藏规则。遮罩闸通过。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
