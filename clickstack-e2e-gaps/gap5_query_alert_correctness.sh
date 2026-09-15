#!/usr/bin/env bash
#
# Gap 5: which answers change when rows leave the hot table, and which stay.
#
# Two feeds of the whole capture through one stack. The first runs a policy that
# regulates nothing, so every record lands in the hot table: that is the "before
# offload" state and its rows are kept in `gaps.hot_before`. The second runs the
# per-type policy, so the overflow lands in the object store. The same three
# questions are then asked of four surfaces: the hot table as it was before, the
# hot table as it is after, the Merge table over hot plus cold, and the
# counts-per-type table.
#
# The three questions are the ones a dashboard and an alert actually ask:
#
#   Q1  count all by service, over a four hour window. The window is four hours
#       rather than one because the two feeds are an hour apart on one clock and a
#       one hour window would drop the first feed's rows for a reason that has
#       nothing to do with the offload.
#   Q2  count of one offloaded message type
#   Q3  a text search for a word that lives only in offloaded rows
#
# The word for Q3 is chosen after the second feed, by asking which words of the
# offloaded type's pattern text have a hot count of zero and a cold count above
# zero, so it is a word the run proved is only on the cold side.
#
# An alert is then created over the HyperDX API on the count of the offloaded
# type, and whether it would have fired before and after is read off the counts
# each surface returns.
#
#   ./gap5_query_alert_correctness.sh
#
# Environment: as lib.sh.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUT="$RESULTS/gap5.json"

trap g_teardown EXIT
g_require
say "input"; g_input
g_render_harness_conf
g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$JRE_IMAGE" "$EDGE_IMAGE"
g_net

say "object store"; g_minio_up
say "ClickStack"; g_clickstack_up

# A policy the receiver accepts and that regulates nothing: the cap file needs a
# row, and a service with no row in it is not regulated at all.
mkdir -p "$BUILD/policy_none" "$BUILD/policy_10x"
printf 'container,cap\nno-such-container,999999999\n' > "$BUILD/policy_none/caps.csv"
printf 'container,action\nno-such-container,offload\n' > "$BUILD/policy_none/actions.csv"
cp "$BUILD/conf/caps.csv" "$BUILD/conf/actions.csv" "$BUILD/policy_10x/"
touch "$BUILD/policy_none/caps.csv" "$BUILD/policy_none/actions.csv" \
      "$BUILD/policy_10x/caps.csv" "$BUILD/policy_10x/actions.csv"

# ------------------------------------------------------------- before offload
say "feed one: no offload, every record into the hot table"
g_engine_up "$BUILD/policy_none"
g_router_up "$BUILD/conf/router.yaml"
g_wait_settle default.otel_logs 4
g_flush_cold
BEFORE_HOT="$(chq "SELECT count() FROM default.otel_logs")"
BEFORE_OBJECTS="$(g_objects)"
python3 "$GAPS_HERE/wire_hashes.py" --wire "$BUILD/wire/returned.json" --out "$BUILD/gap5_before_wire.json"

chq "CREATE DATABASE IF NOT EXISTS gaps"
chq "DROP TABLE IF EXISTS gaps.hot_before SYNC"
chq "CREATE TABLE gaps.hot_before ENGINE = MergeTree ORDER BY (ServiceName, Timestamp) AS
     SELECT Timestamp, ServiceName, Body, SeverityText, LogAttributes FROM default.otel_logs"
chq "DROP TABLE IF EXISTS gaps.counts_before SYNC"
chq "CREATE TABLE gaps.counts_before ENGINE = MergeTree ORDER BY (Minute, ServiceName) AS
     SELECT * FROM default.counts_by_type"
echo "  before: $BEFORE_HOT rows kept in gaps.hot_before, $BEFORE_OBJECTS objects written"

say "reset the hot side, keep the copy"
chq "TRUNCATE TABLE default.otel_logs"
chq "TRUNCATE TABLE default.counts_by_type"
mc "mc rm -r --force m/$BUCKET >/dev/null 2>&1 || true; mc mb -p m/$BUCKET >/dev/null"

# -------------------------------------------------------------- after offload
say "feed two: the per-type policy, overflow offloaded"
g_engine_up "$BUILD/policy_10x"
g_router_up "$BUILD/conf/router.yaml"
g_wait_settle default.otel_logs 4
g_flush_cold
AFTER_HOT="$(chq "SELECT count() FROM default.otel_logs")"
AFTER_OBJECTS="$(g_objects)"
docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"
AFTER_COLD="$(chq "SELECT count() FROM default.otel_logs_coldv")"
g_export_cold "gap5"
python3 "$GAPS_HERE/wire_hashes.py" --wire "$BUILD/wire/returned.json" --out "$BUILD/gap5_after_wire.json"
echo "  after: hot $AFTER_HOT, cold $AFTER_COLD, objects $AFTER_OBJECTS"

# ------------------------------------------------------- pick the type and word
HASH="$(chq "SELECT LogAttributes['tenx_hash'] FROM default.otel_logs_coldv
             WHERE LogAttributes['tenx_hash'] != '' GROUP BY 1 ORDER BY count() DESC LIMIT 1")"
PATTERN="$(chq "SELECT LogAttributes['message_pattern'] FROM default.otel_logs_coldv
                WHERE LogAttributes['tenx_hash'] = '$HASH' LIMIT 1")"
WORD=""
WORD_ONLY_COLD=0
# A word that lives only in offloaded rows is not guaranteed to exist: the cap
# keeps the first occurrences of every type and offloads the overflow, so a
# capped type is usually on both sides. The search therefore walks the twenty
# biggest offloaded types rather than the biggest one alone, and the run reports
# which case it found.
CANDIDATE_PATTERNS="$(chq "SELECT DISTINCT LogAttributes['message_pattern'] FROM default.otel_logs_coldv
                           WHERE LogAttributes['message_pattern'] != ''
                           GROUP BY 1 ORDER BY count() DESC LIMIT 20")"
while IFS= read -r pattern; do
  [ -n "$pattern" ] || continue
  for candidate in $(printf '%s' "$pattern" | tr '_' ' '); do
    [ "${#candidate}" -ge 5 ] || continue
    hot_hits="$(chq "SELECT count() FROM default.otel_logs
                     WHERE positionCaseInsensitive(Body, '$candidate') > 0")"
    if [ "$hot_hits" != "0" ]; then
      [ -n "$WORD" ] || WORD="$candidate"
      continue
    fi
    cold_hits="$(chq "SELECT count() FROM default.otel_logs_coldv
                      WHERE positionCaseInsensitive(Body, '$candidate') > 0")"
    if [ "$cold_hits" != "0" ]; then
      WORD="$candidate"; WORD_ONLY_COLD=1; break
    fi
  done
  [ "$WORD_ONLY_COLD" = "0" ] || break
done <<< "$CANDIDATE_PATTERNS"
if [ "$WORD_ONLY_COLD" = "0" ]; then
  echo "  no word of the twenty biggest offloaded types is absent from the hot table" >&2
fi
echo "  offloaded type $HASH, word '$WORD' (only on the cold side: $WORD_ONLY_COLD)"

say "the three questions, on four surfaces"
python3 - "$BUILD/gap5_queries.json" "$HASH" "$WORD" <<'PY'
import json, sys
out, h, word = sys.argv[1], sys.argv[2], sys.argv[3]
Q1 = ("SELECT ServiceName, count() AS c FROM {t} WHERE {ts} >= now() - INTERVAL 4 HOUR "
      "GROUP BY ServiceName ORDER BY c DESC, ServiceName LIMIT 8")
Q1C = ("SELECT ServiceName, sum(cnt) AS c FROM default.counts_by_type "
       "WHERE Minute >= now() - INTERVAL 4 HOUR GROUP BY ServiceName ORDER BY c DESC, ServiceName LIMIT 8")
Q2 = "SELECT count() FROM {t} WHERE LogAttributes['tenx_hash'] = '%s'" % h
Q2C = ("SELECT sum(cnt) FROM default.counts_by_type WHERE tenx_hash = '%s'" % h)
Q3 = "SELECT count() FROM {t} WHERE positionCaseInsensitive(Body, '%s') > 0" % word
Q3C = ("SELECT sum(cnt) FROM default.counts_by_type WHERE positionCaseInsensitive(message_pattern, '%s') > 0"
       % word)
rows = []
for label, table in (("before, hot table", "gaps.hot_before"),
                     ("after, hot table", "default.otel_logs"),
                     ("after, merge table", "default.otel_logs_all")):
    rows.append({"name": f"Q1 count all by service, last 4 hours: {label}",
                 "sql": Q1.format(t=table, ts="Timestamp")})
for label, table in (("before, hot table", "gaps.hot_before"),
                     ("after, hot table", "default.otel_logs"),
                     ("after, merge table", "default.otel_logs_all")):
    rows.append({"name": f"Q2 count of one offloaded type: {label}", "sql": Q2.format(t=table)})
    rows.append({"name": f"Q3 text search, word only in offloaded rows: {label}",
                 "sql": Q3.format(t=table)})
rows.append({"name": "Q1 count all by service, last 4 hours: after, counts table", "sql": Q1C})
rows.append({"name": "Q2 count of one offloaded type: after, counts table", "sql": Q2C})
rows.append({"name": "Q3 text search, word only in offloaded rows: after, counts table", "sql": Q3C})
rows.append({"name": "Q1 count all by service, last 4 hours: before, counts table",
             "sql": Q1C.replace("default.counts_by_type", "gaps.counts_before")})
rows.append({"name": "Q2 count of one offloaded type: before, counts table",
             "sql": Q2C.replace("default.counts_by_type", "gaps.counts_before")})
rows.append({"name": "Q3 text search, word only in offloaded rows: before, counts table",
             "sql": Q3C.replace("default.counts_by_type", "gaps.counts_before")})
json.dump(rows, open(out, "w"), indent=1)
PY
python3 "$GAPS_HERE/measure.py" --container "$CS" --spec "$BUILD/gap5_queries.json" \
  --out "$BUILD/gap5_queries_out.json"

# Rows stored against rows returned. The end to end harness checks that hot plus
# cold equals what the receiver returned; this checks something else, that no row
# was stored twice, by counting distinct (Timestamp, Body) pairs. A retried
# insert that had already committed shows up here and nowhere else.
say "duplicate rows, each side"
DUP_BEFORE_TOTAL="$(chq "SELECT count() FROM gaps.hot_before")"
DUP_BEFORE_DISTINCT="$(chq "SELECT uniqExact(Timestamp, Body) FROM gaps.hot_before")"
DUP_HOT_TOTAL="$(chq "SELECT count() FROM default.otel_logs")"
DUP_HOT_DISTINCT="$(chq "SELECT uniqExact(Timestamp, Body) FROM default.otel_logs")"
DUP_COLD_TOTAL="$(chq "SELECT count() FROM default.otel_logs_coldv")"
DUP_COLD_DISTINCT="$(chq "SELECT uniqExact(Timestamp, Body) FROM default.otel_logs_coldv")"
printf '  before: %s rows, %s distinct; after hot: %s of %s; after cold: %s of %s\n' \
  "$DUP_BEFORE_TOTAL" "$DUP_BEFORE_DISTINCT" "$DUP_HOT_DISTINCT" "$DUP_HOT_TOTAL" \
  "$DUP_COLD_DISTINCT" "$DUP_COLD_TOTAL"

say "the alert, over the HyperDX API"
python3 "$GAPS_HERE/hyperdx_alert.py" --container "$CS" --hash "$HASH" \
  --out "$BUILD/gap5_alert.json" || true

python3 - "$OUT" "$BUILD/gap5_queries_out.json" "$BUILD/gap5_alert.json" \
  "$BUILD/gap5_before_wire.json" "$BUILD/gap5_after_wire.json" <<PY
import json, pathlib, sys
out, queries, alert, wb, wa = sys.argv[1:6]
def load(p):
    p = pathlib.Path(p)
    return json.loads(p.read_text()) if p.exists() else None
json.dump({
 "gap": 5,
 "feed_lines": $FEED_LINES,
 "before": {"hot_rows": ${BEFORE_HOT:-0}, "objects": "$BEFORE_OBJECTS", "wire": load(wb)},
 "after": {"hot_rows": ${AFTER_HOT:-0}, "cold_rows": ${AFTER_COLD:-0}, "objects": "$AFTER_OBJECTS",
           "wire": load(wa)},
 "duplicates": {"before_total": ${DUP_BEFORE_TOTAL:-0}, "before_distinct": ${DUP_BEFORE_DISTINCT:-0},
                "after_hot_total": ${DUP_HOT_TOTAL:-0}, "after_hot_distinct": ${DUP_HOT_DISTINCT:-0},
                "after_cold_total": ${DUP_COLD_TOTAL:-0}, "after_cold_distinct": ${DUP_COLD_DISTINCT:-0}},
 "type_hash": "$HASH", "type_pattern": "$PATTERN",
 "word": "$WORD", "word_only_cold": $WORD_ONLY_COLD,
 "queries": load(queries), "alert": load(alert),
}, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
