#!/bin/bash
# The two-arm run (research TWO_ARM_METHOD.md). Arm A is the hold of phases-r2.sh, every time constant
# divided by 6; arm B gets every line from the same Fluent Bit, routed by service (top-half.py), no Receiver.
#   0:00  up (both clusters); the numbered feed at 8x (56 lines a second); the seed policy passes every line
#   0:10  dry run with no binding size reads P (DRY_AT_S seconds overrides, for a compressed smoke); S = 0.7 x P;
#         the first hot-tier run applied; then one every 10 minutes
#   S binds at the first meter reading after that run with arm A's hot store at or above 0.95 S,
#         or at 2:10 (R after the first applied run), whichever comes first
#   bind + 40 min: one step to 20x (140 lines a second, 2.5 times the start), held 60 minutes; the feed stops
#   drain 20 minutes; ILM stopped on both clusters; every document's seq read from both; down
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:?results dir}
RUN="$HERE/run.sh"
# ARM_A_ONLY=1 runs arm A alone: no cluster B and no copy to it; Fluent Bit also keeps each returned record whole
if [ -z "${ARM_A_ONLY:-}" ]; then export ARM_B=1 ES_URL_B=http://127.0.0.1:9201; fi
export POLICY_BRANCH=${POLICY_BRANCH:-test/elastic-hot-tier-policy}
export FB_DIR=$RESULTS/fluent-bit KEEP_ROLLOVER=10m KEEP_FROZEN_AFTER=110m TD_ROLLOVER=10m ILM_POLL=100s METER_S=${METER_S:-100}
export FROZEN_CACHE=${FROZEN_CACHE:-128mb}
M=${M:-60}
BIND_SHARE=0.95
at() { local due=$(( T0 + $1 )); while [ "$(date +%s)" -lt "$due" ]; do sleep 5; done; }
[ -s "$RESULTS/arm-b-rule.json" ] || python3 "$HERE/top-half.py" "$RESULTS/replay/source.jsonl" 8 20 "$RESULTS/arm-b-rule.json" > /dev/null
python3 "$HERE/render-fb-two-arm.py" "$RESULTS/arm-b-rule.json" "$FB_DIR" > /dev/null
containers=$(python3 -c "
import json; s=set()
for l in open('$RESULTS/replay/source.jsonl'): s.add(json.loads(l)['container_name'].lstrip('/'))
print(','.join(sorted(s)))")
python3 "$HERE/record-build.py" "$RESULTS" > /dev/null
T0=$(date +%s)
"$RUN" mark run_start "\"scale\":6,\"M\":$M,\"arm_b_top_half\":$(python3 -c "import json;print(json.dumps(json.load(open('$RESULTS/arm-b-rule.json'))['top_half']))")"
SEED=$("$HERE/reset-policy-branch.sh")
"$RUN" mark policy_branch_reset_to_seed "\"commit\":\"$SEED\""
"$RUN" up
"$RUN" feed start 8
"$RUN" mark phase_baseline

at "${DRY_AT_S:-$((10 * M))}"
node "$HERE/gen-policy.mjs" "$RESULTS/policy.yaml" 1000 "$RESULTS/policy-clone" "$POLICY_BRANCH" "$containers" > /dev/null
"$HERE/budget-run.sh" --dry-run || true
dry=$(ls -td "$RESULTS"/budget-runs/* | head -1)
P=$(python3 -c "
import re; t=open('$dry/report.txt').read()
m=re.search(r'settles at about ([0-9.]+) (MB|GB)', t); v=float(m.group(1))*(1e6 if m.group(2)=='MB' else 1e9); print(v)")
python3 -c "import sys; sys.exit(0 if $P > 0 else 1)" || { "$RUN" mark size_unreadable "\"uncapped_settles_bytes\":$P"; "$RUN" down; exit 1; }
S_GB=$(python3 -c "print(round(0.7*$P/1e9, 4))")
S_BYTES=$(python3 -c "print(int($S_GB*1e9))")
"$RUN" mark size_set "\"uncapped_settles_bytes\":$P,\"hot_tier_gb\":$S_GB"
node "$HERE/gen-policy.mjs" "$RESULTS/policy.yaml" "$S_GB" "$RESULTS/policy-clone" "$POLICY_BRANCH" "$containers" > /dev/null
"$HERE/budget-run.sh" || true
HELD=$(date +%s)
"$RUN" mark phase_held

latest_a() {
  tail -n 1 "$RESULTS/meter.jsonl" 2>/dev/null | python3 -c "import json,sys
r=json.loads(sys.stdin.read()); print(r['epoch'], r['summary']['a']['hot_node_store'] or 0)" 2>/dev/null || echo "0 0"
}
next_tick=$(( T0 + 20 * M + 30 ))
bind=0; step_due=0; stepped=0; hold_end=0; drain_end=0
while :; do
  now=$(date +%s)
  if [ "$bind" = 0 ]; then
    read -r ep hs <<< "$(latest_a)"
    if [ "$ep" -gt "$HELD" ] && python3 -c "import sys; sys.exit(0 if $hs >= $BIND_SHARE * $S_BYTES else 1)"; then
      bind=$ep
      "$RUN" mark s_binds "\"rule\":\"meter reading at or above $BIND_SHARE S\",\"reading_epoch\":$ep,\"hot_store\":$hs,\"S\":$S_BYTES"
    elif [ "$now" -ge $(( T0 + 130 * M )) ]; then
      bind=$now
      "$RUN" mark s_binds "\"rule\":\"R after the first applied run\",\"hot_store\":$hs,\"S\":$S_BYTES"
    fi
    [ "$bind" != 0 ] && step_due=$(( bind + 40 * M ))
  fi
  if [ "$step_due" != 0 ] && [ "$stepped" = 0 ] && [ "$now" -ge "$step_due" ]; then
    "$RUN" feed speed 20
    stepped=$(date +%s); hold_end=$(( stepped + 60 * M ))
    "$RUN" mark phase_step "\"speed\":20"
  fi
  if [ "$stepped" != 0 ] && [ "$drain_end" = 0 ] && [ "$now" -ge "$hold_end" ]; then
    "$RUN" feed stop
    "$RUN" mark phase_drain
    drain_end=$(( $(date +%s) + 20 * M ))
  fi
  [ "$drain_end" != 0 ] && [ "$now" -ge "$drain_end" ] && break
  if [ "$now" -ge "$next_tick" ]; then
    "$HERE/budget-run.sh" || true
    next_tick=$(( next_tick + 10 * M ))
  fi
  sleep 5
done

"$RUN" logs
curl -s -m 30 -X POST http://127.0.0.1:9200/_ilm/stop > /dev/null; [ -z "${ARM_B:-}" ] || curl -s -m 30 -X POST http://127.0.0.1:9201/_ilm/stop > /dev/null
"$RUN" mark ilm_stopped
mkdir -p "$RESULTS/delivery"
python3 "$HERE/dump-seq.py" http://127.0.0.1:9200 tenx-app,tenx-tierdown "$RESULTS/delivery/a.tsv.gz" > "$RESULTS/delivery/a.json" || true
[ -z "${ARM_B:-}" ] || python3 "$HERE/dump-seq.py" http://127.0.0.1:9201 native-app,native-overflow "$RESULTS/delivery/b.tsv.gz" > "$RESULTS/delivery/b.json" || true
for p in 9200 ${ARM_B:+9201}; do
  curl -s -m 60 "http://127.0.0.1:$p/_cat/indices?format=json&bytes=b&expand_wildcards=all&h=index,health,status,docs.count,store.size,creation.date" > "$RESULTS/delivery/cat-indices-$p.json" || true
  curl -s -m 60 "http://127.0.0.1:$p/_alias?filter_path=*.aliases" > "$RESULTS/delivery/aliases-$p.json" || true
done
"$RUN" mark delivery_read
"$RUN" down
