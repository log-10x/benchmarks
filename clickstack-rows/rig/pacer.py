#!/usr/bin/env python3
"""Feed the collector's file at a set pace.

Appends lines of the released capture to a file the collector tails, at
`lines_per_s`, looping the capture and rewriting nothing inside a line (the
engine names a line by its wording; the Fluent envelope's timestamp is not read).
Writes a sequence counter into the Fluent envelope as `seq` so delivery can be
counted per line, and a `pacer_epoch` so a window can be attributed. The pace is
re-read from `pace.txt` beside the feed every second, so a phase changes the pace
without restarting the pacer; `0` pauses.

  pacer.py replay <capture> <feed.log> <pace.txt> [start_offset_lines]
  pacer.py inject <feed.log> <pace.txt> <container> <template>      # one line shape, a new service
  pacer.py storm  <feed.log> <pace.txt> <line-json> <until_epoch>   # one stored line, repeated
"""
import json
import os
import sys
import time


def read_pace(path: str, default: float) -> float:
    try:
        with open(path) as fh:
            return float(fh.read().strip() or default)
    except (OSError, ValueError):
        return default


def emit(out, line: str, seq: int) -> None:
    try:
        doc = json.loads(line)
    except json.JSONDecodeError:
        return
    doc["seq"] = seq
    doc["pacer_epoch"] = int(time.time())
    out.write(json.dumps(doc, separators=(",", ":")) + "\n")


def run(gen, feed: str, pace_path: str, until: float | None = None) -> None:
    seq = 0
    with open(feed, "a", buffering=1) as out:
        pace = read_pace(pace_path, 0.0)
        last = time.time()
        credit = 0.0
        for line in gen:
            while True:
                now = time.time()
                if until is not None and now >= until:
                    return
                if now - last >= 1.0:
                    pace = read_pace(pace_path, pace)
                    credit = min(credit + pace * (now - last), pace * 2 if pace else 0)
                    last = now
                if credit >= 1.0:
                    credit -= 1.0
                    break
                time.sleep(0.02)
            seq += 1
            emit(out, line, seq)
            if seq % 5000 == 0:
                out.flush()
                os.fsync(out.fileno())


def replay(capture: str, offset: int):
    with open(capture, errors="replace") as fh:
        lines = fh.read().splitlines()
    n = len(lines)
    i = offset % n if n else 0
    while True:
        yield lines[i]
        i = (i + 1) % n


def inject(container: str, template: str):
    k = 0
    while True:
        k += 1
        yield json.dumps({
            "stream": "stdout",
            "log": template.replace("{n}", str(k)),
            "kubernetes": {"container_name": container, "namespace_name": "default", "pod_name": f"{container}-0"},
        })


def storm(line_json: str):
    with open(line_json) as fh:
        line = fh.read().strip()
    while True:
        yield line


def main() -> int:
    mode = sys.argv[1]
    if mode == "replay":
        capture, feed, pace = sys.argv[2:5]
        offset = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        run(replay(capture, offset), feed, pace)
    elif mode == "inject":
        feed, pace, container, template = sys.argv[2:6]
        run(inject(container, template), feed, pace)
    elif mode == "storm":
        feed, pace, line_json, until = sys.argv[2:6]
        run(storm(line_json), feed, pace, float(until))
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
