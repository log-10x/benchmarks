#!/usr/bin/env bash
#
# The same run as repro.sh, against a PATCHED engine built from source.
#
# The shipped edge image is a native binary, so a patched engine cannot be
# dropped into it. This runs the JVM build instead: the run-cloud shadow jar on
# a stock JRE image, in the same two-container topology, with the config and
# modules trees checked out at the revision the engine builds against.
#
#   PATCHED_JAR=<engine>/pipeline/run-cloud/build/libs/run-cloud-<v>-all.jar \
#   TENX_CONFIG_TREE=<config checkout> \
#   TENX_MODULES_TREE=<modules checkout> \
#   TENX_SYMBOLS_DIR=<dir holding tenx-symbols-*.10x.tar> \
#   ./verify-patched.sh                 all four variants
#
# Build the jar with:
#   ./gradlew :pipeline:run-cloud:shadowJar
# The symbol tar comes out of the shipped image:
#   docker create --name t ghcr.io/log-10x/edge-10x:latest
#   docker cp t:/etc/tenx/symbols/. <TENX_SYMBOLS_DIR>/
#
# Artifacts land under out-patched/<variant>/, same shape as out/<variant>/.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

: "${PATCHED_JAR:?set PATCHED_JAR to the run-cloud shadow jar}"
: "${TENX_CONFIG_TREE:?set TENX_CONFIG_TREE to a checkout of log-10x/config}"
: "${TENX_MODULES_TREE:?set TENX_MODULES_TREE to a checkout of log-10x/modules}"
: "${TENX_SYMBOLS_DIR:?set TENX_SYMBOLS_DIR to a directory holding the symbol tar}"

JRE_IMAGE="${CSE_JRE_IMAGE:-eclipse-temurin:23-jre}"
OTEL_IMAGE="${CSE_OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"

NET=repro-net
ENGINE=repro-engine
ROUTER=repro-router

cleanup() { docker rm -f "$ROUTER" "$ENGINE" >/dev/null 2>&1 || true; }
trap cleanup EXIT

python3 make_lines.py
docker network create "$NET" >/dev/null 2>&1 || true

run_variant() {
  local variant="$1"
  printf '\n== variant: %s\n' "$variant"

  local out="$HERE/out-patched/$variant"
  rm -rf "$out"; mkdir -p "$out/wire"; chmod 777 "$out/wire"

  rsync -a --exclude '.git' "$TENX_CONFIG_TREE/" "$out/tenx-config/"
  CONFIG_DIR="$out/tenx-config" python3 patch_config.py

  rsync -a --exclude '.git' "$TENX_MODULES_TREE/" "$out/modules/"
  if [ "$variant" = "nodrop" ]; then
    python3 - "$out/modules/pipelines/run/modules/input/forwarder/otel-collector/stream.yaml" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
old = "      - drop:tag\n"
if old not in t:
    sys.exit("the shipped extractor no longer carries `- drop:tag`")
p.write_text(t.replace(old, "", 1))
print("  drop:tag removed from the extractor")
PY
  fi

  python3 render_conf.py "$variant" >/dev/null
  cp "$HERE/out/$variant/collector.yaml" "$out/collector.yaml"

  mkdir -p "$out/policy"
  cp conf/caps.csv conf/actions.csv "$out/policy/"
  touch "$out/policy/caps.csv" "$out/policy/actions.csv"

  cleanup

  docker run -d --name "$ENGINE" --network "$NET" --memory 2g --cpus 2 \
    -v "$PATCHED_JAR":/app/run-cloud.jar:ro \
    -v "$out/tenx-config":/etc/tenx/config:ro \
    -v "$out/modules":/opt/tenx/modules:ro \
    -v "$TENX_SYMBOLS_DIR":/etc/tenx/symbols:ro \
    -v "$out/policy":/policy \
    -e TENX_CONFIG=/etc/tenx/config \
    -e TENX_MODULES=/opt/tenx/modules \
    -e TENX_SYMBOLS_PATH=/etc/tenx/symbols \
    -e TENX_LOG_APPENDER=tenxConsoleAppender \
    -e CAP_LOOKUP_FILE=/policy/caps.csv \
    -e ACTION_LOOKUP_FILE=/policy/actions.csv \
    -e outputOffload=true \
    -e symbolMessageHashField=tenx_hash \
    -e TENX_OTEL_COLLECTOR_OUTPUT_HOST="$ROUTER" \
    -e TENX_OTEL_COLLECTOR_OUTPUT_PORT=24225 \
    -w /tmp "$JRE_IMAGE" \
    java -Xmx2g -Dfile.encoding=UTF-8 -classpath /app/run-cloud.jar \
      com.log10x.ext.cloud.run.RunCloud @apps/e2e >/dev/null

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

  # Settle on a count that stopped moving, and never on zero: an empty file is
  # "the run has not started", not "the run is over". The JVM engine takes
  # longer to reach its first flush than the native one, which is how a
  # zero-settling loop produced an empty variant.
  local prev=-1 same=0 waited=0 cur
  until { [ "$same" -ge 3 ] && [ "$prev" -gt 0 ]; } || [ "$waited" -ge 180 ]; do
    sleep 5
    waited=$((waited + 5))
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
