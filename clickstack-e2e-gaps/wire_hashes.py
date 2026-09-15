#!/usr/bin/env python3
"""Census the records the receiver returned, from the collector's wire tap.

The same read ../clickstack-e2e/report.py does, kept to what the gap scripts
reconcile against: how many records came back, how many carried a route, and how
many records each pattern hash accounts for.

  wire_hashes.py --wire returned.json --out wire.json
"""
import argparse
import collections
import json
import pathlib


def read(path: pathlib.Path) -> dict:
    total = no_attrs = with_time = 0
    per_hash: collections.Counter = collections.Counter()
    routes: collections.Counter = collections.Counter()
    if not path.exists():
        return dict(total=0, per_hash={}, routes={}, no_attrs=0, with_time=0)
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            for rl in doc.get("resourceLogs", []):
                for sl in rl.get("scopeLogs", []):
                    for lr in sl.get("logRecords", []):
                        total += 1
                        if lr.get("timeUnixNano") not in (None, "", "0"):
                            with_time += 1
                        attrs = {a["key"]: a["value"] for a in lr.get("attributes", [])}
                        if not attrs:
                            no_attrs += 1
                        routes[attrs.get("routeState", {}).get("stringValue", "") or "(none)"] += 1
                        per_hash[attrs.get("tenx_hash", {}).get("stringValue", "")] += 1
    return dict(total=total, per_hash=dict(per_hash), routes=dict(routes),
                no_attrs=no_attrs, with_time=with_time)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wire", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = read(pathlib.Path(args.wire))
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"  wire: {out['total']} records, {len(out['per_hash'])} pattern hashes, "
          f"routes {out['routes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
