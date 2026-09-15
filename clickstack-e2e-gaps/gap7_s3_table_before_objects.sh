#!/usr/bin/env bash
#
# ClickHouse issue 116888, and the guard for it.
#
# Filed 2026-08-28 by zlareb1, a ClickHouse member, and open. An S3 table with an
# explicit schema and `use_hive_partitioning = 1` resolves its partition columns
# against an empty listing and keeps the result, after which every predicate on a
# path column matches nothing and the table answers zero rows with no error.
#
# What this run adds is the trigger, and it is not the CREATE. The S3 engine
# resolves its listing during SELECT, so a table created over an empty prefix and
# left alone is fine, and the same table read once while the prefix is still
# empty is not. The count with no predicate stays right either way, so the table
# looks healthy on the one query a reader is most likely to run next.
#
# The offload recipe renders that DDL as a setup step, so a reader who creates
# the table before starting the collector and checks the step worked gets a table
# that silently answers nothing to the day and service predicates the whole
# economic argument rests on.
#
# This script shows the trap and the ways out, on one ClickHouse and one MinIO,
# with objects written by ClickHouse itself so no route is needed:
#
#   before   the table created while the bucket is empty, and not read until the
#            objects are there
#   probed   the table created while the bucket is empty AND read once while it
#            is still empty, which is what a reader following the recipe does
#            when checking the setup step worked. The S3 engine resolves its
#            listing during SELECT rather than at CREATE, so this is the arm
#            where a cached empty listing could show
#   after    the same DDL, created once the first object exists, which is the
#            guard `g_wait_for_object` now performs in lib.sh
#   detach   the `probed` table, whose path predicates are dead, recovered
#            with DETACH then ATTACH
#
#   ./gap7_s3_table_before_objects.sh
#
# Environment: as lib.sh. Needs no capture and no receiver.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUT="$RESULTS/gap7.json"
TRAP_BUCKET=trap116888
SVC=cart
ROWS="${ROWS:-20000}"

trap g_teardown EXIT
g_require
g_images "$CS_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE"
g_net
say "object store"; g_minio_up
mc "mc mb -p m/$TRAP_BUCKET >/dev/null && echo '  bucket $TRAP_BUCKET created'"
say "ClickStack"; g_clickstack_up

DAY="$(chq "SELECT toString(today())")"
S3="http://$MINIO:9000/$TRAP_BUCKET"

ddl() { # ddl <table name>
  docker exec -i "$CS" clickhouse-client --multiquery <<SQL
DROP TABLE IF EXISTS default.$1;
CREATE TABLE default.$1
(
  body           String,
  logAttributes  Map(String, String),
  service        LowCardinality(String),
  day            Date
) ENGINE = S3('$S3/**.json', 'minioadmin', 'minioadmin', 'JSONEachRow')
SETTINGS use_hive_partitioning = 1;
SQL
}

say "the bucket is empty, and the table is created anyway"
echo "  objects under $TRAP_BUCKET: $(mc "mc ls -r m/$TRAP_BUCKET | wc -l" | tr -d ' \r')"
ddl s3_before
echo "  default.s3_before created over an empty prefix"
ddl s3_probed
echo "  default.s3_probed created over an empty prefix, and read while empty:"
for w in "" "WHERE service = '$SVC'" "WHERE day = '$DAY'"; do
  printf '    count() %s -> %s\n' "${w:-(no predicate)}" \
    "$(chq "SELECT count() FROM default.s3_probed $w" 2>&1 | head -1)"
done

say "now the objects arrive, the way a collector would write them"
for svc in $SVC kafka; do
  chq "INSERT INTO FUNCTION s3('$S3/service=$svc/day=$DAY/part.json',
         'minioadmin','minioadmin','JSONEachRow')
       SELECT concat('line ', toString(number), ' from $svc') AS body,
              map('ServiceName', '$svc',
                  'TimestampSec', toString(toUnixTimestamp(now()) - number % 3600),
                  'tenx_hash', concat('h', toString(number % 40))) AS logAttributes
       FROM numbers($ROWS)"
done
OBJECTS="$(mc "mc ls -r m/$TRAP_BUCKET | wc -l" | tr -d ' \r')"
echo "  $OBJECTS objects written"

say "the same DDL again, this time after the first object exists"
g_wait_for_object "$TRAP_BUCKET"
ddl s3_after
echo "  default.s3_after created"

ask() { # ask <table> <where>  -> rows
  chq "SELECT count() FROM default.$1 $2" 2>/dev/null || echo "ERROR"
}

say "the same three questions, on each table"
B_ALL="$(ask s3_before '')"
B_SVC="$(ask s3_before "WHERE service = '$SVC'")"
B_DAY="$(ask s3_before "WHERE day = '$DAY'")"
P_ALL="$(ask s3_probed '')"
P_SVC="$(ask s3_probed "WHERE service = '$SVC'")"
P_DAY="$(ask s3_probed "WHERE day = '$DAY'")"
echo "  probed: all $P_ALL, service $P_SVC, day $P_DAY"
A_ALL="$(ask s3_after '')"
A_SVC="$(ask s3_after "WHERE service = '$SVC'")"
A_DAY="$(ask s3_after "WHERE day = '$DAY'")"
echo "  before: all $B_ALL, service $B_SVC, day $B_DAY"
echo "  after:  all $A_ALL, service $A_SVC, day $A_DAY"

say "the recovery: DETACH then ATTACH the table whose path predicates are dead"
chq "DETACH TABLE default.s3_probed" >/dev/null
chq "ATTACH TABLE default.s3_probed" >/dev/null
D_ALL="$(ask s3_probed '')"
D_SVC="$(ask s3_probed "WHERE service = '$SVC'")"
D_DAY="$(ask s3_probed "WHERE day = '$DAY'")"
echo "  after DETACH and ATTACH: all $D_ALL, service $D_SVC, day $D_DAY"

CH_V="$(chq 'SELECT version()')"
python3 - "$OUT" <<PY
import json, sys
json.dump({
 "gap": 7,
 "issue": "ClickHouse 116888, open, filed 2026-08-28 by zlareb1",
 "ch_version": "$CH_V",
 "objects": $OBJECTS, "rows_per_object": $ROWS,
 "day": "$DAY", "service": "$SVC",
 "rows": [
  {"table": "created before any object exists, not read until after", "no predicate": "$B_ALL",
   "service predicate": "$B_SVC", "day predicate": "$B_DAY"},
  {"table": "created AND read while the prefix is empty", "no predicate": "$P_ALL",
   "service predicate": "$P_SVC", "day predicate": "$P_DAY"},
  {"table": "created after the first object exists", "no predicate": "$A_ALL",
   "service predicate": "$A_SVC", "day predicate": "$A_DAY"},
  {"table": "the probed table, after DETACH and ATTACH", "no predicate": "$D_ALL",
   "service predicate": "$D_SVC", "day predicate": "$D_DAY"},
 ],
}, open(sys.argv[1], "w"), indent=1)
print("wrote", sys.argv[1])
PY

say "done"
