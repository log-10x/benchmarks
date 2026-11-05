#!/usr/bin/env python3
"""Per-minute meter readings from every replica's system tables, pulled as they land.

A replica's system tables live on that replica, and a scale event replaces the
replicas, so the readings are copied out every --every seconds rather than read at
the end. Each pull covers [since, now - lag) and appends one JSON line per row to
--out, tagged with the table it came from:

  query_log   per minute, replica, log_comment, kind: count, written/read rows and
              bytes, CPU (OSCPUVirtualTime and user+system), peak memory
  part_log    per minute, replica, table, event type: parts, rows, bytes, duration,
              CPU (user+system and OSCPUVirtualTime from the part's ProfileEvents)
  metric_log  per minute, replica: server CPU (user+system and OSCPUVirtualTime
              summed over the minute), memory tracked (avg, max), merges running
  async       per minute, replica: CGroupMaxCPU, CGroupMemoryTotal, CGroup CPU time,
              resident memory (avg, max)

When the Cloud API says the service is not running, the pull is skipped, so the
meter never wakes an idle service.

  meter.py --service <id> --out results/raw/meter.jsonl [--every 300] [--lag 120] [--since <epoch>]
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cloud_api  # noqa: E402
from chhttp import CH  # noqa: E402

R = "clusterAllReplicas('default', system.{t})"
SQL = {
    "query_log": """
SELECT toUnixTimestamp(toStartOfMinute(event_time)) m, hostName() h, log_comment lc, query_kind kind,
       toString(type) type, count() n, sum(written_rows) wr, sum(written_bytes) wb, sum(read_rows) rr, sum(read_bytes) rb,
       sum(ProfileEvents['OSCPUVirtualTimeMicroseconds']) cpu_virt_us,
       sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']) cpu_us,
       max(memory_usage) mem_max, sum(query_duration_ms) dur_ms
FROM {src} WHERE event_time >= toDateTime({a}) AND event_time < toDateTime({b}) AND type != 'QueryStart'
GROUP BY m, h, lc, kind, type""",
    "part_log": """
SELECT toUnixTimestamp(toStartOfMinute(event_time)) m, hostName() h, database db, table tbl, toString(event_type) ev,
       toString(merge_reason) reason, count() n, sum(rows) rows, sum(size_in_bytes) bytes, sum(duration_ms) dur_ms,
       sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']) cpu_us,
       sum(ProfileEvents['OSCPUVirtualTimeMicroseconds']) cpu_virt_us, max(peak_memory_usage) mem_max
FROM {src} WHERE event_time >= toDateTime({a}) AND event_time < toDateTime({b})
GROUP BY m, h, db, tbl, ev, reason""",
    "metric_log": """
SELECT toUnixTimestamp(toStartOfMinute(event_time)) m, hostName() h, count() samples,
       sum(ProfileEvent_UserTimeMicroseconds + ProfileEvent_SystemTimeMicroseconds) cpu_us,
       sum(ProfileEvent_OSCPUVirtualTimeMicroseconds) cpu_virt_us,
       avg(CurrentMetric_MemoryTracking) mem_avg, max(CurrentMetric_MemoryTracking) mem_max,
       avg(CurrentMetric_Merge) merges_avg, avg(CurrentMetric_Query) queries_avg
FROM {src} WHERE event_time >= toDateTime({a}) AND event_time < toDateTime({b})
GROUP BY m, h""",
    "async": """
SELECT toUnixTimestamp(toStartOfMinute(event_time)) m, hostName() h, metric, avg(value) avg, max(value) max, count() n
FROM {src} WHERE event_time >= toDateTime({a}) AND event_time < toDateTime({b})
  AND metric IN ('CGroupMaxCPU', 'CGroupMemoryTotal', 'CGroupMemoryUsed', 'CGroupUserTime', 'CGroupSystemTime',
                 'MemoryResident', 'OSUserTime', 'OSSystemTime')
GROUP BY m, h, metric""",
}
TABLE = {"query_log": "query_log", "part_log": "part_log", "metric_log": "metric_log", "async": "asynchronous_metric_log"}


def pull(ch, a, b):
    rows = []
    for name, sql in SQL.items():
        q = sql.format(src=R.format(t=TABLE[name]), a=a, b=b) + " FORMAT JSONEachRow"
        body, _ = ch.query(q, {"log_comment": "chce:meter", "skip_unavailable_shards": 1})
        for line in body.splitlines():
            if line.strip():
                rec = json.loads(line)
                rec["src"] = name
                rows.append(rec)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=float, default=300)
    ap.add_argument("--lag", type=int, default=120)
    ap.add_argument("--since", type=int)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    oid = cloud_api.org_id()
    ch = CH()
    since = args.since or int(time.time()) - args.every
    while True:
        until = int(time.time()) - args.lag
        until -= until % 60
        state = None
        try:
            state = cloud_api.call("GET", f"/organizations/{oid}/services/{args.service}").get("result", {}).get("state")
        except Exception:
            pass
        if state == "running" and until > since:
            try:
                rows = pull(ch, since, until)
                with open(args.out, "a") as fh:
                    for r in rows:
                        fh.write(json.dumps(r, separators=(",", ":")) + "\n")
                    fh.write(json.dumps({"src": "pull", "since": since, "until": until, "rows": len(rows), "t": int(time.time())}) + "\n")
                since = until
            except Exception as e:
                with open(args.out, "a") as fh:
                    fh.write(json.dumps({"src": "pull", "since": since, "until": until, "error": repr(e)[:300], "t": int(time.time())}) + "\n")
        if args.once:
            return 0
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
