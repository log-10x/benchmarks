#!/bin/bash
# Containment demo rig: OpenTelemetry demo 3.1.0 + log10x Receiver (edge-10x 1.1.140).
# Phases, each a subcommand so a run can be resumed:
#   up        start Fluent Bit + Receiver (RIG_CAP=0), then the demo
#   quiet     mark the quiet-run window (no flags); caller waits QUIET_MIN minutes
#   cap <n>   recreate the Receiver with rateReceiverAbsoluteCap n
#   sched     start the flagd-ui scheduler with SEED (see scheduler.sh)
#   logs      snapshot flagd-ui and rig container logs into RESULTS
#   down      stop the scheduler, snapshot logs, docker compose down (images kept)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DEMO=${DEMO:-/Users/talweiss/git/l1x-co/otel-demo-3.1.0}
export RIG_DIR=$HERE
export RIG_DATA=${RIG_DATA:-$HERE/../results/data}
export DEMO_VERSION=3.1.0
export RIG_CAP=${RIG_CAP:-0}
RESULTS=${RESULTS:-$HERE/../results}
SEED=${SEED:-20261014}
COMPOSE="docker compose -f $DEMO/compose.yaml -f $DEMO/compose.full.yaml -f $HERE/compose.rig.yaml"
mkdir -p "$RIG_DATA" "$RESULTS"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
mark() { echo "{\"event\":\"$1\",\"at\":\"$(stamp)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$RESULTS/timeline.jsonl"; }

case "${1:-}" in
  up)
    cd "$DEMO"
    $COMPOSE up -d fluent-bit tenx
    until docker logs rig-tenx 2>&1 | grep -q 'Writing TenXObject field'; do sleep 3; done
    mark receiver_ready "\"cap\":$RIG_CAP"
    $COMPOSE up -d --remove-orphans
    mark demo_up
    ;;
  wait-healthy)
    cd "$DEMO"
    for i in $(seq 1 60); do
      bad=$($COMPOSE ps --format '{{.Name}} {{.Status}}' | grep -v -E 'healthy|Up [^(]*$' | grep -v 'rig-' || true)
      [ -z "$bad" ] && break; sleep 10
    done
    $COMPOSE ps --format '{{.Name}} {{.Status}}'
    mark demo_healthy
    ;;
  quiet-start) mark quiet_start ;;
  quiet-end)   mark quiet_end ;;
  cap)
    cd "$DEMO"; export RIG_CAP=${2:?cap bytes}
    $COMPOSE up -d --force-recreate --no-deps tenx
    until docker logs rig-tenx 2>&1 | grep -q 'Writing TenXObject field'; do sleep 3; done
    mark receiver_ready "\"cap\":$RIG_CAP"
    ;;
  sched)
    "$HERE/scheduler.sh" start "$SEED" "${2:-900}" "${3:-240}" "${4:-480}"
    mark scheduler_start "\"seed\":$SEED,\"interval_s\":${2:-900},\"min_hold_s\":${3:-240},\"max_hold_s\":${4:-480}"
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
    if r.get("container_name")=="flagd-ui" and "Flag scheduler" in str(r.get("log","")):
        t=datetime.datetime.fromtimestamp(float(r["fb_ts"]),datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")+"Z"
        print(t, r["log"].strip())' "$RIG_DATA/raw.jsonl" > "$RESULTS/scheduler.log" || true
    docker logs -t rig-tenx > "$RESULTS/receiver.log" 2>&1 || true
    docker logs -t rig-fluent-bit 2>&1 | grep -v '^{' > "$RESULTS/fluent-bit.log" || true
    "$HERE/scheduler.sh" state > "$RESULTS/scheduler-state.txt" 2>&1 || true
    ;;
  down)
    "$0" sched-stop || true
    "$0" logs
    mark run_end
    cd "$DEMO"; $COMPOSE down --remove-orphans
    mark demo_down
    ;;
  *) echo "usage: $0 up|wait-healthy|quiet-start|quiet-end|cap <bytes>|sched [interval min max]|sched-stop|logs|down" >&2; exit 2 ;;
esac
