#!/usr/bin/env bash
#
# One command. Stands up ClickStack, MinIO and the 10x receiver, feeds the
# released capture through an OpenTelemetry Collector so the receiver sees it as
# a forwarder input, routes the rows the receiver marked `offload` into an
# object store and everything else into ClickStack's own ClickHouse exporter,
# reads both sides back as one table, times a set of queries against it, checks
# that nothing was lost, and writes results/clickstack-e2e-<date>.md.
#
#   ./run.sh              everything
#   KEEP=1 ./run.sh       leave the containers up afterwards
#   LINES=20000 ./run.sh  feed a smaller slice of the capture
#
# Needs Docker, about 8 GB of Docker memory, 6 GB of free disk and roughly
# fifteen minutes on a warm host. The capture is fetched into data/ on the first
# run and its sha256 is checked on every run.
#
# Environment:
#   CSE_DATA_DIR   download cache          (default: <dir>/data)
#   LINES          lines of the capture fed (default: 50000)
#   KEEP           1 leaves the containers up

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

DATA_DIR="${CSE_DATA_DIR:-$HERE/data}"
BUILD="$HERE/build"
RESULTS="$HERE/results"
LINES="${LINES:-50000}"

# ------------------------------------------------------------- pinned images
# ClickStack's all-in-one: ClickHouse, HyperDX, the OTel collector and MongoDB
# in one container, the image the ClickStack all-in-one deployment page names.
CS_IMAGE="${CSE_CS_IMAGE:-clickhouse/clickstack-all-in-one:2.38.0}"
# The engine. This is the published image that carries the cap-and-actions
# variant of the regulator (rate-object-cap.js under the config path); the
# pipeline-10x image does not.
ENGINE_IMAGE="${CSE_ENGINE_IMAGE:-ghcr.io/log-10x/edge-10x:latest}"
# The routing hop. ClickStack's collector has the routing connector but no S3
# exporter and no encoding extension, so the route runs in a stock contrib build.
OTEL_IMAGE="${CSE_OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"
MINIO_IMAGE="${CSE_MINIO_IMAGE:-quay.io/minio/minio:latest}"
MC_IMAGE="${CSE_MC_IMAGE:-quay.io/minio/mc:latest}"

NET=cse-net
CS=cse-clickstack
ENGINE=cse-engine
ROUTER=cse-router
MINIO=cse-minio
BUCKET=coldlogs

# The released capture, the same asset and the same sha256 the
# clickhouse-clickstack benchmark checks.
RELEASE="https://github.com/log-10x/config/releases/download/otel-sample-v2"
ASSET="otel-sample-200mb.log"
ASSET_GZ_SHA256="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"

HDX_EMAIL="e2e@log10x.test"
HDX_PASSWORD="Passw0rd!2026"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec "$CS" clickhouse-client "$@"; }
cs_curl() { docker exec "$CS" curl -s "$@"; }
mc() { docker run --rm --network "$NET" --entrypoint sh "$MC_IMAGE" -c "mc alias set m http://$MINIO:9000 minioadmin minioadmin >/dev/null && $1"; }

teardown() {
  if [ "${KEEP:-0}" = "1" ]; then
    echo "KEEP=1: $CS $ENGINE $ROUTER $MINIO left up on network $NET"
    return
  fi
  docker rm -f -v "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap teardown EXIT

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
mkdir -p "$DATA_DIR" "$RESULTS" "$BUILD/policy" "$BUILD/wire"
# The collector runs as a non-root user and its file exporter will not create a
# file in a bind-mounted directory it does not own. The tap file is created here,
# empty and writable, or the collector refuses to start its pipelines and the
# run moves nothing.
: > "$BUILD/wire/returned.json"
chmod 666 "$BUILD/wire/returned.json"
chmod 777 "$BUILD/wire"

# --------------------------------------------------------------------- input
say "the released capture"
GZ="$DATA_DIR/$ASSET.gz"
PLAIN="$DATA_DIR/$ASSET"
[ -s "$GZ" ] || curl -fsSL -o "$GZ" "$RELEASE/$ASSET.gz"
[ -s "$PLAIN" ] || gunzip -c "$GZ" > "$PLAIN"
GZ_SHA="$(shasum -a 256 "$GZ" | cut -d' ' -f1)"
PLAIN_SHA="$(shasum -a 256 "$PLAIN" | cut -d' ' -f1)"
if [ "$GZ_SHA" != "$ASSET_GZ_SHA256" ] || [ "$PLAIN_SHA" != "$ASSET_SHA256" ]; then
  echo "the release asset does not match the sha256 this results file was measured on." >&2
  echo "rerun and recommit results/ rather than reporting the committed numbers." >&2
  exit 1
fi
head -n "$LINES" "$PLAIN" > "$DATA_DIR/slice.log"
SLICE_BYTES="$(wc -c < "$DATA_DIR/slice.log" | tr -d ' ')"
echo "$ASSET sha256 $PLAIN_SHA, feeding $LINES lines, $SLICE_BYTES bytes"

# -------------------------------------------------------------------- images
say "images"
for img in "$CS_IMAGE" "$ENGINE_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE"; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull "$img"
  printf '  %-52s %s\n' "$img" "$(docker image inspect "$img" --format '{{index .RepoDigests 0}}' 2>/dev/null | sed 's/.*@//')"
done

# ------------------------------------------------------------------ teardown
docker rm -f -v "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
docker network create "$NET" >/dev/null 2>&1 || true

# --------------------------------------------------------------------- minio
say "object store"
docker run -d --name "$MINIO" --network "$NET" --memory 512m \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  "$MINIO_IMAGE" server /data >/dev/null
until docker exec "$MINIO" sh -c 'curl -sf http://localhost:9000/minio/health/live' >/dev/null 2>&1; do sleep 2; done
mc "mc mb -p m/$BUCKET >/dev/null && echo '  bucket $BUCKET created'"

# ----------------------------------------------------------------- clickstack
say "ClickStack"
docker run -d --name "$CS" --network "$NET" --memory 3g --cpus 3 \
  -p 8080:8080 "$CS_IMAGE" >/dev/null
for _ in $(seq 1 100); do ch --query "SELECT 1" >/dev/null 2>&1 && break; sleep 3; done
ch --query "SELECT 1" >/dev/null || { echo "ClickStack did not come up" >&2; exit 1; }
until ch --query "EXISTS TABLE default.otel_logs" 2>/dev/null | grep -q 1; do sleep 3; done
CH_VERSION="$(ch --query 'SELECT version()')"
# Which contrib components ClickStack's own collector build actually carries.
docker exec "$CS" /otelcontribcol components > "$BUILD/clickstack-components.txt" 2>&1 || true
echo "  ClickHouse $CH_VERSION, HyperDX UI on http://localhost:8080"

# ClickStack's OTLP endpoint wants the team's ingestion key, and the team is
# created by the first registration. Both are done over the HyperDX API so the
# run needs no click.
for _ in $(seq 1 100); do docker exec "$CS" curl -s -o /dev/null http://localhost:8000/ && break; sleep 3; done
printf '{"email":"%s","password":"%s","confirmPassword":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" "$HDX_PASSWORD" > "$BUILD/register.json"
printf '{"email":"%s","password":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" > "$BUILD/login.json"
docker cp "$BUILD/register.json" "$CS":/tmp/register.json >/dev/null
docker cp "$BUILD/login.json" "$CS":/tmp/login.json >/dev/null
cs_curl -X POST http://localhost:8000/register/password -H "Content-Type: application/json" \
  --data-binary @/tmp/register.json >/dev/null
docker exec "$CS" sh -c 'curl -s -c /tmp/ck.txt -X POST http://localhost:8000/login/password \
  -H "Content-Type: application/json" --data-binary @/tmp/login.json > /dev/null'
HDX_API_KEY="$(docker exec "$CS" sh -c 'curl -s -b /tmp/ck.txt http://localhost:8000/team' \
  | sed -n 's/.*"apiKey":"\([^"]*\)".*/\1/p')"
[ -n "$HDX_API_KEY" ] || { echo "could not read the HyperDX ingestion key" >&2; exit 1; }
echo "  ingestion key obtained over the API"

# The counts table and its materialized view are created BEFORE anything is
# inserted, or the view sees none of the run.
say "counts table, before any data flows"
docker exec -i "$CS" clickhouse-client --multiquery < conf/schema_hot.sql
# ClickStack's otel_logs has no day column, so a day predicate over the merge
# table would exclude every hot row. One materialized column fixes that; it is a
# change to the shipped schema and is reported as one.
ch --query "ALTER TABLE default.otel_logs ADD COLUMN IF NOT EXISTS day Date MATERIALIZED toDate(Timestamp)"
echo "  counts_by_type, counts_by_type_hot_mv, otel_logs.day"

# -------------------------------------------------------------------- engine
say "receiver"
rm -rf "$BUILD/tenx-config"; mkdir -p "$BUILD/tenx-config"
docker rm -f cse-config-tmp >/dev/null 2>&1 || true
docker create --name cse-config-tmp "$ENGINE_IMAGE" >/dev/null
docker cp cse-config-tmp:/etc/tenx/config/. "$BUILD/tenx-config/" >/dev/null
docker rm cse-config-tmp >/dev/null
python3 patch_engine_config.py --config-dir "$BUILD/tenx-config"

cp conf/caps.csv conf/actions.csv "$BUILD/policy/"
# capLookup.retain is ten minutes and a stale file is ignored with one INFO
# line, after which every event comes back `pass`. Both files, every run.
touch "$BUILD/policy/caps.csv" "$BUILD/policy/actions.csv"

docker run -d --name "$ENGINE" --network "$NET" --memory 2g --cpus 2 \
  -v "$BUILD/tenx-config":/etc/tenx/config:ro \
  -v "$BUILD/policy":/policy \
  -e CAP_LOOKUP_FILE=/policy/caps.csv \
  -e ACTION_LOOKUP_FILE=/policy/actions.csv \
  -e outputOffload=true \
  -e symbolMessageHashField=tenx_hash \
  -e TENX_OTEL_COLLECTOR_OUTPUT_HOST="$ROUTER" \
  -e TENX_OTEL_COLLECTOR_OUTPUT_PORT=24225 \
  "$ENGINE_IMAGE" @apps/e2e >/dev/null
# `docker logs | grep -q` would exit on the first match, the engine keeps
# writing, and `pipefail` then reports the broken pipe as a failure. The log
# goes to a file and grep reads the file.
for _ in $(seq 1 60); do
  docker logs "$ENGINE" > "$BUILD/engine.log" 2>&1 || true
  grep -q "OTLP/gRPC logs server listening" "$BUILD/engine.log" && break
  sleep 3
done
grep -q "OTLP/gRPC logs server listening" "$BUILD/engine.log" || { echo "the receiver did not start:" >&2; tail -30 "$BUILD/engine.log" >&2; exit 1; }
grep -E "Writing TenXObject field|rate cap file" "$BUILD/engine.log" | sed 's/^/  /'

# -------------------------------------------------------------------- router
say "collector: read, route, offload"
docker run -d --name "$ROUTER" --network "$NET" --memory 1g --cpus 2 \
  -e HDX_API_KEY="$HDX_API_KEY" \
  -e AWS_ACCESS_KEY_ID=minioadmin -e AWS_SECRET_ACCESS_KEY=minioadmin \
  -v "$HERE/conf/router.yaml":/etc/otelcol-contrib/config.yaml:ro \
  -v "$DATA_DIR":/data:ro \
  -v "$BUILD/wire":/wire \
  "$OTEL_IMAGE" >/dev/null

# The run is over when the hot row count stops moving for a minute.
prev=-1; same=0
until [ "$same" -ge 4 ]; do
  sleep 15
  cur="$(ch --query "SELECT count() FROM default.otel_logs" 2>/dev/null || echo 0)"
  if [ "$cur" = "$prev" ]; then same=$((same + 1)); else same=0; fi
  prev="$cur"
  printf '  hot rows: %s\n' "$cur"
done

# A run that moved nothing is a failed run, not a lossless one.
if [ "$prev" = "0" ]; then
  echo "no rows reached ClickHouse. The collector and the receiver logs follow." >&2
  docker logs --tail 40 "$ROUTER" >&2 || true
  docker logs --tail 20 "$ENGINE" >&2 || true
  exit 1
fi

# The S3 exporter writes on a five second batch timeout; stopping the collector
# flushes what is left.
docker stop "$ROUTER" >/dev/null
sleep 5
echo "  cold objects: $(mc "mc ls -r m/$BUCKET | wc -l")"

# The receiver's own counters, for the lossless check.
docker exec "$ENGINE" sh -c 'curl -s http://localhost:9100/metrics' > "$BUILD/engine-metrics.txt" 2>/dev/null || true

# --------------------------------------------------------------- read it back
say "hot and cold as one table"
docker exec -i "$CS" clickhouse-client --multiquery < conf/schema_cold.sql
ch --query "SELECT _table, count() FROM default.otel_logs_all GROUP BY _table FORMAT PrettyCompactMonoBlock"

# HyperDX gets the merge table as a second source. The hot table stays the
# default: a query against the merge table pays object-store requests.
SRC_CONN="$(docker exec "$CS" sh -c 'curl -s -b /tmp/ck.txt http://localhost:8000/connections' | sed -n 's/.*"_id":"\([^"]*\)".*/\1/p' | head -1)"
cat > "$BUILD/source.json" <<JSON
{"kind":"log","name":"Logs hot plus cold","connection":"$SRC_CONN",
 "from":{"databaseName":"default","tableName":"otel_logs_all"},
 "timestampValueExpression":"Timestamp","displayedTimestampValueExpression":"Timestamp",
 "implicitColumnExpression":"Body","serviceNameExpression":"ServiceName",
 "bodyExpression":"Body","eventAttributesExpression":"LogAttributes",
 "defaultTableSelectExpression":"Timestamp,ServiceName,Body"}
JSON
docker cp "$BUILD/source.json" "$CS":/tmp/source.json >/dev/null
HDX_SOURCE_HTTP="$(docker exec "$CS" sh -c 'curl -s -o /dev/null -w "%{http_code}" -b /tmp/ck.txt -X POST http://localhost:8000/sources -H "Content-Type: application/json" --data-binary @/tmp/source.json')"
echo "  HyperDX source over the merge table: HTTP $HDX_SOURCE_HTTP"

# ------------------------------------------------------------------- measure
say "measure"
python3 report.py \
  --container "$CS" \
  --wire "$BUILD/wire/returned.json" \
  --engine-metrics "$BUILD/engine-metrics.txt" \
  --results "$RESULTS" \
  --conf-dir "$HERE/conf" \
  --clickstack-components "$BUILD/clickstack-components.txt" \
  --slice "$DATA_DIR/slice.log" \
  --lines "$LINES" \
  --asset-sha256 "$PLAIN_SHA" \
  --ch-version "$CH_VERSION" \
  --clickstack-image "$CS_IMAGE" \
  --engine-image "$ENGINE_IMAGE" \
  --otel-image "$OTEL_IMAGE" \
  --minio-image "$MINIO_IMAGE" \
  --hyperdx-source-http "$HDX_SOURCE_HTTP"

say "done. artifacts in $RESULTS"
