#!/usr/bin/env python3
"""Measure the gate: which ClickHouse meter equals the hot table's row count.

Reads ClickHouse through docker exec, the wire tap through clickstack-e2e's own
parser, and the Receiver's Prometheus scrape as text. Writes results/<date>.md
and results/<date>.json. Every number is printed with the query that produced it.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "clickstack-e2e"))
from report import read_wire  # noqa: E402

CAPPED = ["opentelemetry-collector", "kafka", "cart"]
ERROR_LEVELS = "('ERROR','FATAL','CRITICAL','error','fatal','critical','Error','Fatal','Critical')"


class CH:
    def __init__(self, container: str):
        self.c = container
        self.log: list[tuple[str, str]] = []

    def q(self, sql: str) -> str:
        out = subprocess.run(["docker", "exec", self.c, "clickhouse-client", "--query", sql],
                             capture_output=True, text=True)
        val = out.stdout.strip() if out.returncode == 0 else f"ERR {out.stderr.strip()[:200]}"
        self.log.append((sql, val))
        return val

    def num(self, sql: str) -> int | None:
        v = self.q(sql)
        try:
            return int(float(v))
        except ValueError:
            return None

    def rows(self, sql: str) -> list[list[str]]:
        v = self.q(sql + " FORMAT TSV")
        return [r.split("\t") for r in v.splitlines() if r and not r.startswith("ERR")]


def read_csv(path: str) -> dict[str, int]:
    out = {}
    for line in pathlib.Path(path).read_text().splitlines()[1:]:
        if line.strip():
            k, v = line.split(",", 1)
            out[k] = int(v.split(":")[0])
    return out


def engine_metrics(path: pathlib.Path):
    """Metric names that count events, their label keys, and sums by routeState."""
    names: dict[str, set] = collections.defaultdict(set)
    by_route: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    container_keys: collections.Counter = collections.Counter()
    if not path.exists():
        return {}, {}, {}
    for line in path.read_text().splitlines():
        m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+([0-9.eE+-]+)$", line)
        if not m:
            continue
        name, labels, val = m.group(1), m.group(2) or "", float(m.group(3))
        kv = dict(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"', labels))
        names[name].update(kv.keys())
        if "routeState" in kv and "events" in name:
            by_route[name][kv["routeState"]] += val
        for k, v in kv.items():
            if v in CAPPED:
                container_keys[k] += 1
    return {k: sorted(v) for k, v in names.items()}, {k: dict(v) for k, v in by_route.items()}, dict(container_keys)


def main() -> int:
    ap = argparse.ArgumentParser()
    for f in ("container", "wire", "engine-metrics", "patches", "images", "results", "ch-version",
              "engine-image", "lines", "feed-seconds", "reload-at", "hot-at-reload", "totals", "caps", "partlog-before"):
        ap.add_argument(f"--{f}", required=True)
    a = ap.parse_args()
    ch = CH(a.container)
    totals = read_csv(a.totals)
    caps = read_csv(a.caps)

    hot = ch.num("SELECT count() FROM default.otel_logs")
    cold = ch.num("SELECT count() FROM default.otel_logs_coldv")
    counts_hot_rows = ch.num("SELECT count() FROM default.counts_by_type WHERE source = 'hot'")
    counts_hot_sum = ch.num("SELECT sum(cnt) FROM default.counts_by_type WHERE source = 'hot'")

    # the meter candidates
    ql_base = ("FROM system.query_log WHERE type = 'QueryFinish' AND query_kind = '{k}' "
               "AND has(tables, 'default.otel_logs')")
    ql_insert = ch.num("SELECT sum(written_rows) " + ql_base.format(k="Insert"))
    ql_insert_n = ch.num("SELECT count() " + ql_base.format(k="Insert"))
    ql_async = ch.num("SELECT sum(written_rows) " + ql_base.format(k="AsyncInsertFlush"))
    ql_async_n = ch.num("SELECT count() " + ql_base.format(k="AsyncInsertFlush"))
    ql_insert_text = ch.num("SELECT sum(written_rows) FROM system.query_log WHERE type = 'QueryFinish' "
                            "AND query_kind IN ('Insert','AsyncInsertFlush') AND position(query, 'otel_logs') > 0")
    ql_tables = ch.rows("SELECT arrayStringConcat(arraySort(tables), ','), count(), sum(written_rows) FROM system.query_log "
                        "WHERE type = 'QueryFinish' AND query_kind IN ('Insert','AsyncInsertFlush') "
                        "AND (has(tables, 'default.otel_logs') OR has(tables, 'default.counts_by_type')) GROUP BY 1 ORDER BY 2 DESC")
    pl_hot = ch.num("SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs'")
    pl_hot_n = ch.num("SELECT count() FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs'")
    pl_counts = ch.num("SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'counts_by_type'")
    parts_active = ch.num("SELECT sum(rows) FROM system.parts WHERE database = 'default' AND table = 'otel_logs' AND active")

    # per capped service: hot rows, before and after the reload, patterns, error patterns
    per_svc = {}
    for s in CAPPED:
        h = ch.num(f"SELECT count() FROM default.otel_logs WHERE ServiceName = '{s}'")
        before = ch.num(f"SELECT count() FROM default.otel_logs WHERE ServiceName = '{s}' AND ins <= toDateTime64('{a.reload_at.replace('T', ' ')}', 3, 'UTC')")
        pats = ch.num(f"SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = '{s}'")
        err_pats = ch.num(f"SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = '{s}' AND SeverityText IN {ERROR_LEVELS}")
        c = ch.num(f"SELECT count() FROM default.otel_logs_coldv WHERE ServiceName = '{s}'")
        per_svc[s] = dict(hot=h, hot_before_reload=before, hot_after_reload=(h - before) if h is not None and before is not None else None,
                          cold=c, patterns=pats, error_patterns=err_pats, total=totals.get(s), cap=caps.get(s))
    windows = ch.rows("SELECT toStartOfInterval(ins, INTERVAL 4 MINUTE) AS w, ServiceName, count() FROM default.otel_logs "
                      f"WHERE ServiceName IN ({','.join(repr(s) for s in CAPPED)}) GROUP BY w, ServiceName ORDER BY w, ServiceName")
    feed_span = ch.rows("SELECT min(ins), max(ins) FROM default.otel_logs")

    wire = read_wire(pathlib.Path(a.wire))
    names, by_route, container_keys = engine_metrics(pathlib.Path(a.engine_metrics))

    def eq(x):
        return "equal" if x == hot else (f"off by {x - hot:+d}" if isinstance(x, int) and isinstance(hot, int) else "n/a")

    date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out = pathlib.Path(a.results)
    out.mkdir(parents=True, exist_ok=True)
    md = []
    md.append(f"# ClickHouse rows gate, {date}: which meter equals the hot count\n")
    md.append(f"Engine `{a.engine_image}`, ClickHouse {a.ch_version}, {a.lines} lines fed in {a.feed_seconds} s, "
              f"regulator in events with the shipped baseline of 5, totals rewritten in place at {a.reload_at} UTC.\n")
    md.append("## The count to match\n")
    md.append(f"- Hot rows (`SELECT count() FROM default.otel_logs`): **{hot}**")
    md.append(f"- Cold rows through the S3 view: {cold}; hot plus cold: {None if hot is None or cold is None else hot + cold}")
    md.append(f"- Wire records the Receiver returned: {wire['total']}, by route: {json.dumps(wire['routes'], sort_keys=True)}")
    md.append(f"- Active rows in `system.parts`: {parts_active} ({eq(parts_active)})\n")
    md.append("## Meter candidates\n")
    md.append("| Candidate | Rows | Statements | Against hot |\n|---|---:|---:|---|")
    md.append(f"| `query_log` written_rows, kind Insert, tables has otel_logs | {ql_insert} | {ql_insert_n} | {eq(ql_insert)} |")
    md.append(f"| `query_log` written_rows, kind AsyncInsertFlush, tables has otel_logs | {ql_async} | {ql_async_n} | {eq(ql_async)} |")
    md.append(f"| `query_log` written_rows, both kinds, `otel_logs` in the query text | {ql_insert_text} | | {eq(ql_insert_text)} |")
    md.append(f"| `part_log` NewPart rows, otel_logs | {pl_hot} | {pl_hot_n} parts | {eq(pl_hot)} |")
    md.append(f"| `part_log` NewPart rows, counts_by_type | {pl_counts} | | (the materialized view's own parts) |")
    md.append(f"\n`part_log` rows for otel_logs before the feed: {a.partlog_before}. Counts table hot side: {counts_hot_rows} rows summing to {counts_hot_sum}.\n")
    md.append("Insert statements by the `tables` they name (`query_log`):\n")
    md.append("| tables | statements | written_rows |\n|---|---:|---:|")
    for r in ql_tables:
        md.append(f"| `{r[0]}` | {r[1]} | {r[2]} |")
    md.append("\n## The policy reload mid-window\n")
    md.append(f"Feed span by insert time: {feed_span[0] if feed_span else 'n/a'}. Totals file rewritten at {a.reload_at}; hot rows then {a.hot_at_reload}.\n")
    md.append("| Service | cap | total | hot rows | before reload | after reload | cold | patterns in hot | error patterns | floor 5 x patterns + 50 x error |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s, d in per_svc.items():
        floor = (5 * (d["patterns"] or 0)) + (50 * (d["error_patterns"] or 0))
        md.append(f"| {s} | {d['cap']} | {d['total']} | {d['hot']} | {d['hot_before_reload']} | {d['hot_after_reload']} | {d['cold']} | {d['patterns']} | {d['error_patterns']} | {floor} |")
    md.append("\nHot rows per 4-minute insert window, capped services:\n")
    md.append("| window (UTC) | service | hot rows |\n|---|---|---:|")
    for r in windows:
        md.append(f"| {r[0]} | {r[1]} | {r[2]} |")
    md.append("\n## The Receiver's own counters (Prometheus scrape)\n")
    md.append(f"Label keys whose value is a capped container name: {json.dumps(container_keys)}\n")
    for n in sorted(by_route):
        md.append(f"- `{n}` by routeState: {json.dumps(by_route[n], sort_keys=True)}; labels {names.get(n)}")
    if not by_route:
        md.append("- no event metric carried a routeState label in the scrape (see engine-metrics.txt)")
    md.append("\n## Harness patches on 1.1.147\n")
    md.append("```\n" + pathlib.Path(a.patches).read_text().strip() + "\n```\n")
    md.append("## Images\n")
    md.append("```\n" + pathlib.Path(a.images).read_text().strip() + "\n```\n")
    md.append("## Queries, in order\n")
    for sql, val in ch.log:
        md.append(f"- `{sql}` -> `{val[:120]}`")
    (out / f"clickstack-rows-gate-{date}.md").write_text("\n".join(md) + "\n")
    (out / f"clickstack-rows-gate-{date}.json").write_text(json.dumps(dict(
        hot=hot, cold=cold, wire=wire["routes"], wire_total=wire["total"], parts_active=parts_active,
        query_log_insert=ql_insert, query_log_async=ql_async, query_log_text=ql_insert_text,
        part_log_hot=pl_hot, part_log_counts=pl_counts, counts_hot_rows=counts_hot_rows,
        per_service=per_svc, windows=windows, container_label_keys=container_keys, by_route=by_route,
        reload_at=a.reload_at, hot_at_reload=a.hot_at_reload, feed_seconds=a.feed_seconds,
        engine_image=a.engine_image, ch_version=a.ch_version), indent=1, default=str))
    print("\n".join(md[:30]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
