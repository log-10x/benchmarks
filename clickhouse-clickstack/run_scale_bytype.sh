#!/usr/bin/env bash
# The fair best case for the label: the same 100x table with the message type
# FIRST in the sort key, (ServiceName, templateHash, Timestamp), so the primary
# index can prune by type. run_scale.sh measured the label third in ClickStack's
# key, where it has to scan. This shows what the label costs when the table is
# built for it, and what the time-window control pays for that.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"
DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"; RESULTS="$HERE/results"; CTR=ch-clickstack; REPL="${REPL:-100}"; RUNS="${RUNS:-7}"
ch() { docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }
COLS="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName, templateHash"
big=big_labeled_bytype
ch --query "DROP TABLE IF EXISTS bench.$big SYNC"
sed "s/IF NOT EXISTS bench\.otel_logs_labeled_bytype/IF NOT EXISTS bench.$big/" "$DATA_DIR/otel_logs_labeled_bytype.sql" | ch --multiquery
for n in $(seq 0 $((REPL - 1))); do
  ch --query "INSERT INTO bench.$big ($COLS) SELECT Timestamp + toIntervalDay($n), TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName, templateHash FROM bench.otel_logs_labeled_bytype" --max_execution_time 600
done
for _ in 1 2 3; do until [ "$(ch --query "SELECT count() FROM system.merges WHERE database='bench' AND table='$big'")" = "0" ]; do sleep 5; done; sleep 5; done
ch --query "OPTIMIZE TABLE bench.$big FINAL" --receive_timeout 3600
T=bench.$big
declare -A Q
Q[bt_type_label]="SELECT count() FROM $T WHERE templateHash = '&\$18^Az03e'"
Q[bt_type_text_index]="SELECT count() FROM $T WHERE hasToken(lower(Body), 'getcartasync')"
Q[bt_type_rows_label]="SELECT count(), max(length(Body)) FROM $T WHERE templateHash = '&\$18^Az03e'"
Q[bt_census_count]="SELECT templateHash, count() c FROM $T GROUP BY templateHash ORDER BY c DESC LIMIT 10 FORMAT Null"
Q[bt_service_day]="SELECT count() FROM $T WHERE ServiceName = 'frontend' AND Timestamp >= toDateTime64('2025-11-10 00:00:00', 9) AND Timestamp < toDateTime64('2025-11-11 00:00:00', 9)"
Q[bt_day_all]="SELECT count() FROM $T WHERE Timestamp >= toDateTime64('2025-11-10 00:00:00', 9) AND Timestamp < toDateTime64('2025-11-11 00:00:00', 9)"
for name in bt_type_label bt_type_text_index bt_type_rows_label bt_census_count bt_service_day bt_day_all; do
  for _ in $(seq 1 "$RUNS"); do ch --query "/*qs-$name*/ ${Q[$name]}" --max_execution_time 600 >/dev/null; done
done
ch --query "SYSTEM FLUSH LOGS"
python3 - "$CTR" "$RESULTS" <<'PY'
import json, pathlib, statistics, subprocess, sys
ctr, results = sys.argv[1], pathlib.Path(sys.argv[2])
def q(sql):
    o = subprocess.run(["docker","exec","-i",ctr,"clickhouse-client","--format","TabSeparated","--query",sql],capture_output=True,text=True)
    if o.returncode: raise RuntimeError(o.stderr); 
    return [l.split("\t") for l in o.stdout.strip().splitlines() if l]
fmt = lambda n: f"{int(n):,}"
size = q("SELECT sum(rows), sum(bytes_on_disk) FROM system.parts WHERE database='bench' AND active AND table='big_labeled_bytype'")[0]
body = q("SELECT sum(column_data_compressed_bytes) FROM system.parts_columns WHERE database='bench' AND active AND table='big_labeled_bytype' AND column='Body'")[0][0]
data = {}
for name, cpus, rb, rr in q(r"""SELECT extract(query,'/\*qs-(bt_[a-z_]+)\*/') AS n,
   arrayStringConcat(arraySlice(groupArray(toString(ProfileEvents['UserTimeMicroseconds']+ProfileEvents['SystemTimeMicroseconds'])), 2), ' '), max(read_bytes), max(read_rows)
   FROM (SELECT * FROM system.query_log WHERE type='QueryFinish' AND position(query,'/*qs-bt_')>0 ORDER BY event_time_microseconds) GROUP BY n"""):
    c = sorted(int(x) for x in cpus.split()); data[name] = {"cpu_ms_fastest": c[0]/1000, "cpu_ms_median": statistics.median(c)/1000, "read_bytes": int(rb), "read_rows": int(rr)}
L = ["", "## The label's best case: the type first in the sort key", "",
     f"`big_labeled_bytype`, `ORDER BY (ServiceName, templateHash, Timestamp)`, {fmt(size[0])} rows, {fmt(size[1])} bytes on disk, Body {fmt(body)}. Same replicated data, same queries, same method.", "",
     "| Query | How | CPU ms, fastest | median | Bytes read | Rows read |", "|---|---|---:|---:|---:|---:|"]
how = {"bt_type_label":"one type by label, type-first key","bt_type_text_index":"one type's wording by text index","bt_type_rows_label":"one type, read the rows, label",
       "bt_census_count":"top 10 types by count","bt_service_day":"one service, one day (was the control)","bt_day_all":"one day, all services: the time query this key hurts"}
for n in ["bt_type_label","bt_type_text_index","bt_type_rows_label","bt_census_count","bt_service_day","bt_day_all"]:
    d = data[n]; L.append(f"| `{n}` | {how[n]} | {d['cpu_ms_fastest']:.0f} | {d['cpu_ms_median']:.0f} | {fmt(d['read_bytes'])} | {fmt(d['read_rows'])} |")
L.append("")
tl, ti, dy = data["bt_type_label"], data["bt_type_text_index"], data["bt_day_all"]
L.append(f"With the type first, the label filter reads {fmt(tl['read_rows'])} rows and costs {tl['cpu_ms_fastest']:.0f} ms, against the text index's {ti['cpu_ms_fastest']:.0f} ms: still three to four times the CPU, because the inverted index answers a token count from its postings without touching a column, and the label has to walk its granules in each of the 101 daily partitions. The time penalty expected from moving time out of the leading key did not appear in these two queries: a whole day is answered from partition metadata, {fmt(dy['read_rows'])} row read, because the table is partitioned by day, and one service in one day is pruned by the service-first key. A sub-day window across all services is where this order would pay, and that was not measured.")
out = results / "label-query-scale-2026-09-13.md"
out.write_text(out.read_text() + "\n".join(L) + "\n")
j = results / "scale.json"; d0 = json.loads(j.read_text()); d0["bytype"] = {"rows": int(size[0]), "bytes": int(size[1]), "body": int(body), "queries": data}; j.write_text(json.dumps(d0, indent=2) + "\n")
print("\n".join(L))
PY
