#!/bin/bash
# 文本/渲染类守卫（第一/二/三/九/十/十一/十二/十三/十四条）在最终字节上的回归矩阵：逐条具名记 rc。
# 用法：scripts/matrix_text.sh                          # 日志落在 logs/text_<UTC 时间戳>/
#       MATRIX_DIR=logs/text_w28 scripts/matrix_text.sh # 按轮命名；撞上一轮的 matrix.txt 会拒绝执行
#   落点从 2026-09-29 起在仓库里而不在 /tmp：/tmp 是 tmpfs，一次重启把上一轮所有取证件清掉了
#   （现场见 DIAGNOSIS.md 第 27 轮「一次重启把本轮的取证件清掉了」那条），登记行里写的日志路径
#   从此指向一个不存在的目录，而矩阵本身全绿——日志活着不代表锚活着。
#   覆盖判据也跟着搬进机制：目标目录里已经有 matrix.txt 就直接拒绝，不再 rm -rf 重建。
#   矩阵日志仍不进版本库（.gitignore 的 logs/），它是本机取证不是书的组成部分。
# 自证两条：行数必须 =19，且**行名集合**必须等于期望集合——只数行数放过过有重复行、
# 缺条目的矩阵（口径来历见 DIAGNOSIS.md「回归矩阵的覆盖自证改为按行名集合」那条）。
# 名字集合这一支在 2026-09-27 之前只兜住「多一行/少一行」，兜不住「某条守卫有 --selftest 却从未被派到行」——
# 第二十五条就是这样漏掉的：check_links.py 的自检早就存在、一直返回 0，矩阵里没有它的那一行。
# 本件住在仓库里而不是 /tmp：/tmp 会被清，清了下一轮就只剩"记得怎么跑"而没有脚本。
set -u
R=$(cd "$(dirname "$0")/.." && pwd)
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
L=${MATRIX_DIR:-$R/logs/text_$(date -u +%Y%m%dT%H%M%SZ)}
case "$L" in /*) ;; *) L="$R/$L";; esac
M="$L/matrix.txt"
cd "$R" || exit 1

exec 9>/tmp/ainse_matrix_text.lock
flock -n 9 || { echo "!! 已有文本矩阵在跑（锁 /tmp/ainse_matrix_text.lock）——并发跑会把读数写混"; exit 1; }
# 锁留在 /tmp 是有意的：它是互斥量不是取证件，重启后本该没有人持着它。
# 搬进仓库的那一半是证据（matrix.txt 与各条 .log），不是这把锁。

# 派生对账（第 26 轮队列④）：每支自带 --selftest 分派的守卫都必须在本件里有一行 run。
# 为什么要这一格：EXPECT 的名字集合是手抄的，它兜得住「少跑一行」，兜不住「一条守卫的自检
# 从来没被派进行」——那需要有人先知道守卫有自检。第 25 轮就是这样漏掉第二条的（有自检、返 0、矩阵无行）。
# 锚落在分派那一行（`if ... "--selftest" in ...`），不落在字样上：字样会出现在 docstring 与用法注释里，
# 拿它当锚会把「文档提了自检却没实现」的文件也算进来。
MISS=""
for f in scripts/check_*.py; do
  grep -Eq 'if[^#]*"--selftest" in ' "$f" || continue
  grep -Fq "$f --selftest" "$SELF" || MISS="$MISS $f"
done
if [ -n "$MISS" ]; then
  echo "!! 有自检未派行：$MISS"
  echo "   修法：给那支守卫加一行 run NN_xxx_st python3 <脚本> --selftest，并把行名补进 EXPECT 与行数判据。"
  exit 1
fi

if [ -e "$M" ]; then
  echo "!! $M 已存在——跑第二趟会把上一轮的取证覆盖掉（覆盖等于作废那一跑的登记行）。"
  echo "   默认落点带 UTC 时间戳，本来撞不上；撞上说明你显式给了一个用过的 MATRIX_DIR。"
  echo "   要么换目录名，要么先读旧的那份再决定是不是真的要重跑。"
  exit 1
fi
mkdir -p "$L"
: > "$M"

run() {  # run <名字> <命令...>
  local name="$1"; shift
  "$@" > "$L/$name.log" 2>&1
  echo "$name rc=$?" >> "$M"
}

run 01_figures       python3 scripts/check_figures.py
run 01b_figures_st   python3 scripts/check_figures.py --selftest
run 03_markdown      python3 scripts/check_markdown.py
run 03b_markdown_st  python3 scripts/check_markdown.py --selftest
run 11_replay        python3 scripts/check_replay.py
run 11b_replay_st    python3 scripts/check_replay.py --selftest
run 12_tier_ledger   python3 scripts/check_tier_ledger.py
run 12b_tier_st      python3 scripts/check_tier_ledger.py --selftest
run 12c_tier_print   python3 scripts/check_tier_ledger.py --print

# 第二条不自带外部服务了（2026-09-29）：本矩阵原来在这里 `http.server 8080 &`，
# 而端口被外来服务占住时那一条**静默绑定失败**，检查却继续对着别人的目录跑——
# 108 条正常引用当场报成死链、退出码 1。现在 `check_links.py` 与浏览器那几条守卫一样
# 自起服务于空闲端口，所以这里不再起服务，也不再需要 `sleep` 等它就绪。
run 02_links         python3 scripts/check_links.py
run 02b_links_st     python3 scripts/check_links.py --selftest
# 02b 的对照件全是内存里的文本，不碰网络也不读 docs/，所以它绿不绿与 02 那格互不背书：
# 02 报 2 时（判不了：端口上不是本书、或连接层就没通，本闸一条引用都没判）02b 仍应是 0。
# 矩阵行按原始 rc 逐条记录，2 与 1 在 matrix.txt 里本来就分得开——2 是判不了，1 才是真死链。

run 10_incidents     python3 scripts/check_incidents.py
run 10b_incidents_st python3 scripts/check_incidents.py --selftest

# 第九条真起 Chrome
run 09_leaks         python3 scripts/check_render_leaks.py
run 09b_leaks_st     python3 scripts/check_render_leaks.py --selftest

run 13_citations     python3 scripts/check_citations.py
run 13b_citations_st python3 scripts/check_citations.py --selftest

run 14_response_dates     python3 scripts/check_response_dates.py
run 14b_response_dates_st python3 scripts/check_response_dates.py --selftest

EXPECT=$(printf '%s\n' 01_figures 01b_figures_st 02_links 02b_links_st 03_markdown 03b_markdown_st \
  09_leaks 09b_leaks_st 10_incidents 10b_incidents_st 11_replay 11b_replay_st \
  12_tier_ledger 12b_tier_st 12c_tier_print 13_citations 13b_citations_st \
  14_response_dates 14b_response_dates_st | sort | tr '\n' ' ')
GOT=$(awk '{print $1}' "$M" | sort | tr '\n' ' ')
N=$(grep -c "" "$M")
if [ "$N" -ne 19 ] || [ "$GOT" != "$EXPECT" ]; then
  echo "!! 矩阵自证失败：$N 行；期望 [$EXPECT] 实得 [$GOT]"
  cat "$M"; exit 1
fi
echo "== 矩阵（$N 行，名字集合已核对）=="
cat "$M"
BAD=$(awk '$2 != "rc=0"' "$M" | wc -l)
echo "非零项数 $BAD"
[ "$BAD" -eq 0 ] && echo "全部通过" || { echo "!! 有非零退出"; exit 1; }
