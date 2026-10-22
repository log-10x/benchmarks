#!/bin/bash
# Elastic hot-tier rig. Phases, each a subcommand:
#   up                       Elasticsearch hot + frozen, trial licence, snapshot repository and
#                            the MCP's frozen-tier recipe (es-setup.mjs); then Fluent Bit and the
#                            Receiver as the MCP renders it with no cap; then the meter
#   receiver <cap|none>      re-render the Receiver values (with that fleet cap in bytes, tier_down)
#                            and recreate rig-tenx with them
#   replay start <speed> [offset s] | stop   the published OTel sample at 7 lines a second x speed
#   inject start|stop        a new service with one new statement, 2 lines a second
#   storm <rate> <until>     one real Grafana error line at <rate> lines a second until <until epoch>
#   mark <event> [json]      add a line to the timeline
#   down                     stop the load, snapshot logs, docker compose down (volumes kept)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export RIG_DIR=$HERE
RESULTS=${RESULTS:-$HERE/../results}
export RIG_DATA=${RIG_DATA:-$RESULTS/data}
export MCP=${MCP:-/Users/talweiss/git/l1x-co/wt-elastic-mcp}
VALUES=$RESULTS/values
mkdir -p "$RIG_DATA" "$RESULTS"
T=$RESULTS/timeline.jsonl
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
compose() { docker compose -p elastic-rig -f "$HERE/compose.yaml" -f "$VALUES/compose.receiver.yaml" "$@"; }
es() { curl -s -m 30 "http://127.0.0.1:9200$1"; }
receiver_ready() {
  for i in $(seq 1 120); do
    docker logs rig-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field' && return 0
    sleep 3
  done
  return 1
}
render() {
  rm -rf "$VALUES.new" && mkdir -p "$VALUES.new"
  node "$HERE/gen-receiver-values.mjs" "$VALUES.new" ${1:+$1} > "$VALUES.new/render.out"
  if [ -d "$VALUES" ]; then mv "$VALUES" "$RESULTS/values.$(date -u +%H%M%S)"; fi
  mv "$VALUES.new" "$VALUES"
}

case "${1:-}" in
  up)
    render
    # The shared snapshot volume is created root-owned; Elasticsearch runs as uid 1000.
    docker volume create elastic-rig_es-snapshots >/dev/null
    docker run --rm -v elastic-rig_es-snapshots:/s alpine:latest chown 1000:0 /s
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
    mark receiver_ready "\"cap\":null"
    python3 "$HERE/detach.py" "$RESULTS/meter.log" python3 "$HERE/meter.py" 600
    mark meter_started
    ;;
  receiver)
    cap=${2:?cap or none}
    if [ "$cap" = none ]; then render; else render "$cap"; fi
    compose up -d --force-recreate --no-deps tenx
    receiver_ready || { mark receiver_not_ready; exit 1; }
    mark receiver_ready "\"cap\":$([ "$cap" = none ] && echo null || echo "$cap")"
    ;;
  replay)
    case "${2:-}" in
      start)
        speed=${3:?speed}; offset=${4:-0}
        docker run -d --name rig-replay --network elastic-rig -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
          python3 -u /rig/forward_send.py replay /replay/source.jsonl "$speed" 172.29.0.250 24224 "$offset" >/dev/null
        echo "$(date +%s) $speed $offset" > "$RESULTS/replay.state"
        mark replay_start "\"speed\":$speed,\"offset_s\":$offset,\"lines_per_s\":$(python3 -c "print(7*$speed)")"
        ;;
      stop)
        docker rm -f rig-replay >/dev/null 2>&1 || true
        mark replay_stop
        ;;
      *) echo "replay start <speed> [offset] | stop" >&2; exit 2;;
    esac
    ;;
  inject)
    case "${2:-}" in
      start)
        docker run -d --name inventory --network elastic-rig \
          --log-driver fluentd --log-opt fluentd-address=172.29.0.250:24224 --log-opt tag=app.inventory \
          --log-opt fluentd-async=true --log-opt fluentd-sub-second-precision=true --log-opt mode=non-blocking \
          alpine:latest sh -c 'i=0; while :; do i=$((i+1)); echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFO inventory reconcile sku=SKU-$((i % 500)) warehouse=eu-west-$((i % 3)) delta=$((i % 7)) took_ms=$((i % 90))"; usleep 500000; done' >/dev/null
        mark inject_start
        ;;
      stop)
        docker rm -f inventory >/dev/null 2>&1 || true
        mark inject_stop
        ;;
    esac
    ;;
  storm)
    rate=${2:?rate}; until=${3:?until epoch}
    docker run -d --name rig-storm --network elastic-rig -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
      python3 -u /rig/forward_send.py storm /replay/storm-line.json "$rate" "$until" 172.29.0.250 24224 >/dev/null
    mark storm_start "\"rate\":$rate,\"until\":$until"
    ;;
  mark)
    mark "${2:?event}" ${3:+"$3"}
    ;;
  logs)
    for c in rig-tenx rig-fluent-bit rig-es-hot rig-es-frozen; do docker logs "$c" > "$RESULTS/$c.log" 2>&1 || true; done
    ;;
  down)
    docker rm -f rig-replay rig-storm inventory >/dev/null 2>&1 || true
    "$0" logs
    compose down
    mark run_end
    touch "$RESULTS/.down.done"
    ;;
  *) sed -n '2,13p' "$0"; exit 2;;
esac
