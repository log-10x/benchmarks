#!/bin/bash
# Ceiling rig: OpenTelemetry demo 3.1.0 + the log10x Receiver launched from the values
# log10x-mcp renders (rig/gen-receiver-values.mjs), returned records to Datadog.
# The keys come from the shell environment only (rig/ddenv.sh exports them from SSM, and
# GH_TOKEN from `gh auth token`); nothing here writes a key to a file.
# Phases, each a subcommand:
#   up               start Fluent Bit + the Receiver, then the demo (kafka health retry)
#   wait-healthy     wait until no demo container is Created, Exited, unhealthy or starting
#   load <users> [spawn]   recreate the load generator with that many users (the growth knob)
#   flag <name> <variant>  set one demo flag through flagd-ui's storage (the UI's own write)
#   inject start|stop      a new service with one new statement, 2 lines a second
#   replay start <speed>|stop  replay the baseline capture (results/replay/source.jsonl) at
#                          its own pace times <speed>, looping (more load)
#   replay storm <rate> <until>  one real error line (results/replay/storm-line.json) at
#                          <rate> lines a second until <until epoch> (error storm)
#   mark <event> [json]    add a line to the timeline
#   logs             snapshot the rig container logs into RESULTS
#   down             stop the injector, snapshot logs, docker compose down (images kept)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DEMO=${DEMO:-/Users/talweiss/git/l1x-co/otel-demo-3.1.0}
export RIG_DIR=$HERE
RESULTS=${RESULTS:-$HERE/../results}
export RIG_DATA=${RIG_DATA:-$RESULTS/data}
export DEMO_VERSION=3.1.0
RIG_RECEIVER=${RIG_RECEIVER:-$RESULTS/values}
COMPOSE="docker compose -f $DEMO/compose.yaml -f $DEMO/compose.full.yaml -f $HERE/compose.rig.yaml -f $RIG_RECEIVER/compose.receiver.yaml"
mkdir -p "$RIG_DATA" "$RESULTS"
T=$RESULTS/timeline.jsonl
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
need_keys() { : "${DD_API_KEY:?run under rig/ddenv.sh}" "${GH_TOKEN:?export GH_TOKEN}"; }
receiver_ready() {
  until docker logs rig-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field'; do sleep 3; done
}

case "${1:-}" in
  up)
    need_keys
    cd "$DEMO"
    $COMPOSE up -d fluent-bit tenx
    receiver_ready
    mark receiver_ready
    for attempt in 1 2 3; do
      $COMPOSE up -d --remove-orphans && break
      echo "compose up attempt $attempt failed; waiting for kafka healthy"
      until [ "$(docker inspect kafka --format '{{.State.Health.Status}}' 2>/dev/null)" = healthy ]; do sleep 10; done
    done
    mark demo_up
    ;;
  wait-healthy)
    cd "$DEMO"
    bad=x
    for i in $(seq 1 60); do
      bad=$($COMPOSE ps -a --format '{{.Name}} {{.Status}}' | grep -E 'Created|Exited|unhealthy|starting' || true)
      [ -z "$bad" ] && break; sleep 10
    done
    $COMPOSE ps -a --format '{{.Name}} {{.Status}}'
    if [ -n "$bad" ]; then mark demo_not_healthy; exit 1; fi
    mark demo_healthy
    ;;
  load)
    need_keys
    users=${2:?users}; spawn=${3:-1}
    cd "$DEMO"
    RIG_LOCUST_USERS=$users RIG_LOCUST_SPAWN_RATE=$spawn $COMPOSE up -d --no-deps --force-recreate load-generator
    mark load "\"users\":$users,\"spawn_rate\":$spawn"
    ;;
  flag)
    name=${2:?flag}; variant=${3:?variant}
    docker exec flagd-ui /app/bin/flagd_ui rpc "GenServer.cast(Storage, {:write, \"$name\", \"$variant\"}) |> IO.inspect()"
    mark flag "\"flag\":\"$name\",\"variant\":\"$variant\""
    ;;
  inject)
    case "${2:-}" in
      start)
        net=$(docker inspect rig-fluent-bit --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')
        docker run -d --name inventory --network "$net" \
          --log-driver fluentd --log-opt fluentd-address=172.28.0.250:24224 --log-opt tag=app.inventory \
          --log-opt fluentd-async=true --log-opt fluentd-sub-second-precision=true --log-opt mode=non-blocking \
          alpine:latest sh -c 'i=0; while :; do i=$((i+1)); echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFO inventory reconcile sku=SKU-$((i % 500)) warehouse=eu-west-$((i % 3)) delta=$((i % 7)) took_ms=$((i % 90))"; usleep 500000; done'
        mark inject_start "\"service\":\"inventory\",\"lines_per_s\":2"
        ;;
      stop) docker rm -f inventory; mark inject_stop ;;
      *) echo "inject start|stop" >&2; exit 2 ;;
    esac
    ;;
  replay)
    # forward_send.py in a python:3.12-slim container on the demo network sends each line to
    # Fluent Bit over the Forward protocol, as the Docker driver would (a file feed through a
    # Docker Desktop bind mount arrived stale and was dropped).
    net=$(docker inspect rig-fluent-bit --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')
    case "${2:-}" in
      start)
        speed=${3:?speed}
        docker run -d --name rig-replay --network "$net" -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
          python3 -u /rig/forward_send.py replay /replay/source.jsonl "$speed" 172.28.0.250 24224
        mark replay_start "\"speed\":$speed,\"source\":\"baseline capture 02:00-04:00\""
        ;;
      stop) docker rm -f rig-replay; mark replay_stop ;;
      storm)
        rate=${3:?lines per second}; until=${4:?until epoch}
        docker run -d --name rig-storm --network "$net" -v "$HERE:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
          python3 -u /rig/forward_send.py storm /replay/storm-line.json "$rate" "$until" 172.28.0.250 24224
        mark storm_boost_start "\"lines_per_s\":$rate,\"until\":$until"
        ;;
      *) echo "replay start <speed>|stop|storm <rate> <until>" >&2; exit 2 ;;
    esac
    ;;
  mark) mark "${2:?event}" "${3:-}" ;;
  logs)
    docker logs -t rig-tenx > "$RESULTS/receiver.log" 2>&1 || true
    docker logs -t rig-fluent-bit > "$RESULTS/fluent-bit.log" 2>&1 || true
    ;;
  down)
    if ! mkdir "$RESULTS/.down.lock" 2>/dev/null; then echo "down already running"; exit 0; fi
    trap 'rmdir "$RESULTS/.down.lock"' EXIT
    if [ -f "$RESULTS/.down.done" ]; then echo "run already ended"; exit 0; fi
    docker rm -f inventory 2>/dev/null || true
    docker rm -f rig-replay rig-storm 2>/dev/null || true
    "$0" logs
    mark run_end
    touch "$RESULTS/.down.done"
    cd "$DEMO"; DD_API_KEY=x GH_TOKEN=x $COMPOSE down --remove-orphans
    mark demo_down
    ;;
  *) echo "usage: $0 up|wait-healthy|load <users> [spawn]|flag <name> <variant>|inject start|stop|mark <event>|logs|down" >&2; exit 2 ;;
esac
