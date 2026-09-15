#!/usr/bin/env bash
#
# The second rung. Runs against the ClickHouse container that `KEEP=1 ./run.sh`
# leaves up, so the ClickStack arms it measured are already loaded and this only
# adds the layouts a ClickHouse engineer would have asked for next:
#
#   compact_sorted           ClickStack DDL, Body still the compact text, but the
#                            template hash materialised and added to the sort key.
#                            Isolates what the sort key alone is worth.
#   compact_typed            Body replaced by templateHash + typed value arrays,
#                            same sort key as compact_sorted. Typing on top of sorting.
#   compact_typed_bytemplate The same typed layout sorted by (service, template,
#                            time), the maximum-compression order, at the cost of
#                            a weaker time-range primary key.
#
# Then the ingest cost, cleanly this time: each layout is copied table-to-table
# with INSERT ... SELECT, so every arm pays the same parsing cost (none) and the
# CPU ClickHouse records is the cost of building and compressing the columns.
#
#   KEEP=1 ./run.sh && ./run_typed.sh
#   SKIP_LOAD=1 ./run_typed.sh    reuse the three typed tables, redo the copies and the report
#
# Environment: CCS_DATA_DIR as for run.sh.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"
ARMS_DIR="$DATA_DIR/arms"
INNER="$DATA_DIR/inner"
RESULTS="$HERE/results"
CTR=ch-clickstack

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }

docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1 \
  || { echo "no $CTR container: run KEEP=1 ./run.sh first" >&2; exit 1; }
for t in otel_logs_native_zstd1 otel_logs_native_folded_zstd1 otel_logs_compact_zstd1; do
  [ "$(ch --query "SELECT count() FROM system.tables WHERE database='bench' AND name='$t'")" = "1" ] \
    || { echo "bench.$t is missing: run KEEP=1 ./run.sh first" >&2; exit 1; }
done

# ------------------------------------------------------------- typed layout
if [ ! -s "$ARMS_DIR/compact_typed.jsonl" ]; then
  say "split the compact events into typed arrays (reversed row by row before writing)"
  python3 build_typed.py --arms "$ARMS_DIR" --templates "$INNER/templates.json"
fi

# ---------------------------------------------------------------- the DDLs
say "DDL variants, generated from schema.sql.tpl so every other line stays ClickStack's"
python3 - "$DATA_DIR" <<'PY'
import pathlib, sys
data = pathlib.Path(sys.argv[1])
base = pathlib.Path("schema.sql.tpl").read_text().replace("__CODEC__", "ZSTD(1)")
CLICKSTACK_ORDER = "ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)"
HASH = ("  `templateHash` LowCardinality(String) MATERIALIZED "
        "if(startsWith(Body,'~'), if(position(Body,',')>0, "
        "substring(Body,2,position(Body,',')-2), substring(Body,2)), '') CODEC(ZSTD(1)),\n")
TYPED = (
    "  `templateHash` LowCardinality(String) CODEC(ZSTD(1)),\n"
    "  `slot_kinds` Array(UInt8) CODEC(ZSTD(1)),\n"
    "  `ts_vals` Array(Int64) CODEC(Delta(8), ZSTD(1)),\n"
    "  `num_vals` Array(Int64) CODEC(ZSTD(1)),\n"
    "  `str_vals` Array(String) CODEC(ZSTD(1)),\n")
BODY = "  `Body` String CODEC(ZSTD(1)),\n"
BODY_IDX = "  INDEX idx_lower_body lower(Body) TYPE text(tokenizer = 'splitByNonAlpha')\n"
EVENT = "  `EventName` String CODEC(ZSTD(1)),\n"
assert BODY in base and BODY_IDX in base and EVENT in base and CLICKSTACK_ORDER in base

def write(name, ddl):
    (data / f"{name}.sql").write_text(ddl.replace("__TABLE__", name))
    print(f"  {name}.sql")

# 1. sort key only
write("otel_logs_compact_sorted",
      base.replace(EVENT, EVENT + HASH)
          .replace(CLICKSTACK_ORDER,
                   "ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, templateHash, Timestamp)"))
# 2. typed, ClickStack-style sort key with the hash added
typed = (base.replace(BODY, "")
             .replace(EVENT, EVENT + TYPED)
             .replace(",\n" + BODY_IDX, "\n"))
write("otel_logs_compact_typed",
      typed.replace(CLICKSTACK_ORDER,
                    "ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, templateHash, Timestamp)"))
# 3. typed, sorted by template first
write("otel_logs_compact_typed_bytemplate",
      typed.replace(CLICKSTACK_ORDER, "ORDER BY (ServiceName, templateHash, Timestamp)"))
PY

load() {  # table, source jsonl
  say "$1"
  ch --query "DROP TABLE IF EXISTS bench.$1"
  docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 --multiquery < "$DATA_DIR/$1.sql"
  docker exec "$CTR" bash -c \
    "clickhouse-client --allow_experimental_full_text_index=1 --query 'INSERT INTO bench.$1 FORMAT JSONEachRow' < /arms/$2"
  ch --query "OPTIMIZE TABLE bench.$1 FINAL" --receive_timeout 1200
  ch --query "SELECT '  rows: ' || toString(sum(rows)) || ', on disk: ' || formatReadableSize(sum(bytes_on_disk))
              FROM system.parts WHERE database='bench' AND table='$1' AND active"
}
if [ "${SKIP_LOAD:-0}" != "1" ]; then
  load otel_logs_compact_sorted            compact.jsonl
  load otel_logs_compact_typed             compact_typed.jsonl
  load otel_logs_compact_typed_bytemplate  compact_typed.jsonl
fi

# ------------------------------------------------------ does it come back
say "does the typed layout rebuild the compact event inside ClickHouse"
ch --query "
WITH rebuilt AS (
  SELECT concat('~', templateHash,
           if(length(slot_kinds) = 0, '',
              concat(',', arrayStringConcat(
                arrayMap((k, i) -> multiIf(
                    k = 0, toString(ts_vals[countEqual(arraySlice(slot_kinds, 1, i), 0)]),
                    k = 1, toString(num_vals[countEqual(arraySlice(slot_kinds, 1, i), 1)]),
                           str_vals[countEqual(arraySlice(slot_kinds, 1, i), 2)]),
                  slot_kinds, arrayEnumerate(slot_kinds)), ',')))) AS Body
  FROM bench.otel_logs_compact_typed)
SELECT
  (SELECT count() FROM rebuilt) AS typed_rows,
  (SELECT sum(sipHash64(Body)) FROM rebuilt) = (SELECT sum(sipHash64(Body)) FROM bench.otel_logs_compact_zstd1) AS hash_sums_equal,
  (SELECT sum(length(Body)) FROM rebuilt) = (SELECT sum(length(Body)) FROM bench.otel_logs_compact_zstd1) AS lengths_equal
FORMAT Vertical"

# ---------------------------------------------------------- ingest, cleanly
# Copy each layout table-to-table. No JSON parsing on any side, so the CPU is
# what ClickHouse spends turning rows into compressed columns for that layout.
say "ingest cost per layout, INSERT ... SELECT into a fresh table of the same shape"
COMMON="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName"
clone() {  # table, column list
  local src="$1" cols="$2" dst="${1}_clone"
  ch --query "DROP TABLE IF EXISTS bench.$dst"
  sed "s/bench\.$src\b/bench.$dst/; s/IF NOT EXISTS bench\.$src/IF NOT EXISTS bench.$dst/" "$DATA_DIR/$src.sql" \
    | docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 --multiquery
  # Three copies, truncating between them. The first run on a busy host has
  # read as much as double the others, so the report takes the fastest and
  # prints every run.
  for i in 1 2 3; do
    ch --query "TRUNCATE TABLE bench.$dst"
    ch --query "/*ingest-$dst*/ INSERT INTO bench.$dst ($cols) SELECT $cols FROM bench.$src"
  done
  ch --query "/*merge-$dst*/ OPTIMIZE TABLE bench.$dst FINAL" --receive_timeout 1200
  echo "  $dst copied three times and merged"
}
clone otel_logs_native_zstd1          "$COMMON, Body"
clone otel_logs_native_folded_zstd1   "$COMMON, Body"
clone otel_logs_compact_zstd1         "$COMMON, Body"
clone otel_logs_compact_sorted        "$COMMON, Body"
clone otel_logs_compact_typed         "$COMMON, templateHash, slot_kinds, ts_vals, num_vals, str_vals"
clone otel_logs_compact_typed_bytemplate "$COMMON, templateHash, slot_kinds, ts_vals, num_vals, str_vals"
ch --query "SYSTEM FLUSH LOGS"

# ------------------------------------------------------------------ report
say "measure"
python3 report_typed.py --container "$CTR" --results "$RESULTS" \
  --typed-manifest "$ARMS_DIR/compact_typed.manifest.json"
say "done"
