#!/usr/bin/env bash
#
# One command. Fetches the two captures, runs each engine image and the Drain3
# arm over them, scores every run against the labels, and writes results/.
#
#   ./run.sh
#
# Needs Docker, curl and python3 (3.13 recorded; the Drain3 arm builds its own
# virtualenv from ../pattern-identity/requirements.txt).
#
# Environment:
#   INTENT_ENGINES   space-separated engine images to run (default: the two
#                    pinned below). Any image tag or digest of
#                    log10x/pipeline-10x works; results are named after the
#                    part after the last ':' or '@'.
#   INTENT_CACHE     where inputs and engine output go (default: ./cache)
#   INTENT_PYTHON    interpreter for the Drain3 virtualenv (default: python3)
#
# Timings on an Intel macOS laptop with Docker Desktop: about 10 minutes per
# engine run on otel215 (the dev app prints its metrics as it goes), 1 minute
# on rec1155; Drain3 about 1 minute on rec1155 and 5 on otel215 per arm.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

CACHE="${INTENT_CACHE:-$HERE/cache}"
PY="${INTENT_PYTHON:-python3}"
VENV="$HERE/.venv"
ENGINES="${INTENT_ENGINES:-log10x/pipeline-10x:1.1.132@sha256:3e21cd41cde6d8263b5fa1b121ff15587a6bfe33ca4b3338b08bbb8c0e7a0c5f log10x/pipeline-10x:1.1.133@sha256:fe3dcdefdc2f42fa7117c4f63fe97b28508fbf1356725422703f0dfab55f2360}"

OTEL_URL="https://github.com/log-10x/config/releases/download/otel-sample-v1/otel-sample-200mb.log.gz"
OTEL_GZ_SHA="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
OTEL_SHA="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
REC_URL="https://github.com/log-10x/benchmarks/releases/download/intent-data-v1/rec1155.log.gz"
REC_GZ_SHA="d9ebe8c79e3ef6c1ca656599203d588831b6ed72e1f245cc32cd26124b6c4301"
REC_SHA="df78e200d929bc57f826a396fb8e1764717bf6b61544970261f3647163351b77"

say() { printf '\n=== %s\n' "$*"; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }

mkdir -p "$CACHE" results

# ------------------------------------------------------------------- inputs
if [ ! -f "$CACHE/otel215.log" ] || [ "$(sha "$CACHE/otel215.log")" != "$OTEL_SHA" ]; then
  say "otel215: downloading the otel-sample-v1 release asset"
  curl -fsSL "$OTEL_URL" -o "$CACHE/otel215.log.gz"
  [ "$(sha "$CACHE/otel215.log.gz")" = "$OTEL_GZ_SHA" ] || { echo "otel215 download hash mismatch"; exit 1; }
  gunzip -c "$CACHE/otel215.log.gz" > "$CACHE/otel215.log"
  rm -f "$CACHE/otel215.log.gz"
fi
[ "$(sha "$CACHE/otel215.log")" = "$OTEL_SHA" ] || { echo "otel215 hash mismatch"; exit 1; }

if [ ! -f "$CACHE/rec1155.log" ] || [ "$(sha "$CACHE/rec1155.log")" != "$REC_SHA" ]; then
  say "rec1155: downloading the intent-data-v1 release asset"
  curl -fsSL "$REC_URL" -o "$CACHE/rec1155.log.gz"
  [ "$(sha "$CACHE/rec1155.log.gz")" = "$REC_GZ_SHA" ] || { echo "rec1155 download hash mismatch"; exit 1; }
  gunzip -c "$CACHE/rec1155.log.gz" > "$CACHE/rec1155.log"
  rm -f "$CACHE/rec1155.log.gz"
fi
[ "$(sha "$CACHE/rec1155.log")" = "$REC_SHA" ] || { echo "rec1155 hash mismatch"; exit 1; }

# ------------------------------------------------------------------- engines
for image in $ENGINES; do
  ver="${image##*:}"; ver="${ver%%@*}"
  case "$image" in *@sha256:*) ver="$(echo "$image" | sed -E 's|.*:([^:@]+)@sha256:.*|\1|')";; esac
  for cap in rec1155 otel215; do
    out="$CACHE/engine-$ver/$cap"
    say "engine $ver on $cap"
    bench/engine.sh "$image" "$CACHE/$cap.log" "$out"
    gzip -f "$out/events.jsonl"
    "$PY" bench/score.py "$cap" "$out/events.jsonl.gz" --out "results/engine-${ver}_${cap}.json" > /dev/null
    "$PY" bench/score.py "$cap" "$out/events.jsonl.gz" --exclude-container opentelemetry-collector \
      --out "results/engine-${ver}_${cap}_without-collector.json" > /dev/null
  done
done

# ------------------------------------------------------------------- Drain3
if [ ! -x "$VENV/bin/python" ]; then
  say "creating virtualenv at $VENV"
  "$PY" -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi
"$VENV/bin/pip" install --quiet -r ../pattern-identity/requirements.txt

for cap in rec1155 otel215; do
  for arm in strong baseline; do
    for unit in event record; do
      tag="drain3-$arm-$unit"
      out="$CACHE/$tag/$cap"
      say "$tag on $cap"
      "$VENV/bin/python" bench/drain_arm.py "$cap" "$CACHE/$cap.log" "$out" --arm "$arm" --unit "$unit" > /dev/null
      cp "$out/drain_stats.json" "results/${tag}_${cap}_stats.json"
      "$PY" bench/score.py "$cap" "$out/events.jsonl.gz" --grouping-only --out "results/${tag}_$cap.json" > /dev/null
      "$PY" bench/score.py "$cap" "$out/events.jsonl.gz" --grouping-only --exclude-container opentelemetry-collector \
        --out "results/${tag}_${cap}_without-collector.json" > /dev/null
    done
  done
done

# ------------------------------------------------------------------- summary
"$PY" bench/summarize.py > results/results.md
say "done: results/results.md"
