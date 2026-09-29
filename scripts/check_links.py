#!/usr/bin/env python3
"""死链守卫：把 docs 里每一条本地引用换成真实 HTTP 请求。

用法：
    python3 scripts/check_links.py                    # 默认自起服务于空闲端口，不依赖外部服务
    python3 scripts/check_links.py --base http://127.0.0.1:8080   # 指到已有的服务（要过身份哨兵）

解析口径：
- Markdown 链接/图片、HTML 的 href/src、Docsify 的 /manuscript/x.md 根相对路径。
- 锚点（#…）只校验宿主文件存在；外链（http/https/mailto）交 public-evidence.md 的可达性台账。
- 尖括号包裹的链接与 `<>` 路由（九部分卷首）同样解析。
"""
import functools
import http.server
import re
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import free_port  # noqa: E402  与第四/第七条守卫同一把端口尺

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
    """排除集的两种死法都要红：把示例当链接（过窄），把正文链接也放掉（过宽）。

    每支对照自带「家族／类别」两个标签，末行的分母、家族明细与极性—假阳配比全部现算——
    加一支对照不需要改任何文案，改文案也不能让读数好看一点。
    """
    fams, kinds, fails = {}, {}, []

    def check(fam, kind, name, ok, detail=""):
        fams.setdefault(fam, [0, 0])[0] += 1
        kinds[kind] = kinds.get(kind, 0) + 1
        if not ok:
            fams[fam][1] += 1
            fails.append(f"[{kind}] {fam}｜{name}" + (f"：{detail}" if detail else ""))

    in_fence = "正文。\n\n```python\nlink = '[a](./nope.md)'\nx = '<link href=\"nope.css\">'\n```\n"
    in_icode = "示例草稿正文：`模板在 [附录 D](./nope.md)`，其余是话。\n"
    prose = "真引用：[第 9 章](./ch14-第9章-契约先行.md)。\n"
    wide = "正文里还有 [坏链](./does-not-exist.md)。\n"
    for name, kind, txt, want in (("代码块内不计", "假阳", in_fence, []),
                                  ("行内代码内不计", "假阳", in_icode, []),
                                  ("正文链接要计", "极性", prose, ["./ch14-第9章-契约先行.md"]),
                                  ("正文坏链要计", "极性", wide, ["./does-not-exist.md"])):
        got = targets(txt)
        check("排除集", kind, name, got == want, f"期望 {want}，实测 {got}")
    # 嵌套围栏：四反引号包住三反引号示例，只有外层闭合才算出块
    nested = "````markdown\n```python\nf = '[b](./nope.md)'\n```\n````\n之后 [c](./ok.md)\n"
    check("围栏闭合", "极性", "嵌套围栏只算外层闭合", targets(nested) == ["./ok.md"],
          f"期望 ['./ok.md']，实测 {targets(nested)}")
    # 未闭合围栏必须拒绝读数，不能悄悄把后半篇当代码块豁免掉
    try:
        visible_markdown("```python\nf = 1\n[a](./b.md)\n")
        check("围栏闭合", "极性", "未闭合围栏拒绝读数", False, "应当 SystemExit，却返回了读数")
    except SystemExit:
        check("围栏闭合", "极性", "未闭合围栏拒绝读数", True)
    # 退出码三档：极性与假阳各一支。判不了与判出死链不可共用一个码，
    # 而「有服务但根路径非 200」与「服务未起」都要落进「判不了」那一档（同一个码、不同文案）。
    for name, live, dead, want in (("服务未起判不了", False, 0, RC_UNREADABLE),
                                   ("有服务但非本书也判不了", False, 108, RC_UNREADABLE),
                                   ("服务在且零死链", True, 0, RC_PASS),
                                   ("服务在且有死链", True, 3, RC_DEAD)):
        check("退出码分档", "假阳" if want == RC_PASS else "极性", name,
              classify(live, dead) == want, f"期望 {want}，实测 {classify(live, dead)}")
    # 上面几条对照用的是常量，常量本身被改成同一个值时它们会一起变绿，所以再钉一次档位互不相等
    check("退出码分档", "极性", "三档互不相等",
          len({classify(False, 0), classify(True, 0), classify(True, 3)}) == 3,
          "判不了与真死链共用一个码，本闸的红灯就不可解释")
    # 预检：把「端口上不是本书」判成可信，就会把一整本正常引用报成死链（2026-09-29 真发生过）。
    # 唯一那支假阳对照＝真·本书的三件全对；其余每一支都必须拒绝，且拒绝文案各指一件事。
    for name, (rc, sc, same), want_ok, want_kw in (
            ("根 200 且哨兵字节一致", (200, 200, True), True, None),
            ("连接层就没通", (None, None, True), False, "未起"),
            ("根路径非 200", (404, None, True), False, "根路径"),
            ("端口上给不出哨兵", (200, None, True), False, "给不出"),
            ("哨兵回非 200", (200, 403, True), False, "回 HTTP 403"),
            ("哨兵同名而字节不等", (200, 200, False), False, "另一本书"),
    ):
        ok, why = judge_liveness(rc, sc, same)
        check("预检", "假阳" if want_ok else "极性", name, ok == want_ok and
              (want_kw is None or want_kw in why),
              f"期望 {'可信' if want_ok else '不可信'}且含「{want_kw}」，实测 {ok}／{why}")
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        print(f"死链守卫自检未通过：{len(fails)} 条未达预期"
              f"（分母 {sum(v[0] for v in fams.values())} 支）")
        return 1
    total = sum(v[0] for v in fams.values())
    print(f"死链守卫自检通过：{total} 支对照，未达预期 0 支——"
          + "／".join(f"{k} {v[0]} 支（红 {v[1]}）" for k, v in fams.items()))
    print("  类别配比现算：" + "／".join(f"{k} {n} 支" for k, n in kinds.items()))
    print(f"  退出码三档由 classify 现算：判不了 {classify(False, 0)}／"
          f"判过且干净 {classify(True, 0)}／判出死链 {classify(True, 3)}")
    return 0


RC_PASS, RC_DEAD, RC_UNREADABLE = 0, 1, 2


def classify(live, dead_count):
    """探测档 + 死链条数 → 退出码。纯函数：网络与文件系统都不进来。

    存在的理由是那一格「判不了」与「判出死链」曾共用退出码 1，而服务没起时本闸会把
    每一条引用都记成死链（实测 108 条），读数长得和真断链一模一样。分档之后：
    2 是「本闸一条都没判」，1 才是「判了，有死的」。
    """
    if not live:
        return RC_UNREADABLE
    return RC_DEAD if dead_count else RC_PASS


SENTINEL = "_sidebar.md"  # 身份哨兵：Docsify 的导航件，删了书就坏了，所以拿它问"这是不是本书"


def judge_liveness(root_code, sentinel_code, same_bytes):
    """（根路径码, 哨兵码, 哨兵字节是否相等）→ (可信, 原因)。纯函数：网络与磁盘都不进来。

    三档不合并的理由是今天这一跑：8080 上挂着另一本书的服务，`http.server 8080` 静默绑定失败，
    旧探针只问过根路径是不是 200，于是 108 条正常引用全报成死链、退出码 1——与真断链同一个码。
    「没服务」「服务不是本书」「是本书但字节漂了」是三件不同的修，共用一个 200 时红灯就失去指认能力。
    """
    if root_code is None:
        return False, "本地 http 服务未起（连接层就没通）"
    if root_code != 200:
        return False, f"根路径回 HTTP {root_code}（不是本书的 docs 目录？）"
    if sentinel_code is None:
        return False, f"端口上有服务，但它给不出本书的 {SENTINEL}——那是另一个目录"
    if sentinel_code != 200:
        return False, f"端口上有服务，但对本书的 {SENTINEL} 回 HTTP {sentinel_code}——那是另一个目录"
    if not same_bytes:
        return False, f"{SENTINEL} 取到了却与仓库里的字节不等——那是另一本书的同名件"
    return True, f"根路径 200、{SENTINEL} 字节与仓库一致"


def sentinel_bytes():
    """对照件从仓库现取，不抄常量也不抄内容：改一次侧栏文字不该把预检洗成"永远不等"。"""
    f = DOCS / SENTINEL
    if not f.is_file():
        raise SystemExit(f"哨兵 {SENTINEL} 在 docs/ 里查无此人——预检没有对照件，本闸拒绝读数")
    return f.read_bytes()


def http_code(url):
    """取一次状态码；连不上（被拒、超时）返回 None，HTTP 错误返回那个码。"""
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            r.read()  # 读干净再走：半读断开会让自起的服务往 stderr 倒 traceback
            return r.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return None


def fetch(url):
    return urllib.request.urlopen(url, timeout=5).read()


def self_serve():
    """默认自起服务：把运行时面从「别人在 8080 上起了什么」收回到本闸自己手里。

    浏览器那几条守卫早就这么做（`check_legibility.serve()` 用同一个 `cdp.free_port()`），
    第二条是最后一个还依赖外部固定端口的，而端口正是这台机器上会被别的项目占走的东西。
    `--base` 仍然留给"已有服务"那一档，只是那一档现在要过身份哨兵。
    """
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    httpd = socketserver.ThreadingTCPServer(
        ("127.0.0.1", free_port()), functools.partial(Quiet, directory=str(DOCS)))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", httpd.shutdown


def probe(base):
    """开跑前先问两次：端口在不在，以及那个端口**是不是本书**。返回 (可信, 原因)。

    原因分四档写：未起 / 根路径不是 200 / 端口上不是本书 / 是本书但对照件漂了。
    四档都判「不可读」，但文案不能混——前三档修的是环境，第四档修的是这一跑的可信度。
    """
    root = base.rstrip("/") + "/"
    code = http_code(root)
    surl = base.rstrip("/") + "/" + urllib.parse.quote(SENTINEL)
    if code != 200:
        return judge_liveness(code, None, True)
    scode = http_code(surl)
    same = True
    if scode == 200:
        try:
            same = fetch(surl) == sentinel_bytes()
        except Exception:  # noqa: BLE001
            scode = None
    return judge_liveness(code, scode, same)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    external = "--base" in sys.argv
    if external:
        base, stop, how = sys.argv[sys.argv.index("--base") + 1], None, "外部 --base 指定的服务"
    else:
        base, shutdown = self_serve()
        def stop():
            shutdown()
        how = "本闸自起的空闲端口"
    try:
        return check_all(base, how)
    finally:
        if stop:
            stop()


def check_all(base, how):
    live, why = probe(base)
    if not live:  # 判不了时不逐条判，也不逐条报——那 108 条「请求失败」不是 108 条死链
        print(f"[服务] {why}：{base}")
        print("[服务] 本闸一条引用都没判——判了但全挂 ≠ 判不了；"
              "退出码 2 与真死链的 1 分开，去修的那一件是环境不是稿件。")
        return classify(live, 0)
    print(f"[服务] {how}：{base}（{why}）")
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
                with urllib.request.urlopen(url, timeout=10) as r:
                    r.read()
                    code = r.getcode()
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
    else:
        print("死链 = 0。")
    return classify(live, len(bad))


if __name__ == "__main__":
    sys.exit(main())
