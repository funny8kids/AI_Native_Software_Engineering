#!/bin/bash
# 浏览器类闸（第四至第八条）的具名 rc 矩阵。
# 用法：MATRIX_DIR=/tmp/matrix_browser_x scripts/matrix_browser.sh
#   日志目录由环境变量给；不给就用 /tmp/matrix_browser。
# 自证两条：行数必须 =6，且**行名集合**必须等于期望集合。上一跑（bat13_browser）被
# TaskStop 停掉的脚本其实没死透——它的后代接着跑完并把一行追加进新一轮同一份矩阵，
# 只数行数的自证放行了一个有重复行、缺第八条的矩阵。名字集合才是真覆盖。
# 锁用 flock 而不是 pgrep 自匹配：pgrep 那版第一跑就被 harness 包的祖先进程拦死。
# 注意：flock 的 fd 会被子进程继承——父死锁不解，孤儿守卫会继续占锁，见 DIAGNOSIS.md。
set -u
R=$(cd "$(dirname "$0")/.." && pwd)
L=${MATRIX_DIR:-/tmp/matrix_browser}
M="$L/matrix.txt"
cd "$R" || exit 1

exec 9>/tmp/ainse_matrix_browser.lock
flock -n 9 || { echo "!! 已有浏览器矩阵在跑（锁 /tmp/ainse_matrix_browser.lock）——并发跑会把读数写混"; exit 1; }

rm -rf "$L"; mkdir -p "$L"
: > "$M"

run() {  # run <名字> <命令...>
  local name="$1"; shift
  "$@" > "$L/$name.log" 2>&1
  echo "$name rc=$?" >> "$M"
}

run 04_overlays       python3 scripts/check_overlays.py
run 05_interactions   python3 scripts/check_interactions.py
run 06_mobile         python3 scripts/check_mobile.py
run 07_legibility     python3 scripts/check_legibility.py
run 07b_legibility_mt python3 scripts/check_legibility.py --mutate
run 08_palette        python3 scripts/check_palette.py

EXPECT=$(printf '%s\n' 04_overlays 05_interactions 06_mobile 07_legibility 07b_legibility_mt 08_palette | sort | tr '\n' ' ')
GOT=$(awk '{print $1}' "$M" | sort | tr '\n' ' ')
N=$(grep -c "" "$M")
if [ "$N" -ne 6 ] || [ "$GOT" != "$EXPECT" ]; then
  echo "!! 矩阵自证失败：$N 行；期望 [$EXPECT] 实得 [$GOT]"
  cat "$M"; exit 1
fi
echo "== 矩阵（$N 行，名字集合已核对）=="
cat "$M"
BAD=$(awk '$2 != "rc=0"' "$M" | wc -l)
echo "非零项数 $BAD"
[ "$BAD" -eq 0 ] && echo "全部通过" || { echo "!! 有非零退出"; exit 1; }
