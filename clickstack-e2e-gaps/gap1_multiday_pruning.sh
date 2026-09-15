#!/usr/bin/env bash
#
# Gap 1: does a day predicate prune to one day's objects, and does a time-only
# query open every day's objects?
#
# ../clickstack-e2e/run.sh writes its objects during the run, so they all carry
# one day in the path and the question cannot be asked there. This runs the same
# route over the whole capture, then replicates the objects the run returned
# across 30 day partitions the way ../../clickhouse-clickstack/run_scale.sh
# replicates rows across days: the rows are staged once inside ClickHouse and
# written back out per day with their timestamps shifted by whole days, so the
# same services and the same message types recur on every day.
#
# Two changes from the objects the collector wrote, both stated in the results:
# the replicated objects are gzipped, because thirty uncompressed copies of the
# cold side of the full capture does not fit on the host this ran on, and they
# are written by ClickHouse rather than by the collector, which is what makes
# the day shift possible at all. Neither changes what the measurement is about:
# object count, request count and which objects a predicate opens.
#
#   ./gap1_multiday_pruning.sh
#
# Environment: as lib.sh. DAYS (default 30), BATCHES (default 2) objects per
# service and day.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

DAYS="${DAYS:-30}"
BATCHES="${BATCHES:-2}"
COLD30=cold30

# Which questions to put to the layout once it exists. `pruning` is gap 1's own
# set and writes results/gap1.json. `agg` is the set Altinity's published
# objection aims at, a GROUP BY and an ORDER BY with a LIMIT, each three ways,
# and writes results/gap1-agg.json so gap 1's committed numbers are left alone.
QUERY_SET="${QUERY_SET:-pruning}"
OUT="$RESULTS/gap1.json"
[ "$QUERY_SET" = "pruning" ] || OUT="$RESULTS/gap1-$QUERY_SET.json"

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
WIRE_RECORDS="$(python3 - "$BUILD/wire/returned.json" <<'PY'
import json, sys
n = 0
for line in open(sys.argv[1]):
    line = line.strip()
    if not line:
        continue
    for rl in json.loads(line).get("resourceLogs", []):
        for sl in rl.get("scopeLogs", []):
            n += len(sl.get("logRecords", []))
print(n)
PY
)"
echo "  wire $WIRE_RECORDS, hot $HOT_ROWS, cold $COLD_ROWS"

g_cold30_layout "$COLD30" "$DAYS" "$BATCHES"

SVC="$(chq "SELECT service FROM gaps.cold_stage GROUP BY service ORDER BY count() DESC LIMIT 1")"
HASH="$(chq "SELECT logAttributes['tenx_hash'] FROM gaps.cold_stage
             WHERE logAttributes['tenx_hash'] != '' GROUP BY 1 ORDER BY count() DESC LIMIT 1")"
PROBE_OFFSET=$(( DAYS > 5 ? 5 : DAYS - 1 ))
MIDDAY="$(chq "SELECT toString(today() - $PROBE_OFFSET)")"
WORD=snapshot

say "queries, set: $QUERY_SET"
if [ "$QUERY_SET" = "agg" ]; then
# Alexander Zaitsev of Altinity, 2025-11-07, on trying Merge over MergeTree plus
# object storage: "the Merge engine does not push query execution steps down,
# such as aggregations or limits". Gap 1 measured filters and counts, which is a
# different claim, so this set puts the two shapes his objection names. Each
# runs three ways over the same Merge table: the time predicate a dashboard
# sends, the same with a day predicate in the path, and the same with
# `_table = 'otel_logs'`, which is the hot side named through the Merge table
# rather than queried directly. The hot table alone is the baseline for both.
#
# The ORDER BY shape returns a digest rather than a hundred rows, so the table
# has one comparable cell per query and the sort and the read of `Body` still
# happen.
python3 - "$BUILD/gap1_queries.json" <<'PY'
import json, sys
out = sys.argv[1]
T, HOT = "default.otel_logs_all30", "default.otel_logs"
TIME = "Timestamp >= now() - INTERVAL 1 HOUR"
GROUP = ("SELECT ServiceName, count() AS c FROM {t} WHERE {w} "
         "GROUP BY ServiceName ORDER BY c DESC")
RECENT = ("SELECT count(), cityHash64(groupArray(Body)) FROM "
          "(SELECT Timestamp, ServiceName, Body FROM {t} WHERE {w} "
          "ORDER BY Timestamp DESC LIMIT 100)")
ways = [("time only", T, TIME),
        ("time plus day >= today() - 1", T, f"{TIME} AND day >= today() - 1"),
        ("time plus _table = 'otel_logs'", T, f"{TIME} AND _table = 'otel_logs'"),
        ("hot table alone, the baseline", HOT, TIME)]
q = []
for shape, sql in (("GROUP BY ServiceName", GROUP), ("ORDER BY Timestamp DESC LIMIT 100", RECENT)):
    for label, t, w in ways:
        q.append({"name": f"{shape}: {label}", "sql": sql.format(t=t, w=w)})
json.dump(q, open(out, "w"), indent=1)
PY
else
python3 - "$BUILD/gap1_queries.json" "$SVC" "$HASH" "$MIDDAY" "$WORD" <<'PY'
import json, sys
out, svc, h, day, word = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
T = "default.otel_logs_all30"
q = [
 ("hot only, last hour, count",
  "SELECT count() FROM default.otel_logs WHERE Timestamp >= now() - INTERVAL 1 HOUR"),
 (f"merge, service {svc} and one day, both in the path",
  f"SELECT count() FROM {T} WHERE ServiceName = '{svc}' AND day = '{day}'"),
 (f"merge, service {svc}, no day predicate",
  f"SELECT count() FROM {T} WHERE ServiceName = '{svc}'"),
 ("merge, time only, the shape HyperDX sends",
  f"SELECT count() FROM {T} WHERE Timestamp >= now() - INTERVAL 1 HOUR"),
 ("merge, time plus day >= today() - 1",
  f"SELECT count() FROM {T} WHERE Timestamp >= now() - INTERVAL 1 HOUR AND day >= today() - 1"),
 (f"merge, text search for '{word}', no other filter",
  f"SELECT count() FROM {T} WHERE positionCaseInsensitive(Body, '{word}') > 0"),
 (f"merge, text search for '{word}', one day",
  f"SELECT count() FROM {T} WHERE positionCaseInsensitive(Body, '{word}') > 0 AND day = '{day}'"),
 ("merge, one pattern hash, no time filter",
  f"SELECT count() FROM {T} WHERE LogAttributes['tenx_hash'] = '{h}'"),
 ("merge, one pattern hash and one day",
  f"SELECT count() FROM {T} WHERE LogAttributes['tenx_hash'] = '{h}' AND day = '{day}'"),
 ("cold only, one day, count",
  f"SELECT count() FROM default.otel_logs_cold30v WHERE day = '{day}'"),
]
json.dump([{"name": n, "sql": s} for n, s in q], open(out, "w"), indent=1)
PY
fi
python3 "$GAPS_HERE/measure.py" --container "$CS" --spec "$BUILD/gap1_queries.json" --out "$BUILD/gap1_queries_out.json"

OBJ_PER_DAY="$(chq "SELECT count(DISTINCT _path) FROM default.otel_logs_cold30 WHERE day = '$MIDDAY'")"
OBJ_ALL="$(chq "SELECT count(DISTINCT _path) FROM default.otel_logs_cold30")"
ROWS30="$(chq "SELECT count() FROM default.otel_logs_cold30")"

python3 - "$OUT" "$BUILD/gap1_queries_out.json" <<PY
import json, sys
out, queries = sys.argv[1], sys.argv[2]
json.dump({
 "gap": 1,
 "query_set": "$QUERY_SET",
 "feed_lines": $FEED_LINES, "feed_bytes": $FEED_BYTES,
 "wire_records": $WIRE_RECORDS, "hot_rows": $HOT_ROWS, "cold_rows": $COLD_ROWS,
 "run_objects": "$RUN_OBJECTS",
 "days": $DAYS, "batches_per_service_day": $BATCHES,
 "services": "$SERVICES".split(),
 "replicated_objects": $DAY_OBJECTS, "replicated_bytes": "$DAY_BYTES",
 "replicated_rows": $ROWS30,
 "objects_one_day": $OBJ_PER_DAY, "objects_all_days": $OBJ_ALL,
 "day_probed": "$MIDDAY", "service_probed": "$SVC", "hash_probed": "$HASH",
 "ch_version": "$CH_VERSION",
 "queries": json.load(open(queries)),
}, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
