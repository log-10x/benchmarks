#!/bin/bash
# The budget phase, unattended: hourly budget runs (the MCP's `hourly` preset, minute 0),
# the growth steps, the error storm, the new service, then the stop. Times are minutes
# after B0, the epoch of the first applied budget run (run by hand once X is set).
# Run detached under rig/ddenv.sh with GH_TOKEN exported:
#   B0=<epoch> USERS_2X=<n> USERS_3X=<n> MCP=<pkg> budget-phase.sh
# Settings: HOURS (5), STORM_AT (90), STORM_MIN (30), INJECT_AT (135), INJECT_MIN (60),
#           GROW2_AT (5), GROW3_AT (65).
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
export RESULTS
B0=${B0:?epoch of the first budget run}
HOURS=${HOURS:-5}
GROW2_AT=${GROW2_AT:-5}; GROW3_AT=${GROW3_AT:-65}
STORM_AT=${STORM_AT:-90}; STORM_MIN=${STORM_MIN:-30}
INJECT_AT=${INJECT_AT:-135}; INJECT_MIN=${INJECT_MIN:-60}
first_hour=$(( (B0 / 3600 + 1) * 3600 ))
end=$(( first_hour + (HOURS - 1) * 3600 ))
echo $(( end + 1800 )) > "$RESULTS/deadline"

events=()
add() { events+=("$1 $2"); }
add $(( B0 + GROW2_AT * 60 )) "load ${USERS_2X:?}"
add $(( B0 + GROW3_AT * 60 )) "load ${USERS_3X:?}"
add $(( B0 + STORM_AT * 60 )) "storm on"
add $(( B0 + (STORM_AT + STORM_MIN) * 60 )) "storm off"
add $(( B0 + INJECT_AT * 60 )) "inject start"
add $(( B0 + (INJECT_AT + INJECT_MIN) * 60 )) "inject stop"
for ((h = first_hour; h <= end; h += 3600)); do add "$h" "budget"; done
add $(( end + 300 )) "down"
IFS=$'\n' sorted=($(printf '%s\n' "${events[@]}" | sort -n)); unset IFS
"$HERE/run.sh" mark budget_phase_plan "\"b0\":$B0,\"end\":$end"
for e in "${sorted[@]}"; do
  at=${e%% *}; what=${e#* }
  while [ "$(date +%s)" -lt "$at" ]; do sleep 5; done
  [ -f "$RESULTS/.down.done" ] && { echo "$(date -u +%FT%TZ) run already ended"; exit 0; }
  echo "$(date -u +%FT%TZ) $what"
  case "$what" in
    load*) "$HERE/run.sh" load ${what#load } 2 ;;
    "storm on") "$HERE/run.sh" flag paymentFailure 100% ;;
    "storm off") "$HERE/run.sh" flag paymentFailure off ;;
    "inject start") "$HERE/run.sh" inject start ;;
    "inject stop") "$HERE/run.sh" inject stop ;;
    budget) "$HERE/budget-run.sh"; echo "budget run exit $?" ;;
    down) "$HERE/run.sh" down ;;
  esac
done
