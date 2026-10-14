#!/bin/bash
# The whole run, one command: quiet run, POC and fleet values, scheduled run. The scheduled
# phase, the disk guard and the hard stop run detached, so the run stops itself at the
# planned end even if this shell goes away.
#   DEMO=<demo 3.1.0 clone> MCP=<log10x-mcp 1.30.54, unpacked, dependencies installed> rig/go.sh
# Settings: SETTLE_S (120), QUIET_MIN (22), RUN_MIN (75), SEED (20261014), FLOOR_MB (4500).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
export DEMO=${DEMO:?demo clone} MCP=${MCP:?log10x-mcp package}
ENGINE=log10x/edge-10x:1.1.141@sha256:45157d0bdf506615aa015db7b8b7251ae39be5f4330233d2d2d659c69d1f93d1
SETTLE_S=${SETTLE_S:-120}; QUIET_MIN=${QUIET_MIN:-22}; RUN_MIN=${RUN_MIN:-75}; SEED=${SEED:-20261014}; FLOOR_MB=${FLOOR_MB:-4500}
T=$RESULTS/timeline.jsonl
mkdir -p "$RESULTS/data" "$RESULTS/planner"
: > "$T"; rm -rf "$RESULTS/.down.done" "$RESULTS/.down.lock"

# 1. Quiet run: the values a Datadog Receiver gets before a fleet default (no cap).
node "$HERE/gen-receiver-values.mjs" "$RESULTS/values-quiet" > /dev/null
echo $(( $(date +%s) + (QUIET_MIN + 45) * 60 )) > "$RESULTS/deadline"
python3 "$HERE/detach.py" "$RESULTS/disk-guard.out" env FLOOR_MB="$FLOOR_MB" INTERVAL=300 "$HERE/disk-guard.sh"
python3 "$HERE/detach.py" "$RESULTS/hard-stop.out" env GRACE=120 "$HERE/hard-stop.sh"
export RIG_RECEIVER=$RESULTS/values-quiet
"$HERE/run.sh" up
"$HERE/run.sh" wait-healthy
sleep "$SETTLE_S"
"$HERE/run.sh" quiet-start
sleep $((QUIET_MIN * 60))
"$HERE/run.sh" quiet-end

# 2. The POC on the quiet capture, then the fleet values, then the Receiver relaunched.
python3 - "$RESULTS" <<'PY'
import json, sys
R = sys.argv[1]
ev = [json.loads(l) for l in open(R + '/timeline.jsonl') if l.strip()]
q0 = [e['epoch'] for e in ev if e['event'] == 'quiet_start'][-1]
q1 = [e['epoch'] for e in ev if e['event'] == 'quiet_end'][-1]
n = 0
with open(R + '/planner/quiet-raw.jsonl', 'w') as out:
    for l in open(R + '/data/raw.jsonl'):
        try:
            t = float(json.loads(l)['fb_ts'])
        except Exception:
            continue
        if q0 <= t < q1:
            out.write(l); n += 1
print('quiet capture', n, 'lines')
PY
LOG10X_TENX_MODE=docker LOG10X_RUNTIME_IMAGE=$ENGINE node "$HERE/run-planner.mjs" "$RESULTS/planner/quiet-raw.jsonl" "$RESULTS/planner"
node "$HERE/gen-receiver-values.mjs" "$RESULTS/values-fleet" "$RESULTS/planner/poc-envelope.json"
export RIG_RECEIVER=$RESULTS/values-fleet
"$HERE/run.sh" receiver

# 3. The scheduled phase, detached.
python3 "$HERE/detach.py" "$RESULTS/run-unattended.out" env RIG_RECEIVER="$RIG_RECEIVER" SEED="$SEED" INTERVAL=600 MIN_HOLD=240 MAX_HOLD=480 RUN_MIN="$RUN_MIN" "$HERE/run-unattended.sh"
echo "scheduled phase started; it stops itself $RUN_MIN minutes after the scheduler starts"
