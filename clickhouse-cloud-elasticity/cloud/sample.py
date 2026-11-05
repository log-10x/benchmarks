#!/usr/bin/env python3
"""Service size over time, from the Cloud API only (no SQL connection).

Every --every seconds: GET the service (state, configured min/max memory and
replicas) and its Prometheus endpoint (per replica: memory limit, CGroupMaxCPU,
CGroup CPU time, resident memory). One JSON line per sample to --out. The
Prometheus read is the size meter: the service object carries only the configured
bounds, not the size the autoscaler chose.

  sample.py --service <id> --out results/raw/size.jsonl [--every 60]
"""
import argparse
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cloud_api  # noqa: E402

LINE = re.compile(r'^([A-Za-z_:][A-Za-z0-9_:]*)(\{[^}]*\})?\s+(\S+)')
LABEL = re.compile(r'(\w+)="([^"]*)"')
PER_HOST = {
    "ClickHouseAsyncMetrics_CGroupMaxCPU": "cpu",
    "ClickHouseAsyncMetrics_CGroupMemoryTotal": "mem_total",
    "ClickHouseAsyncMetrics_CGroupMemoryUsed": "mem_used",
    "ClickHouseAsyncMetrics_MemoryResident": "resident",
    "ClickHouseAsyncMetrics_CGroupUserTime": "cg_user",
    "ClickHouseAsyncMetrics_CGroupSystemTime": "cg_system",
    "ClickHouseAsyncMetrics_Uptime": "uptime",
    "ClickHouseMetrics_Merge": "merges",
    "ClickHouseMetrics_Query": "queries",
    "ClickHouseMetrics_PartsActive": "parts_active",
}


def parse(text):
    hosts, svc = {}, {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = LINE.match(line)
        if not m:
            continue
        name, labels, val = m.group(1), dict(LABEL.findall(m.group(2) or "")), m.group(3)
        try:
            v = float(val)
        except ValueError:
            continue
        if name == "ClickHouse_ServiceInfo":
            svc["cluster_status"] = labels.get("clickhouse_cluster_status")
            svc["scrape"] = labels.get("scrape")
        elif name == "ClickHouseServer_MemoryLimit":
            svc["memory_limit"] = v
        elif name in PER_HOST and "hostname" in labels:
            hosts.setdefault(labels["hostname"], {})[PER_HOST[name]] = v
    return svc, hosts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=float, default=60)
    args = ap.parse_args()
    oid = cloud_api.org_id()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    while True:
        t = time.time()
        rec = {"t": round(t, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))}
        try:
            s = cloud_api.call("GET", f"/organizations/{oid}/services/{args.service}").get("result", {})
            rec["state"] = s.get("state")
            rec["configured"] = {k: s.get(k) for k in ("minReplicaMemoryGb", "maxReplicaMemoryGb", "numReplicas", "idleScaling", "idleTimeoutMinutes")}
            prom = cloud_api.call("GET", f"/organizations/{oid}/services/{args.service}/prometheus?filtered_metrics=true", raw=True)
            svc, hosts = parse(prom if isinstance(prom, str) else "")
            rec.update(svc)
            rec["hosts"] = hosts
            rec["units"] = round(sum(h.get("mem_total", 0) for h in hosts.values()) / 8 / 2**30, 3) if hosts else 0
        except Exception as e:  # one failed read must not end the series
            rec["error"] = repr(e)[:300]
        with open(out, "a") as fh:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        time.sleep(max(1.0, args.every - (time.time() - t)))


if __name__ == "__main__":
    raise SystemExit(main())
