#!/bin/bash
# 浏览器类闸（第四至第八条）的具名 rc 矩阵。
# 用法：scripts/matrix_browser.sh                            # 日志落在 logs/browser_<UTC 时间戳>/
#       MATRIX_DIR=logs/browser_w28 scripts/matrix_browser.sh # 按轮命名；撞 matrix.txt 会拒绝执行
#   落点与文本矩阵同批改到仓库里（2026-09-29，见 matrix_text.sh 头部与本仓第 27 轮登记）：
#   /tmp 是 tmpfs，一次重启会把登记行指向的取证目录整个清掉，而矩阵自己全绿。
#   覆盖判据搬进机制：目标目录里已有 matrix.txt 就拒绝，不再 rm -rf 重建。
# 自证两条：行数必须 =6，且**行名集合**必须等于期望集合。上一跑（bat13_browser）被
# TaskStop 停掉的脚本其实没死透——它的后代接着跑完并把一行追加进新一轮同一份矩阵，
# 只数行数的自证放行了一个有重复行、缺第八条的矩阵。名字集合才是真覆盖。
# 默认落点带时间戳之后，孤儿那一支写的是它自己那一轮的目录，不会再混进新一轮；
# 名字集合判据照留——显式复用目录名时只有它还拦得住。
# 锁用 flock 而不是 pgrep 自匹配：pgrep 那版第一跑就被 harness 包的祖先进程拦死。
# 注意：flock 的 fd 会被子进程继承——父死锁不解，孤儿守卫会继续占锁，见 DIAGNOSIS.md。
set -u
R=$(cd "$(dirname "$0")/.." && pwd)
L=${MATRIX_DIR:-$R/logs/browser_$(date -u +%Y%m%dT%H%M%SZ)}
case "$L" in /*) ;; *) L="$R/$L";; esac
M="$L/matrix.txt"
cd "$R" || exit 1

exec 9>/tmp/ainse_matrix_browser.lock
flock -n 9 || { echo "!! 已有浏览器矩阵在跑（锁 /tmp/ainse_matrix_browser.lock）——并发跑会把读数写混"; exit 1; }

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
