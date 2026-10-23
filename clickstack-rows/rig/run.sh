#!/usr/bin/env bash
# The ClickHouse rows run's rig: the clickstack-e2e containers plus Prometheus, a
# pacer that feeds the collector's file at a set rate, and the Receiver reading
# its policy files from a GitHub branch the rows run commits to.
#
#   rig/run.sh up                 seed the policy branch, start the containers, start the meter
#   rig/run.sh pace <lines/s>     set the replay pace (0 pauses); starts the pacer on first use
#   rig/run.sh inject start|stop  a new service (inventory) at 2 lines/s
#   rig/run.sh storm <lines/s> <until-epoch>   one real Grafana error line, repeated
#   rig/run.sh mark <event> [json]
#   rig/run.sh collect            logs, the Receiver's scrape, the wire tap
#   rig/run.sh down               remove the containers, the network and the volumes
#
# Names stay the e2e ones (cse-*): rig/router.yaml and clickstack-e2e/conf/schema_cold.sql
# address them. Memory: ClickStack 3g, Receiver 2g, collector 1g, RustFS 512m, Prometheus 512m.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
E2E="$ROOT/../clickstack-e2e"
GATE="$ROOT/../clickstack-rows-gate"
RESULTS="${RESULTS:-$ROOT/results}"
DATA="$RESULTS/data"
T="$RESULTS/timeline.jsonl"
POLICY_REPO="${POLICY_REPO:-log-10x/config}"
export POLICY_BRANCH="${POLICY_BRANCH:-test/clickhouse-rows-policy}"
CAPTURE="${CAPTURE:-$ROOT/../../benchmarks/clickstack-e2e/data/otel-sample-200mb.log}"
CS_IMAGE="${CSE_CS_IMAGE:-clickhouse/clickstack-all-in-one:2.38.0}"
ENGINE_IMAGE="${CSE_ENGINE_IMAGE:-ghcr.io/log-10x/edge-10x:1.1.147}"
OTEL_IMAGE="${CSE_OTEL_IMAGE:-otel/opentelemetry-collector-contrib:0.160.0}"
S3_IMAGE="${CSE_MINIO_IMAGE:-rustfs/rustfs:latest}"
AWS_IMAGE="${CSE_AWS_IMAGE:-amazon/aws-cli:latest}"
PROM_IMAGE="${CSE_PROM_IMAGE:-prom/prometheus:v3.9.1}"
PY_IMAGE="${CSE_PY_IMAGE:-python:3.12-slim}"
NET=cse-net; CS=cse-clickstack; ENGINE=cse-engine; ROUTER=cse-router; S3=cse-minio; PROM=cse-prom; PACER=cse-pacer; INJECT=cse-inject; STORM=cse-storm
BUCKET=coldlogs
HDX_EMAIL="rows@log10x.test"; HDX_PASSWORD="Passw0rd!2026"

mark() { mkdir -p "$RESULTS"; echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
chq() { docker exec "$CS" clickhouse-client --query "$1"; }
s3() { docker run --rm --network "$NET" -e AWS_ACCESS_KEY_ID=minioadmin -e AWS_SECRET_ACCESS_KEY=minioadmin -e AWS_DEFAULT_REGION=us-east-1 "$AWS_IMAGE" --endpoint-url "http://$S3:9000" s3 "$@"; }

up() {
  : "${GH_TOKEN:?export GH_TOKEN=\$(gh auth token)}"
  mkdir -p "$RESULTS" "$DATA" "$RESULTS/wire" "$RESULTS/build"
  : > "$DATA/feed.log"; chmod 666 "$DATA/feed.log"; echo 0 > "$DATA/pace.txt"
  : > "$RESULTS/wire/returned.json"; chmod 666 "$RESULTS/wire/returned.json"; chmod 777 "$RESULTS/wire"
  [ -s "$CAPTURE" ] || { echo "capture not at $CAPTURE" >&2; exit 1; }
  SEED="$(POLICY_BRANCH="$POLICY_BRANCH" POLICY_REPO="$POLICY_REPO" bash "$HERE/seed-policy-branch.sh")"
  mark policy_branch_seeded "\"branch\":\"$POLICY_BRANCH\",\"commit\":\"$SEED\""
  for img in "$CS_IMAGE" "$ENGINE_IMAGE" "$OTEL_IMAGE" "$S3_IMAGE" "$AWS_IMAGE" "$PROM_IMAGE" "$PY_IMAGE"; do
    docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img" >/dev/null
    printf '%s %s\n' "$img" "$(docker image inspect "$img" --format '{{index .RepoDigests 0}}' 2>/dev/null | sed 's/.*@//')"
  done > "$RESULTS/images.txt"
  docker network create "$NET" >/dev/null 2>&1 || true

  docker run -d --name "$S3" --network "$NET" --memory 512m -e RUSTFS_ACCESS_KEY=minioadmin -e RUSTFS_SECRET_KEY=minioadmin "$S3_IMAGE" >/dev/null
  for _ in $(seq 1 30); do s3 ls >/dev/null 2>&1 && break; sleep 2; done
  s3 mb "s3://$BUCKET" >/dev/null && mark s3_ready

  docker run -d --name "$CS" --network "$NET" --memory 3g --cpus 3 -p 127.0.0.1:8123:8123 "$CS_IMAGE" >/dev/null
  for _ in $(seq 1 100); do chq "SELECT 1" >/dev/null 2>&1 && break; sleep 3; done
  until chq "EXISTS TABLE default.otel_logs" 2>/dev/null | grep -q 1; do sleep 3; done
  for _ in $(seq 1 100); do docker exec "$CS" curl -s -o /dev/null http://localhost:8000/ && break; sleep 3; done
  printf '{"email":"%s","password":"%s","confirmPassword":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" "$HDX_PASSWORD" > "$RESULTS/build/register.json"
  printf '{"email":"%s","password":"%s"}' "$HDX_EMAIL" "$HDX_PASSWORD" > "$RESULTS/build/login.json"
  docker cp "$RESULTS/build/register.json" "$CS":/tmp/register.json >/dev/null
  docker cp "$RESULTS/build/login.json" "$CS":/tmp/login.json >/dev/null
  docker exec "$CS" curl -s -X POST http://localhost:8000/register/password -H "Content-Type: application/json" --data-binary @/tmp/register.json >/dev/null
  docker exec "$CS" sh -c 'curl -s -c /tmp/ck.txt -X POST http://localhost:8000/login/password -H "Content-Type: application/json" --data-binary @/tmp/login.json > /dev/null'
  HDX_API_KEY="$(docker exec "$CS" sh -c 'curl -s -b /tmp/ck.txt http://localhost:8000/team' | sed -n 's/.*"apiKey":"\([^"]*\)".*/\1/p')"
  [ -n "$HDX_API_KEY" ] || { echo "no HyperDX ingestion key" >&2; exit 1; }
  # ClickStack's own collector starts under an OpAMP supervisor that can time out at boot
  # ("collector's OpAMP client never connected"); without it nothing listens on 4317.
  otlp_up() { docker exec "$CS" sh -c 'netstat -ltn 2>/dev/null | grep -q ":4317 "'; }
  for _ in $(seq 1 30); do otlp_up && break; sleep 3; done
  if ! otlp_up; then
    mark clickstack_collector_restart
    docker restart "$CS" >/dev/null
    for _ in $(seq 1 100); do chq "SELECT 1" >/dev/null 2>&1 && break; sleep 3; done
    for _ in $(seq 1 60); do otlp_up && break; sleep 3; done
    otlp_up || { echo "ClickStack's collector never listened on 4317" >&2; docker exec "$CS" tail -5 /var/log/otel-collector.log >&2; exit 1; }
  fi
  # a read-only user for the rows run over HTTP: SELECT on the two system tables it reads
  docker exec -i "$CS" sh -c 'cat > /etc/clickhouse-server/users.d/rows_meter.xml' < "$HERE/rows_meter.xml"
  chq "SYSTEM RELOAD CONFIG" >/dev/null
  for _ in $(seq 1 15); do curl -s -u rows_meter:rows-meter-rig 'http://127.0.0.1:8123/' --data-binary 'SELECT 1' | grep -qx 1 && break; sleep 2; done
  docker exec -i "$CS" clickhouse-client --multiquery < "$E2E/conf/schema_hot.sql"
  chq "ALTER TABLE default.otel_logs ADD COLUMN IF NOT EXISTS day Date MATERIALIZED toDate(Timestamp)"
  chq "ALTER TABLE default.otel_logs ADD COLUMN IF NOT EXISTS ins DateTime64(3) MATERIALIZED now64(3)"
  mark clickstack_ready "\"version\":\"$(chq 'SELECT version()')\""

  # the Receiver: the gate's config patches (collector input, Prometheus scrape, unit events, pattern text
  # on the wire), and the same options as launch arguments, the way receiverFleetValues writes them
  rm -rf "$RESULTS/build/tenx-config"; mkdir -p "$RESULTS/build/tenx-config"
  docker rm -f cse-config-tmp >/dev/null 2>&1 || true
  docker create --name cse-config-tmp "$ENGINE_IMAGE" >/dev/null
  docker cp cse-config-tmp:/etc/tenx/config/. "$RESULTS/build/tenx-config/" >/dev/null
  docker rm cse-config-tmp >/dev/null
  python3 "$GATE/patch_engine_config.py" --config-dir "$RESULTS/build/tenx-config" > "$RESULTS/build/patches.txt"
  docker run -d --name "$ENGINE" --network "$NET" --memory 2g --cpus 2 \
    -v "$RESULTS/build/tenx-config":/etc/tenx/config:ro \
    -e GH_ENABLED=true -e GH_REPO="$POLICY_REPO" -e GH_BRANCH="$POLICY_BRANCH" -e GH_TOKEN="$GH_TOKEN" -e GH_SYNC_INTERVAL=30s \
    -e outputOffload=true \
    -e TENX_OTEL_COLLECTOR_OUTPUT_HOST="$ROUTER" -e TENX_OTEL_COLLECTOR_OUTPUT_PORT=24225 \
    "$ENGINE_IMAGE" @apps/gate rateReceiverUnit events symbolMessageHashField tenx_hash >/dev/null
  for _ in $(seq 1 60); do
    docker logs "$ENGINE" > "$RESULTS/build/engine-start.log" 2>&1 || true
    grep -q "OTLP/gRPC logs server listening" "$RESULTS/build/engine-start.log" && break
    sleep 3
  done
  grep -q "OTLP/gRPC logs server listening" "$RESULTS/build/engine-start.log" || { echo "the receiver did not start" >&2; tail -30 "$RESULTS/build/engine-start.log" >&2; exit 1; }
  mark receiver_ready

  docker run -d --name "$PROM" --network "$NET" --memory 512m -p 127.0.0.1:9090:9090 \
    -v "$HERE/prometheus.yml":/etc/prometheus/prometheus.yml:ro "$PROM_IMAGE" >/dev/null
  docker run -d --name "$ROUTER" --network "$NET" --memory 1g --cpus 2 \
    -e HDX_API_KEY="$HDX_API_KEY" -e AWS_ACCESS_KEY_ID=minioadmin -e AWS_SECRET_ACCESS_KEY=minioadmin \
    -v "$HERE/router.yaml":/etc/otelcol-contrib/config.yaml:ro -v "$DATA":/data:ro -v "$RESULTS/wire":/wire \
    "$OTEL_IMAGE" >/dev/null
  mark collector_ready
  nohup python3 "$HERE/meter.py" "${METER_S:-100}" "$CS" "$RESULTS/wire/returned.json" "$RESULTS/meter.log" > "$RESULTS/meter.err" 2>&1 &
  echo $! > "$RESULTS/meter.pid"
  mark meter_started "\"every_s\":${METER_S:-100}"
}

pace() {
  echo "${1:?lines per second}" > "$DATA/pace.txt"
  if ! docker ps --format '{{.Names}}' | grep -q "^$PACER$"; then
    docker run -d --name "$PACER" --network "$NET" -v "$HERE:/rig:ro" -v "$CAPTURE":/capture.log:ro -v "$DATA":/data "$PY_IMAGE" \
      python3 -u /rig/pacer.py replay /capture.log /data/feed.log /data/pace.txt >/dev/null
  fi
  mark pace "\"lines_per_s\":$1"
}

case "${1:-}" in
  up) up ;;
  pace) pace "$2" ;;
  inject)
    case "${2:-}" in
      start)
        echo 2 > "$DATA/inject-pace.txt"
        docker run -d --name "$INJECT" --network "$NET" -v "$HERE:/rig:ro" -v "$DATA":/data "$PY_IMAGE" \
          python3 -u /rig/pacer.py inject /data/feed.log /data/inject-pace.txt inventory 'Inventory check for sku {n} finished in 12 ms' >/dev/null
        mark inject_start ;;
      stop) docker rm -f "$INJECT" >/dev/null 2>&1 || true; mark inject_stop ;;
    esac ;;
  storm)
    echo "${2:?rate}" > "$DATA/storm-pace.txt"
    docker run -d --name "$STORM" --network "$NET" -v "$HERE:/rig:ro" -v "$DATA":/data "$PY_IMAGE" \
      python3 -u /rig/pacer.py storm /data/feed.log /data/storm-pace.txt /rig/storm-line.json "${3:?until epoch}" >/dev/null
    mark storm_start "\"rate\":$2,\"until\":$3" ;;
  mark) mark "${2:?event}" ${3:+"$3"} ;;
  collect)
    for c in "$ENGINE" "$ROUTER" "$CS" "$PROM"; do docker logs "$c" > "$RESULTS/$c.log" 2>&1 || true; done
    docker run --rm --network "$NET" alpine:latest wget -qO- "http://$ENGINE:9100/metrics" > "$RESULTS/engine-metrics.txt" 2>/dev/null || true
    echo "cold objects: $(s3 ls --recursive "s3://$BUCKET" | wc -l | tr -d ' ')" > "$RESULTS/objects.txt"
    docker exec -i "$CS" clickhouse-client --multiquery < "$E2E/conf/schema_cold.sql" > /dev/null 2>&1 || true
    mark collected ;;
  down)
    [ -f "$RESULTS/meter.pid" ] && kill "$(cat "$RESULTS/meter.pid")" 2>/dev/null || true
    docker rm -f -v "$PACER" "$INJECT" "$STORM" "$ROUTER" "$PROM" "$ENGINE" "$CS" "$S3" >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
    mark run_end ;;
  *) sed -n 2,14p "$0"; exit 1 ;;
esac
