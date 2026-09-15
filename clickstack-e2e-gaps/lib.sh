#!/usr/bin/env bash
#
# The compose pattern the gap scripts share, lifted from ../run.sh and
# ../repro-otel-return/verify-patched.sh.
#
# One network, four containers: MinIO as the object store, ClickStack as the
# ClickHouse and the HyperDX, the 10x receiver as the regulator, and a stock
# contrib collector as the routing hop. The one difference from ../run.sh is the
# receiver: the shipped edge image is a native binary carrying the three OTel
# return path defects, so these runs use the PATCHED engine the way
# verify-patched.sh does, as the run-cloud shadow jar on a stock JRE image with
# the config and modules trees mounted beside it.
#
# Required environment, no defaults, the same four verify-patched.sh asks for:
#
#   PATCHED_JAR        pipeline/run-cloud/build/libs/run-cloud-<v>-all.jar
#   TENX_CONFIG_TREE   a checkout of log-10x/config
#   TENX_MODULES_TREE  a checkout of log-10x/modules
#
# Optional:
#   CSE_DATA_DIR       where the capture lives      (default: ../data)
#   LINES              lines of the capture fed     (default: 197430, all)
#   KEEP               1 leaves the containers up
#
# Sourced, never run.
#
# The container memory caps below sum to more than the Docker VM holds. They are
# caps and not reservations, and the four together have not gone past half of it:
# the runs that died were the ones capped near what a container usually uses,
# where a slow receiver backs the collector's queue up and the cap is reached.

set -euo pipefail

GAPS_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="$(cd "$GAPS_HERE/../clickstack-e2e" && pwd)"
DATA_DIR="${CSE_DATA_DIR:-$HARNESS/data}"
BUILD="$GAPS_HERE/build"
RESULTS="$GAPS_HERE/results"
LINES="${LINES:-197430}"

cd "$GAPS_HERE"

CS_IMAGE="${CSE_CS_IMAGE:-clickhouse/clickstack-all-in-one:2.38.0}"
EDGE_IMAGE="${CSE_ENGINE_IMAGE:-ghcr.io/log-10x/edge-10x:latest}"
OTEL_IMAGE="${CSE_OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"
MINIO_IMAGE="${CSE_MINIO_IMAGE:-quay.io/minio/minio:latest}"
MC_IMAGE="${CSE_MC_IMAGE:-quay.io/minio/mc:latest}"
JRE_IMAGE="${CSE_JRE_IMAGE:-eclipse-temurin:23-jre}"
VECTOR_IMAGE="${CSE_VECTOR_IMAGE:-timberio/vector:0.50.0-debian}"

NET=csg-net
CS=csg-clickstack
ENGINE=csg-engine
ROUTER=csg-router
VECTOR=csg-vector
MINIO=csg-minio
BUCKET=coldlogs

ASSET="otel-sample-200mb.log"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"

HDX_EMAIL="gaps@log10x.test"
HDX_PASSWORD="Passw0rd!2026"
HDX_API_KEY=""

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec "$CS" clickhouse-client "$@"; }
chq() { docker exec "$CS" clickhouse-client --query "$1"; }
mc() { docker run --rm --network "$NET" --entrypoint sh "$MC_IMAGE" -c \
       "mc alias set m http://$MINIO:9000 minioadmin minioadmin >/dev/null && $1"; }

g_require() {
  : "${PATCHED_JAR:?set PATCHED_JAR to the patched run-cloud shadow jar}"
  : "${TENX_CONFIG_TREE:?set TENX_CONFIG_TREE to a checkout of log-10x/config}"
  : "${TENX_MODULES_TREE:?set TENX_MODULES_TREE to a checkout of log-10x/modules}"
  command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
  [ -s "$PATCHED_JAR" ] || { echo "no jar at $PATCHED_JAR" >&2; exit 1; }
  mkdir -p "$BUILD" "$RESULTS"
}

g_teardown() {
  if [ "${KEEP:-0}" = "1" ]; then
    echo "KEEP=1: containers left up on network $NET"
    return
  fi
  docker rm -f -v "$VECTOR" "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}

# ------------------------------------------------------------------- the input
# The full capture, checked by sha256 the way run.sh checks it. `LINES` exists
# for a smoke run; every committed number is the whole file.
g_input() {
  local plain="$DATA_DIR/$ASSET"
  [ -s "$plain" ] || { echo "no capture at $plain: run ../clickstack-e2e/run.sh once" >&2; exit 1; }
  local sha
  sha="$(shasum -a 256 "$plain" | cut -d' ' -f1)"
  [ "$sha" = "$ASSET_SHA256" ] || { echo "the capture does not match the pinned sha256" >&2; exit 1; }
  FEED="$DATA_DIR/gaps-feed.log"
  if [ "$LINES" -ge 197430 ]; then
    FEED="$plain"
  else
    head -n "$LINES" "$plain" > "$FEED"
  fi
  FEED_LINES="$(wc -l < "$FEED" | tr -d ' ')"
  FEED_BYTES="$(wc -c < "$FEED" | tr -d ' ')"
  FEED_DIR="$(dirname "$FEED")"
  FEED_NAME="$(basename "$FEED")"
  echo "  feeding $FEED_LINES lines, $FEED_BYTES bytes, from $FEED_NAME"
}

g_images() {
  for img in "$@"; do
    docker image inspect "$img" >/dev/null 2>&1 || docker pull "$img"
  done
}

g_net() {
  docker rm -f -v "$VECTOR" "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
  docker network create "$NET" >/dev/null 2>&1 || true
}

# -------------------------------------------------------------------- MinIO
g_minio_up() {
  docker run -d --name "$MINIO" --network "$NET" --memory 512m \
    -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
    "$MINIO_IMAGE" server /data >/dev/null
  until docker exec "$MINIO" sh -c 'curl -sf http://localhost:9000/minio/health/live' >/dev/null 2>&1; do sleep 2; done
  mc "mc mb -p m/$BUCKET >/dev/null && echo '  bucket $BUCKET created'"
}

g_objects() { mc "mc ls -r m/$BUCKET | wc -l" | tr -d ' \r'; }
g_object_bytes() { mc "mc du m/$BUCKET" | awk '{print $1}'; }

# --------------------------------------------------------------- ClickStack
g_clickstack_up() {
  # No published port: the HyperDX UI is reached over `docker exec` here, and a
  # published 8080 collides with any other ClickStack on the same host.
  docker run -d --name "$CS" --network "$NET" --memory 4g --cpus 3 \
    "$CS_IMAGE" >/dev/null
  for _ in $(seq 1 100); do chq "SELECT 1" >/dev/null 2>&1 && break; sleep 3; done
  chq "SELECT 1" >/dev/null || { echo "ClickStack did not come up" >&2; exit 1; }
  until chq "EXISTS TABLE default.otel_logs" 2>/dev/null | grep -q 1; do sleep 3; done
  CH_VERSION="$(chq 'SELECT version()')"
  echo "  ClickHouse $CH_VERSION"

  for _ in $(seq 1 100); do docker exec "$CS" curl -s -o /dev/null http://localhost:8000/ && break; sleep 3; done
  printf '{"email":"%s","password":"%s","confirmPassword":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" "$HDX_PASSWORD" > "$BUILD/register.json"
  printf '{"email":"%s","password":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" > "$BUILD/login.json"
  docker cp "$BUILD/register.json" "$CS":/tmp/register.json >/dev/null
  docker cp "$BUILD/login.json" "$CS":/tmp/login.json >/dev/null
  docker exec "$CS" curl -s -X POST http://localhost:8000/register/password \
    -H "Content-Type: application/json" --data-binary @/tmp/register.json >/dev/null
  docker exec "$CS" sh -c 'curl -s -c /tmp/ck.txt -X POST http://localhost:8000/login/password \
    -H "Content-Type: application/json" --data-binary @/tmp/login.json > /dev/null'
  HDX_API_KEY="$(docker exec "$CS" sh -c 'curl -s -b /tmp/ck.txt http://localhost:8000/team' \
    | sed -n 's/.*"apiKey":"\([^"]*\)".*/\1/p')"
  [ -n "$HDX_API_KEY" ] || { echo "could not read the HyperDX ingestion key" >&2; exit 1; }
  echo "  ingestion key obtained over the API"

  docker exec -i "$CS" clickhouse-client --multiquery < "$HARNESS/conf/schema_hot.sql"
  chq "ALTER TABLE default.otel_logs ADD COLUMN IF NOT EXISTS day Date MATERIALIZED toDate(Timestamp)"
}

# ------------------------------------------------------------------- engine
# The patched receiver: the shadow jar on a JRE image, config and modules trees
# mounted, the harness's own asserted edits applied to the config copy.
g_engine_up() {
  local policy_dir="$1"; shift
  # The running container has these trees bind-mounted, so it goes first.
  docker rm -f -v "$ENGINE" >/dev/null 2>&1 || true
  rm -rf "$BUILD/tenx-config" "$BUILD/modules"
  rsync -a --exclude '.git' "$TENX_CONFIG_TREE/" "$BUILD/tenx-config/"
  rsync -a --exclude '.git' "$TENX_MODULES_TREE/" "$BUILD/modules/"
  python3 "$HARNESS/patch_engine_config.py" --config-dir "$BUILD/tenx-config"

  if [ ! -d "$BUILD/symbols" ] || [ -z "$(ls -A "$BUILD/symbols" 2>/dev/null)" ]; then
    mkdir -p "$BUILD/symbols"
    docker rm -f csg-symbols-tmp >/dev/null 2>&1 || true
    docker create --name csg-symbols-tmp "$EDGE_IMAGE" >/dev/null
    docker cp csg-symbols-tmp:/etc/tenx/symbols/. "$BUILD/symbols/" >/dev/null
    docker rm csg-symbols-tmp >/dev/null
  fi

  docker run -d --name "$ENGINE" --network "$NET" --memory 2500m --cpus 2 \
    -v "$PATCHED_JAR":/app/run-cloud.jar:ro \
    -v "$BUILD/tenx-config":/etc/tenx/config:ro \
    -v "$BUILD/modules":/opt/tenx/modules:ro \
    -v "$BUILD/symbols":/etc/tenx/symbols:ro \
    -v "$policy_dir":/policy \
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
    "$@" \
    -w /tmp "$JRE_IMAGE" \
    java -Xmx1800m -Dfile.encoding=UTF-8 -classpath /app/run-cloud.jar \
      com.log10x.ext.cloud.run.RunCloud @apps/e2e >/dev/null
  g_engine_wait
}

g_engine_wait() {
  for _ in $(seq 1 90); do
    docker logs "$ENGINE" > "$BUILD/engine.log" 2>&1 || true
    grep -q "OTLP/gRPC logs server listening" "$BUILD/engine.log" && break
    sleep 2
  done
  grep -q "OTLP/gRPC logs server listening" "$BUILD/engine.log" || {
    echo "the receiver did not start:" >&2; tail -30 "$BUILD/engine.log" >&2; exit 1; }
  echo "  receiver up"
}

# ------------------------------------------------------------------- router
# `extra` is passed through to docker run, so a gap can add a mount.
g_router_up() {
  local conf="$1"; shift
  mkdir -p "$BUILD/wire"
  : > "$BUILD/wire/returned.json"
  chmod 666 "$BUILD/wire/returned.json"
  chmod 777 "$BUILD/wire"
  docker rm -f -v "$ROUTER" >/dev/null 2>&1 || true
  docker run -d --name "$ROUTER" --network "$NET" --memory 1500m --cpus 2 \
    -e HDX_API_KEY="$HDX_API_KEY" \
    -e AWS_ACCESS_KEY_ID=minioadmin -e AWS_SECRET_ACCESS_KEY=minioadmin \
    -v "$conf":/etc/otelcol-contrib/config.yaml:ro \
    -v "$FEED_DIR":/data:ro \
    -v "$BUILD/wire":/wire \
    "$@" \
    "$OTEL_IMAGE" >/dev/null
}

# The run is over when the hot row count stops moving. `same` counts settled
# polls; a run that moved nothing is a failed run, not a finished one.
# How many lines the collector's file receiver has accepted, read from its own
# telemetry. This is the only number that says whether the feed finished.
g_router_accepted() {
  # Never fails: a collector with no telemetry endpoint, a curl that times out
  # and a container that has gone all report zero. Under `set -e` a failing
  # command substitution here would end the run with no message at all, which is
  # how one arm of gap 6 disappeared mid-feed.
  { docker exec "$MINIO" sh -c "curl -s --max-time 5 http://$ROUTER:8888/metrics" 2>/dev/null \
    | awk '/^otelcol_receiver_accepted_log_records/ && /filelog/ {s+=$NF} END {printf "%d", s+0}'; } || true
}

# The run is over when the file receiver has accepted every line of the feed AND
# the hot row count has stopped moving. A count that stops moving on its own is
# not the end of a run: the first version of this waited only for stillness and
# called a run finished at 1,425 records of 120,593, because a slow sink upstream
# had stalled the whole route for a minute.
#
#   g_wait_settle <table> <still polls> <strict>
#
# `strict` 0 skips the accepted-lines check, for a run that restarts the
# collector on purpose and resets its counters.
g_wait_settle() {
  local table="${1:-default.otel_logs}" need="${2:-4}" strict="${3:-1}"
  local prev=-1 same=0 cur accepted=0 stalled=0
  until [ "$same" -ge "$need" ]; do
    sleep 15
    for c in "$CS" "$ROUTER"; do
      docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null | grep -q true || {
        echo "container $c is not running; the run is not finished, it is broken" >&2
        docker logs --tail 20 "$c" >&2 || true
        exit 1
      }
    done
    cur="$(chq "SELECT count() FROM $table" 2>/dev/null || echo 0)"
    accepted="$(g_router_accepted)"
    if [ "$cur" = "$prev" ]; then same=$((same + 1)); else same=0; fi
    prev="$cur"
    printf '  rows in %s: %s, lines accepted: %s of %s\n' "$table" "$cur" "$accepted" "$FEED_LINES"
    if [ "$strict" = "1" ] && [ "$same" -ge "$need" ] && [ "$accepted" -lt "$FEED_LINES" ]; then
      same=0
      stalled=$((stalled + 1))
      echo "  still, but only $accepted of $FEED_LINES lines read: waiting" >&2
      if [ "$stalled" -ge 8 ]; then
        echo "the route stalled with $accepted of $FEED_LINES lines read" >&2
        docker logs --tail 30 "$ROUTER" >&2 || true
        docker logs --tail 20 "$ENGINE" >&2 || true
        exit 1
      fi
    fi
  done
  SETTLED_ROWS="$prev"
  ACCEPTED_LINES="$accepted"
  [ "$prev" != "0" ] || { echo "no rows reached ClickHouse" >&2;
    docker logs --tail 40 "$ROUTER" >&2 || true; docker logs --tail 20 "$ENGINE" >&2 || true; exit 1; }
}

g_flush_cold() {
  docker stop "$ROUTER" >/dev/null 2>&1 || true
  sleep 5
}

# The harness's own collector config and SQL, with the container names this
# folder uses. Rendering rather than copying keeps the route identical to the
# one PR #11 measured: a change there lands here on the next run.
g_render_harness_conf() {
  mkdir -p "$BUILD/conf"
  for f in router.yaml schema_cold.sql schema_hot.sql caps.csv actions.csv; do
    sed -e "s/cse-engine/$ENGINE/g" -e "s/cse-clickstack/$CS/g" -e "s/cse-minio/$MINIO/g" \
        -e "s#/data/slice.log#/data/$FEED_NAME#g" \
        "$HARNESS/conf/$f" > "$BUILD/conf/$f"
  done
  # One addition to the harness's collector config: its own telemetry on an
  # address the rest of the network can read, so a run can ask the file receiver
  # how many lines it has accepted and know whether the feed finished. Nothing
  # in the route changes.
  python3 - "$BUILD/conf/router.yaml" <<'PY'
import sys
p = sys.argv[1]
t = open(p).read()
old = "  telemetry:\n    logs:\n      level: warn"
new = ("  telemetry:\n    logs:\n      level: warn\n    metrics:\n      level: basic\n"
       "      readers:\n        - pull:\n            exporter:\n              prometheus:\n"
       "                host: 0.0.0.0\n                port: 8888")
if old in t:
    t = t.replace(old, new, 1)
# The second addition: the exporter into the receiver blocks when its queue is
# full instead of rejecting the batch. Without it the file receiver reads far
# faster than the receiver can take, the exporter logs "sending queue is full"
# and the records in that batch are gone before anything has counted them. A
# hundred thousand lines were read in twenty seconds with nothing listening.
old_q = "  otlp/engine:\n    endpoint:"
new_q = "  otlp/engine:\n    sending_queue:\n      block_on_overflow: true\n    endpoint:"
if old_q in t:
    t = t.replace(old_q, new_q, 1)
open(p, "w").write(t)
PY
}

# Copy the objects the run wrote out of the object store, so a later script can
# read the layout exactly as the collector produced it. Gap 3 reads this.
g_export_cold() {
  local label="$1" dest="$BUILD/cold-export"
  rm -rf "$dest"; mkdir -p "$dest"; chmod 777 "$dest"
  docker run --rm --network "$NET" -v "$dest":/export --entrypoint sh "$MC_IMAGE" -c \
    "mc alias set m http://$MINIO:9000 minioadmin minioadmin >/dev/null && \
     mc mirror --quiet m/$BUCKET /export >/dev/null 2>&1; true"
  local n
  n="$(find "$dest" -type f | wc -l | tr -d ' ')"
  printf '{"written_by": "%s", "objects": %s, "feed_lines": %s}\n' "$label" "$n" "${FEED_LINES:-0}" \
    > "$BUILD/cold-export.json"
  echo "  exported $n objects to build/cold-export"
}
