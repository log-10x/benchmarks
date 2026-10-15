#!/bin/bash
# Disk guard: every INTERVAL seconds log free space; gzip-rotate raw.jsonl past 1 GB;
# under FLOOR_MB free (confirmed 60 s later), stop the demo cleanly (run.sh down keeps
# images) and mark it. Exits when the run ends. Run it detached (detach.py).
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
DATA=${RIG_DATA:-$RESULTS/data}
INTERVAL=${INTERVAL:-300}
FLOOR_MB=${FLOOR_MB:-4500}
T=$RESULTS/timeline.jsonl
ends0=$(grep -c '"run_end"' "$T" 2>/dev/null || echo 0)
free() { echo $(( $(df -k / | awk 'NR==2{print $4}') / 1024 )); }
while true; do
  free_mb=$(free)
  raw_mb=$(( $(stat -f %z "$DATA/raw.jsonl" 2>/dev/null || echo 0) / 1048576 ))
  swap=$(sysctl -n vm.swapusage | awk '{print $6}')
  echo "$(date -u +%FT%TZ) free_mb=$free_mb raw_mb=$raw_mb data_mb=$(du -sm "$DATA" | cut -f1) swap_used=$swap vm_volume_mb=$(df -m /System/Volumes/VM | awk 'NR==2{print $3}')" >> "$RESULTS/disk.log"
  if [ "$raw_mb" -ge 1024 ]; then
    n=$(date -u +%H%M%S); gzip -c "$DATA/raw.jsonl" > "$DATA/raw.$n.jsonl.gz" && : > "$DATA/raw.jsonl"
    echo "$(date -u +%FT%TZ) rotated raw.jsonl to raw.$n.jsonl.gz" >> "$RESULTS/disk.log"
  fi
  if [ "$free_mb" -lt "$FLOOR_MB" ]; then
    echo "$(date -u +%FT%TZ) under floor (${free_mb} MB); confirming in 60 s" >> "$RESULTS/disk.log"
    sleep 60
    free_mb=$(free)
    echo "$(date -u +%FT%TZ) confirmation reading free_mb=$free_mb" >> "$RESULTS/disk.log"
    if [ "$free_mb" -lt "$FLOOR_MB" ]; then
      echo "$(date -u +%FT%TZ) FLOOR BREACH: free ${free_mb} MB < ${FLOOR_MB} MB; stopping the demo" >> "$RESULTS/disk.log"
      echo "{\"event\":\"disk_stop\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"free_mb\":$free_mb}" >> "$T"
      "$HERE/run.sh" down >> "$RESULTS/disk.log" 2>&1 || true
      exit 3
    fi
  fi
  for i in $(seq 1 $((INTERVAL / 10))); do
    sleep 10
    [ "$(grep -c '"run_end"' "$T" 2>/dev/null || echo 0)" != "$ends0" ] && { echo "$(date -u +%FT%TZ) run ended; guard exits" >> "$RESULTS/disk.log"; exit 0; }
  done
done
