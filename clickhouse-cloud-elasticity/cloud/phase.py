#!/usr/bin/env python3
"""Set the run's phase: rewrite the control file the feed and the queries read,
and append the change to the events log with its time.

  phase.py <control.json> <events.jsonl> <phase> <arm> <rows_per_s> [note] [mode=read] [stage=bench.stage_b]
  phase.py <control.json> <events.jsonl> stop

mode=read makes the feed read its slices into Null instead of inserting them;
stage= names the stage table the feed reads (default bench.stage).
"""
import json
import os
import sys
import time


def main() -> int:
    extra = dict(a.split("=", 1) for a in sys.argv if a.startswith(("mode=", "stage=")))
    argv = [a for a in sys.argv if not a.startswith(("mode=", "stage="))]
    control, events, phase = argv[1], argv[2], argv[3]
    ctl = {"phase": phase}
    if phase != "stop":
        ctl.update({"arm": argv[4], "rows_per_s": float(argv[5])})
        ctl.update(extra)
    note = argv[6] if len(argv) > 6 else ""
    tmp = control + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(ctl, fh)
    os.replace(tmp, control)
    t = time.time()
    with open(events, "a") as fh:
        fh.write(json.dumps({"t": round(t, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)), **ctl, "note": note}) + "\n")
    print(json.dumps(ctl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
