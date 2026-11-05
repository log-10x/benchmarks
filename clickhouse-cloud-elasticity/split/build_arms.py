#!/usr/bin/env python3
"""Turn the records the Receiver returned into ClickStack `otel_logs` rows.

One JSONEachRow file, one row per returned record, in the order the Receiver
returned them, with two extra fields the stage table keeps and the logs table
does not: `i`, the row's position, and `kept`, 1 when the Receiver passed the
record (routeState pass) and 0 when it held it (routeState offload). Arm A
inserts every row; arm B inserts the rows with kept = 1 from the same slices.

The column mapping is clickhouse-clickstack/build_arms.py's, so the rows match the
09-13 runs: the Fluentd envelope goes to ResourceAttributes under the OpenTelemetry
names, `stream` to LogAttributes as `log.iostream`, and nothing the rig or the
engine added (`tenx_tag`, `seq`, `log.file.name`, `k8s_container`, `k8s_namespace`,
`tenx_hash`, `message_pattern`, `routeState`) is written, in either arm. Timestamp
is the record's own time from the split run; the load shifts it to the time of
the insert.

  build_arms.py <returned.json> <out.jsonl>
"""
import json
import sys


def value(v):
    if not v:
        return None
    kind, inner = next(iter(v.items()))
    if kind == "kvlistValue":
        return {kv["key"]: value(kv.get("value")) for kv in inner.get("values", [])}
    if kind == "arrayValue":
        return [value(x) for x in inner.get("values", [])]
    return inner


def kv(attrs):
    return {a["key"]: value(a.get("value")) for a in attrs or []}


def as_datetime64(ns: int) -> str:
    s, frac = divmod(ns, 1_000_000_000)
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(s)) + f".{frac:09d}"


def row(i, rec):
    a = kv(rec.get("attributes"))
    kubernetes = a.get("kubernetes") or {}
    docker = a.get("docker") or {}
    labels = kubernetes.get("labels") or {}
    resource = {
        "k8s.container.name": kubernetes.get("container_name", ""),
        "k8s.namespace.name": kubernetes.get("namespace_name", ""),
        "k8s.pod.name": kubernetes.get("pod_name", ""),
        "k8s.pod.uid": kubernetes.get("pod_id", ""),
        "k8s.pod.ip": kubernetes.get("pod_ip", ""),
        "k8s.node.name": kubernetes.get("host", ""),
        "container.id": docker.get("container_id", ""),
        "container.image.name": kubernetes.get("container_image", ""),
        "container.image.id": kubernetes.get("container_image_id", ""),
    }
    for key, val in labels.items():
        resource["k8s.pod.label." + key] = val
    resource = {k: str(v) for k, v in resource.items() if v not in ("", None)}
    log_attributes = {"log.iostream": a["stream"]} if a.get("stream") else {}
    body = value(rec.get("body")) or ""
    return {
        "i": i,
        "kept": 0 if a.get("routeState") == "offload" else 1,
        "Timestamp": as_datetime64(int(rec.get("timeUnixNano") or rec.get("observedTimeUnixNano") or 0)),
        "TraceId": "", "SpanId": "", "TraceFlags": 0,
        "SeverityText": "", "SeverityNumber": 0,
        "ServiceName": kubernetes.get("container_name", ""),
        "Body": body if isinstance(body, str) else json.dumps(body),
        "ResourceSchemaUrl": "", "ResourceAttributes": resource,
        "ScopeSchemaUrl": "", "ScopeName": "", "ScopeVersion": "", "ScopeAttributes": {},
        "LogAttributes": log_attributes, "EventName": "",
    }


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    n = kept = 0
    with open(src) as fh, open(dst, "w") as out:
        for line in fh:
            if not line.strip():
                continue
            for rl in json.loads(line).get("resourceLogs", []):
                for sl in rl.get("scopeLogs", []):
                    for rec in sl.get("logRecords", []):
                        r = row(n, rec)
                        kept += r["kept"]
                        out.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")
                        n += 1
    print(json.dumps({"rows": n, "kept": kept, "kept_share": round(kept / n, 4) if n else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
