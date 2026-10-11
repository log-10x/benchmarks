#!/usr/bin/env bash
#
# Datadog Flex Logs accounting: what the released engine moves to Flex under the plan the
# released MCP writes, counted two ways and priced at Datadog list prices. Nothing is
# sent to Datadog.
#
#   ./run.sh                  everything
#   ./run.sh plan replay      some stages only, in the order given
#
# Stages: data plan control policy replay count metrics report
#
# Environment:
#   ACCT_TARGETS   percent targets to plan (default: "30 50 70")
#   ACCT_WINDOW    the span the capture covers, passed to the MCP (default: 10h)
#   ACCT_DATA_DIR  capture cache (default: <dir>/data)
#   ACCT_IMAGE     engine image (default: log10x/pipeline-10x:1.1.140, by digest)
#   ACCT_MCP       log10x-mcp version (default: 1.30.48)
#   ACCT_MCP_TARBALL  a local `npm pack` of log10x-mcp to install instead (its version must match)

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
LIB="$(cd "$HERE/../accounting-lib" && pwd)"
# shellcheck source=../accounting-lib/engine.sh
. "$LIB/engine.sh"

SIEM=datadog
TARGETS="${ACCT_TARGETS:-30 50 70}"
WINDOW="${ACCT_WINDOW:-10h}"
DATA_DIR="${ACCT_DATA_DIR:-$HERE/data}"
IMAGE="${ACCT_IMAGE:-log10x/pipeline-10x:1.1.140@sha256:fd9c98384a775df13ed41921c2cf95ef1d1313f62f1300aac61da55ca64feb67}"
MCP_VERSION="${ACCT_MCP:-1.30.48}"
MCP_TARBALL="${ACCT_MCP_TARBALL:-}"
MCP_DIR="$HERE/.mcp"
MCP_HOME="$HERE/.mcp/home"
RESULTS="$HERE/results"
RUNS="$HERE/runs"
CAPTURE="$DATA_DIR/$ASSET"
WINDOW_SECONDS="$(python3 -c "import re;m=re.fullmatch(r'(\d+)([hm])','$WINDOW');print(int(m.group(1))*(3600 if m.group(2)=='h' else 60))")"
mkdir -p "$RESULTS" "$RUNS"

stage_data() { say "public capture"; fetch_capture "$DATA_DIR"; say "engine image"; pull_engine; }

stage_plan() {
  say "the MCP's plan"; install_mcp
  for t in $TARGETS; do plan "$SIEM" "$t" "$RESULTS/plan-$t.json"; done
}

stage_control() {
  say "control: the capture through the Receiver with no cap"
  replay "$CAPTURE" "$RUNS/control"
  python3 "$LIB/count.py" --routed "$RUNS/control/routed.jsonl" --summaries "$RUNS/control/summaries.jsonl" \
    --seconds "$(cat "$RUNS/control/seconds.txt")" --out "$RESULTS/control.tally.json"
}

stage_policy() {
  say "the engine files the tool wrote, caps scaled to the one-window replay"
  for t in $TARGETS; do
    python3 "$LIB/policy.py" --plan "$RESULTS/plan-$t.json" --out-prefix "$RESULTS/policy-$t"
  done
}

stage_replay() {
  for t in $TARGETS; do
    say "replay, target $t%"
    replay "$CAPTURE" "$RUNS/$t" "$RESULTS/policy-$t.caps.csv" "$RESULTS/policy-$t.actions.csv"
  done
}

stage_count() {
  say "count, two ways"
  for t in $TARGETS; do
    python3 "$LIB/count.py" --routed "$RUNS/$t/routed.jsonl" --summaries "$RUNS/$t/summaries.jsonl" \
      --seconds "$(cat "$RUNS/$t/seconds.txt")" --out "$RESULTS/$t.tally.json"
  done
}

# The engine's shipped Datadog metric output, posting to a local stand-in for Datadog's
# intake (../accounting-lib/ddcapture.py). The one change to the image's own config is the
# URI the output posts to; results/datadog-config.diff records it.
CAPTURE_IMAGE="python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
metrics_replay() {
  local name="$1" caps="${2:-}" actions="${3:-}"
  local out="$RUNS/metrics-$name" net="acct-dd" srv="acct-ddcapture-$name"
  rm -rf "$out"; mkdir -p "$out/data" "$out/ddcfg"
  docker run --rm --entrypoint cat "$IMAGE" /etc/tenx/config/pipelines/run/output/metric/datadog/config.yaml > "$out/ddcfg/config.yaml"
  cp "$out/ddcfg/config.yaml" "$out/config.shipped.yaml"
  python3 "$LIB/datadog_config.py" --shipped "$out/config.shipped.yaml" --out "$out/ddcfg/config.yaml" \
    --replay "$LIB/replay.config.yaml" --replay-out "$out/replay.yaml"
  diff "$out/config.shipped.yaml" "$out/ddcfg/config.yaml" > "$RESULTS/datadog-config.diff" || true
  docker network create "$net" >/dev/null 2>&1 || true
  docker rm -f "$srv" >/dev/null 2>&1 || true
  docker run -d --name "$srv" --network "$net" --network-alias ddcapture \
    -v "$LIB/ddcapture.py":/srv/ddcapture.py:ro -v "$out/data":/data "$CAPTURE_IMAGE" python /srv/ddcapture.py >/dev/null
  sleep 2
  local envs=(-e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out -e DD_API_KEY=not-a-key -e DD_APP_KEY=not-a-key)
  local vols=(-v "$CAPTURE":/in/events.log:ro -v "$out":/out -v "$out/replay.yaml":/cfg/replay.yaml:ro
              -v "$out/ddcfg/config.yaml":/etc/tenx/config/pipelines/run/output/metric/datadog/config.yaml:ro)
  if [ -n "$caps" ]; then
    mkdir -p "$out/policy"; cp "$caps" "$out/policy/caps.csv"; cp "$actions" "$out/policy/actions.csv"
    envs+=(-e CAP_LOOKUP_FILE=/policy/caps.csv -e ACTION_LOOKUP_FILE=/policy/actions.csv)
    vols+=(-v "$out/policy":/policy:ro)
  fi
  docker run --rm --network "$net" "${envs[@]}" "${vols[@]}" "$IMAGE" @/cfg/replay.yaml rateReceiverWarmupMs 0 \
    > "$out/engine.log" 2>&1 || { docker rm -f "$srv" >/dev/null; tail -20 "$out/engine.log"; die "engine run failed"; }
  sleep 3
  docker rm -f "$srv" >/dev/null
  python3 "$LIB/datadog_series.py" --posts "$out/data/posts.jsonl" --out "$RESULTS/datadog-series-$name.json"
}

stage_metrics() {
  say "the Datadog metric output, posting to a local stand-in"
  metrics_replay control
  for t in $TARGETS; do metrics_replay "$t" "$RESULTS/policy-$t.caps.csv" "$RESULTS/policy-$t.actions.csv"; done
}

stage_report() {
  say "report"
  pull_engine >/dev/null
  python3 - "$RESULTS/run.json" "$IMAGE_DIGEST" "${IMAGE%@*}" "$MCP_VERSION" "$ASSET" "$ASSET_SHA256" "$ASSET_BYTES" "$ASSET_LINES" "$WINDOW_SECONDS" $TARGETS <<'PY'
import json, sys
out, image, ref, mcp, asset, sha, b, n, w, *targets = sys.argv[1:]
json.dump({'engine_image': image, 'engine_tag': ref.rsplit(':', 1)[-1], 'mcp_version': mcp,
           'capture': {'name': asset, 'sha256': sha, 'bytes': int(b), 'lines': int(n)},
           'window_hours': int(w) / 3600, 'targets': [int(t) for t in targets]}, open(out, 'w'), indent=1)
PY
  python3 "$HERE/report.py" --results "$RESULTS"
  python3 "$HERE/report.py" --results "$RESULTS" --check
}

if [ "$#" -gt 0 ]; then STAGES=("$@"); else STAGES=(data plan control policy replay count metrics report); fi
for s in "${STAGES[@]}"; do "stage_$s"; done
say "done. results in $RESULTS"
