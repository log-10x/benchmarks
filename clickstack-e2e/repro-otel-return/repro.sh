#!/usr/bin/env bash
#
# Root-causes the three defects the ClickStack end to end run reported on the
# OpenTelemetry Collector return path. No ClickStack, no MinIO, no capture: one
# receiver, one stock collector and 47 crafted lines.
#
#   ./repro.sh                 all four variants
#   ./repro.sh resource        one variant
#
# Variants:
#   resource     the kubernetes container is copied to the resource attribute
#                service.name, so the receiver writes `_tenx_resource_keys`
#   noresource   the same lines with no resource attribute at all
#   nodrop       `resource`, with `drop:tag` removed from the receiver's own
#                extractor, everything else identical
#   withtime     `resource`, with a record time set on the way in, so
#                `_tenx_time` reaching the output appender is not zero
#
# Needs Docker and the two images the harness pinned. Leaves every artifact
# under out/<variant>/.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

ENGINE_IMAGE="${CSE_ENGINE_IMAGE:-ghcr.io/log-10x/edge-10x:latest}"
OTEL_IMAGE="${CSE_OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"

NET=repro-net
ENGINE=repro-engine
ROUTER=repro-router

say() { printf '\n== %s\n' "$*"; }

cleanup() {
  docker rm -f "$ROUTER" "$ENGINE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python3 make_lines.py

docker network create "$NET" >/dev/null 2>&1 || true

# ------------------------------------------------------------- engine config
# The config tree out of the pinned image, with the two edits the harness makes
# that this reproduction needs: the OpenTelemetry Collector forwarder input
# enabled, and the pattern text added to the fullText splice list. Both assert,
# so a change in the shipped text fails here rather than producing a silently
# unmarked run.
prepare_config() {
  local dir="$1"
  rm -rf "$dir"; mkdir -p "$dir"
  docker rm -f repro-config-tmp >/dev/null 2>&1 || true
  docker create --name repro-config-tmp "$ENGINE_IMAGE" >/dev/null
  docker cp repro-config-tmp:/etc/tenx/config/. "$dir/" >/dev/null
  docker cp repro-config-tmp:/opt/tenx-edge/lib/app/modules/pipelines/run/modules/input/forwarder/otel-collector/stream.yaml \
    "$dir/../stream.yaml" >/dev/null
  docker rm repro-config-tmp >/dev/null
  CONFIG_DIR="$dir" python3 patch_config.py
}

run_variant() {
  local variant="$1"
  say "variant: $variant"

  local out="$HERE/out/$variant"
  rm -rf "$out"; mkdir -p "$out/wire"
  chmod 777 "$out/wire"

  prepare_config "$out/tenx-config"
  python3 render_conf.py "$variant" >/dev/null

  mkdir -p "$out/policy"
  cp conf/caps.csv conf/actions.csv "$out/policy/"
  touch "$out/policy/caps.csv" "$out/policy/actions.csv"

  local mounts=()
  if [ "$variant" = "nodrop" ]; then
    # `drop:tag` removed from the receiver's own extractor, nothing else.
    python3 - "$out/stream.yaml" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text()
old = "      - drop:tag\n"
if old not in t:
    sys.exit("the shipped extractor no longer carries `- drop:tag`")
p.write_text(t.replace(old, "", 1))
print("  drop:tag removed from the extractor")
PY
    mounts+=(-v "$out/stream.yaml":/opt/tenx-edge/lib/app/modules/pipelines/run/modules/input/forwarder/otel-collector/stream.yaml:ro)
  fi

  cleanup

  docker run -d --name "$ENGINE" --network "$NET" --memory 2g --cpus 2 \
    -v "$out/tenx-config":/etc/tenx/config:ro \
    -v "$out/policy":/policy \
    "${mounts[@]}" \
    -e CAP_LOOKUP_FILE=/policy/caps.csv \
    -e ACTION_LOOKUP_FILE=/policy/actions.csv \
    -e outputOffload=true \
    -e symbolMessageHashField=tenx_hash \
    -e TENX_OTEL_COLLECTOR_OUTPUT_HOST="$ROUTER" \
    -e TENX_OTEL_COLLECTOR_OUTPUT_PORT=24225 \
    "$ENGINE_IMAGE" @apps/e2e >/dev/null

  for _ in $(seq 1 60); do
    docker logs "$ENGINE" > "$out/engine.log" 2>&1 || true
    grep -q "OTLP/gRPC logs server listening" "$out/engine.log" && break
    sleep 2
  done
  grep -q "OTLP/gRPC logs server listening" "$out/engine.log" || {
    echo "the receiver did not start:" >&2; tail -30 "$out/engine.log" >&2; exit 1; }
  echo "  receiver up"

  docker run -d --name "$ROUTER" --network "$NET" --memory 1g --cpus 2 \
    -v "$out/collector.yaml":/etc/otelcol-contrib/config.yaml:ro \
    -v "$HERE/lines":/data:ro \
    -v "$out/wire":/wire \
    "$OTEL_IMAGE" >/dev/null

  # 47 lines. The file exporter flushes on write, so the count settling twice
  # is the end of the run.
  prev=-1; same=0
  until [ "$same" -ge 3 ]; do
    sleep 5
    cur="$(wc -l < "$out/wire/returned.json" 2>/dev/null || echo 0)"
    if [ "$cur" = "$prev" ]; then same=$((same + 1)); else same=0; fi
    prev="$cur"
  done
  docker stop "$ROUTER" >/dev/null
  docker logs "$ENGINE" > "$out/engine.log" 2>&1 || true
  echo "  returned batches: $prev"
  cleanup
}

VARIANTS=("$@")
if [ ${#VARIANTS[@]} -eq 0 ]; then
  VARIANTS=(resource noresource nodrop withtime)
fi

for v in "${VARIANTS[@]}"; do
  run_variant "$v"
done

say "analysis"
python3 analyze.py "${VARIANTS[@]}"
