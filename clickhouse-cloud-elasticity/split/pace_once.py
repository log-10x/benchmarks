#!/usr/bin/env python3
"""Append the capture to the collector's file once, at a fixed pace.

The clickstack-rows pacer loops the capture; this one writes each line once and
exits. Each line gets `seq` (its 1-based line number in the capture) in the Fluent
envelope, as the rows pacer does, and nothing inside `log` changes. With a start
line, the first `start` lines of the capture are skipped and `seq` still counts
from the top of the capture, so slices run side by side keep distinct numbers.

  pace_once.py <capture> <feed.log> <lines_per_s> [max_lines] [start]
"""
import json
import os
import sys
import time


def main() -> int:
    capture, feed, pace = sys.argv[1], sys.argv[2], float(sys.argv[3])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
    start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    t0 = time.time()
    seq = written = last = 0
    with open(capture, errors="replace") as src, open(feed, "a", buffering=1) as out:
        for line in src:
            seq += 1
            if seq <= start:
                continue
            if limit is not None and written >= limit:
                break
            written += 1
            due = t0 + written / pace
            delay = due - time.time()
            if delay > 0:
                time.sleep(delay)
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc["seq"] = last = seq
            out.write(json.dumps(doc, separators=(",", ":")) + "\n")
            if written % 5000 == 0:
                out.flush()
                os.fsync(out.fileno())
                print(f"{int(time.time())} {seq}", flush=True)
    print(f"{int(time.time())} {last} done, {written} lines", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
