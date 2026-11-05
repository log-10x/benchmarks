#!/usr/bin/env bash
# The arm split: which rows of the capture the Receiver keeps under a rows policy.
#
# The Receiver runs once, locally, over the released OpenTelemetry demo capture at
# the clickstack-rows rerun's starting pace (14 lines a second), with the policy
# files that rerun's first applied run wrote (2026-10-24T03:41:48Z: 29,399 rows an
# hour against 42,000 measured, every held line offloaded). The engine is the
# released 1.1.153, which ships the sample bound (`baselineMaxOverTotal: 50`), with
# the rows gate's config patches (collector input, events unit). Every record the
# Receiver returns is written to build/wire/returned.json with its routeState.
#
# The pacer runs in a container, as the rows rig's does. On Docker Desktop for Mac
# the collector's file reader does not see lines appended to the bind-mounted feed
# from the host until something inside the VM changes the file: a host-side pacer
# delivered the 11-02 run to the Receiver in four bursts an hour apart.
#
#   split/run.sh                  # the whole capture, about 3.9 hours
#   split/run_slices.sh           # the same capture as four quarters side by side
#   LINES=3000 PACE=200 split/run.sh   # a smoke run
#   START=49357 LINES=49358 NAME=chce1 BUILD=split/build/slice1 split/run.sh   # one slice
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/../.."
cd "$HERE"

CAPTURE="${CAPTURE:-$HOME/git/l1x-co/benchmarks/clickstack-e2e/data/otel-sample-200mb.log}"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
LINES="${LINES:-197430}"
START="${START:-0}"
PACE="${PACE:-14}"
BUILD="${BUILD:-$HERE/build}"
ENGINE_IMAGE="${ENGINE_IMAGE:-log10x/edge-10x:1.1.153}"
OTEL_IMAGE="${OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"
PY_IMAGE="${PY_IMAGE:-python:3.12-slim}"
# NAME sets the network and container names so two runs can go side by side; the
# engine keeps the alias chce-engine on its own network, which collector.yaml names.
NAME="${NAME:-chce}"
NET="$NAME-net"; ENGINE="$NAME-engine"; COLL="$NAME-split"; PACER="$NAME-pacer"

say() { printf '\n=== %s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
teardown() {
  docker rm -f -v "$PACER" >/dev/null 2>&1 || true
  if [ "${KEEP:-0}" = "1" ]; then echo "KEEP=1: containers left up on $NET"; return; fi
  docker rm -f -v "$COLL" "$ENGINE" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap teardown EXIT

say "capture"
[ "$(shasum -a 256 "$CAPTURE" | cut -d' ' -f1)" = "$ASSET_SHA256" ] || { echo "capture sha256 mismatch: $CAPTURE" >&2; exit 1; }
rm -rf "$BUILD"; mkdir -p "$BUILD/data" "$BUILD/wire" "$BUILD/policy"
: > "$BUILD/data/feed.log"; : > "$BUILD/wire/returned.json"
chmod 777 "$BUILD/wire" "$BUILD/data"; chmod 666 "$BUILD/wire/returned.json" "$BUILD/data/feed.log"
echo "  $LINES lines from line $((START + 1)) at $PACE a second"

say "images"
for img in "$ENGINE_IMAGE" "$OTEL_IMAGE" "$PY_IMAGE"; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img" >/dev/null
  printf '  %-52s %s\n' "$img" "$(docker image inspect "$img" --format '{{index .RepoDigests 0}}' | sed 's/.*@//')"
done | tee "$BUILD/images.txt"
docker rm -f -v "$PACER" "$COLL" "$ENGINE" >/dev/null 2>&1 || true
docker network create "$NET" >/dev/null 2>&1 || true

say "receiver"
mkdir -p "$BUILD/tenx-config"
docker rm -f "$NAME-config-tmp" >/dev/null 2>&1 || true
docker create --name "$NAME-config-tmp" "$ENGINE_IMAGE" >/dev/null
docker cp "$NAME-config-tmp":/etc/tenx/config/. "$BUILD/tenx-config/" >/dev/null
docker rm "$NAME-config-tmp" >/dev/null
python3 "$ROOT/clickstack-rows-gate/patch_engine_config.py" --config-dir "$BUILD/tenx-config" | tee "$BUILD/patches.txt"
grep -n -E "^  (unit|resetIntervalMs|baselineCount|baselineMaxOverTotal|keepMaxOverTotal|warmupMs):" \
  "$BUILD/tenx-config/pipelines/run/receive/rate/config.yaml" | tee "$BUILD/rate-settings.txt"
cp policy/caps.csv policy/totals.csv policy/actions.csv "$BUILD/policy/"
docker run -d --name "$ENGINE" --network "$NET" --network-alias chce-engine --memory 2g --cpus 2 \
  -v "$BUILD/tenx-config":/etc/tenx/config:ro \
  -v "$BUILD/policy":/policy:ro \
  -e CAP_LOOKUP_FILE=/policy/caps.csv \
  -e ACTION_LOOKUP_FILE=/policy/actions.csv \
  -e TOTAL_LOOKUP_FILE=/policy/totals.csv \
  -e outputOffload=true \
  -e TENX_OTEL_COLLECTOR_OUTPUT_HOST="$COLL" -e TENX_OTEL_COLLECTOR_OUTPUT_PORT=24225 \
  "$ENGINE_IMAGE" @apps/gate rateReceiverUnit events symbolMessageHashField tenx_hash >/dev/null
for _ in $(seq 1 60); do
  docker logs "$ENGINE" > "$BUILD/engine-start.log" 2>&1 || true
  grep -q "OTLP/gRPC logs server listening" "$BUILD/engine-start.log" && break
  sleep 3
done
grep -q "OTLP/gRPC logs server listening" "$BUILD/engine-start.log" || { echo "the receiver did not start" >&2; tail -30 "$BUILD/engine-start.log" >&2; exit 1; }
sleep 5
if [ "$(docker inspect -f '{{.State.Running}}' "$ENGINE")" != true ]; then
  echo "the receiver exited after start" >&2; tail -30 "$BUILD/engine-start.log" >&2; exit 1
fi

say "collector"
docker run -d --name "$COLL" --network "$NET" --memory 1g --cpus 2 \
  -v "$HERE/collector.yaml":/etc/otelcol-contrib/config.yaml:ro \
  -v "$BUILD/data":/data:ro -v "$BUILD/wire":/wire \
  "$OTEL_IMAGE" >/dev/null
sleep 5

say "feed"
T0="$(date -u +%s)"; echo "$T0" > "$BUILD/t0"
docker run -d --name "$PACER" -v "$HERE":/rig:ro -v "$CAPTURE":/capture.log:ro -v "$BUILD/data":/data \
  "$PY_IMAGE" python3 -u /rig/pace_once.py /capture.log /data/feed.log "$PACE" "$LINES" "$START" >/dev/null
[ "$(docker wait "$PACER")" = 0 ] || { docker logs "$PACER" >&2; echo "the pacer failed" >&2; exit 1; }
docker logs "$PACER" > "$BUILD/pacer.log" 2>&1; tail -1 "$BUILD/pacer.log"
docker rm -f -v "$PACER" >/dev/null

say "drain"
prev=-1; same=0
until [ "$same" -ge 4 ]; do
  sleep 15
  cur="$(wc -c < "$BUILD/wire/returned.json" | tr -d ' ')"
  if [ "$cur" = "$prev" ]; then same=$((same + 1)); else same=0; fi
  prev="$cur"
done
T1="$(date -u +%s)"; echo "$T1" > "$BUILD/t1"
docker run --rm --network "$NET" alpine:latest wget -qO- "http://$ENGINE:9100/metrics" > "$BUILD/engine-metrics.txt" 2>/dev/null || true
docker logs "$ENGINE" > "$BUILD/engine.log" 2>&1 || true
docker logs "$COLL" > "$BUILD/collector.log" 2>&1 || true
echo "  wire file $(wc -c < "$BUILD/wire/returned.json" | tr -d ' ') bytes, feed $((T1 - T0)) s"

say "count"
python3 "$HERE/count_wire.py" "$BUILD/wire/returned.json" | tee "$BUILD/split-count.txt"
