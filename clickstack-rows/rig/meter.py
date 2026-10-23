#!/usr/bin/env python3
"""The run's own meter, every N seconds, appended as JSON lines.

Reads ClickHouse through docker exec: rows written into the logs table in the
last complete 4-minute windows (system.part_log NewPart rows by event_time, the
meter the gate picked), the hot table's count, the cold view's count and the
Receiver's returned records on the wire. Each reading is one line in meter.log.

  meter.py <seconds> <container> <wire.json> <out.log>
"""
import json
import os
import subprocess
import sys
import time

WINDOW = 240


def ch(container: str, sql: str) -> str:
    r = subprocess.run(["docker", "exec", container, "clickhouse-client", "--query", sql], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def wire_lines(path: str) -> int:
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def main() -> int:
    every = int(sys.argv[1])
    cs = sys.argv[2]
    wire = sys.argv[3]
    out = sys.argv[4]
    while True:
        now = int(time.time())
        cur = (now // WINDOW) * WINDOW
        windows = ch(cs,
            f"SELECT intDiv(toUnixTimestamp(event_time), {WINDOW}) * {WINDOW} AS w, sum(rows) FROM system.part_log "
            f"WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs' "
            f"AND event_time >= toDateTime({cur - 6 * WINDOW}) AND event_time < toDateTime({cur}) GROUP BY w ORDER BY w FORMAT TSV")
        by_window = {int(a): int(b) for a, b in (l.split("\t") for l in windows.splitlines() if l)}
        rec = {
            "epoch": now,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "hot_rows": int(ch(cs, "SELECT count() FROM default.otel_logs") or 0),
            "cold_rows": int(ch(cs, "SELECT count() FROM default.otel_logs_coldv") or 0),
            "part_log_rows_total": int(ch(cs, "SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs'") or 0),
            "windows": by_window,
            "wire_lines": wire_lines(wire),
            "storm_hot_rows": int(ch(cs, "SELECT count() FROM default.otel_logs WHERE ServiceName = 'grafana' AND SeverityText IN ('error','ERROR') AND positionCaseInsensitive(Body, 'Could not register plugin') > 0") or 0),
        }
        with open(out, "a") as fh:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        time.sleep(every)


if __name__ == "__main__":
    raise SystemExit(main())
