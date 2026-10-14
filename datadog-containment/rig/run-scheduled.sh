#!/bin/bash
# Scheduled run: Receiver with the fleet default cap, demo up (kafka retry), settle,
# seeded scheduler, stop after N completed activations plus one regulator window, or at
# MAX_MIN minutes of scheduler time, or when the disk guard stops the demo.
#   RIG_CAP=<bytes> SEED=<seed> INTERVAL=600 MIN_HOLD=240 MAX_HOLD=480 ACTIVATIONS=4 MAX_MIN=75 SETTLE=300 ./run-scheduled.sh
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DEMO=${DEMO:-/Users/talweiss/git/l1x-co/otel-demo-3.1.0}
export RIG_DIR=$HERE RIG_DATA=${RIG_DATA:-$HERE/../results/data} DEMO_VERSION=3.1.0
export RIG_CAP=${RIG_CAP:?cap bytes}
SEED=${SEED:-20261014}; INTERVAL=${INTERVAL:-600}; MIN_HOLD=${MIN_HOLD:-240}; MAX_HOLD=${MAX_HOLD:-480}
ACTIVATIONS=${ACTIVATIONS:-4}; MAX_MIN=${MAX_MIN:-75}; SETTLE=${SETTLE:-300}
T=$HERE/../results/timeline.jsonl
C="docker compose -f $DEMO/compose.yaml -f $DEMO/compose.full.yaml -f $HERE/compose.rig.yaml"
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
stops0=$(grep -c '"disk_stop"' "$T")
stopped() { [ "$(grep -c '"disk_stop"' "$T")" != "$stops0" ]; }

cd "$DEMO"
$C up -d fluent-bit tenx || exit 1
until docker logs rig-tenx 2>&1 | grep -q 'Writing TenXObject field'; do sleep 3; done
mark receiver_ready "\"cap\":$RIG_CAP"
for attempt in 1 2 3; do
  $C up -d --remove-orphans && break
  echo "compose up attempt $attempt failed; waiting for kafka healthy"
  until [ "$(docker inspect kafka --format '{{.State.Health.Status}}' 2>/dev/null)" = healthy ]; do sleep 10; stopped && exit 0; done
done
mark demo_up
for i in $(seq 1 60); do
  bad=$($C ps -a --format '{{.Name}} {{.Status}}' | grep -E 'Created|Exited|unhealthy|starting' || true)
  [ -z "$bad" ] && break; sleep 10; stopped && exit 0
done
if [ -n "$bad" ]; then echo "not healthy: $bad"; mark demo_not_healthy; exit 1; fi
mark demo_healthy
end=$(( $(date +%s) + SETTLE )); while [ "$(date +%s)" -lt "$end" ]; do sleep 10; stopped && exit 0; done

cd "$HERE"
./scheduler.sh start "$SEED" "$INTERVAL" "$MIN_HOLD" "$MAX_HOLD" || exit 1
mark scheduler_start "\"seed\":$SEED,\"interval_s\":$INTERVAL,\"min_hold_s\":$MIN_HOLD,\"max_hold_s\":$MAX_HOLD"
s0=$(date +%s); done_at=0
while true; do
  sleep 15
  stopped && { echo "disk guard stopped the run"; exit 0; }
  reverts=$(python3 - "$RIG_DATA/raw.jsonl" "$s0" <<'PY'
import json,sys
n=0
for l in open(sys.argv[1], errors='replace'):
    if 'Flag scheduler reverted' not in l: continue
    try: r=json.loads(l)
    except Exception: continue
    if r.get('container_name')=='flagd-ui' and float(r['fb_ts'])>=float(sys.argv[2]): n+=1
print(n)
PY
)
  now=$(date +%s)
  if [ "$reverts" -ge "$ACTIVATIONS" ] && [ "$done_at" -eq 0 ]; then done_at=$now; echo "$reverts activations completed at $(date -u +%T); one more window"; fi
  if [ "$done_at" -gt 0 ] && [ $((now - done_at)) -ge 240 ]; then echo "stopping: activations done"; break; fi
  if [ $((now - s0)) -ge $((MAX_MIN * 60)) ]; then echo "stopping: $MAX_MIN minutes"; break; fi
done
./run.sh down
