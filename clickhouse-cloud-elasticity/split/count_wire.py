#!/usr/bin/env python3
"""Count the records the Receiver returned, by routeState and by service.

Reads the collector's file exporter output (one OTLP JSON export request per line)
and prints the totals and the kept share as JSON.

  count_wire.py <returned.json>
"""
import collections
import json
import sys


def attrs(kvs):
    out = {}
    for kv in kvs or []:
        v = kv.get("value", {})
        out[kv["key"]] = next(iter(v.values()), None) if v else None
    return out


def records(path):
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            req = json.loads(line)
            for rl in req.get("resourceLogs", []):
                res = attrs(rl.get("resource", {}).get("attributes"))
                for sl in rl.get("scopeLogs", []):
                    for rec in sl.get("logRecords", []):
                        yield res, rec


def main() -> int:
    by_route = collections.Counter()
    by_service = collections.defaultdict(collections.Counter)
    for res, rec in records(sys.argv[1]):
        a = attrs(rec.get("attributes"))
        route = a.get("routeState") or "(none)"
        svc = res.get("service.name") or a.get("k8s_container") or "(none)"
        by_route[route] += 1
        by_service[svc][route] += 1
    total = sum(by_route.values())
    held = by_route.get("offload", 0)
    print(json.dumps({
        "records": total,
        "by_route": dict(by_route),
        "kept": total - held,
        "held": held,
        "kept_share": round((total - held) / total, 4) if total else None,
        "by_service": {k: dict(v) for k, v in sorted(by_service.items(), key=lambda kv: -sum(kv[1].values()))},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
