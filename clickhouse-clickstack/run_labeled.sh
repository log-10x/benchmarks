#!/usr/bin/env bash
#
# The shape actually being proposed: keep the original log text in Body, add the
# message type as a column, put it in the sort key. No compaction, no decoder.
#
# Everything measured so far compared native text against compact text. The
# recommendation that came out of it was to ship the label and leave the text
# alone, and that shape was never loaded. This does, against the container
# `KEEP=1 ./run.sh` leaves up:
#
#   native            ClickStack as published, one row per line     (already loaded)
#   labeled           the same rows plus templateHash, ClickStack sort key
#   labeled_sorted    the same, templateHash added inside the ClickStack sort key
#   labeled_bytype    the same, sorted (ServiceName, templateHash, Timestamp)
#
# The text index on Body stays in every arm, because the text is still there and
# word search is the point of keeping it. Ingest is measured table-to-table,
# three copies each, as run_typed.sh does.
#
#   KEEP=1 ./run.sh && ./run_labeled.sh

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"
ARMS_DIR="$DATA_DIR/arms"
INNER="$DATA_DIR/inner"
RESULTS="$HERE/results"
CTR=ch-clickstack

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }
docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1 \
  || { echo "no $CTR container: run KEEP=1 ./run.sh first" >&2; exit 1; }

# ------------------------------------------------------- label every native row
if [ ! -s "$ARMS_DIR/native_labeled.jsonl" ]; then
  say "label every captured line with its message type"
  python3 - "$DATA_DIR/otel-sample-200mb.log" "$INNER/encoded.log" "$INNER/templates.json" "$ARMS_DIR" <<'PY'
import json, pathlib, sys
sys.path.insert(0, ".")
from build_arms import envelope, load_templates, split_encoded
raw_p, enc_p, tpl_p, arms = sys.argv[1], sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])
templates = load_templates(pathlib.Path(tpl_p))
raw = [json.loads(l) for l in open(raw_p, encoding="utf-8")]
encoded = [json.loads(l) for l in open(enc_p, encoding="utf-8")]
native = list(open(arms / "native.jsonl", encoding="utf-8"))
assert len(native) == len(raw)
cursor, n = 0, 0
with open(arms / "native_labeled.jsonl", "w", encoding="utf-8") as out:
    for rec in encoded:
        h, _ = split_encoded(rec.get("log", ""))
        t = templates.get(h) if h else None
        lines = t["lines"] if t else 1
        assert envelope(rec) == envelope(raw[cursor]), f"alignment broke at {cursor}"
        for j in range(cursor, cursor + lines):
            row = json.loads(native[j]); row["templateHash"] = h or ""
            out.write(json.dumps(row) + "\n"); n += 1
        cursor += lines
assert cursor == len(raw) and n == len(raw)
print(f"  {n:,} rows labeled")
PY
fi

# -------------------------------------------------------------------- the DDLs
say "DDL variants from schema.sql.tpl"
python3 - "$DATA_DIR" <<'PY'
import pathlib, sys
data = pathlib.Path(sys.argv[1])
base = pathlib.Path("schema.sql.tpl").read_text().replace("__CODEC__", "ZSTD(1)")
ORDER = "ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)"
EVENT = "  `EventName` String CODEC(ZSTD(1)),\n"
LABEL = "  `templateHash` LowCardinality(String) CODEC(ZSTD(1)),\n"
assert ORDER in base and EVENT in base
labeled = base.replace(EVENT, EVENT + LABEL)
def w(name, ddl): (data / f"{name}.sql").write_text(ddl.replace("__TABLE__", name)); print(f"  {name}.sql")
w("otel_logs_labeled", labeled)
w("otel_logs_labeled_sorted", labeled.replace(ORDER, "ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, templateHash, Timestamp)"))
w("otel_logs_labeled_bytype", labeled.replace(ORDER, "ORDER BY (ServiceName, templateHash, Timestamp)"))
PY

load() {
  say "$1"
  ch --query "DROP TABLE IF EXISTS bench.$1 SYNC"
  ch --multiquery < "$DATA_DIR/$1.sql"
  docker exec "$CTR" bash -c \
    "clickhouse-client --allow_experimental_full_text_index=1 --query 'INSERT INTO bench.$1 FORMAT JSONEachRow' < /arms/native_labeled.jsonl"
  ch --query "OPTIMIZE TABLE bench.$1 FINAL" --receive_timeout 1200
  ch --query "SELECT '  rows: ' || toString(sum(rows)) || ', on disk: ' || formatReadableSize(sum(bytes_on_disk))
              FROM system.parts WHERE database='bench' AND table='$1' AND active"
}
load otel_logs_labeled
load otel_logs_labeled_sorted
load otel_logs_labeled_bytype

# ------------------------------------------------------------------- ingest
say "ingest, table-to-table, three copies each"
COLS="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName"
clone() {
  local src="$1" cols="$2" dst="${1}_clone"
  ch --query "DROP TABLE IF EXISTS bench.$dst SYNC"
  sed "s/bench\.$src\b/bench.$dst/; s/IF NOT EXISTS bench\.$src/IF NOT EXISTS bench.$dst/" "$DATA_DIR/$src.sql" | ch --multiquery
  for i in 1 2 3; do
    ch --query "TRUNCATE TABLE bench.$dst"
    ch --query "/*lingest-$dst*/ INSERT INTO bench.$dst ($cols) SELECT $cols FROM bench.$src"
  done
  echo "  $dst"
}
clone otel_logs_native_zstd1   "$COLS"
clone otel_logs_labeled        "$COLS, templateHash"
clone otel_logs_labeled_sorted "$COLS, templateHash"
clone otel_logs_labeled_bytype "$COLS, templateHash"
ch --query "SYSTEM FLUSH LOGS"

# ------------------------------------------------------------------- report
say "measure"
python3 - "$CTR" "$RESULTS" <<'PY'
import datetime, json, pathlib, subprocess, sys
ctr, results = sys.argv[1], pathlib.Path(sys.argv[2])
def q(sql):
    o = subprocess.run(["docker","exec","-i",ctr,"clickhouse-client","--allow_experimental_full_text_index=1","--format","TabSeparated","--query",sql],capture_output=True,text=True)
    if o.returncode: raise RuntimeError(o.stderr)
    return [l.split("\t") for l in o.stdout.strip().splitlines() if l]
T = [("native","otel_logs_native_zstd1","ClickStack as published"),
     ("labeled","otel_logs_labeled","plus templateHash, ClickStack sort key"),
     ("labeled_sorted","otel_logs_labeled_sorted","templateHash inside the ClickStack sort key"),
     ("labeled_bytype","otel_logs_labeled_bytype","sorted (ServiceName, templateHash, Timestamp)")]
names = ",".join(f"'{t[1]}'" for t in T)
tot = {r[0]:(int(r[1]),int(r[2])) for r in q(f"SELECT table,sum(rows),sum(bytes_on_disk) FROM system.parts WHERE database='bench' AND active AND table IN ({names}) GROUP BY table")}
col = {}
for t,c,b,u in q(f"SELECT table,column,sum(column_data_compressed_bytes),sum(column_data_uncompressed_bytes) FROM system.parts_columns WHERE database='bench' AND active AND table IN ({names}) GROUP BY table,column"):
    col.setdefault(t,{})[c]=(int(b),int(u))
idx = {r[0]:int(r[1]) for r in q(f"SELECT table,sum(data_compressed_bytes) FROM system.data_skipping_indices WHERE database='bench' AND table IN ({names}) GROUP BY table")}
body_idx = {r[0]:int(r[1]) for r in q(f"SELECT table,data_compressed_bytes FROM system.data_skipping_indices WHERE database='bench' AND name='idx_lower_body' AND table IN ({names})")}
ing = {}
for t,cpus in q("SELECT extract(query,'/\\\\*lingest-([a-z_0-9]+)\\\\*/') AS t, arrayStringConcat(groupArray(toString(ProfileEvents['UserTimeMicroseconds']+ProfileEvents['SystemTimeMicroseconds'])),' ') FROM system.query_log WHERE type='QueryFinish' AND t!='' GROUP BY t"):
    ing[t.removesuffix("_clone")] = sorted(int(x) for x in cpus.split())
def fmt(n): return f"{int(n):,}"
def pct(a,b): return f"{(1-b/a)*100:.1f}%"
base = "otel_logs_native_zstd1"
L=[]; a=L.append
d=datetime.date.today().isoformat()
a("# Ship the label, keep the text: native rows plus a message-type column"); a("")
a(f"Measured {d} by `run_labeled.sh`. Same 197,430 rows, same ClickStack schema at ZSTD(1), same "
  "text index on Body. The only additions are one LowCardinality column and, in two arms, its place in the sort key."); a("")
a("| Arm | What | Body | attributes | text index | all skip idx | total | vs native | ingest CPU s, fastest | every run |")
a("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
for k,t,desc in T:
    body = col[t]["Body"][0]; attrs = sum(v[0] for c,v in col[t].items() if c not in ("Body","templateHash"))
    runs = ", ".join(f"{x/1e6:.2f}" for x in ing.get(t,[]))
    a(f"| `{k}` | {desc} | {fmt(body)} | {fmt(attrs)} | {fmt(body_idx.get(t,0))} | {fmt(idx.get(t,0))} | {fmt(tot[t][1])} | {pct(tot[base][1],tot[t][1])} | {ing[t][0]/1e6:.2f} | {runs} |")
a(""); a(f"The templateHash column itself: " + ", ".join(f"`{k}` {fmt(col[t]['templateHash'][0])} bytes" for k,t,_ in T if 'templateHash' in col[t]) + ".")
a(""); a("## What it says"); a("")
b0,b1,b2 = col[base]["Body"][0], col["otel_logs_labeled_sorted"]["Body"][0], col["otel_logs_labeled_bytype"]["Body"][0]
t0,t1,t2 = tot[base][1], tot["otel_logs_labeled_sorted"][1], tot["otel_logs_labeled_bytype"][1]
a(f"Adding the column alone costs {fmt(col['otel_logs_labeled']['templateHash'][0])} bytes and changes nothing else. "
  f"Putting it inside ClickStack's own sort key takes the original text from {fmt(b0)} to {fmt(b1)} bytes ({pct(b0,b1)}) and the whole table "
  f"from {fmt(t0)} to {fmt(t1)} ({pct(t0,t1)}), with the text index intact and no decoder anywhere. Sorting by type first takes the text to {fmt(b2)} "
  f"({pct(b0,b2)}) and the table to {fmt(t2)} ({pct(t0,t2)}), at the cost of a weaker time-range primary key.")
a(""); a("Ingest CPU, fastest of three table-to-table copies, is in the table; read the every-run column before believing a difference.")
out = results / f"labeled-layout-{d}.md"; out.write_text("\n".join(L)+"\n"); print(f"wrote {out}"); print("\n".join(L[4:9]))
(results / "labeled.json").write_text(json.dumps({"totals":tot,"columns":col,"skip":idx,"body_idx":body_idx,"ingest":ing},indent=2))
PY
say "done"
