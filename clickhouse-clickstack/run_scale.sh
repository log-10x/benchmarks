#!/usr/bin/env bash
#
# Does the message-type label save QUERY compute at a size where queries cost
# something? run_query_compute.sh could not tell: at 7 MB every query is a few
# milliseconds of fixed cost. This builds a table about a hundred times larger
# inside ClickHouse, by replicating the labeled rows with shifted timestamps, so
# there are no intermediate files and the same 2,627 message types recur across
# a hundred days. Then it asks the same questions three ways:
#
#   text_scan   position(Body, wording)            the plain scan many users write
#   text_index  hasToken(lower(Body), word)        ClickStack's own full-text index
#   label       templateHash = '...'               the message type, in the sort key
#
# CPU, bytes read and the answer are read back from system.query_log, seven runs
# each with the first discarded, fastest and median kept. The label is also asked
# the questions text cannot answer at all: the census of message types. And the
# text index is asked the one the label cannot: a word across everything.
#
# Replication caveat, stated up front: the same day's traffic repeated across a
# hundred days compresses better than a hundred real days would, so the storage
# figures here are optimistic. The query comparison is between two ways of
# reading the same table, so it is unaffected.
#
#   KEEP=1 ./run.sh && ./run_labeled.sh && ./run_scale.sh
#
# Environment: CCS_DATA_DIR as for run.sh. REPL (default 100). RUNS (default 7).

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
RESULTS="$HERE/results"
CTR=ch-clickstack
REPL="${REPL:-100}"
RUNS="${RUNS:-7}"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }
docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1 \
  || { echo "no $CTR container: run KEEP=1 ./run.sh && ./run_labeled.sh first" >&2; exit 1; }
[ "$(ch --query "SELECT count() FROM system.tables WHERE database='bench' AND name='otel_logs_labeled_sorted'")" = "1" ] \
  || { echo "bench.otel_logs_labeled_sorted is missing: run ./run_labeled.sh first" >&2; exit 1; }

COLS="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName, templateHash"

# ------------------------------------------------------------ the big tables
# Two, so the sort-key effect can be read at this size as well: ClickStack's own
# order with the label present, and the label inside the order.
say "replicate ${REPL}x with shifted timestamps"
DDL_DIR="${CCS_DATA_DIR:-$HERE/data}"
for variant in labeled labeled_sorted; do
  big="big_$variant"; src="otel_logs_$variant"
  ch --query "DROP TABLE IF EXISTS bench.$big SYNC"
  sed "s/otel_logs_$variant\b/$big/g; s/IF NOT EXISTS bench\.otel_logs_$variant/IF NOT EXISTS bench.$big/" "$DDL_DIR/otel_logs_$variant.sql" | ch --multiquery
  # One replicated day per insert. A single INSERT SELECT over a cross join
  # buffers a block per partition, and a hundred partitions at once is more
  # memory than the container has; a day at a time is also what a real
  # pipeline looks like.
  for n in $(seq 0 $((REPL - 1))); do
    ch --query "INSERT INTO bench.$big ($COLS)
                SELECT Timestamp + toIntervalDay($n), TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName, templateHash
                FROM bench.$src" --max_execution_time 600
  done
  for _ in 1 2 3; do until [ "$(ch --query "SELECT count() FROM system.merges WHERE database='bench' AND table='$big'")" = "0" ]; do sleep 5; done; sleep 5; done
  ch --query "OPTIMIZE TABLE bench.$big FINAL" --receive_timeout 3600
  printf '  %-16s %s rows, %s parts, %s on disk\n' "$big" \
    "$(ch --query "SELECT count() FROM bench.$big")" \
    "$(ch --query "SELECT count() FROM system.parts WHERE database='bench' AND table='$big' AND active")" \
    "$(ch --query "SELECT formatReadableSize(sum(bytes_on_disk)) FROM system.parts WHERE database='bench' AND table='$big' AND active")"
done

# ---------------------------------------------------------------- the queries
# Two real message types share the wording "GetCartAsync called with userId=",
# one carrying an id and one not (hashes from the census). A text search finds
# both; the label finds one. 'checkout' is the 1.17% term used throughout.
say "queries, $RUNS runs each, on big_labeled_sorted"
T=bench.big_labeled_sorted
declare -A Q
Q[type_text_scan]="SELECT count() FROM $T WHERE position(Body, 'GetCartAsync called with userId=') > 0"
Q[type_text_index]="SELECT count() FROM $T WHERE hasToken(lower(Body), 'getcartasync')"
Q[type_label]="SELECT count() FROM $T WHERE templateHash = '&\$18^Az03e'"
Q[type_label_both]="SELECT count() FROM $T WHERE templateHash IN ('&\$18^Az03e', '-.a7HKgM>82')"
Q[type_rows_scan]="SELECT count(), max(length(Body)) FROM $T WHERE position(Body, 'GetCartAsync called with userId=') > 0"
Q[type_rows_label]="SELECT count(), max(length(Body)) FROM $T WHERE templateHash = '&\$18^Az03e'"
Q[word_text_index]="SELECT count() FROM $T WHERE hasToken(lower(Body), 'checkout')"
Q[word_text_scan]="SELECT count() FROM $T WHERE position(Body, 'checkout') > 0"
Q[census_count]="SELECT templateHash, count() c FROM $T GROUP BY templateHash ORDER BY c DESC LIMIT 10 FORMAT Null"
Q[census_bytes]="SELECT templateHash, sum(length(Body)) b FROM $T GROUP BY templateHash ORDER BY b DESC LIMIT 10 FORMAT Null"
Q[service_day]="SELECT count() FROM $T WHERE ServiceName = 'frontend' AND Timestamp >= toDateTime64('2025-11-10 00:00:00', 9) AND Timestamp < toDateTime64('2025-11-11 00:00:00', 9)"
Q[anyword_error]="SELECT count() FROM $T WHERE hasToken(lower(Body), 'error')"
ORDER="type_text_scan type_text_index type_label type_label_both type_rows_scan type_rows_label word_text_scan word_text_index census_count census_bytes service_day anyword_error"
for name in $ORDER; do
  for _ in $(seq 1 "$RUNS"); do ch --query "/*qs-$name*/ ${Q[$name]}" --max_execution_time 600 >/dev/null; done
  echo "  $name"
done
ch --query "SYSTEM FLUSH LOGS"

say "measure"
python3 - "$CTR" "$RESULTS" "$REPL" "$RUNS" "$ORDER" <<'PY'
import datetime, json, pathlib, statistics, subprocess, sys
ctr, results, repl, runs, order = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5].split()
def q(sql):
    o = subprocess.run(["docker","exec","-i",ctr,"clickhouse-client","--format","TabSeparated","--query",sql],capture_output=True,text=True)
    if o.returncode: raise RuntimeError(o.stderr)
    return [l.split("\t") for l in o.stdout.strip().splitlines() if l]
def fmt(n): return f"{int(n):,}"
parts = {r[0]: (int(r[1]), int(r[2])) for r in q("SELECT table, sum(rows), sum(bytes_on_disk) FROM system.parts WHERE database='bench' AND active AND table LIKE 'big_%' GROUP BY table")}
cols = {}
for t, c, b in q("SELECT table, column, sum(column_data_compressed_bytes) FROM system.parts_columns WHERE database='bench' AND active AND table LIKE 'big_%' GROUP BY table, column"):
    cols.setdefault(t, {})[c] = int(b)
data = {}
for name, cpus, rb, rr, res in q(r"""
    SELECT extract(query,'/\*qs-([a-z_]+)\*/') AS n,
           arrayStringConcat(arraySlice(groupArray(toString(ProfileEvents['UserTimeMicroseconds']+ProfileEvents['SystemTimeMicroseconds'])), 2), ' '),
           max(read_bytes), max(read_rows), any(result_rows)
    FROM (SELECT * FROM system.query_log WHERE type='QueryFinish' AND position(query,'/*qs-')>0 ORDER BY event_time_microseconds)
    GROUP BY n"""):
    c = sorted(int(x) for x in cpus.split())
    data[name] = {"cpu_ms_fastest": c[0]/1000, "cpu_ms_median": statistics.median(c)/1000, "read_bytes": int(rb), "read_rows": int(rr), "runs_ms": [x/1000 for x in c]}
answers = {}
for name in ("type_text_scan","type_text_index","type_label","type_label_both","word_text_scan","word_text_index","anyword_error","service_day"):
    sql = {"type_text_scan":"SELECT count() FROM bench.big_labeled_sorted WHERE position(Body, 'GetCartAsync called with userId=') > 0",
           "type_text_index":"SELECT count() FROM bench.big_labeled_sorted WHERE hasToken(lower(Body), 'getcartasync')",
           "type_label":"SELECT count() FROM bench.big_labeled_sorted WHERE templateHash = '&$18^Az03e'",
           "type_label_both":"SELECT count() FROM bench.big_labeled_sorted WHERE templateHash IN ('&$18^Az03e', '-.a7HKgM>82')",
           "word_text_scan":"SELECT count() FROM bench.big_labeled_sorted WHERE position(Body, 'checkout') > 0",
           "word_text_index":"SELECT count() FROM bench.big_labeled_sorted WHERE hasToken(lower(Body), 'checkout')",
           "anyword_error":"SELECT count() FROM bench.big_labeled_sorted WHERE hasToken(lower(Body), 'error')",
           "service_day":"SELECT count() FROM bench.big_labeled_sorted WHERE ServiceName = 'frontend' AND Timestamp >= toDateTime64('2025-11-10 00:00:00', 9) AND Timestamp < toDateTime64('2025-11-11 00:00:00', 9)"}[name]
    answers[name] = int(q(sql)[0][0])
out = {"repl": repl, "runs": runs, "tables": parts, "columns": cols, "queries": data, "answers": answers}
(results / "scale.json").write_text(json.dumps(out, indent=2) + "\n")

L=[]; a=L.append; d=datetime.date.today().isoformat()
bl, bs = parts["big_labeled"], parts["big_labeled_sorted"]
a("# The label as a query lever, at a size where queries cost something"); a("")
a(f"Measured {d} by `run_scale.sh`. The labeled sample replicated {repl}x with timestamps shifted by whole days, "
  f"{fmt(bs[0])} rows, the same 2,627 message types across {repl} days. CPU is ClickHouse's own user plus system time from "
  f"`system.query_log`, {runs} runs with the first discarded, fastest and median kept. Replicated data compresses better "
  "than real data would, so the storage figures are optimistic; the query comparison is two ways of reading one table and is not affected.")
a(""); a("## Storage at this size"); a("")
a("| Table | Rows | On disk | Body | vs ClickStack order |"); a("|---|---:|---:|---:|---:|")
a(f"| `big_labeled`, ClickStack order plus the label column | {fmt(bl[0])} | {fmt(bl[1])} | {fmt(cols['big_labeled']['Body'])} | |")
a(f"| `big_labeled_sorted`, label inside the order | {fmt(bs[0])} | {fmt(bs[1])} | {fmt(cols['big_labeled_sorted']['Body'])} | {(1-bs[1]/bl[1])*100:.1f}% |")
a(""); a("## The same question three ways"); a("")
a("Two message types share the wording `GetCartAsync called with userId=`, one carrying an id and one not. The question is "
  "\"how many of the one with the id\". Text cannot tell them apart; the label can. `type_label_both` asks for both, which is the "
  "question the text queries actually answer, so their cost can be compared on equal terms.")
a(""); a("| Query | How | CPU ms, fastest | median | Bytes read | Rows read | Answer |"); a("|---|---|---:|---:|---:|---:|---:|")
how = {"type_text_scan":"`position(Body, wording)`, plain scan","type_text_index":"`hasToken`, ClickStack text index","type_label":"`templateHash = x`, the label",
       "type_label_both":"label, both types","type_rows_scan":"scan, and read the rows","type_rows_label":"label, and read the rows",
       "word_text_scan":"word `checkout`, plain scan","word_text_index":"word `checkout`, text index","census_count":"top 10 types by count, label only",
       "census_bytes":"top 10 types by bytes, label only","service_day":"one service, one day, control","anyword_error":"word `error`, text index, no label equivalent"}
for name in order:
    dq = data[name]; ans = answers.get(name, "")
    a(f"| `{name}` | {how[name]} | {dq['cpu_ms_fastest']:.0f} | {dq['cpu_ms_median']:.0f} | {fmt(dq['read_bytes'])} | {fmt(dq['read_rows'])} | {fmt(ans) if ans!='' else ''} |")
a(""); a("## What it says"); a("")
ts, ti, tl, tb = data["type_text_scan"], data["type_text_index"], data["type_label"], data["type_label_both"]
a(f"**One message type.** The plain scan costs {ts['cpu_ms_fastest']:.0f} ms and reads {fmt(ts['read_bytes'])} bytes; the text index costs "
  f"{ti['cpu_ms_fastest']:.0f} ms and reads {fmt(ti['read_bytes'])}; the label costs {tl['cpu_ms_fastest']:.0f} ms and reads {fmt(tl['read_bytes'])}. "
  f"Against the plain scan the label is {ts['cpu_ms_fastest']/max(tl['cpu_ms_fastest'],0.01):.0f}x less CPU; against the text index "
  f"{ti['cpu_ms_fastest']/max(tl['cpu_ms_fastest'],0.01):.1f}x. And the answers differ for a reason that is not an error on either side: "
  f"this type is a two-line event, a header line and a GetCartAsync line, and the label tags both lines of every event, {fmt(answers['type_label'])} "
  f"lines after replication. The wording sits on one line per event and belongs to two types, {fmt(answers['type_text_scan'])} lines. The label's unit "
  f"is the event; the text's unit is the line that carries the words. Asked for both types by label the answer is {fmt(answers['type_label_both'])} lines "
  f"and the cost, {tb['cpu_ms_fastest']:.0f} ms, is unchanged.")
a("")
ws, wi = data["word_text_scan"], data["word_text_index"]
a(f"**A word, not a type.** `checkout` by plain scan is {ws['cpu_ms_fastest']:.0f} ms; by text index {wi['cpu_ms_fastest']:.0f} ms. The label has no "
  "equivalent for a word, and does not pretend to. `error` across everything is the text index's question alone.")
a("")
cc, cb = data["census_count"], data["census_bytes"]
a(f"**The census.** Top ten types by count costs {cc['cpu_ms_fastest']:.0f} ms reading {fmt(cc['read_bytes'])} bytes. By bytes it costs "
  f"{cb['cpu_ms_fastest']:.0f} ms reading {fmt(cb['read_bytes'])}, because summing `length(Body)` reads the text; a materialised length column "
  "would make it as cheap as the count. Text has no version of either query.")
a("")
a("**What this does and does not establish.** At this size the fixed cost is gone and the differences are real. Whether they are money depends on "
  "what a cluster's query load is made of: type-shaped questions and censuses move to the label and get cheaper; word-shaped questions stay on "
  "the text index and do not. Neither the mix nor the Cloud autoscaler's response to lower CPU is measured here.")
out_md = results / f"label-query-scale-{d}.md"; out_md.write_text("\n".join(L)+"\n"); print(f"wrote {out_md}")
print("\n".join(L[L.index("## Storage at this size"):]))
PY
say "done"
