#!/bin/bash
# Disk guard: every INTERVAL seconds log free space and the rig's data size; gzip-rotate
# raw.jsonl past 1 GB; under FLOOR_MB free (confirmed 60 s later) stop the rig (run.sh down,
# volumes and images kept) and mark it. With OWN_MAX_MB set, also stop when the rig's own use (its
# Docker volumes plus the results directory) passes OWN_MAX_MB. Exits when the run ends. Run it detached (detach.py).
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
DATA=${RIG_DATA:-$RESULTS/data}
INTERVAL=${INTERVAL:-300}
FLOOR_MB=${FLOOR_MB:-3000}
T=$RESULTS/timeline.jsonl
free() { echo $(( $(df -k / | awk 'NR==2{print $4}') / 1024 )); }
own() {
  local v
  v=$(docker system df -v --format '{{json .Volumes}}' 2>/dev/null | python3 -c "
import json,re,sys
u={'B':1e-6,'kB':1e-3,'KB':1e-3,'MB':1,'GB':1e3,'TB':1e6}
t=0
for x in json.loads(sys.stdin.read() or '[]'):
    if x.get('Name','').startswith('elastic-budget_'):
        m=re.match(r'([0-9.]+)\s*([A-Za-z]+)',x.get('Size','0B')); t+=float(m.group(1))*u.get(m.group(2),1) if m else 0
print(int(t))" 2>/dev/null || echo 0)
  echo $(( v + $(du -sm "$RESULTS" | cut -f1) ))
}
while [ ! -e "$RESULTS/.down.done" ]; do
  free_mb=$(free)
  raw_mb=$(( $(stat -f %z "$DATA/raw.jsonl" 2>/dev/null || echo 0) / 1048576 ))
  own_mb=$([ -n "${OWN_MAX_MB:-}" ] && own || echo 0)
  echo "$(date -u +%FT%TZ) free_mb=$free_mb raw_mb=$raw_mb data_mb=$(du -sm "$DATA" | cut -f1) own_mb=$own_mb" >> "$RESULTS/disk.log"
  if [ -n "${OWN_MAX_MB:-}" ] && [ "$own_mb" -gt "$OWN_MAX_MB" ]; then
    echo "{\"event\":\"disk_stop\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"own_mb\":$own_mb}" >> "$T"
    "$HERE/run.sh" down >> "$RESULTS/disk.log" 2>&1 || true
    exit 3
  fi
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
