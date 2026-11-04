#!/usr/bin/env python3
"""Take the OpenSearch slice from the records the Receiver returned in the ClickHouse
Cloud elasticity run (engine 1.1.153, the 10-24 policy). The engine is not run again.

Walks returned.json in order and keeps the first record of each tenx_hash whose
records all carry one routeState in the whole file: HELD (routeState offload)
until HELD_N hashes, KEPT (routeState pass) until KEPT_N. One record per hash, so
a term query on a hash expects exactly one hit. 171 hashes appear under both
states in that file; they are left out so a hash names one side only.

Writes data/bulk.ndjson (kept to the tenx-app alias, held to tenx-tierdown, as
the forwarder would) and data/slice.json (every hash sent, its source position
and the counts).

  build_slice.py <returned.json> <out dir>
"""
import collections
import json
import sys
import time

HELD_N, KEPT_N = 400, 200


def value(v):
    if not v:
        return None
    kind, inner = next(iter(v.items()))
    if kind == "kvlistValue":
        return {kv["key"]: value(kv.get("value")) for kv in inner.get("values", [])}
    if kind == "arrayValue":
        return [value(x) for x in inner.get("values", [])]
    return inner


def records(path):
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            for rl in json.loads(line).get("resourceLogs", []):
                for sl in rl.get("scopeLogs", []):
                    yield from sl.get("logRecords", [])


def iso(ns):
    s, frac = divmod(int(ns), 1_000_000_000)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(s)) + f".{frac // 1000:06d}Z"


def main() -> int:
    src, out = sys.argv[1], sys.argv[2]
    states = collections.defaultdict(set)
    total = collections.Counter()
    for rec in records(src):
        a = {x["key"]: value(x.get("value")) for x in rec.get("attributes", [])}
        states[a["tenx_hash"]].add(a["routeState"])
        total[a["routeState"]] += 1
    mixed = {h for h, s in states.items() if len(s) > 1}

    picked = {"offload": [], "pass": []}
    want = {"offload": HELD_N, "pass": KEPT_N}
    seen = set()
    with open(f"{out}/bulk.ndjson", "w") as bulk:
        for i, rec in enumerate(records(src)):
            a = {x["key"]: value(x.get("value")) for x in rec.get("attributes", [])}
            h, rs = a["tenx_hash"], a["routeState"]
            if h in mixed or h in seen or len(picked[rs]) >= want[rs]:
                continue
            seen.add(h)
            k = a.get("kubernetes") or {}
            body = value(rec.get("body")) or ""
            doc = {
                "@timestamp": iso(rec.get("timeUnixNano") or rec.get("observedTimeUnixNano") or 0),
                "message": body if isinstance(body, str) else json.dumps(body),
                "tenx_hash": h,
                "routeState": rs,
                "message_pattern": a.get("message_pattern"),
                "k8s_container": k.get("container_name"),
                "k8s_namespace": k.get("namespace_name"),
                "k8s_pod": k.get("pod_name"),
                "source_pos": i,
            }
            alias = "tenx-tierdown" if rs == "offload" else "tenx-app"
            bulk.write(json.dumps({"index": {"_index": alias, "_id": h}}) + "\n")
            bulk.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
            picked[rs].append({"tenx_hash": h, "source_pos": i, "bytes": len(doc["message"].encode())})
            if all(len(picked[s]) >= want[s] for s in want):
                break
    summary = {
        "source": "clickhouse-cloud-elasticity split/build/wire/returned.json (engine 1.1.153, 10-24 policy)",
        "source_records": dict(total),
        "source_hashes": len(states),
        "mixed_state_hashes_excluded": len(mixed),
        "held_sent": len(picked["offload"]),
        "kept_sent": len(picked["pass"]),
        "held_message_bytes": sum(p["bytes"] for p in picked["offload"]),
        "kept_message_bytes": sum(p["bytes"] for p in picked["pass"]),
        "held": picked["offload"],
        "kept": picked["pass"],
    }
    with open(f"{out}/slice.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("held", "kept")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
