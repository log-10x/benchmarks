#!/bin/bash
# Disk guard: every INTERVAL seconds log free space and the rig's data size; gzip-rotate
# raw.jsonl past 1 GB; under FLOOR_MB free (confirmed 60 s later) stop the rig (run.sh down,
# volumes and images kept) and mark it. Exits when the run ends. Run it detached (detach.py).
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
DATA=${RIG_DATA:-$RESULTS/data}
INTERVAL=${INTERVAL:-300}
FLOOR_MB=${FLOOR_MB:-3000}
T=$RESULTS/timeline.jsonl
free() { echo $(( $(df -k / | awk 'NR==2{print $4}') / 1024 )); }
while [ ! -e "$RESULTS/.down.done" ]; do
  free_mb=$(free)
  raw_mb=$(( $(stat -f %z "$DATA/raw.jsonl" 2>/dev/null || echo 0) / 1048576 ))
  echo "$(date -u +%FT%TZ) free_mb=$free_mb raw_mb=$raw_mb data_mb=$(du -sm "$DATA" | cut -f1)" >> "$RESULTS/disk.log"
  if [ "$raw_mb" -ge 1024 ]; then
    n=$(date -u +%H%M%S); gzip -c "$DATA/raw.jsonl" > "$DATA/raw.$n.jsonl.gz" && : > "$DATA/raw.jsonl"
  fi
  if [ "$free_mb" -lt "$FLOOR_MB" ]; then
    sleep 60
    if [ "$(free)" -lt "$FLOOR_MB" ]; then
      echo "{\"event\":\"disk_stop\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"free_mb\":$(free)}" >> "$T"
      "$HERE/run.sh" down >> "$RESULTS/disk.log" 2>&1 || true
      exit 3
    fi
  fi
  sleep "$INTERVAL"
done
