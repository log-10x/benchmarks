#!/bin/bash
# Elastic hot-tier budget rig. Subcommands:
#   up                    seed the policy branch, start Elasticsearch hot + frozen, apply the MCP recipe
#                         (es-setup.mjs, the kept stream held KEEP_HOT_HOURS on hot), start Fluent Bit and the
#                         Receiver as the MCP renders it for the hot-tier run, start the meter
#   replay start <speed> [offset s] | stop   the published OTel sample at 7 lines a second x speed
#   feed start <speed> | speed <speed> | stop   the same sample from one sender for the whole run, each
#                         line numbered (seq); a speed change takes effect within a second
#   inject start|stop     a new service with one new statement, 2 lines a second
#   storm <rate> <until>  one real Grafana error line at <rate> lines a second until <until epoch>
#   mark <event> [json]   add a line to the timeline
#   down                  stop the load, snapshot logs, docker compose down (volumes kept)
#   clean                 remove the rig's containers (docker rm -f -v), its elastic-budget_* volumes and network
# ARM_B=1 adds arm B's cluster (compose.arm-b.yaml, 127.0.0.1:9201), set up by es-setup-b.mjs after arm A's.
# WARM=1 adds compose.warm.yaml (each frozen node also data_warm); TD_PLACEMENT reaches es-setup.mjs.
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
compose() { docker compose -p elastic-budget -f "$HERE/compose.yaml" -f "$VALUES/compose.receiver.yaml" ${ARM_B:+-f "$HERE/compose.arm-b.yaml"} ${WARM:+-f "$HERE/compose.warm.yaml"} "$@"; }
oneshot() { local n=$1; shift; docker rm -f -v "$n" >/dev/null 2>&1 || true; docker run -d --name "$n" "$@" >/dev/null; docker wait "$n" >/dev/null; docker logs "$n" 2>/dev/null; docker rm -f -v "$n" >/dev/null 2>&1 || true; }
es() { curl -s -m 30 "http://127.0.0.1:${2:-9200}$1"; }
nodes_up() {
  for i in $(seq 1 90); do
    n=$( (es '/_cat/nodes?h=name' "$1" 2>/dev/null || true) | grep -c . || true)
    [ "$n" = 2 ] && return 0; sleep 5
  done
  return 1
}
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
    oneshot hb-chown -v elastic-budget_es-snapshots:/s alpine:latest chown 1000:0 /s
    if [ -n "${ARM_B:-}" ]; then
      docker volume create elastic-budget_es-snapshots-b >/dev/null
      oneshot hb-chown -v elastic-budget_es-snapshots-b:/s alpine:latest chown 1000:0 /s
    fi
    compose up -d es-hot es-frozen ${ARM_B:+es-hot-b es-frozen-b}
    nodes_up 9200 || { mark es_not_ready; exit 1; }
    mark es_ready "\"version\":\"$(es / | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"]["number"])')\""
    node "$HERE/es-setup.mjs" "$RESULTS/es-setup"
    mark es_setup_done
    if [ -n "${ARM_B:-}" ]; then
      nodes_up 9201 || { mark es_b_not_ready; exit 1; }
      mark es_b_ready "\"version\":\"$(es / 9201 | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"]["number"])')\""
      node "$HERE/es-setup-b.mjs" "$RESULTS/es-setup-b"
      mark es_b_setup_done
    fi
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
  feed)
    case "${2:-}" in
      start)
        echo "${3:?speed}" > "$RESULTS/replay/speed"
        docker run -d --name hb-feed --network elastic-budget -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
          python3 -u /rig/forward_send.py paced /replay/source.jsonl /replay/speed 172.30.0.250 24224 >/dev/null
        mark feed_start "\"speed\":$3,\"lines_per_s\":$(python3 -c "print(7*$3)")"
        ;;
      speed)
        echo "${3:?speed}" > "$RESULTS/replay/speed"
        mark feed_speed "\"speed\":$3,\"lines_per_s\":$(python3 -c "print(7*$3)")"
        ;;
      stop)
        echo 0 > "$RESULTS/replay/speed"
        for i in $(seq 1 30); do [ "$(docker inspect -f '{{.State.Running}}' hb-feed 2>/dev/null)" = true ] || break; sleep 1; done
        final=$(docker logs hb-feed 2>&1 | python3 -c "import json,sys
f=[json.loads(l)['final_seq'] for l in sys.stdin if l.startswith('{') and 'final_seq' in l]; print(f[-1] if f else 'null')")
        docker logs hb-feed > "$RESULTS/hb-feed.log" 2>&1 || true
        docker rm -f -v hb-feed >/dev/null 2>&1 || true
        mark feed_stop "\"final_seq\":$final"
        ;;
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
    for c in hb-tenx hb-fluent-bit hb-es-hot hb-es-frozen ${ARM_B:+hb-es-hot-b hb-es-frozen-b}; do docker logs "$c" > "$RESULTS/$c.log" 2>&1 || true; done
    # Fluent Bit's own counters: lines in (forward.0) and records back (forward.1), for delivery without a raw copy
    oneshot hb-fbmetrics --network elastic-budget python:3.12-slim python3 -c "import urllib.request; print(urllib.request.urlopen('http://172.30.0.250:2020/api/v1/metrics').read().decode())" > "$RESULTS/fluentbit-metrics.json" || true
    ;;
  down)
    docker rm -f hb-replay hb-storm hb-inventory >/dev/null 2>&1 || true
    docker inspect hb-feed >/dev/null 2>&1 && "$0" feed stop
    "$0" logs
    GH_TOKEN=x compose down
    mark run_end
    touch "$RESULTS/.down.done"
    ;;
  clean)
    docker rm -f -v hb-replay hb-storm hb-inventory hb-feed hb-chown hb-fbmetrics hb-tenx hb-fluent-bit \
      hb-es-hot hb-es-frozen hb-es-hot-b hb-es-frozen-b >/dev/null 2>&1 || true
    vols=$(docker volume ls -q | grep '^elastic-budget_' || true)
    [ -z "$vols" ] || docker volume rm -f $vols >/dev/null
    docker network rm elastic-budget >/dev/null 2>&1 || true
    mark clean "\"volumes_removed\":\"$(echo $vols)\""
    ;;
  *) sed -n '2,16p' "$0"; exit 2;;
esac
