#!/usr/bin/env python3
"""
Counts what the template dictionary carries, and fails if a template has more
timestamp slots than the Splunk app can reconstruct.

The app stores one timestamp_format per template and substitutes one placeholder.
A template with two $(...) slots therefore expands wrongly however the format is
converted, and the fix is the Receiver's maxPerObject setting, not the app. This
check is what stands behind that setting on every run: if the engine ever stops
honouring it, the run fails here instead of moving the expansion figure quietly.
"""
import argparse
import json
import re
import sys

SLOT = re.compile(r"\$\([^)]*\)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", required=True)
    ap.add_argument("--max-slots", type=int, default=1)
    args = ap.parse_args()

    total = timestamped = over = 0
    worst = 0
    for line in open(args.templates, encoding="utf-8"):
        if not line.strip():
            continue
        slots = len(SLOT.findall(json.loads(line)["template"]))
        total += 1
        timestamped += slots > 0
        over += slots > args.max_slots
        worst = max(worst, slots)
    print(f"  templates {total}, with a timestamp {timestamped}, "
          f"with more than {args.max_slots} slot(s) {over}, most slots on one {worst}")
    if over:
        print(f"{over} templates carry more than {args.max_slots} timestamp slot(s); "
              f"the Splunk app stores one format per template", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
