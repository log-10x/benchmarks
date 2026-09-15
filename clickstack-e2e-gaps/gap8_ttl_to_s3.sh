#!/usr/bin/env bash
#
# Gap 6, second question: what does the obvious alternative cost?
#
# The objection is Denny Crane's, written on ClickHouse discussion 77681,
# 2025-03-16, and it is the strongest version of "just use TTL": "keep the recent
# data (last partition (e.g. last month)) on 'Hot' EBS disk and move data to a
# 'Cold' S3 using TTL when data is merged because insertion already goes into a
# new partition... This way you avoid download/upload of data from/to S3 because
# of merges." That recipe is the fair baseline, and this arm runs it.
#
# One ClickStack, one MinIO, a MinIO-backed `s3` disk in a storage policy, and
# ClickStack's own `otel_logs` recreated under that policy with
# `TTL Timestamp + INTERVAL <n> SECOND TO VOLUME 'cold'`. The whole capture is
# fed with the receiver regulating nothing, so every record lands in the hot
# table, and then the move is counted:
#
#   DiskS3PutObject and S3PutObject from system.events, before and after
#   merge and move CPU from system.part_log
#   the objects the move left in the bucket
#
# Then the case the recipe does not survive, which Mohamed Aziz of Luciq named
# on 2026-08-10: late data "is, in the most literal sense, born expired. So it
# gets essentially no time to merge on hot disk." A slice of the same capture is
# replayed with timestamps behind the TTL boundary, and the moves and PUTs that
# insert alone triggers are counted.
#
#   ./gap8_ttl_to_s3.sh
#
# Environment: as lib.sh, plus TTL_SECONDS (default 60) and LATE_ROWS
# (default 200000, the late slice).

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUT="$RESULTS/gap8.json"
TTL_BUCKET=ttlcold
TTL_SECONDS="${TTL_SECONDS:-60}"
LATE_ROWS="${LATE_ROWS:-200000}"

trap g_teardown EXIT
g_require
say "input"; g_input
g_render_harness_conf
g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$EDGE_IMAGE"
g_net

say "object store"
g_minio_up
# The disk is opened when ClickHouse starts, so the bucket exists first.
mc "mc mb -p m/$TTL_BUCKET >/dev/null && echo '  bucket $TTL_BUCKET created'"

mkdir -p "$BUILD/chconf"
cat > "$BUILD/chconf/s3cold.xml" <<XML
<clickhouse>
  <storage_configuration>
    <disks>
      <s3cold>
        <type>s3</type>
        <endpoint>http://$MINIO:9000/$TTL_BUCKET/data/</endpoint>
        <access_key_id>minioadmin</access_key_id>
        <secret_access_key>minioadmin</secret_access_key>
      </s3cold>
    </disks>
    <policies>
      <hot_cold>
        <volumes>
          <hot>
            <disk>default</disk>
          </hot>
          <cold>
            <disk>s3cold</disk>
          </cold>
        </volumes>
      </hot_cold>
    </policies>
  </storage_configuration>
</clickhouse>
XML

say "ClickStack, with a MinIO-backed s3 disk in a storage policy"
g_clickstack_up -v "$BUILD/chconf/s3cold.xml":/etc/clickhouse-server/config.d/s3cold.xml:ro
DISKS="$(chq "SELECT arrayStringConcat(groupArray(name), ', ') FROM system.disks")"
echo "  disks: $DISKS"
case "$DISKS" in *s3cold*) ;; *) echo "the s3 disk is not configured; the mount did not take" >&2; exit 1;; esac

# ---------------------------------------------- otel_logs under the TTL policy
# ClickStack creates the table, so its own DDL is read back and reissued with
# the policy and the TTL added. Nothing else about the table changes.
say "otel_logs under the storage policy, with TTL TO VOLUME 'cold'"
chq "SHOW CREATE TABLE default.otel_logs" > "$BUILD/otel_logs_ddl.sql"
python3 - "$BUILD/otel_logs_ddl.sql" "$BUILD/otel_logs_ttl.sql" "$TTL_SECONDS" <<'PY'
import re, sys
src, dst, ttl = sys.argv[1], sys.argv[2], int(sys.argv[3])
t = open(src).read().replace("\\n", "\n").strip().rstrip(";")
# The table keeps its name and every column. Three edits only: the move rule is
# added to the TTL, the policy is set, and any policy the shipped DDL already
# named is dropped so the statement carries one.
move = f"Timestamp + INTERVAL {ttl} SECOND TO VOLUME 'cold'"
m = re.search(r"\nSETTINGS ", t)
assert m, "no SETTINGS clause in the shipped DDL"
head, settings = t[:m.start()], t[m.end():]
settings = re.sub(r"storage_policy\s*=\s*'[^']*'\s*,?\s*", "", settings).strip().rstrip(",")
# An existing TTL is a retention rule and stays; the move is another expression
# on the same clause, which is how ClickHouse takes more than one.
tm = re.search(r"\nTTL ((?:.|\n)*?)$", head)
if tm:
    head = head[:tm.start()] + "\nTTL " + tm.group(1).rstrip() + ",\n     " + move
else:
    head = head.rstrip() + "\nTTL " + move
out = head + "\nSETTINGS storage_policy = 'hot_cold'" + (", " + settings if settings else "")
open(dst, "w").write(out + ";\n")
print("  DDL rewritten with the policy and the move rule")
print("  " + "\n  ".join(l for l in out.splitlines() if l.startswith(("TTL", "SETTINGS", "     "))))
PY
chq "DROP TABLE IF EXISTS default.otel_logs SYNC"
docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/otel_logs_ttl.sql"
POLICY="$(chq "SELECT storage_policy FROM system.tables WHERE database='default' AND name='otel_logs'")"
echo "  storage_policy: $POLICY"
[ "$POLICY" = "hot_cold" ] || { echo "the table did not take the policy" >&2; exit 1; }

# ------------------------------------------------------------------- the feed
mkdir -p "$BUILD/policy_none"
printf 'container,cap\nno-such-container,999999999\n' > "$BUILD/policy_none/caps.csv"
printf 'container,action\nno-such-container,offload\n' > "$BUILD/policy_none/actions.csv"
touch "$BUILD/policy_none/caps.csv" "$BUILD/policy_none/actions.csv"

ev() { chq "SELECT value FROM system.events WHERE event = '$1'" 2>/dev/null | head -1; }
evz() { local v; v="$(ev "$1")"; echo "${v:-0}"; }

say "receiver, regulating nothing: every record into the hot table"
g_engine_up "$BUILD/policy_none"
say "collector: read and return"; g_router_up "$BUILD/conf/router.yaml"
g_wait_settle default.otel_logs 4
g_flush_cold
chq "SYSTEM FLUSH LOGS"

HOT_ROWS="$(chq "SELECT count() FROM default.otel_logs")"
SPAN="$(chq "SELECT dateDiff('second', min(Timestamp), max(Timestamp)) FROM default.otel_logs")"
INSERT_CPU="$(chq "SELECT sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds'])
                   FROM system.query_log WHERE type='QueryFinish' AND query_kind='Insert'")"
echo "  $HOT_ROWS rows, the capture spans $SPAN seconds as inserted"

PUT_BEFORE="$(evz S3PutObject)"
DPUT_BEFORE="$(evz DiskS3PutObject)"
BYTES_BEFORE="$(chq "SELECT sum(bytes_on_disk) FROM system.parts WHERE database='default' AND table='otel_logs' AND active")"

# --------------------------------------------------------------- the TTL move
# A TTL rule fires when the part containing the row is merged. Waiting for the
# background scheduler makes the number depend on which parts it happened to
# pick inside the window, so the move is forced and the whole table moves once.
say "the TTL move, forced so the whole table moves exactly once"
MOVE_T0="$(date +%s)"
chq "OPTIMIZE TABLE default.otel_logs FINAL" >/dev/null
chq "SYSTEM FLUSH LOGS"
MOVE_SECONDS=$(( $(date +%s) - MOVE_T0 ))

PUT_AFTER="$(evz S3PutObject)"
DPUT_AFTER="$(evz DiskS3PutObject)"
MOVE_PUTS=$(( PUT_AFTER - PUT_BEFORE ))
MOVE_DPUTS=$(( DPUT_AFTER - DPUT_BEFORE ))
COLD_PARTS="$(chq "SELECT count() FROM system.parts WHERE database='default' AND table='otel_logs' AND active AND disk_name='s3cold'")"
HOT_PARTS="$(chq "SELECT count() FROM system.parts WHERE database='default' AND table='otel_logs' AND active AND disk_name='default'")"
COLD_BYTES="$(chq "SELECT sum(bytes_on_disk) FROM system.parts WHERE database='default' AND table='otel_logs' AND active AND disk_name='s3cold'")"
MOVE_CPU="$(chq "SELECT sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds'])
                 FROM system.part_log WHERE database='default' AND table='otel_logs'
                 AND event_type IN ('MergeParts','MovePart')")"
MOVE_EVENTS="$(chq "SELECT arrayStringConcat(arrayMap(x -> concat(x.1, '=', toString(x.2)),
                      arraySort(groupArray((toString(event_type), c)))), ', ')
                    FROM (SELECT event_type, count() AS c FROM system.part_log
                          WHERE database='default' AND table='otel_logs' GROUP BY event_type)")"
TTL_OBJECTS="$(mc "mc ls -r m/$TTL_BUCKET | wc -l" | tr -d ' \r')"
TTL_BYTES="$(mc "mc du m/$TTL_BUCKET" | awk '{print $1}')"
ROWS_AFTER="$(chq "SELECT count() FROM default.otel_logs")"
echo "  moved in ${MOVE_SECONDS}s: $COLD_PARTS parts on s3cold, $TTL_OBJECTS objects, $TTL_BYTES"
echo "  PUTs: S3PutObject $MOVE_PUTS, DiskS3PutObject $MOVE_DPUTS"

# ------------------------------------------------------------- the late slice
# Born expired: the same rows with timestamps behind the boundary. These have no
# time on hot disk at all, so the move is charged on the insert path.
say "the late slice: $LATE_ROWS rows stamped behind the TTL boundary"
PUT_L0="$(evz S3PutObject)"; DPUT_L0="$(evz DiskS3PutObject)"
LATE_T0="$(date +%s)"
chq "INSERT INTO default.otel_logs (Timestamp, ServiceName, Body, SeverityText, LogAttributes)
     SELECT now() - INTERVAL 7 DAY - toIntervalSecond(number % 3600) AS Timestamp,
            ServiceName, Body, SeverityText, LogAttributes
     FROM (SELECT ServiceName, Body, SeverityText, LogAttributes FROM default.otel_logs LIMIT $LATE_ROWS),
          numbers(1)"
chq "SYSTEM FLUSH LOGS"
LATE_INSERT_SECONDS=$(( $(date +%s) - LATE_T0 ))
LATE_MOVE_T0="$(date +%s)"
chq "OPTIMIZE TABLE default.otel_logs FINAL" >/dev/null
chq "SYSTEM FLUSH LOGS"
LATE_MOVE_SECONDS=$(( $(date +%s) - LATE_MOVE_T0 ))
LATE_PUTS=$(( $(evz S3PutObject) - PUT_L0 ))
LATE_DPUTS=$(( $(evz DiskS3PutObject) - DPUT_L0 ))
LATE_OBJECTS="$(mc "mc ls -r m/$TTL_BUCKET | wc -l" | tr -d ' \r')"
LATE_COLD_PARTS="$(chq "SELECT count() FROM system.parts WHERE database='default' AND table='otel_logs' AND active AND disk_name='s3cold'")"
LATE_ROWS_TOTAL="$(chq "SELECT count() FROM default.otel_logs")"
echo "  late slice: PUTs S3PutObject $LATE_PUTS, DiskS3PutObject $LATE_DPUTS, objects now $LATE_OBJECTS"

python3 - "$OUT" <<PY
import json, sys
json.dump({
 "gap": 8,
 "baseline": "ClickHouse discussion 77681, den-crane, 2025-03-16",
 "ttl_seconds": $TTL_SECONDS,
 "ch_version": "$CH_VERSION",
 "feed_lines": $FEED_LINES,
 "hot_rows": ${HOT_ROWS:-0},
 "capture_span_seconds": ${SPAN:-0},
 "insert_cpu_us": ${INSERT_CPU:-0},
 "bytes_before_move": ${BYTES_BEFORE:-0},
 "move": {
   "seconds": $MOVE_SECONDS,
   "s3_put_object": $MOVE_PUTS,
   "disk_s3_put_object": $MOVE_DPUTS,
   "parts_on_s3cold": ${COLD_PARTS:-0},
   "parts_on_default": ${HOT_PARTS:-0},
   "bytes_on_s3cold": ${COLD_BYTES:-0},
   "objects_in_bucket": ${TTL_OBJECTS:-0},
   "bucket_size": "$TTL_BYTES",
   "merge_and_move_cpu_us": ${MOVE_CPU:-0},
   "part_log_events": "$MOVE_EVENTS",
   "rows_after": ${ROWS_AFTER:-0}
 },
 "late": {
   "rows_inserted": $LATE_ROWS,
   "insert_seconds": $LATE_INSERT_SECONDS,
   "move_seconds": $LATE_MOVE_SECONDS,
   "s3_put_object": $LATE_PUTS,
   "disk_s3_put_object": $LATE_DPUTS,
   "objects_in_bucket": ${LATE_OBJECTS:-0},
   "parts_on_s3cold": ${LATE_COLD_PARTS:-0},
   "rows_total": ${LATE_ROWS_TOTAL:-0}
 },
}, open(sys.argv[1], "w"), indent=1)
print("wrote", sys.argv[1])
PY

say "done"
