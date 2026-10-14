#!/bin/bash
# Disk guard: every INTERVAL seconds log free space; gzip-rotate raw.jsonl past 1 GB;
# under FLOOR_MB free, stop the demo cleanly (run.sh down keeps images) and mark it.
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
DATA=${RIG_DATA:-$RESULTS/data}
INTERVAL=${INTERVAL:-300}
FLOOR_MB=${FLOOR_MB:-4500}
while true; do
  free_mb=$(( $(df -k / | awk 'NR==2{print $4}') / 1024 ))
  raw_mb=$(( $(stat -f %z "$DATA/raw.jsonl" 2>/dev/null || echo 0) / 1048576 ))
  echo "$(date -u +%FT%TZ) free_mb=$free_mb raw_mb=$raw_mb data_mb=$(du -sm "$DATA" | cut -f1)" >> "$RESULTS/disk.log"
  if [ "$raw_mb" -ge 1024 ]; then
    n=$(date -u +%H%M%S); gzip -c "$DATA/raw.jsonl" > "$DATA/raw.$n.jsonl.gz" && : > "$DATA/raw.jsonl"
    echo "$(date -u +%FT%TZ) rotated raw.jsonl to raw.$n.jsonl.gz" >> "$RESULTS/disk.log"
  fi
  if [ "$free_mb" -lt "$FLOOR_MB" ]; then
    # Another process on this host writes and deletes about 1 GB in cycles; confirm the
    # reading 60 s later before stopping, so a transient dip does not end the run.
    echo "$(date -u +%FT%TZ) under floor (${free_mb} MB); confirming in 60 s" >> "$RESULTS/disk.log"
    sleep 60
    free_mb=$(( $(df -k / | awk 'NR==2{print $4}') / 1024 ))
    echo "$(date -u +%FT%TZ) confirmation reading free_mb=$free_mb" >> "$RESULTS/disk.log"
  fi
  if [ "$free_mb" -lt "$FLOOR_MB" ]; then
    echo "$(date -u +%FT%TZ) FLOOR BREACH: free ${free_mb} MB < ${FLOOR_MB} MB; stopping the demo" >> "$RESULTS/disk.log"
    echo "{\"event\":\"disk_stop\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"free_mb\":$free_mb}" >> "$RESULTS/timeline.jsonl"
    "$HERE/run.sh" down >> "$RESULTS/disk.log" 2>&1 || true
    exit 3
  fi
  sleep "$INTERVAL"
done
