#!/usr/bin/env python3
"""The run's own meter, every N seconds, appended as JSON lines.

Reads ClickHouse through docker exec: rows written into the logs table in the
last complete 4-minute windows (system.part_log NewPart rows by event_time, the
meter the gate picked), the hot table's count, the cold view's count and the
Receiver's returned records on the wire. Each reading is one line in meter.log.

  meter.py <seconds> <container> <wire.json> <out.log> [--tables-out <log> --origin <epoch> --window <s>]
  meter.py dump <container> <origin> <window> <out.json> [feed.log]

With --tables-out (the two-arm run), each reading also appends, per table and per
window counted from the origin, the NewPart rows and parts from system.part_log,
merge CPU from its MergeParts ProfileEvents, and insert CPU from system.query_log.
`dump` writes every window since the origin once, plus the buckets and the totals.
"""
import json
import os
import subprocess
import sys
import time

WINDOW = 240
TABLES = ("otel_logs", "otel_logs_rule", "counts_by_type", "counts_by_type_rule")
CPU = "ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']"


def ch(container: str, sql: str) -> str:
    r = subprocess.run(["docker", "exec", container, "clickhouse-client", "--query", sql], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def wire_lines(path: str) -> int:
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def tsv(text: str):
    return [l.split("\t") for l in text.splitlines() if l and "\t" in l]


def into(t: str) -> str:
    """An insert into default.<t>, by `tables`, or by its text when `tables` is empty."""
    pat = '(?i)insert[[:space:]]+into[[:space:]]+[`"]?default[`"]?[.][`"]?' + t + '([`"]|[[:space:]]|[(])'
    return f"(has(tables, 'default.{t}') OR (empty(tables) AND match(query, '{pat}')))"


def table_windows(cs: str, origin: int, w: int, since: int, until: int) -> dict:
    """Per table and window: parts, rows, merges, merge CPU, inserts, insert CPU; plus inserts into no logs table and whole-node CPU."""
    key = f"intDiv(toUnixTimestamp(event_time) - {origin}, {w}) * {w} + {origin}"
    span = f"event_time >= toDateTime({since}) AND event_time < toDateTime({until})"
    kinds = "query_kind IN ('Insert', 'AsyncInsertFlush')"
    names = ", ".join(f"'{t}'" for t in TABLES)
    out: dict = {t: {} for t in TABLES}
    for t, k, parts, rows, merges, merge_us in tsv(ch(cs,
            f"SELECT table, {key} AS k, countIf(event_type = 'NewPart'), sumIf(rows, event_type = 'NewPart'), "
            f"countIf(event_type = 'MergeParts'), sumIf({CPU}, event_type = 'MergeParts') FROM system.part_log "
            f"WHERE database = 'default' AND table IN ({names}) AND {span} GROUP BY table, k ORDER BY k FORMAT TSV")):
        out[t].setdefault(k, {}).update(parts=int(parts), rows=int(rows), merges=int(merges), merge_us=int(merge_us))
    for t in TABLES:
        for k, ins, flushes, ins_us, written, failed in tsv(ch(cs,
                f"SELECT {key} AS k, countIf(type = 'QueryFinish' AND query_kind = 'Insert'), "
                f"countIf(type = 'QueryFinish' AND query_kind = 'AsyncInsertFlush'), sumIf({CPU}, type = 'QueryFinish'), "
                f"sumIf(written_rows, type = 'QueryFinish'), countIf(type != 'QueryFinish') FROM system.query_log "
                f"WHERE type != 'QueryStart' AND {kinds} AND {into(t)} AND {span} GROUP BY k ORDER BY k FORMAT TSV")):
            out[t].setdefault(k, {}).update(inserts=int(ins), flushes=int(flushes), insert_us=int(ins_us),
                                            written_rows=int(written), failed_inserts=int(failed))
    other = {k: {"inserts": int(n), "flushes": int(fl), "insert_us": int(us)} for k, n, fl, us in tsv(ch(cs,
        f"SELECT {key} AS k, countIf(query_kind = 'Insert'), countIf(query_kind = 'AsyncInsertFlush'), sum({CPU}) FROM system.query_log "
        f"WHERE type = 'QueryFinish' AND {kinds} AND NOT {into('otel_logs')} AND NOT {into('otel_logs_rule')} AND {span} GROUP BY k ORDER BY k FORMAT TSV"))}
    node = {k: int(us) for k, us in tsv(ch(cs,
        f"SELECT {key} AS k, sum(ProfileEvent_UserTimeMicroseconds + ProfileEvent_SystemTimeMicroseconds) "
        f"FROM system.metric_log WHERE {span} GROUP BY k ORDER BY k FORMAT TSV"))}
    return {"tables": out, "other_inserts": other, "node_us": node}


def dump(cs: str, origin: int, w: int, out_path: str, feed: str | None) -> int:
    ch(cs, "SYSTEM FLUSH LOGS")
    now = int(time.time())
    rec = {"origin": origin, "window_s": w, "at": now, **table_windows(cs, origin, w, origin, now + 1)}
    bucket = {}
    for t, cold in (("otel_logs", "otel_logs_cold"), ("otel_logs_rule", "otel_logs_rule_cold")):
        sec = "toInt64(toUInt64OrZero(logAttributes['TimestampSec']))"
        bucket[t] = {k: int(n) for k, n in tsv(ch(cs,
            f"SELECT intDiv({sec} - {origin}, {w}) * {w} + {origin} AS k, count() FROM default.{cold} "
            f"WHERE {sec} >= {origin} GROUP BY k ORDER BY k FORMAT TSV"))}
    rec["bucket"] = bucket

    def n(sql: str) -> int:
        v = ch(cs, sql)
        return int(v) if v.isdigit() else -1
    rec["totals"] = {
        "hot_rows": n("SELECT count() FROM default.otel_logs"),
        "rule_rows": n("SELECT count() FROM default.otel_logs_rule"),
        "cold_rows": n("SELECT count() FROM default.otel_logs_coldv"),
        "rule_cold_rows": n("SELECT count() FROM default.otel_logs_rule_coldv"),
        "part_log_rows": n("SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs'"),
        "rule_part_log_rows": n("SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs_rule'"),
    }
    if feed:
        try:
            with open(feed, "rb") as fh:
                rec["totals"]["feed_lines"] = sum(1 for l in fh if l.strip())
        except OSError:
            rec["totals"]["feed_lines"] = -1
    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    return 0


def main() -> int:
    if sys.argv[1] == "dump":
        return dump(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6] if len(sys.argv) > 6 else None)
    every = int(sys.argv[1])
    cs = sys.argv[2]
    wire = sys.argv[3]
    out = sys.argv[4]
    opts = dict(zip(sys.argv[5::2], sys.argv[6::2]))
    tables_out = opts.get("--tables-out")
    origin = int(opts.get("--origin", 0))
    tw = int(opts.get("--window", 600))
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
        if tables_out:
            done = origin + ((now - 30 - origin) // tw) * tw
            if done > origin:
                trec = {"epoch": now, **table_windows(cs, origin, tw, max(origin, done - 3 * tw), done)}
                with open(tables_out, "a") as fh:
                    fh.write(json.dumps(trec, separators=(",", ":")) + "\n")
        time.sleep(every)


if __name__ == "__main__":
    raise SystemExit(main())
