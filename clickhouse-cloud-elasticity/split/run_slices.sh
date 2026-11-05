#!/usr/bin/env bash
# The arm split as K contiguous slices of the capture side by side, one Receiver each.
#
# The regulator decides per node and per 4-minute window, so a node fed a slice at
# 14 lines a second sees the same lines in each window as one node fed the whole
# capture at that pace; the difference is K partial first windows in place of one.
# Each slice is split/run.sh with its own names and build folder. The slices' wire
# files are joined in slice order into build/wire/returned.json and counted.
#
#   split/run_slices.sh          # K=4: about an hour for the whole capture
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
K="${K:-4}"
N="${N:-197430}"
BUILD="$HERE/build"

rm -rf "$BUILD"; mkdir -p "$BUILD/wire"
pids=()
for k in $(seq 0 $((K - 1))); do
  a=$((k * N / K)); b=$(((k + 1) * N / K))
  echo "slice $k: lines $((a + 1)) to $b"
  START=$a LINES=$((b - a)) NAME="chce$k" BUILD="$BUILD/slice$k" bash run.sh > "$BUILD/slice$k.log" 2>&1 &
  pids+=($!)
  sleep 2
done
fail=0
for k in $(seq 0 $((K - 1))); do
  wait "${pids[$k]}" || { echo "slice $k failed" >&2; tail -20 "$BUILD/slice$k.log" >&2; fail=1; }
done
[ "$fail" = 0 ] || exit 1

for k in $(seq 0 $((K - 1))); do cat "$BUILD/slice$k/wire/returned.json"; done > "$BUILD/wire/returned.json"
cp "$BUILD/slice0/images.txt" "$BUILD/slice0/patches.txt" "$BUILD/slice0/rate-settings.txt" "$BUILD/"
for k in $(seq 0 $((K - 1))); do echo "slice $k $(cat "$BUILD/slice$k/t0") $(cat "$BUILD/slice$k/t1") $(tail -1 "$BUILD/slice$k/pacer.log")"; done | tee "$BUILD/slices.txt"
python3 "$HERE/count_wire.py" "$BUILD/wire/returned.json" | tee "$BUILD/split-count.txt"
