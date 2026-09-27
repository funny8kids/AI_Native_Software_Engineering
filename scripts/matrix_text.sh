#!/bin/bash
# 文本/渲染类守卫（第一/二/三/九/十/十一/十二/十三条）在最终字节上的回归矩阵：逐条具名记 rc。
# 用法：MATRIX_DIR=/tmp/matrix_text_x scripts/matrix_text.sh
#   日志目录由环境变量给；不给就用 /tmp/matrix_text。矩阵日志一旦开跑就不许复用旧目录
#   （脚本会 rm -rf 重建，覆盖等于作废上一跑的取证）。
# 自证两条：行数必须 =16，且**行名集合**必须等于期望集合——只数行数放过过有重复行、
# 缺条目的矩阵（口径来历见 DIAGNOSIS.md「回归矩阵的覆盖自证改为按行名集合」那条）。
# 本件住在仓库里而不是 /tmp：/tmp 会被清，清了下一轮就只剩"记得怎么跑"而没有脚本。
set -u
R=$(cd "$(dirname "$0")/.." && pwd)
L=${MATRIX_DIR:-/tmp/matrix_text}
M="$L/matrix.txt"
cd "$R" || exit 1

exec 9>/tmp/ainse_matrix_text.lock
flock -n 9 || { echo "!! 已有文本矩阵在跑（锁 /tmp/ainse_matrix_text.lock）——并发跑会把读数写混"; exit 1; }

rm -rf "$L"; mkdir -p "$L"
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

# 第二条要起服务。按 PID 收，不用 pkill -f——那条模式的字面串就在本脚本自己的命令行里。
python3 -m http.server 8080 --directory docs > "$L/httpd.log" 2>&1 &
HTTPD=$!
sleep 2
run 02_links         python3 scripts/check_links.py
kill "$HTTPD" 2>/dev/null
wait "$HTTPD" 2>/dev/null

run 10_incidents     python3 scripts/check_incidents.py
run 10b_incidents_st python3 scripts/check_incidents.py --selftest

# 第九条真起 Chrome
run 09_leaks         python3 scripts/check_render_leaks.py
run 09b_leaks_st     python3 scripts/check_render_leaks.py --selftest

run 13_citations     python3 scripts/check_citations.py
run 13b_citations_st python3 scripts/check_citations.py --selftest

EXPECT=$(printf '%s\n' 01_figures 01b_figures_st 02_links 03_markdown 03b_markdown_st \
  09_leaks 09b_leaks_st 10_incidents 10b_incidents_st 11_replay 11b_replay_st \
  12_tier_ledger 12b_tier_st 12c_tier_print 13_citations 13b_citations_st | sort | tr '\n' ' ')
GOT=$(awk '{print $1}' "$M" | sort | tr '\n' ' ')
N=$(grep -c "" "$M")
if [ "$N" -ne 16 ] || [ "$GOT" != "$EXPECT" ]; then
  echo "!! 矩阵自证失败：$N 行；期望 [$EXPECT] 实得 [$GOT]"
  cat "$M"; exit 1
fi
echo "== 矩阵（$N 行，名字集合已核对）=="
cat "$M"
BAD=$(awk '$2 != "rc=0"' "$M" | wc -l)
echo "非零项数 $BAD"
[ "$BAD" -eq 0 ] && echo "全部通过" || { echo "!! 有非零退出"; exit 1; }
