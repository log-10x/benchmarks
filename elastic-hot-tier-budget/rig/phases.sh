#!/bin/bash
# The run, as written in the method before it started. Run detached (detach.py), with MCP and GH_TOKEN set.
#   0:00  up; replay at 2x (14 lines a second); the seed policy passes every line
#   1:00  a dry run with no binding size reads where hot would settle uncapped (P); S = 0.7 x P;
#         policy.yaml written with hot_tier_gb = S; the first hot-tier run applied; then one every hour
#   7:00  (one hot retention after the first run) load steps up each hour: 2.75x, 3.5x, 4.25x, 5x at 10:00
#   8:00  a new service injected; 9:00 error storm, 10 lines a second for 20 minutes
#   13:00 load stops; 14:00 down
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
RUN="$HERE/run.sh"
export POLICY_BRANCH=${POLICY_BRANCH:-test/elastic-hot-tier-policy}
HOUR=${HOUR:-3600}
at() { local due=$(( T0 + $1 )); while [ "$(date +%s)" -lt "$due" ]; do sleep 20; done; }
containers=$(python3 -c "
import json; s=set()
for l in open('$RESULTS/replay/source.jsonl'): s.add(json.loads(l)['container_name'].lstrip('/'))
s.add('inventory'); print(','.join(sorted(s)))")
T0=$(date +%s)
"$RUN" mark run_start "\"hour_s\":$HOUR"
"$RUN" up
"$RUN" replay start 2
"$RUN" mark phase_baseline

at $((1 * HOUR))
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
for h in 2 3 4 5 6 7 8 9 10 11 12 13; do
  case $h in
    7)  at $((7 * HOUR));  step 2.75; "$RUN" mark phase_growth ;;
    8)  at $((8 * HOUR));  step 3.5; "$RUN" inject start ;;
    9)  at $((9 * HOUR));  step 4.25; "$RUN" storm 10 $(( $(date +%s) + 1200 )); "$RUN" mark phase_storm ;;
    10) at $((10 * HOUR)); step 5 ;;
    13) at $((13 * HOUR)); "$RUN" replay stop; "$RUN" inject stop; "$RUN" mark phase_drain ;;
  esac
  at $((h * HOUR + 120))
  "$HERE/budget-run.sh" || true
done

at $((14 * HOUR))
"$RUN" down
