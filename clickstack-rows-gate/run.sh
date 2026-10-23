#!/usr/bin/env bash
# The meter gate for a ClickHouse rows run (research/37 RECOMMENDATION_STEP3.md, 5a).
#
# One question: which ClickHouse meter equals the hot table's row count, to the
# row, when the Receiver regulates in events with a service total and the shipped
# baseline of 5? Candidates: system.query_log written_rows on inserts into the logs
# table, and system.part_log NewPart rows. Also recorded: the Receiver's own pass
# count on the wire and in its Prometheus scrape, the label that carries the
# container, what a policy reload mid-window does to a capped service's count,
# and whether the e2e harness's config patches still apply to 1.1.147.
#
# The rig is clickstack-e2e's, reused file for file (its conf/ is read in place).
# Nothing here is a cost or a bill.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E="$HERE/../clickstack-e2e"
cd "$HERE"

DATA_DIR="${CSE_DATA_DIR:-$E2E/data}"
BUILD="$HERE/build"
RESULTS="$HERE/results"
LINES="${LINES:-197430}"
RELOAD_AFTER="${RELOAD_AFTER:-40}"       # seconds into the feed to rewrite the totals file in place
CS_IMAGE="${CSE_CS_IMAGE:-clickhouse/clickstack-all-in-one:2.38.0}"
ENGINE_IMAGE="${CSE_ENGINE_IMAGE:-ghcr.io/log-10x/edge-10x:1.1.147}"
OTEL_IMAGE="${CSE_OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"
# MinIO's public images were withdrawn from quay.io and Docker Hub (401 / access denied on
# 2026-10-23), so the S3 store is RustFS, S3-compatible on the same port and endpoint name,
# with the same static credentials; bucket operations run through the AWS CLI image.
MINIO_IMAGE="${CSE_MINIO_IMAGE:-rustfs/rustfs:latest}"
AWS_IMAGE="${CSE_AWS_IMAGE:-amazon/aws-cli:latest}"
# the e2e router.yaml and schema_cold.sql address these hosts by name, so the names stay
NET=cse-net; CS=cse-clickstack; ENGINE=cse-engine; ROUTER=cse-router; MINIO=cse-minio
BUCKET=coldlogs
ASSET="otel-sample-200mb.log"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
HDX_EMAIL="gate@log10x.test"; HDX_PASSWORD="Passw0rd!2026"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec "$CS" clickhouse-client "$@"; }
chq() { docker exec "$CS" clickhouse-client --query "$1"; }
s3() { docker run --rm --network "$NET" -e AWS_ACCESS_KEY_ID=minioadmin -e AWS_SECRET_ACCESS_KEY=minioadmin -e AWS_DEFAULT_REGION=us-east-1 "$AWS_IMAGE" --endpoint-url "http://$MINIO:9000" s3 "$@"; }
teardown() {
  if [ "${KEEP:-0}" = "1" ]; then echo "KEEP=1: containers left up on $NET"; return; fi
  docker rm -f -v "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap teardown EXIT

mkdir -p "$RESULTS" "$BUILD/policy" "$BUILD/wire"
: > "$BUILD/wire/returned.json"; chmod 666 "$BUILD/wire/returned.json"; chmod 777 "$BUILD/wire"

say "the released capture"
PLAIN="$DATA_DIR/$ASSET"
[ -s "$PLAIN" ] || { echo "capture not at $PLAIN; run clickstack-e2e/run.sh once or set CSE_DATA_DIR" >&2; exit 1; }
[ "$(shasum -a 256 "$PLAIN" | cut -d' ' -f1)" = "$ASSET_SHA256" ] || { echo "capture sha256 mismatch" >&2; exit 1; }
mkdir -p "$BUILD/data"; head -n "$LINES" "$PLAIN" > "$BUILD/data/slice.log"
echo "  feeding $LINES lines, $(wc -c < "$BUILD/data/slice.log" | tr -d ' ') bytes"

say "images"
for img in "$CS_IMAGE" "$ENGINE_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$AWS_IMAGE"; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img" >/dev/null
  printf '  %-52s %s\n' "$img" "$(docker image inspect "$img" --format '{{index .RepoDigests 0}}' 2>/dev/null | sed 's/.*@//')"
done | tee "$BUILD/images.txt"
docker rm -f -v "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
docker network create "$NET" >/dev/null 2>&1 || true

say "object store"
docker run -d --name "$MINIO" --network "$NET" --memory 512m \
  -e RUSTFS_ACCESS_KEY=minioadmin -e RUSTFS_SECRET_KEY=minioadmin "$MINIO_IMAGE" >/dev/null
for _ in $(seq 1 30); do s3 ls >/dev/null 2>&1 && break; sleep 2; done
s3 ls >/dev/null || { echo "the S3 store did not come up:" >&2; docker logs --tail 20 "$MINIO" >&2; exit 1; }
s3 mb "s3://$BUCKET" >/dev/null && echo "  bucket $BUCKET created"

say "ClickStack"
docker run -d --name "$CS" --network "$NET" --memory 3g --cpus 3 "$CS_IMAGE" >/dev/null
for _ in $(seq 1 100); do chq "SELECT 1" >/dev/null 2>&1 && break; sleep 3; done
chq "SELECT 1" >/dev/null || { echo "ClickStack did not come up" >&2; exit 1; }
until chq "EXISTS TABLE default.otel_logs" 2>/dev/null | grep -q 1; do sleep 3; done
CH_VERSION="$(chq 'SELECT version()')"; echo "  ClickHouse $CH_VERSION"
for _ in $(seq 1 100); do docker exec "$CS" curl -s -o /dev/null http://localhost:8000/ && break; sleep 3; done
printf '{"email":"%s","password":"%s","confirmPassword":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" "$HDX_PASSWORD" > "$BUILD/register.json"
printf '{"email":"%s","password":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" > "$BUILD/login.json"
docker cp "$BUILD/register.json" "$CS":/tmp/register.json >/dev/null
docker cp "$BUILD/login.json" "$CS":/tmp/login.json >/dev/null
docker exec "$CS" curl -s -X POST http://localhost:8000/register/password -H "Content-Type: application/json" --data-binary @/tmp/register.json >/dev/null
docker exec "$CS" sh -c 'curl -s -c /tmp/ck.txt -X POST http://localhost:8000/login/password -H "Content-Type: application/json" --data-binary @/tmp/login.json > /dev/null'
HDX_API_KEY="$(docker exec "$CS" sh -c 'curl -s -b /tmp/ck.txt http://localhost:8000/team' | sed -n 's/.*"apiKey":"\([^"]*\)".*/\1/p')"
[ -n "$HDX_API_KEY" ] || { echo "could not read the HyperDX ingestion key" >&2; exit 1; }

say "counts table and insert-time column, before any data flows"
docker exec -i "$CS" clickhouse-client --multiquery < "$E2E/conf/schema_hot.sql"
chq "ALTER TABLE default.otel_logs ADD COLUMN IF NOT EXISTS day Date MATERIALIZED toDate(Timestamp)"
chq "ALTER TABLE default.otel_logs ADD COLUMN IF NOT EXISTS ins DateTime64(3) MATERIALIZED now64(3)"
chq "SYSTEM FLUSH LOGS"
Q0_PARTLOG="$(chq "SELECT count() FROM system.part_log WHERE database='default' AND table='otel_logs'" 2>/dev/null || echo na)"
echo "  part_log rows for otel_logs before the feed: $Q0_PARTLOG"

say "receiver, 1.1.147, events unit, shipped baseline 5, service totals"
rm -rf "$BUILD/tenx-config"; mkdir -p "$BUILD/tenx-config"
docker rm -f cse-config-tmp >/dev/null 2>&1 || true
docker create --name cse-config-tmp "$ENGINE_IMAGE" >/dev/null
docker cp cse-config-tmp:/etc/tenx/config/. "$BUILD/tenx-config/" >/dev/null
docker rm cse-config-tmp >/dev/null
python3 patch_engine_config.py --config-dir "$BUILD/tenx-config" | tee "$BUILD/patches.txt"
grep -n -E "^  warmupMs:|^  baselineCount:|^  unit:|^  resetIntervalMs:" "$BUILD/tenx-config/pipelines/run/receive/rate/config.yaml" | sed 's/^/  shipped: /'
cp conf/caps.csv conf/actions.csv conf/totals.csv "$BUILD/policy/"
docker run -d --name "$ENGINE" --network "$NET" --memory 2g --cpus 2 \
  -v "$BUILD/tenx-config":/etc/tenx/config:ro \
  -v "$BUILD/policy":/policy \
  -e CAP_LOOKUP_FILE=/policy/caps.csv \
  -e ACTION_LOOKUP_FILE=/policy/actions.csv \
  -e TOTAL_LOOKUP_FILE=/policy/totals.csv \
  -e rateReceiverUnit=events \
  -e outputOffload=true \
  -e symbolMessageHashField=tenx_hash \
  -e TENX_OTEL_COLLECTOR_OUTPUT_HOST="$ROUTER" \
  -e TENX_OTEL_COLLECTOR_OUTPUT_PORT=24225 \
  "$ENGINE_IMAGE" @apps/gate >/dev/null
for _ in $(seq 1 60); do
  docker logs "$ENGINE" > "$BUILD/engine.log" 2>&1 || true
  grep -q "OTLP/gRPC logs server listening" "$BUILD/engine.log" && break
  sleep 3
done
grep -q "OTLP/gRPC logs server listening" "$BUILD/engine.log" || { echo "the receiver did not start:" >&2; tail -30 "$BUILD/engine.log" >&2; exit 1; }
grep -i -E "rate|total|unit|lookup" "$BUILD/engine.log" | head -12 | sed 's/^/  /'

say "collector: read, route, offload (clickstack-e2e/conf/router.yaml, unchanged)"
docker run -d --name "$ROUTER" --network "$NET" --memory 1g --cpus 2 \
  -e HDX_API_KEY="$HDX_API_KEY" \
  -e AWS_ACCESS_KEY_ID=minioadmin -e AWS_SECRET_ACCESS_KEY=minioadmin \
  -v "$E2E/conf/router.yaml":/etc/otelcol-contrib/config.yaml:ro \
  -v "$BUILD/data":/data:ro \
  -v "$BUILD/wire":/wire \
  "$OTEL_IMAGE" >/dev/null
T0="$(date -u +%s)"
sleep "$RELOAD_AFTER"
RELOAD_AT="$(date -u +%Y-%m-%dT%H:%M:%S)"
HOT_AT_RELOAD="$(chq "SELECT count() FROM default.otel_logs" 2>/dev/null || echo 0)"
# in-place rewrite: same rows, a new reason column, which is what a policy run does every hour
sed 's/$/:gate reload/' conf/totals.csv | sed '1s/:gate reload$//' > "$BUILD/policy/totals.csv.new"
cat "$BUILD/policy/totals.csv.new" > "$BUILD/policy/totals.csv"; rm -f "$BUILD/policy/totals.csv.new"
echo "  totals.csv rewritten in place at $RELOAD_AT, hot rows then: $HOT_AT_RELOAD"
prev=-1; same=0
until [ "$same" -ge 4 ]; do
  sleep 15
  cur="$(chq "SELECT count() FROM default.otel_logs" 2>/dev/null || echo 0)"
  if [ "$cur" = "$prev" ]; then same=$((same + 1)); else same=0; fi
  prev="$cur"; printf '  hot rows: %s\n' "$cur"
done
[ "$prev" != "0" ] || { echo "no rows reached ClickHouse" >&2; docker logs --tail 40 "$ROUTER" >&2 || true; docker logs --tail 20 "$ENGINE" >&2 || true; exit 1; }
docker stop "$ROUTER" >/dev/null; sleep 5
T1="$(date -u +%s)"
# the native engine image carries no curl; scrape from a helper on the same network
docker run --rm --network "$NET" alpine:latest wget -qO- "http://$ENGINE:9100/metrics" > "$BUILD/engine-metrics.txt" 2>/dev/null || true
echo "  prometheus scrape: $(wc -l < "$BUILD/engine-metrics.txt" | tr -d ' ') lines"
docker logs "$ENGINE" > "$BUILD/engine.log" 2>&1 || true
echo "  cold objects: $(s3 ls --recursive "s3://$BUCKET" | wc -l | tr -d " ")"

say "measure"
chq "SYSTEM FLUSH LOGS"
docker exec -i "$CS" clickhouse-client --multiquery < "$E2E/conf/schema_cold.sql" >/dev/null 2>&1 || echo "  (cold schema: see engine of the e2e; counts table cold side may be empty)"
python3 gate_report.py \
  --container "$CS" --wire "$BUILD/wire/returned.json" --engine-metrics "$BUILD/engine-metrics.txt" \
  --patches "$BUILD/patches.txt" --images "$BUILD/images.txt" --results "$RESULTS" \
  --ch-version "$CH_VERSION" --engine-image "$ENGINE_IMAGE" --lines "$LINES" \
  --feed-seconds "$((T1 - T0))" --reload-at "$RELOAD_AT" --hot-at-reload "$HOT_AT_RELOAD" \
  --totals conf/totals.csv --caps conf/caps.csv --partlog-before "$Q0_PARTLOG"
echo; echo "results in $RESULTS"
