#!/bin/bash
# The run, start to end, as written in the method before it started. Run detached (detach.py).
#   0:00  up, replay at 1x (7 lines a second)                     phase 1, baseline, no cap
#   2:00  cap from the second baseline hour (cap.py, 50% of bytes over the cap); Receiver
#         re-rendered with that fleet cap and tier_down            phase 2, capped
#   6:00  replay at 2.5x from where it was, new service injected   phase 3, growth
#   7:00  error storm, 10 lines a second for 20 minutes            phase 4, inside phase 3
#   9:00  load stops; the meter keeps reading                      drain
#  11:00  down
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
RUN="$HERE/run.sh"
HOUR=${HOUR:-3600}
at() { local due=$(( T0 + $1 )); while [ "$(date +%s)" -lt "$due" ]; do sleep 20; done; }

T0=$(date +%s)
"$RUN" mark run_start "\"hour_s\":$HOUR"
"$RUN" up
"$RUN" replay start 1
"$RUN" mark phase_baseline

at $((2 * HOUR))
python3 "$HERE/cap.py" $((T0 + HOUR)) $((T0 + 2 * HOUR)) 0.5 > "$RESULTS/cap.out"
CAP=$(tail -1 "$RESULTS/cap.out")
"$RUN" mark cap_computed "\"cap_bytes_per_window_per_node\":$CAP"
"$RUN" receiver "$CAP"
"$RUN" mark phase_capped

at $((6 * HOUR))
read -r rs speed off < "$RESULTS/replay.state"
OFFSET=$(python3 -c "print(round($off + ($(date +%s) - $rs) * $speed, 1))")
"$RUN" replay stop
"$RUN" replay start 2.5 "$OFFSET"
"$RUN" inject start
"$RUN" mark phase_growth

at $((7 * HOUR))
"$RUN" storm 10 $(( $(date +%s) + 1200 ))
"$RUN" mark phase_storm

at $((9 * HOUR))
"$RUN" replay stop
"$RUN" inject stop
"$RUN" mark phase_drain

at $((11 * HOUR))
"$RUN" down
