#!/usr/bin/env bash
#
# Gap 9: does bounding the cold side to a recent window put the object count
# back under a time-only query?
#
# Gap 1 measured the layout: over thirty days of objects the Merge engine pushes
# nothing down, so a GROUP BY with a time predicate and no `day` predicate lists
# and reads every object. A `day` predicate in the query text costs a twelfth of
# that, but no dashboard writes one, and the hot table alone answers in single
# digit milliseconds.
#
# This asks what a bounded window costs instead: the same layout, a view over
# the cold table that carries the `day` predicate itself, and a second Merge
# table over the hot table plus that view. The question is whether the predicate
# inside the view prunes the same way the predicate in the query text prunes,
# with nothing in the query text to write.
#
# Both shapes are tried. A Merge table over the view is the first, because gap 1
# already proves the Merge engine takes a view as a child. If the server refuses
# one, the fallback is a UNION ALL view over the hot table and the bounded view,
# and the results record which shape was needed.
#
#   ./gap9_bounded_window.sh
#
# Environment: as lib.sh. DAYS (default 30), BATCHES (default 2) objects per
# service and day, WINDOW_DAYS (default 7) the bound the view carries.
#
# The layout is gap 1's, built by the same `g_cold30_layout` gap 1 calls, so the
# object count, the object sizes and the day shift are the ones gap 1 measured.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

DAYS="${DAYS:-30}"
BATCHES="${BATCHES:-2}"
WINDOW_DAYS="${WINDOW_DAYS:-7}"
COLD30=cold30
OUT="$RESULTS/gap9.json"

trap g_teardown EXIT
g_require
say "input"; g_input
g_render_harness_conf
g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$JRE_IMAGE" "$EDGE_IMAGE"
g_net

say "object store"; g_minio_up
mc "mc mb -p m/$COLD30 >/dev/null && echo '  bucket $COLD30 created'"
say "ClickStack"; g_clickstack_up

mkdir -p "$BUILD/policy"
cp "$BUILD/conf/caps.csv" "$BUILD/conf/actions.csv" "$BUILD/policy/"
touch "$BUILD/policy/caps.csv" "$BUILD/policy/actions.csv"
say "receiver"; g_engine_up "$BUILD/policy"
say "collector: read, route, offload"; g_router_up "$BUILD/conf/router.yaml"
g_wait_settle default.otel_logs 4
g_flush_cold

RUN_OBJECTS="$(g_objects)"
echo "  objects the run wrote: $RUN_OBJECTS"
docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"
HOT_ROWS="$(chq "SELECT count() FROM default.otel_logs")"
COLD_ROWS="$(chq "SELECT count() FROM default.otel_logs_coldv")"
echo "  hot $HOT_ROWS, cold $COLD_ROWS"

# Gap 3 reads the objects the collector wrote, in the shape it wrote them.
g_export_cold gap9

# The layout, gap 1's own, built by the function gap 1 calls.
g_cold30_layout "$COLD30" "$DAYS" "$BATCHES"

# --------------------------------------------------------- the bounded window
# `day` is a Date column on the S3 table, filled by hive partitioning from the
# path, so the bound is a Date comparison and not a string one.
say "the bounded view and the merge table over it"
docker exec -i "$CS" clickhouse-client --multiquery <<SQL
DROP VIEW IF EXISTS default.cold_recent;
CREATE VIEW default.cold_recent AS
SELECT toDateTime64(toUInt64OrZero(logAttributes['TimestampSec']), 9) AS Timestamp,
       CAST(service AS LowCardinality(String))                        AS ServiceName,
       body                                                           AS Body,
       CAST(logAttributes['SeverityText'] AS LowCardinality(String))  AS SeverityText,
       logAttributes                                                  AS LogAttributes,
       day                                                            AS day
FROM default.otel_logs_cold30
WHERE day >= today() - $WINDOW_DAYS;
SQL

WIN_SHAPE=merge
set +e
docker exec -i "$CS" clickhouse-client --multiquery 2> "$BUILD/gap9_merge_err.txt" <<SQL
DROP TABLE IF EXISTS default.otel_logs_win;
CREATE TABLE default.otel_logs_win
(
  Timestamp     DateTime64(9),
  ServiceName   LowCardinality(String),
  Body          String,
  SeverityText  LowCardinality(String),
  LogAttributes Map(String, String),
  day           Date
) ENGINE = Merge(default, '^(otel_logs|cold_recent)\$');
SQL
MERGE_RC=$?
set -e
MERGE_ERR="$(g_one_line "$BUILD/gap9_merge_err.txt")"
if [ "$MERGE_RC" = "0" ]; then
  set +e
  PROBE="$(chq "SELECT count() FROM default.otel_logs_win" 2>> "$BUILD/gap9_merge_err.txt")"
  PROBE_RC=$?
  set -e
  [ "$PROBE_RC" = "0" ] || MERGE_RC="$PROBE_RC"
  MERGE_ERR="$(g_one_line "$BUILD/gap9_merge_err.txt")"
fi
if [ "$MERGE_RC" != "0" ]; then
  WIN_SHAPE=union
  echo "  the Merge engine refused the view: $MERGE_ERR"
  docker exec -i "$CS" clickhouse-client --multiquery <<SQL
DROP TABLE IF EXISTS default.otel_logs_win;
DROP VIEW IF EXISTS default.otel_logs_win;
CREATE VIEW default.otel_logs_win AS
SELECT Timestamp, ServiceName, Body, SeverityText, LogAttributes, day
FROM default.otel_logs
UNION ALL
SELECT Timestamp, ServiceName, Body, SeverityText, LogAttributes, day
FROM default.cold_recent;
SQL
fi
echo "  window shape: $WIN_SHAPE, bound day >= today() - $WINDOW_DAYS"

OBJ_IN_WINDOW="$(chq "SELECT count(DISTINCT _path) FROM default.otel_logs_cold30
                      WHERE day >= today() - $WINDOW_DAYS")"
OBJ_ALL="$(chq "SELECT count(DISTINCT _path) FROM default.otel_logs_cold30")"
echo "  objects inside the window: $OBJ_IN_WINDOW of $OBJ_ALL"

# ------------------------------------------------------------------- queries
# The two shapes gap 1's `agg` set put to the unbounded Merge table, each asked
# twice: once of the bounded table and once of the unbounded one in the same
# run, so the pair is comparable without reaching across runs. The counts below
# them are the proof that the same rows come back inside the window.
python3 - "$BUILD/gap9_queries.json" "$WINDOW_DAYS" <<'PY'
import json, sys
out, window = sys.argv[1], int(sys.argv[2])
WIN, ALL, HOT = "default.otel_logs_win", "default.otel_logs_all30", "default.otel_logs"
TIME = "Timestamp >= now() - INTERVAL 1 HOUR"
GROUP = ("SELECT ServiceName, count() AS c FROM {t} WHERE {w} "
         "GROUP BY ServiceName ORDER BY c DESC")
RECENT = ("SELECT count(), cityHash64(groupArray(Body)) FROM "
          "(SELECT Timestamp, ServiceName, Body FROM {t} WHERE {w} "
          "ORDER BY Timestamp DESC LIMIT 100)")
COUNT = "SELECT count() FROM {t} WHERE {w}"
q = []
for shape, sql in (("GROUP BY ServiceName", GROUP),
                   ("ORDER BY Timestamp DESC LIMIT 100", RECENT)):
    q.append({"name": f"{shape}: time only, bounded window", "sql": sql.format(t=WIN, w=TIME)})
    q.append({"name": f"{shape}: time only, unbounded Merge", "sql": sql.format(t=ALL, w=TIME)})
    q.append({"name": f"{shape}: hot table alone, the baseline", "sql": sql.format(t=HOT, w=TIME)})
q += [
 {"name": "count: time only, bounded window", "sql": COUNT.format(t=WIN, w=TIME)},
 {"name": "count: time only, unbounded Merge", "sql": COUNT.format(t=ALL, w=TIME)},
 {"name": f"count: the whole window, bounded", "sql": COUNT.format(t=WIN, w="1")},
 {"name": f"count: day >= today() - {window} written out, unbounded Merge",
  "sql": COUNT.format(t=ALL, w=f"day >= today() - {window}")},
]
json.dump(q, open(out, "w"), indent=1)
PY
say "queries"
python3 "$GAPS_HERE/measure.py" --container "$CS" --spec "$BUILD/gap9_queries.json" \
  --out "$BUILD/gap9_queries_out.json"

python3 - "$OUT" "$BUILD/gap9_queries_out.json" <<PY
import json, sys
out, queries = sys.argv[1], sys.argv[2]
json.dump({
 "gap": 9,
 "feed_lines": $FEED_LINES, "feed_bytes": $FEED_BYTES,
 "hot_rows": $HOT_ROWS, "cold_rows": $COLD_ROWS, "run_objects": "$RUN_OBJECTS",
 "days": $DAYS, "batches_per_service_day": $BATCHES,
 "window_days": $WINDOW_DAYS,
 "window_shape": "$WIN_SHAPE",
 "merge_over_view_error": "$MERGE_ERR",
 "objects_in_window": $OBJ_IN_WINDOW, "objects_all_days": $OBJ_ALL,
 "services": "$SERVICES".split(),
 "replicated_objects": $DAY_OBJECTS, "replicated_bytes": "$DAY_BYTES",
 "ch_version": "$CH_VERSION",
 "queries": json.load(open(queries)),
}, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
