#!/usr/bin/env python3
"""
Where the gap is smallest.

A single reduction figure over a whole capture hides the spread across what is
in it. This walks the capture and the encoded stream together, the same way
build_groundtruth.py does, and accumulates bytes per Kubernetes container, so the
results file can name the slice that compacts worst rather than only the average.

Bytes are counted on the licence meter's basis, the text of each event with its
line terminator already stripped, so these numbers are comparable with the
metered figures rather than with file sizes.

The template dictionary is not in these per-slice figures. A template is shared
across every service whose lines match it, so there is no honest way to charge a
share of it to one container. The whole-capture figures in results.md do carry
it. That makes each per-slice reduction here slightly better than the same slice
would be in a deployment, and the gap between this table's total and the metered
total in results.md is exactly the dictionary and the app's re-index.
"""

import argparse
import json
import pathlib
import re
import sys

CONTAINER = re.compile(r'"container_name":"([^"]*)"')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--encoded", required=True)
    ap.add_argument("--templates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-events", type=int, default=100,
                    help="slices smaller than this are pooled, not ranked")
    args = ap.parse_args()

    spans = {}
    with open(args.templates, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            spans[record["templateHash"]] = record["template"].count("\n") + 1

    slices, lines_used, records = {}, 0, 0
    raw = open(args.raw, encoding="utf-8", errors="surrogateescape")
    with open(args.encoded, encoding="utf-8", errors="surrogateescape") as enc:
        for record_line in enc:
            record = record_line.rstrip("\n")
            records += 1
            comma = record.find(",")
            span = spans.get(record[1:comma] if comma >= 0 else record[1:], 1)
            original = [raw.readline().rstrip("\n") for _ in range(span)]
            lines_used += span
            # the event as Splunk meters it: the lines joined, terminators gone
            original_bytes = sum(len(l.encode("utf-8", "surrogateescape"))
                                 for l in original) + (span - 1)
            name = CONTAINER.search(original[0])
            key = name.group(1) if name else "(no container_name)"
            slot = slices.setdefault(key, {"events": 0, "lines": 0,
                                           "raw_bytes": 0, "compact_bytes": 0})
            slot["events"] += 1
            slot["lines"] += span
            slot["raw_bytes"] += original_bytes
            slot["compact_bytes"] += len(record.encode("utf-8", "surrogateescape"))
    raw.close()

    for slot in slices.values():
        slot["reduction_pct"] = round(
            100.0 * (1 - slot["compact_bytes"] / slot["raw_bytes"]), 2) \
            if slot["raw_bytes"] else None

    ranked = sorted((k for k, v in slices.items() if v["events"] >= args.min_events),
                    key=lambda k: slices[k]["reduction_pct"])
    small = [k for k, v in slices.items() if v["events"] < args.min_events]

    payload = {
        "records": records,
        "lines_assigned": lines_used,
        "min_events_to_rank": args.min_events,
        "ranked_worst_first": [dict(container=k, **slices[k]) for k in ranked],
        "below_threshold": [dict(container=k, **slices[k]) for k in small],
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")

    print(f"{records} records, {lines_used} lines, {len(slices)} containers")
    print(f"{'container':<34} {'events':>8} {'raw bytes':>14} {'compact':>13} {'cut':>7}")
    for key in ranked[:6]:
        s = slices[key]
        print(f"{key:<34} {s['events']:>8,} {s['raw_bytes']:>14,} "
              f"{s['compact_bytes']:>13,} {s['reduction_pct']:>6}%")
    print("...")
    for key in ranked[-3:]:
        s = slices[key]
        print(f"{key:<34} {s['events']:>8,} {s['raw_bytes']:>14,} "
              f"{s['compact_bytes']:>13,} {s['reduction_pct']:>6}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
