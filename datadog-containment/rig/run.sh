#!/bin/bash
# Containment demo rig: OpenTelemetry demo 3.1.0 + the log10x Receiver launched from the
# values log10x-mcp renders (rig/gen-receiver-values.mjs). RIG_RECEIVER names the directory
# that holds those values and their compose.receiver.yaml.
# Phases, each a subcommand so a run can be resumed:
#   up            start Fluent Bit + the Receiver, then the demo (kafka health retry)
#   wait-healthy  wait until no demo container is Created, Exited, unhealthy or starting
#   quiet-start   mark the quiet-run window (no flags)
#   quiet-end     mark its end
#   receiver      recreate the Receiver from RIG_RECEIVER (the demo keeps running)
#   sched         start the flagd-ui scheduler with SEED (see scheduler.sh)
#   logs          snapshot the scheduler lines and the rig container logs into RESULTS
#   down          stop the scheduler, snapshot logs, docker compose down (images kept);
#                 runs once per run even when several stoppers call it
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DEMO=${DEMO:-/Users/talweiss/git/l1x-co/otel-demo-3.1.0}
export RIG_DIR=$HERE
export RIG_DATA=${RIG_DATA:-$HERE/../results/data}
export DEMO_VERSION=3.1.0
RESULTS=${RESULTS:-$HERE/../results}
RIG_RECEIVER=${RIG_RECEIVER:-$(cat "$RESULTS/receiver-current" 2>/dev/null || true)}
SEED=${SEED:-20261014}
[ -n "$RIG_RECEIVER" ] && [ -f "$RIG_RECEIVER/compose.receiver.yaml" ] || { echo "RIG_RECEIVER must name a values directory with compose.receiver.yaml" >&2; exit 2; }
COMPOSE="docker compose -f $DEMO/compose.yaml -f $DEMO/compose.full.yaml -f $HERE/compose.rig.yaml -f $RIG_RECEIVER/compose.receiver.yaml"
mkdir -p "$RIG_DATA" "$RESULTS"
T=$RESULTS/timeline.jsonl
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
cap_of() { python3 -c 'import json,sys; v=json.load(open(sys.argv[1])); fd=v.get("fleet_default_input") or {}; print(fd.get("capBytesPerWindowPerNode",0))' "$RIG_RECEIVER/launch.json"; }
receiver_ready() {
  until docker logs rig-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field'; do sleep 3; done
}

case "${1:-}" in
  up)
    cd "$DEMO"
    echo "$RIG_RECEIVER" > "$RESULTS/receiver-current"
    $COMPOSE up -d fluent-bit tenx
    receiver_ready
    mark receiver_ready "\"cap\":$(cap_of),\"values\":\"$RIG_RECEIVER\""
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
  quiet-start) mark quiet_start ;;
  quiet-end)   mark quiet_end ;;
  receiver)
    cd "$DEMO"
    echo "$RIG_RECEIVER" > "$RESULTS/receiver-current"
    $COMPOSE up -d --no-deps --force-recreate tenx
    receiver_ready
    mark receiver_ready "\"cap\":$(cap_of),\"values\":\"$RIG_RECEIVER\""
    ;;
  sched)
    "$HERE/scheduler.sh" start "$SEED" "${2:-600}" "${3:-240}" "${4:-480}"
    mark scheduler_start "\"seed\":$SEED,\"interval_s\":${2:-600},\"min_hold_s\":${3:-240},\"max_hold_s\":${4:-480}"
    ;;
  sched-stop)
    "$HERE/scheduler.sh" stop; mark scheduler_stop
    ;;
  logs)
    # flagd-ui logs through the fluentd driver (dual-logging cache off), so its lines
    # live in raw.jsonl; keep a plain copy of the scheduler lines with their ingest time.
    python3 -c 'import json,sys,datetime
for l in open(sys.argv[1], errors="replace"):
    try: r=json.loads(l)
    except Exception: continue
    if (r.get("kubernetes") or {}).get("container_name")=="flagd-ui" and "Flag scheduler" in str(r.get("log","")):
        t=datetime.datetime.fromtimestamp(float(r["fb_ts"]),datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")+"Z"
        print(t, r["log"].strip())' "$RIG_DATA/raw.jsonl" > "$RESULTS/scheduler.log" || true
    docker logs -t rig-tenx > "$RESULTS/receiver.log" 2>&1 || true
    docker logs -t rig-fluent-bit > "$RESULTS/fluent-bit.log" 2>&1 || true
    "$HERE/scheduler.sh" state > "$RESULTS/scheduler-state.txt" 2>&1 || true
    ;;
  down)
    # One stopper at a time; a second caller finds the run already ended and returns.
    if ! mkdir "$RESULTS/.down.lock" 2>/dev/null; then echo "down already running"; exit 0; fi
    trap 'rmdir "$RESULTS/.down.lock"' EXIT
    if [ -f "$RESULTS/.down.done" ]; then echo "run already ended"; exit 0; fi
    "$0" sched-stop || true
    "$0" logs
    mark run_end
    touch "$RESULTS/.down.done"
    cd "$DEMO"; $COMPOSE down --remove-orphans
    mark demo_down
    ;;
  *) echo "usage: $0 up|wait-healthy|quiet-start|quiet-end|receiver|sched [interval min max]|sched-stop|logs|down" >&2; exit 2 ;;
esac
