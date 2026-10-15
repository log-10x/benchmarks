#!/bin/bash
# The scheduled phase, unattended: starts the seeded flagd-ui scheduler, moves the deadline
# to the planned end, and at the planned end runs `run.sh down`. Run it detached
# (detach.py) beside disk-guard.sh and hard-stop.sh, each in its own session, so the run
# stops itself at the planned end even if the shell that launched it goes away.
#   RIG_RECEIVER=<values dir> SEED=20261014 INTERVAL=600 MIN_HOLD=240 MAX_HOLD=480 RUN_MIN=75 ./run-unattended.sh
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
T=$RESULTS/timeline.jsonl
SEED=${SEED:-20261014}; INTERVAL=${INTERVAL:-600}; MIN_HOLD=${MIN_HOLD:-240}; MAX_HOLD=${MAX_HOLD:-480}; RUN_MIN=${RUN_MIN:-75}
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
ends0=$(grep -c '"run_end"' "$T" 2>/dev/null || echo 0)
ended() { [ "$(grep -c '"run_end"' "$T" 2>/dev/null || echo 0)" != "$ends0" ]; }

if ! "$HERE/scheduler.sh" start "$SEED" "$INTERVAL" "$MIN_HOLD" "$MAX_HOLD"; then
  mark scheduler_start_failed; "$HERE/run.sh" down; exit 1
fi
s0=$(date +%s); end=$((s0 + RUN_MIN * 60))
echo "$end" > "$RESULTS/deadline"
mark scheduler_start "\"seed\":$SEED,\"interval_s\":$INTERVAL,\"min_hold_s\":$MIN_HOLD,\"max_hold_s\":$MAX_HOLD,\"planned_end\":$end"
echo "$(date -u +%FT%TZ) scheduler started; planned end $(date -u -r $end +%FT%TZ)"
while [ "$(date +%s)" -lt "$end" ]; do
  sleep 10
  ended && { echo "$(date -u +%FT%TZ) run ended before the planned end"; exit 0; }
done
mark planned_end
echo "$(date -u +%FT%TZ) planned end; stopping"
"$HERE/run.sh" down
