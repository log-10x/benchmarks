#!/usr/bin/env bash
#
# CloudWatch Infrequent Access accounting: what the released engine moves to IA and S3 under the plan the
# released MCP writes, counted two ways and priced at AWS list prices. Nothing is
# sent to AWS.
#
#   ./run.sh                  everything
#   ./run.sh plan replay      some stages only, in the order given
#
# Stages: data plan control policy replay count report
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

SIEM=cloudwatch
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
  for t in $TARGETS; do plan "$SIEM" "$t" "$RESULTS/plan-$t.json" retriever_installed=true; done
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

stage_report() {
  say "report"
  pull_engine >/dev/null
  python3 - "$RESULTS/run.json" "$IMAGE_DIGEST" "$MCP_VERSION" "$ASSET" "$ASSET_SHA256" "$ASSET_BYTES" "$ASSET_LINES" "$WINDOW_SECONDS" $TARGETS <<'PY'
import json, sys
out, image, mcp, asset, sha, b, n, w, *targets = sys.argv[1:]
json.dump({'engine_image': image, 'mcp_version': mcp,
           'capture': {'name': asset, 'sha256': sha, 'bytes': int(b), 'lines': int(n)},
           'window_hours': int(w) / 3600, 'targets': [int(t) for t in targets]}, open(out, 'w'), indent=1)
PY
  python3 "$HERE/report.py" --results "$RESULTS"
  python3 "$HERE/report.py" --results "$RESULTS" --check
}

if [ "$#" -gt 0 ]; then STAGES=("$@"); else STAGES=(data plan control policy replay count report); fi
for s in "${STAGES[@]}"; do "stage_$s"; done
say "done. results in $RESULTS"
