#!/usr/bin/env bash
#
# Does ClickHouse compute scale with rows?
#
# ClickHouse Cloud bills compute per unit-hour and storage at $25.30 per
# COMPRESSED TB per month, so for a log workload of ordinary size the storage
# line is tens of dollars and the compute line is the bill. `run.sh` and
# `run_typed.sh` settled the storage question: compaction is worth about 7% of
# the table at scale. This settles the compute one, and it decides whether the
# product has a cost story on ClickHouse at all.
#
# The claim under test: compute follows ROW COUNT, so removing rows is a lever
# and making each row smaller is not. The falsifier is stated before the run:
# if halving the rows does not roughly halve insert-plus-merge CPU, the claim
# is wrong and this file says so.
#
# Every arm holds the same original log text in the same ClickStack schema. The
# only thing that varies is which rows are present:
#
#   full              every captured line
#   sampled_75/50/25  a seeded uniform sample; same content mix, fewer rows
#   bypattern_75/50/25  whole message types removed, largest first; the lever
#                     the product pulls. Against the uniform sample at the same
#                     row count it separates "fewer rows" from "fewer kinds".
#
# Inserts arrive in batches of a FIXED NUMBER OF ROWS, the way a collector
# delivers them, so an arm with half the data sends half the batches. A fixed
# batch COUNT would charge every arm the same per-insert overhead and bias the
# result against the smaller ones; the first version of this script did that and
# its numbers were wrong.
#
# Each arm is loaded three times and the fastest is kept. The first load on this
# host has read up to four times the others, so a single pass is not a number.
#
#   KEEP=1 ./run.sh && ./run_compute.sh
#
# Environment: CCS_DATA_DIR as for run.sh. BATCH_ROWS (default 5000), REPEATS
# (default 3).

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"
ARMS_DIR="$DATA_DIR/arms"
INNER="$DATA_DIR/inner"
RESULTS="$HERE/results"
CTR=ch-clickstack
BATCH_ROWS="${BATCH_ROWS:-5000}"
REPEATS="${REPEATS:-3}"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }

docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1 \
  || { echo "no $CTR container: run KEEP=1 ./run.sh first" >&2; exit 1; }

# ------------------------------------------------------------------ the arms
if [ ! -s "$ARMS_DIR/reduction.manifest.json" ]; then
  say "label every captured line with its message type, build the reduction arms"
  python3 build_reduction.py --raw "$DATA_DIR/otel-sample-200mb.log" \
    --encoded "$INNER/encoded.log" --templates "$INNER/templates.json" --arms "$ARMS_DIR"
fi

ARMS=(full sampled_75 sampled_50 sampled_25 bypattern_75 bypattern_50 bypattern_25)
source_for() { [ "$1" = "full" ] && echo "native.jsonl" || echo "native_$1.jsonl"; }

# Every arm is loaded once into a staging table with no indexes and no sort key,
# purely as a row source, so the measured insert reads from ClickHouse rather
# than parsing JSON and every arm pays the same zero parsing cost.
say "staging the arms as row sources"
STAGE_COLS="Timestamp DateTime64(9), TraceId String, SpanId String, TraceFlags UInt8, SeverityText LowCardinality(String), SeverityNumber UInt8, ServiceName LowCardinality(String), Body String, ResourceSchemaUrl LowCardinality(String), ResourceAttributes Map(LowCardinality(String), String), ScopeSchemaUrl LowCardinality(String), ScopeName String, ScopeVersion LowCardinality(String), ScopeAttributes Map(LowCardinality(String), String), LogAttributes Map(LowCardinality(String), String), EventName String"
COLS="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName"
for arm in "${ARMS[@]}"; do
  stage="stage_$arm"
  if [ "$(ch --query "SELECT count() FROM system.tables WHERE database='bench' AND name='$stage'")" != "1" ]; then
    ch --query "CREATE TABLE bench.$stage ($STAGE_COLS) ENGINE = MergeTree ORDER BY tuple()"
    docker exec "$CTR" bash -c \
      "clickhouse-client --query 'INSERT INTO bench.$stage FORMAT JSONEachRow' < /arms/$(source_for "$arm")"
  fi
  printf '  %-14s %s rows\n' "$arm" "$(ch --query "SELECT count() FROM bench.$stage")"
done

# ------------------------------------------------------------- the measurement
say "load each arm in batches of $BATCH_ROWS rows, $REPEATS times, letting merges settle"
settle() {  # table
  for _ in 1 2 3; do
    until [ "$(ch --query "SELECT count() FROM system.merges WHERE database='bench' AND table='$1'")" = "0" ]; do
      sleep 2
    done
    sleep 4
  done
}
# A warm-up pass over the largest arm, thrown away. Without it the first arm
# measured carries the cost of a cold server and every ratio computed against
# it is wrong.
say "warm-up pass, discarded"
ch --query "DROP TABLE IF EXISTS bench.warmup SYNC"
sed -e "s/__TABLE__/warmup/g" -e "s/__CODEC__/ZSTD(1)/g" schema.sql.tpl \
  | docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 --multiquery
ch --query "INSERT INTO bench.warmup ($COLS) SELECT $COLS FROM bench.stage_full"
settle warmup
ch --query "DROP TABLE IF EXISTS bench.warmup SYNC"

for arm in "${ARMS[@]}"; do
  table="compute_$arm"; stage="stage_$arm"
  rows="$(ch --query "SELECT count() FROM bench.$stage")"
  batches=$(( (rows + BATCH_ROWS - 1) / BATCH_ROWS ))
  for pass in $(seq 1 "$REPEATS"); do
    ch --query "DROP TABLE IF EXISTS bench.$table SYNC"
    sed -e "s/__TABLE__/$table/g" -e "s/__CODEC__/ZSTD(1)/g" schema.sql.tpl \
      | docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 --multiquery
    for i in $(seq 0 $((batches - 1))); do
      ch --query "/*load-$table-p$pass*/ INSERT INTO bench.$table ($COLS)
                  SELECT $COLS FROM bench.$stage LIMIT $BATCH_ROWS OFFSET $((i * BATCH_ROWS))"
    done
    settle "$table"
  done
  printf '  %-14s %s rows, %s batches, %s parts, %s\n' "$arm" "$rows" "$batches" \
    "$(ch --query "SELECT count() FROM system.parts WHERE database='bench' AND table='$table' AND active")" \
    "$(ch --query "SELECT formatReadableSize(sum(bytes_on_disk)) FROM system.parts WHERE database='bench' AND table='$table' AND active")"
done
ch --query "SYSTEM FLUSH LOGS"

# ------------------------------------------------------------------- report
say "measure"
python3 report_compute.py --container "$CTR" --results "$RESULTS" \
  --manifest "$ARMS_DIR/reduction.manifest.json" --batch-rows "$BATCH_ROWS" --repeats "$REPEATS"
say "done"
