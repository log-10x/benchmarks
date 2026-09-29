#!/usr/bin/env python3
"""
Does the 10x Splunk app give back the text that went in?

Reads the search export on stdin as newline-delimited JSON, one row per compact
event, each row carrying the compact record as indexed and the _raw the app's
inflate macro produced. Compares every row against the ground truth built by
build_groundtruth.py and reports how many came back byte for byte.

A volume win with wrong text is a failure, so this counts three outcomes
separately: matched, expanded to something else, and left unexpanded (the macro
returns the compact record itself when the template lookup misses).
"""

import argparse
import hashlib
import json
import sys


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groundtruth", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--examples", type=int, default=3,
                    help="mismatching rows to keep verbatim")
    args = ap.parse_args()

    truth = json.load(open(args.groundtruth))
    mapping = truth["map"]

    rows = matched = wrong = unexpanded = unknown = 0
    mismatches = []

    for line in sys.stdin:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        result = payload.get("result")
        if not result:
            continue
        compact = result.get("tenx_compact")
        expanded = result.get("_raw")
        if compact is None or expanded is None:
            continue
        rows += 1
        expected = mapping.get(sha(compact))
        if expected is None:
            unknown += 1
            continue
        if sha(expanded) == expected:
            matched += 1
        elif expanded == compact:
            unexpanded += 1
            if len(mismatches) < args.examples:
                mismatches.append({"kind": "unexpanded", "compact": compact})
        else:
            wrong += 1
            if len(mismatches) < args.examples:
                mismatches.append({"kind": "wrong", "compact": compact,
                                   "expanded": expanded[:2000]})

    summary = {
        "rows": rows,
        "matched": matched,
        "wrong_text": wrong,
        "unexpanded": unexpanded,
        "compact_record_not_in_ground_truth": unknown,
        "match_pct": round(100.0 * matched / rows, 4) if rows else None,
        "mismatch_examples": mismatches,
    }
    open(args.out, "w").write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items()
                      if k != "mismatch_examples"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
