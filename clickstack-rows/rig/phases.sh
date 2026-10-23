#!/usr/bin/env bash
# The compressed run, as ROWS_RUN_METHOD.md pre-registers it (every clock divided by 6).
# Minutes from T0:
#    0  up; replay at 2x the capture's pace (14 lines/s)
#   30  dry run with rows_per_hour auto -> P; R = 0.7 P written to policy.yaml
#   40  first applied run; then a run every 10 minutes to the end
#   60  2.75x (19 l/s)      80  3.5x (24.5 l/s) + inject      100  4.25x (30 l/s) + storm 20 min
#  120  5x (35 l/s), held to 160
#  160  replay and inject stop; drain
#  180  last run, collect, down
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RUN="$HERE/run.sh"
RESULTS=${RESULTS:-$HERE/../results}
export RESULTS
: "${MCP:?log10x-mcp checkout with build/}"
: "${GH_TOKEN:?export GH_TOKEN=\$(gh auth token)}"
export POLICY_BRANCH=${POLICY_BRANCH:-test/clickhouse-rows-policy}
M=${M:-60}                       # seconds per "minute"; 60 is the run, 6 a smoke
METER_MIN=${METER_MIN:-10}       # the meter window in real minutes: 10 for the run, 1 for a smoke
export CAPTURE=${CAPTURE:-$HERE/../../../benchmarks/clickstack-e2e/data/otel-sample-200mb.log}
T0=$(date +%s); echo "$T0" > "$RESULTS/t0"
at() { local due=$(( T0 + $1 * M )); while [ "$(date +%s)" -lt "$due" ]; do sleep 5; done; }
tick() { "$HERE/budget-run.sh" "$@" || true; }
containers() {
  python3 - "$CAPTURE" <<'EOF'
import json,sys,collections
c=collections.Counter()
with open(sys.argv[1], errors='replace') as fh:
    for i,l in enumerate(fh):
        if i>60000: break
        try: c[json.loads(l)['kubernetes']['container_name']]+=1
        except Exception: pass
print(','.join(sorted(c)) + ',inventory')
EOF
}

"$RUN" up
"$RUN" mark phase_baseline
"$RUN" pace 14
CONTAINERS=$(containers)
node "$HERE/gen-policy.mjs" "$RESULTS/policy.yaml" auto "$RESULTS/policy-clone" "$POLICY_BRANCH" "$CONTAINERS" "$METER_MIN" > /dev/null

at 30;  tick --dry-run; "$RUN" mark dry_run_done
# R = 0.7 x P, P the dry run's meter hour (rowsLastHour in the report line "Rows written: W of R")
P=$(python3 - "$RESULTS" <<'EOF'
import json,sys,glob,os,re
d=sorted(glob.glob(os.path.join(sys.argv[1],'budget-runs','*')))[-1]
txt=open(os.path.join(d,'report.txt')).read()
m=re.search(r'Rows written: ([0-9.]+)([kM]?) of', txt)
v=float(m.group(1))*{'':1,'k':1e3,'M':1e6}[m.group(2)] if m else 0
print(int(v))
EOF
)
if [ "${P:-0}" -le 0 ]; then
  "$RUN" mark dry_run_read_nothing; "$RUN" collect; "$RUN" down
  echo "the dry run measured no rows (see budget-runs/*/report.txt); stopping" >&2; exit 1
fi
R=$(python3 -c "print(int(0.7*$P))")
"$RUN" mark rate_set "\"P\":$P,\"R\":$R"
node "$HERE/gen-policy.mjs" "$RESULTS/policy.yaml" "$R" "$RESULTS/policy-clone" "$POLICY_BRANCH" "$CONTAINERS" "$METER_MIN" > /dev/null

at 40;  tick; "$RUN" mark phase_held
at 50;  tick
at 60;  "$RUN" pace 19; tick; "$RUN" mark phase_growth
at 70;  tick
at 80;  "$RUN" pace 24; "$RUN" inject start; tick
at 90;  tick
at 100; "$RUN" pace 30; "$RUN" storm 10 $(( $(date +%s) + 20 * M )); tick; "$RUN" mark phase_storm
at 110; tick
at 120; "$RUN" pace 35; tick; "$RUN" mark phase_hold_5x
at 130; tick
at 140; tick
at 150; tick
at 160; "$RUN" pace 0; "$RUN" inject stop; tick; "$RUN" mark phase_drain
at 170; tick
at 180; tick; "$RUN" collect
python3 "$HERE/score.py" "$RESULTS" > "$RESULTS/score.md" 2> "$RESULTS/score.err" || true
if python3 "$HERE/final.py" "$RESULTS" cse-clickstack > "$RESULTS/final.md" 2> "$RESULTS/final.err"; then
  "$RUN" down
else
  "$RUN" mark final_failed_containers_kept
  echo "final.py failed; containers left up for a rerun (rig/final.py \$RESULTS cse-clickstack), then rig/run.sh down" >&2
fi
