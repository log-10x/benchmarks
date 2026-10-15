#!/bin/bash
# Drive the flagd-ui scheduler (demo 3.1.0) through the Elixir release's rpc entry point.
# The scheduler has no HTTP API; FlagdUi.Scheduler.start_schedule/1 is the same call the
# LiveView form makes. Flags of interest with the variant each is activated at.
#   scheduler.sh start <seed> [interval_s] [min_hold_s] [max_hold_s]
#   scheduler.sh stop
#   scheduler.sh state
set -euo pipefail
cmd=${1:-state}
case "$cmd" in
  start)
    seed=${2:?seed}; interval=${3:-900}; minh=${4:-240}; maxh=${5:-480}
    docker exec flagd-ui /app/bin/flagd_ui rpc "FlagdUi.Scheduler.start_schedule(%{interval_ms: ${interval}000, min_duration_ms: ${minh}000, max_duration_ms: ${maxh}000, concurrency: 1, seed: ${seed}, flags: %{\"kafkaQueueProblems\" => [\"on\"], \"cartFailure\" => [\"100%\"], \"paymentFailure\" => [\"100%\"], \"recommendationCacheFailure\" => [\"on\"], \"loadGeneratorFloodHomepage\" => [\"on\"], \"emailMemoryLeak\" => [\"1000x\"]}}) |> IO.inspect()"
    ;;
  stop)
    docker exec flagd-ui /app/bin/flagd_ui rpc "FlagdUi.Scheduler.stop_schedule() |> IO.inspect()"
    ;;
  state)
    docker exec flagd-ui /app/bin/flagd_ui rpc "FlagdUi.Scheduler.state() |> IO.inspect(limit: :infinity)"
    ;;
  *) echo "usage: $0 start <seed> [interval_s] [min_hold_s] [max_hold_s] | stop | state" >&2; exit 2;;
esac
