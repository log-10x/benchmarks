#!/bin/bash
# The compressed rerun, every time constant divided by 6.
#   0:00  up; replay at 8x (56 lines a second); the seed policy passes every line
#   0:10  dry run with no binding size reads P; S = 0.7 x P; the first hot-tier run applied; then one every 10 minutes
#   2:10  load steps every 20 minutes: 11x, 14x, 17x, 20x at 3:10 (2.5 times the start); new service at 2:30;
#         storm (the Grafana error line, 10 a second) for 5 minutes at 2:50
#   4:10  load stops; 4:30 down
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:?results dir}
RUN="$HERE/run.sh"
export POLICY_BRANCH=${POLICY_BRANCH:-test/elastic-hot-tier-policy}
export FB_DIR=$HERE/fluent-bit-slim KEEP_ROLLOVER=10m KEEP_FROZEN_AFTER=110m TD_ROLLOVER=3m ILM_POLL=100s METER_S=100
M=60
at() { local due=$(( T0 + $1 )); while [ "$(date +%s)" -lt "$due" ]; do sleep 10; done; }
containers=$(python3 -c "
import json; s=set()
for l in open('$RESULTS/replay/source.jsonl'): s.add(json.loads(l)['container_name'].lstrip('/'))
s.add('inventory'); print(','.join(sorted(s)))")
T0=$(date +%s)
"$RUN" mark run_start "\"scale\":6"
SEED=$("$HERE/reset-policy-branch.sh")
"$RUN" mark policy_branch_reset_to_seed "\"commit\":\"$SEED\""
"$RUN" up
"$RUN" replay start 8
"$RUN" mark phase_baseline

at $((10 * M))
node "$HERE/gen-policy.mjs" "$RESULTS/policy.yaml" 1000 "$RESULTS/policy-clone" "$POLICY_BRANCH" "$containers" > /dev/null
"$HERE/budget-run.sh" --dry-run || true
dry=$(ls -td "$RESULTS"/budget-runs/* | head -1)
P=$(python3 -c "
import re; t=open('$dry/report.txt').read()
m=re.search(r'settles at about ([0-9.]+) (MB|GB)', t); v=float(m.group(1))*(1e6 if m.group(2)=='MB' else 1e9); print(v)")
python3 -c "import sys; sys.exit(0 if $P > 0 else 1)" || { "$RUN" mark size_unreadable "\"uncapped_settles_bytes\":$P"; "$RUN" down; exit 1; }
S_GB=$(python3 -c "print(round(0.7*$P/1e9, 4))")
"$RUN" mark size_set "\"uncapped_settles_bytes\":$P,\"hot_tier_gb\":$S_GB"
node "$HERE/gen-policy.mjs" "$RESULTS/policy.yaml" "$S_GB" "$RESULTS/policy-clone" "$POLICY_BRANCH" "$containers" > /dev/null
"$HERE/budget-run.sh" || true
"$RUN" mark phase_held

step() {
  read -r rs speed off < "$RESULTS/replay.state"
  OFFSET=$(python3 -c "print(round($off + ($(date +%s) - $rs) * $speed, 1))")
  "$RUN" replay stop; "$RUN" replay start "$1" "$OFFSET"
}
# ticks every 10 minutes from 0:20 to 4:20; load steps on their own schedule
for t in $(seq 20 10 260); do
  case $t in
    130) at $((130 * M)); step 11; "$RUN" mark phase_growth ;;
    150) at $((150 * M)); step 14; "$RUN" inject start ;;
    170) at $((170 * M)); step 17; "$RUN" storm 10 $(( $(date +%s) + 300 )); "$RUN" mark phase_storm ;;
    190) at $((190 * M)); step 20 ;;
    250) at $((250 * M)); "$RUN" replay stop; "$RUN" inject stop; "$RUN" mark phase_drain ;;
  esac
  at $((t * M + 30))
  "$HERE/budget-run.sh" || true
done

at $((270 * M))
"$RUN" down
