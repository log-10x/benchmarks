#!/bin/bash
# Elastic hot-tier budget rig. Subcommands:
#   up                    seed the policy branch, start Elasticsearch hot + frozen, apply the MCP recipe
#                         (es-setup.mjs, the kept stream held KEEP_HOT_HOURS on hot), start Fluent Bit and the
#                         Receiver as the MCP renders it for the hot-tier run, start the meter
#   replay start <speed> [offset s] | stop   the published OTel sample at 7 lines a second x speed
#   inject start|stop     a new service with one new statement, 2 lines a second
#   storm <rate> <until>  one real Grafana error line at <rate> lines a second until <until epoch>
#   mark <event> [json]   add a line to the timeline
#   down                  stop the load, snapshot logs, docker compose down (volumes kept)
# GH_TOKEN (gh auth token) reaches the Receiver from the shell by name; nothing writes it to a file.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export RIG_DIR=$HERE
RESULTS=${RESULTS:-$HERE/../results}
export RIG_DATA=${RIG_DATA:-$RESULTS/data}
export MCP=${MCP:?log10x-mcp package}
export POLICY_BRANCH=${POLICY_BRANCH:-test/elastic-hot-tier-policy}
VALUES=$RESULTS/values
mkdir -p "$RIG_DATA" "$RESULTS"
T=$RESULTS/timeline.jsonl
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
compose() { docker compose -p elastic-budget -f "$HERE/compose.yaml" -f "$VALUES/compose.receiver.yaml" "$@"; }
es() { curl -s -m 30 "http://127.0.0.1:9200$1"; }
receiver_ready() {
  for i in $(seq 1 120); do
    docker logs hb-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field' && return 0
    sleep 3
  done
  return 1
}
case "${1:-}" in
  up)
    : "${GH_TOKEN:?export GH_TOKEN=\$(gh auth token)}"
    mkdir -p "$VALUES" && node "$HERE/gen-receiver-values.mjs" "$VALUES" > "$VALUES/render.out"
    bash "$VALUES/seed.sh" && mark policy_branch_seeded "\"branch\":\"$POLICY_BRANCH\""
    docker volume create elastic-budget_es-snapshots >/dev/null
    docker run --rm -v elastic-budget_es-snapshots:/s alpine:latest chown 1000:0 /s
    compose up -d es-hot es-frozen
    for i in $(seq 1 90); do
      n=$( (es '/_cat/nodes?h=name' 2>/dev/null || true) | grep -c . || true)
      [ "$n" = 2 ] && break; sleep 5
    done
    [ "$n" = 2 ] || { mark es_not_ready; exit 1; }
    mark es_ready "\"version\":\"$(es / | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"]["number"])')\""
    node "$HERE/es-setup.mjs" "$RESULTS/es-setup"
    mark es_setup_done
    compose up -d fluent-bit tenx
    receiver_ready || { mark receiver_not_ready; exit 1; }
    mark receiver_ready
    python3 "$HERE/detach.py" "$RESULTS/meter.log" python3 "$HERE/meter.py" "${METER_S:-600}"
    mark meter_started
    ;;
  replay)
    case "${2:-}" in
      start)
        speed=${3:?speed}; offset=${4:-0}
        docker run -d --name hb-replay --network elastic-budget -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
          python3 -u /rig/forward_send.py replay /replay/source.jsonl "$speed" 172.30.0.250 24224 "$offset" >/dev/null
        echo "$(date +%s) $speed $offset" > "$RESULTS/replay.state"
        mark replay_start "\"speed\":$speed,\"offset_s\":$offset,\"lines_per_s\":$(python3 -c "print(7*$speed)")"
        ;;
      stop) docker rm -f hb-replay >/dev/null 2>&1 || true; mark replay_stop ;;
    esac
    ;;
  inject)
    case "${2:-}" in
      start)
        docker run -d --name hb-inventory --network elastic-budget \
          --log-driver fluentd --log-opt fluentd-address=172.30.0.250:24224 --log-opt tag=app.inventory \
          --log-opt fluentd-async=true --log-opt fluentd-sub-second-precision=true --log-opt mode=non-blocking \
          alpine:latest sh -c 'i=0; while :; do i=$((i+1)); echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFO inventory reconcile sku=SKU-$((i % 500)) warehouse=eu-west-$((i % 3)) delta=$((i % 7)) took_ms=$((i % 90))"; usleep 500000; done' >/dev/null
        mark inject_start ;;
      stop) docker rm -f hb-inventory >/dev/null 2>&1 || true; mark inject_stop ;;
    esac
    ;;
  storm)
    rate=${2:?rate}; until=${3:?until epoch}
    docker run -d --name hb-storm --network elastic-budget -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
      python3 -u /rig/forward_send.py storm /replay/storm-line.json "$rate" "$until" 172.30.0.250 24224 >/dev/null
    mark storm_start "\"rate\":$rate,\"until\":$until"
    ;;
  mark) mark "${2:?event}" ${3:+"$3"} ;;
  logs)
    for c in hb-tenx hb-fluent-bit hb-es-hot hb-es-frozen; do docker logs "$c" > "$RESULTS/$c.log" 2>&1 || true; done
    # Fluent Bit's own counters: lines in (forward.0) and records back (forward.1), for delivery without a raw copy
    docker run --rm --network elastic-budget python:3.12-slim python3 -c "import urllib.request; print(urllib.request.urlopen('http://172.30.0.250:2020/api/v1/metrics').read().decode())" > "$RESULTS/fluentbit-metrics.json" 2>/dev/null || true
    ;;
  down)
    docker rm -f hb-replay hb-storm hb-inventory >/dev/null 2>&1 || true
    "$0" logs
    GH_TOKEN=x compose down
    mark run_end
    touch "$RESULTS/.down.done"
    ;;
  *) sed -n '2,12p' "$0"; exit 2;;
esac
