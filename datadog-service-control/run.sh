#!/usr/bin/env bash
#
# One service, two captures of the same code: the kafka container's records from two public
# captures of the OpenTelemetry demo, a per-pattern plan against an index filter per logger
# class, counted from the released engine's own output. Nothing is sent to Datadog.
#
#   ./run.sh                  everything
#   ./run.sh plan replay      some stages only, in the order given
#
# Stages: data plan control policy replay count report       (one service, the kafka slices)
#         floor-plan floor-replay floor-count                  (the floor, the whole captures)
#
# Environment:
#   ACCT_TARGETS   percent targets to plan on the slices (default: "30 50 70 90")
#   FLOOR_TARGET   the plan's target on the whole captures (default: 70, the target whose
#                  service filters form the floor)
#   ACCT_DATA_DIR  capture cache (default: <dir>/data)
#   ACCT_IMAGE     engine image (default: log10x/pipeline-10x:1.1.140, by digest)
#   ACCT_MCP       log10x-mcp version (default: 1.30.49)
#   ACCT_MCP_TARBALL  a local `npm pack` of log10x-mcp to install instead (its version must match)

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
LIB="$(cd "$HERE/../accounting-lib" && pwd)"
# shellcheck source=../accounting-lib/engine.sh
. "$LIB/engine.sh"

SIEM=datadog
CONTAINER=kafka
TARGETS="${ACCT_TARGETS:-30 50 70 90}"
FLOOR_TARGET="${FLOOR_TARGET:-70}"
DATA_DIR="${ACCT_DATA_DIR:-$HERE/data}"
IMAGE="${ACCT_IMAGE:-log10x/pipeline-10x:1.1.140@sha256:fd9c98384a775df13ed41921c2cf95ef1d1313f62f1300aac61da55ca64feb67}"
MCP_VERSION="${ACCT_MCP:-1.30.49}"
MCP_TARBALL="${ACCT_MCP_TARBALL:-}"
MCP_DIR="$HERE/.mcp"
MCP_HOME="$HERE/.mcp/home"
RESULTS="$HERE/results"
RUNS="$HERE/runs"
mkdir -p "$RESULTS" "$RUNS"

# Capture A is the asset engine.sh fetches (otel-sample-v1, 10 hours, demo 2.1.3). Capture B is
# the intent benchmark's recording (intent-data-v1, 2 hours, demo 2.2.0).
B_URL="https://github.com/log-10x/benchmarks/releases/download/intent-data-v1/rec1155.log.gz"
B_ASSET="rec1155.log"
B_GZ_SHA256="d9ebe8c79e3ef6c1ca656599203d588831b6ed72e1f245cc32cd26124b6c4301"
B_SHA256="df78e200d929bc57f826a396fb8e1764717bf6b61544970261f3647163351b77"
B_BYTES=51439789
B_LINES=41713
A_SPAN=36000
B_SPAN=7200
# The kafka slices, byte for byte, as slice.py writes them.
A_SLICE_SHA256="eb6dea993e84a2d0519ef9f0ccbae7ea79599bec86602297751a806035b19557"
B_SLICE_SHA256="9d5c92ccca38e75c83d464731c85662f6d0f2199d3334b49ca358497a5dc69a5"
SLICE_A="$DATA_DIR/kafka-A.log"
SLICE_B="$DATA_DIR/kafka-B.log"
# The shared replay config with one field added to the routed records: each event's source
# records, from which classes.py reads the logger class. results/replay-config.diff records it.
REPLAY_CONFIG="$RUNS/replay.config.yaml"

fetch_b() {
  if [ -f "$DATA_DIR/$B_ASSET" ] && [ "$(sha256 "$DATA_DIR/$B_ASSET")" = "$B_SHA256" ]; then
    echo "$DATA_DIR/$B_ASSET present, sha256 matches"; return
  fi
  curl -fsSL "$B_URL" -o "$DATA_DIR/$B_ASSET.gz"
  [ "$(sha256 "$DATA_DIR/$B_ASSET.gz")" = "$B_GZ_SHA256" ] || die "rec1155.log.gz sha256 does not match"
  gunzip -kf "$DATA_DIR/$B_ASSET.gz"
  [ "$(sha256 "$DATA_DIR/$B_ASSET")" = "$B_SHA256" ] || die "rec1155.log sha256 does not match"
  [ "$(wc -c < "$DATA_DIR/$B_ASSET" | tr -d ' ')" = "$B_BYTES" ] || die "rec1155.log byte count differs"
  [ "$(wc -l < "$DATA_DIR/$B_ASSET" | tr -d ' ')" = "$B_LINES" ] || die "rec1155.log line count differs"
}

replay_config() {
  python3 - "$LIB/replay.config.yaml" "$REPLAY_CONFIG" <<'PY'
import sys
src, out = sys.argv[1:3]
t = open(src).read()
old = "      - utf8Size()\n"
assert t.count(old) == 1, 'the shared replay config changed shape'
open(out, 'w').write(t.replace(old, old + "      - fullText\n"))
PY
  diff "$LIB/replay.config.yaml" "$REPLAY_CONFIG" > "$RESULTS/replay-config.diff" || true
}

stage_data() {
  say "public captures"
  fetch_capture "$DATA_DIR"; fetch_b
  say "the $CONTAINER slices"
  python3 "$HERE/slice.py" --capture "$DATA_DIR/$ASSET" --container "$CONTAINER" --out "$SLICE_A" > "$RESULTS/slice-A.json"
  python3 "$HERE/slice.py" --capture "$DATA_DIR/$B_ASSET" --container "$CONTAINER" --out "$SLICE_B" > "$RESULTS/slice-B.json"
  [ "$(sha256 "$SLICE_A")" = "$A_SLICE_SHA256" ] || die "capture A's kafka slice differs"
  [ "$(sha256 "$SLICE_B")" = "$B_SLICE_SHA256" ] || die "capture B's kafka slice differs"
  cat "$RESULTS/slice-A.json" "$RESULTS/slice-B.json"
  say "engine image"; pull_engine
}

stage_plan() {
  say "the MCP's plans"; install_mcp
  for t in $TARGETS; do
    CAPTURE="$SLICE_A" WINDOW=10h plan "$SIEM" "$t" "$RESULTS/plan-A-$t.json"
    CAPTURE="$SLICE_B" WINDOW=2h plan "$SIEM" "$t" "$RESULTS/plan-B-$t.json"
  done
}

stage_control() {
  replay_config
  for c in A B; do
    say "control: capture $c's slice through the Receiver with no cap"
    local slice="$SLICE_A"; [ "$c" = B ] && slice="$SLICE_B"
    REPLAY_CONFIG="$REPLAY_CONFIG" replay "$slice" "$RUNS/control-$c"
  done
}

stage_policy() {
  say "the engine files the tool wrote, caps scaled to the one-window replay"
  for t in $TARGETS; do
    python3 "$LIB/policy.py" --plan "$RESULTS/plan-A-$t.json" --out-prefix "$RESULTS/policy-A-$t"
    python3 "$LIB/policy.py" --plan "$RESULTS/plan-A-$t.json" --out-prefix "$RESULTS/policy-AonB-$t" \
      --plan-span-seconds "$A_SPAN" --replay-span-seconds "$B_SPAN"
    python3 "$LIB/policy.py" --plan "$RESULTS/plan-B-$t.json" --out-prefix "$RESULTS/policy-B-$t"
  done
}

stage_replay() {
  replay_config
  for t in $TARGETS; do
    say "replay, target $t%: A's plan on A, A's cap on B, B's plan on B"
    REPLAY_CONFIG="$REPLAY_CONFIG" replay "$SLICE_A" "$RUNS/A-$t" "$RESULTS/policy-A-$t.caps.csv" "$RESULTS/policy-A-$t.actions.csv"
    REPLAY_CONFIG="$REPLAY_CONFIG" replay "$SLICE_B" "$RUNS/AonB-$t" "$RESULTS/policy-AonB-$t.caps.csv" "$RESULTS/policy-AonB-$t.actions.csv"
    REPLAY_CONFIG="$REPLAY_CONFIG" replay "$SLICE_B" "$RUNS/B-$t" "$RESULTS/policy-B-$t.caps.csv" "$RESULTS/policy-B-$t.actions.csv"
  done
}

stage_count() {
  say "count, two ways, and the logger class of every event"
  local runs=(control-A control-B)
  for t in $TARGETS; do runs+=("A-$t" "AonB-$t" "B-$t"); done
  for r in "${runs[@]}"; do
    python3 "$LIB/count.py" --routed "$RUNS/$r/routed.jsonl" --summaries "$RUNS/$r/summaries.jsonl" \
      --seconds "$(cat "$RUNS/$r/seconds.txt")" --out "$RESULTS/$r.tally.json"
    python3 "$HERE/classes.py" --routed "$RUNS/$r/routed.jsonl" --tally "$RESULTS/$r.tally.json" --out "$RESULTS/$r.classes.json"
  done
}

# The floor: each whole capture after a buyer's own levers. The plan at FLOOR_TARGET on the
# whole capture says which patterns it moves and keeps; the control run, with each event's
# text, gives the attributes a native filter could name.
capture_file() { [ "$1" = A ] && echo "$DATA_DIR/$ASSET" || echo "$DATA_DIR/$B_ASSET"; }

stage_floor-plan() {
  say "the MCP's plan on each whole capture, target $FLOOR_TARGET%"; install_mcp
  CAPTURE="$(capture_file A)" WINDOW=10h plan "$SIEM" "$FLOOR_TARGET" "$RESULTS/plan-full-A-$FLOOR_TARGET.json"
  CAPTURE="$(capture_file B)" WINDOW=2h plan "$SIEM" "$FLOOR_TARGET" "$RESULTS/plan-full-B-$FLOOR_TARGET.json"
  for c in A B; do
    python3 "$LIB/policy.py" --plan "$RESULTS/plan-full-$c-$FLOOR_TARGET.json" --out-prefix "$RESULTS/policy-full-$c-$FLOOR_TARGET"
  done
}

stage_floor-replay() {
  replay_config
  for c in A B; do
    say "capture $c whole: no cap, with each event's text; then the plan's files"
    REPLAY_CONFIG="$REPLAY_CONFIG" replay "$(capture_file "$c")" "$RUNS/full-$c-control"
    replay "$(capture_file "$c")" "$RUNS/full-$c-$FLOOR_TARGET" \
      "$RESULTS/policy-full-$c-$FLOOR_TARGET.caps.csv" "$RESULTS/policy-full-$c-$FLOOR_TARGET.actions.csv"
  done
}

stage_floor-count() {
  say "count the whole captures, two ways, each event's native attributes and the text signals"
  for c in A B; do
    for r in "full-$c-control" "full-$c-$FLOOR_TARGET"; do
      python3 "$LIB/count.py" --routed "$RUNS/$r/routed.jsonl" --summaries "$RUNS/$r/summaries.jsonl" \
        --seconds "$(cat "$RUNS/$r/seconds.txt")" --out "$RESULTS/$r.tally.json"
    done
    python3 "$HERE/attrs.py" --routed "$RUNS/full-$c-control/routed.jsonl" --tally "$RESULTS/full-$c-control.tally.json" \
      --integrations "$HERE/integrations.json" --out "$RESULTS/full-$c-control.attrs.json"
    python3 "$HERE/text.py" --routed "$RUNS/full-$c-control/routed.jsonl" --tally "$RESULTS/full-$c-control.tally.json" \
      --plan "$RESULTS/full-$c-$FLOOR_TARGET.tally.json" --out "$RESULTS/full-$c-control.text.json"
  done
}

stage_report() {
  say "report"
  pull_engine >/dev/null
  python3 - "$RESULTS/run.json" "$IMAGE_DIGEST" "${IMAGE%@*}" "$MCP_VERSION" "$ASSET" "$ASSET_SHA256" "$B_ASSET" "$B_SHA256" "$A_SPAN" "$B_SPAN" "$FLOOR_TARGET" $TARGETS <<'PY'
import json, sys
out, image, ref, mcp, a, a_sha, b, b_sha, a_span, b_span, floor_target, *targets = sys.argv[1:]
json.dump({'engine_image': image, 'engine_tag': ref.rsplit(':', 1)[-1], 'mcp_version': mcp, 'floor_target': int(floor_target),
           'captures': {'A': {'name': a, 'sha256': a_sha, 'span_seconds': int(a_span)},
                        'B': {'name': b, 'sha256': b_sha, 'span_seconds': int(b_span)}},
           'targets': [int(t) for t in targets]}, open(out, 'w'), indent=1)
PY
  python3 "$HERE/report.py" --results "$RESULTS"
  python3 "$HERE/report.py" --results "$RESULTS" --check
}

if [ "$#" -gt 0 ]; then STAGES=("$@"); else STAGES=(data plan control policy replay count report); fi
for s in "${STAGES[@]}"; do "stage_$s"; done
say "done. results in $RESULTS"
