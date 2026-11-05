#!/usr/bin/env python3
"""The query load: the 09-13 query set on a fixed cadence, both arms the same.

The five shapes of clickhouse-clickstack/run_query_compute.sh (a word search, a
service window, a top-services count, a recent tail, a substring scan), moved
from the capture's fixed dates to windows ending now, plus two a HyperDX
dashboard runs: a per-minute histogram and a count by service and severity.
Every --every seconds the set runs once, in order, on one connection. Each
statement carries `log_comment` = chce:<phase>:<arm>:select:<name>, so its CPU is
read back from system.query_log.

With --overlap N, each cycle starts on the --every grid in its own thread and
connection even while earlier cycles still run, up to N in flight; a cycle due
while N are running is skipped and logged. The set then runs the same number of
times an hour in both arms, however long a cycle takes. Without it, cycles run
serially on one connection and a cycle that overruns delays the next.

  queries.py --control control.json --log results/raw/queries.jsonl [--every 60] [--overlap 3]
"""
import argparse
import json
import pathlib
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from chhttp import CH  # noqa: E402

T = "bench.otel_logs"
QUERIES = [
    ("histogram", f"SELECT toStartOfMinute(Timestamp) t, count() FROM {T} WHERE Timestamp >= now64() - INTERVAL 15 MINUTE GROUP BY t ORDER BY t"),
    ("top_services", f"SELECT ServiceName, count() c FROM {T} WHERE Timestamp >= now64() - INTERVAL 15 MINUTE GROUP BY ServiceName ORDER BY c DESC LIMIT 10"),
    ("count_by_type", f"SELECT ServiceName, SeverityText, count() c FROM {T} WHERE Timestamp >= now64() - INTERVAL 1 HOUR GROUP BY ServiceName, SeverityText ORDER BY c DESC LIMIT 50"),
    ("service_window", f"SELECT count(), max(length(Body)) FROM {T} WHERE ServiceName = 'frontend' AND Timestamp >= now64() - INTERVAL 1 HOUR"),
    ("recent_tail", f"SELECT Timestamp, ServiceName, Body FROM {T} WHERE Timestamp >= now64() - INTERVAL 15 MINUTE ORDER BY Timestamp DESC LIMIT 200"),
    ("word", f"SELECT count() FROM {T} WHERE Timestamp >= now64() - INTERVAL 1 HOUR AND hasToken(lower(Body), 'checkout')"),
    ("substring", f"SELECT count() FROM {T} WHERE Timestamp >= now64() - INTERVAL 1 HOUR AND position(Body, 'userId=') > 0"),
]


def cycle(ch, ctl, out, lock):
    for name, sql in QUERIES:
        rec = {"t": round(time.time(), 3), "phase": ctl.get("phase"), "arm": ctl.get("arm"), "q": name}
        t1 = time.time()
        try:
            _, summary = ch.query(sql + " FORMAT Null",
                                  {"log_comment": f"chce:{ctl.get('phase')}:{ctl.get('arm')}:select:{name}"})
            rec["read_rows"] = int(summary.get("read_rows", 0))
            rec["read_bytes"] = int(summary.get("read_bytes", 0))
        except Exception as e:
            rec["error"] = repr(e)[:300]
        rec["ms"] = round((time.time() - t1) * 1000)
        with lock:
            out.write(json.dumps(rec, separators=(",", ":")) + "\n")
            out.flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--every", type=float, default=60)
    ap.add_argument("--overlap", type=int, default=0)
    args = ap.parse_args()
    lock = threading.Lock()
    serial = CH()
    running = []
    t_next = time.time()
    with open(args.log, "a") as out:
        while True:
            try:
                ctl = json.load(open(args.control))
            except (OSError, ValueError):
                ctl = {}
            if ctl.get("phase") == "stop":
                return 0
            now = time.time()
            if now < t_next:
                time.sleep(min(t_next - now, 1.0))
                continue
            t_next += args.every
            if not ctl.get("queries", True) or float(ctl.get("rows_per_s", 0)) <= 0:
                continue
            if not args.overlap:
                cycle(serial, ctl, out, lock)
                continue
            running = [th for th in running if th.is_alive()]
            if len(running) >= args.overlap:
                with lock:
                    out.write(json.dumps({"t": round(now, 3), "phase": ctl.get("phase"), "arm": ctl.get("arm"),
                                          "skipped": True, "in_flight": len(running)}) + "\n")
                    out.flush()
                continue
            th = threading.Thread(target=cycle, args=(CH(), dict(ctl), out, lock), daemon=True)
            th.start()
            running.append(th)

if __name__ == "__main__":
    raise SystemExit(main())
