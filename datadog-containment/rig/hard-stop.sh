#!/bin/bash
# Hard stop: stops the demo once the deadline in results/deadline (epoch seconds) has passed
# by GRACE seconds and the run has not ended. The deadline is set when the demo starts and
# moved to the planned end when the scheduler starts. Run it detached (detach.py).
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
GRACE=${GRACE:-120}
T=$RESULTS/timeline.jsonl
ends0=$(grep -c '"run_end"' "$T" 2>/dev/null || echo 0)
while true; do
  sleep 15
  [ "$(grep -c '"run_end"' "$T" 2>/dev/null || echo 0)" != "$ends0" ] && { echo "$(date -u +%FT%TZ) run ended; hard stop exits"; exit 0; }
  d=$(cat "$RESULTS/deadline" 2>/dev/null || echo 0)
  if [ "$d" -gt 0 ] && [ "$(date +%s)" -ge $((d + GRACE)) ]; then
    echo "$(date -u +%FT%TZ) deadline $d passed by ${GRACE} s; stopping"
    echo "{\"event\":\"hard_stop\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"deadline\":$d}" >> "$T"
    "$HERE/run.sh" down
    exit 0
  fi
done
