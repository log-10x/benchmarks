#!/usr/bin/env bash
#
# Can a retention policy be written per message type on ClickHouse today?
#
# The other destinations each have one cheaper place to put a log line: Splunk's
# frozen tier, Elastic's frozen tier, Datadog's Flex tier, CloudWatch's
# Infrequent Access, Azure's Basic and Auxiliary tables. The assumption worth
# testing is that ClickHouse has none of that, which would leave deletion as the
# only lever and make the whole story lossy.
#
# ClickHouse's own MergeTree documentation says otherwise. Its TTL grammar is:
#
#   TTL expr
#       [DELETE | RECOMPRESS codec | TO DISK 'x' | TO VOLUME 'x'][, ...]
#       [WHERE conditions]
#       [GROUP BY key_expr [SET v = aggr_func(v), ...]]
#
# So ClickHouse ships four levers: move to cheaper storage, recompress harder,
# roll up into aggregates, and delete. Three of the four keep every line. What
# it does not ship is any way to point them at a message type, because nothing
# in the row says which message it is.
#
# This script checks each lever against a real message-type column and reports
# what actually happened to the rows, rather than what the grammar allows.
#
#   ./run_policy.sh
#
# Needs Docker. Runs in about two minutes on its own small container.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
RESULTS="$HERE/results"
CTR="${CCS_POLICY_CTR:-ch-policy}"
IMAGE="${CCS_CH_IMAGE:-clickhouse/clickhouse-server:latest}"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec -i "$CTR" clickhouse-client "$@"; }

mkdir -p "$RESULTS"
if ! docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then
  say "starting $CTR"
  docker rm -f "$CTR" >/dev/null 2>&1 || true
  # A second volume on the same disk. It is not a cheaper tier by itself; it is
  # here to prove the MOVE fires and names a destination, which in a real
  # deployment is an S3-backed disk.
  mkdir -p "$HERE/.policy-cold"
  docker run -d --name "$CTR" --memory 6g --cpus 6 "$IMAGE" >/dev/null
  until docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1; do sleep 2; done
  docker exec "$CTR" bash -c 'mkdir -p /var/lib/clickhouse/cold && chown clickhouse:clickhouse /var/lib/clickhouse/cold'
  docker exec -i "$CTR" bash -c 'cat > /etc/clickhouse-server/config.d/cold.xml' <<'XML'
<clickhouse>
  <storage_configuration>
    <disks><cold><path>/var/lib/clickhouse/cold/</path></cold></disks>
    <policies>
      <hot_cold>
        <volumes>
          <hot><disk>default</disk></hot>
          <cold><disk>cold</disk></cold>
        </volumes>
      </hot_cold>
    </policies>
  </storage_configuration>
</clickhouse>
XML
  docker restart "$CTR" >/dev/null
  until docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1; do sleep 2; done
fi
CH_VERSION="$(ch --query "SELECT version()")"
say "ClickHouse $CH_VERSION"
ch --query "CREATE DATABASE IF NOT EXISTS policy"

# A stand-in estate: three message types, one of them noisy, ages spread over
# ninety days. The shape is what matters, not the volume. Loading ninety days in
# one statement creates more partitions per insert block than ClickHouse allows
# by default; a real pipeline inserts recent data only and never meets that
# guard, so the seed loads raise it rather than working around it.
say "one table, three message types, rows aged 0 to 90 days"
ch --multiquery --query "
DROP TABLE IF EXISTS policy.seed SYNC;
CREATE TABLE policy.seed (
  Timestamp DateTime,
  templateHash LowCardinality(String),
  ServiceName LowCardinality(String),
  Body String
) ENGINE = MergeTree ORDER BY (templateHash, Timestamp);
INSERT INTO policy.seed
SELECT
  now() - toIntervalDay(number % 90) - toIntervalMinute(number % 1440),
  ['debug_exporter','healthcheck','order_placed'][(number % 3) + 1],
  ['collector','frontend','checkout'][(number % 3) + 1],
  concat('line ', toString(number), ' value=', toString(number % 997))
FROM numbers(300000);"
ch --query "SELECT templateHash, count() FROM policy.seed GROUP BY templateHash ORDER BY templateHash FORMAT PrettyCompactMonoBlock"

report() { printf '  %-52s %s\n' "$1" "$2"; }

# ---------------------------------------------------------------- 1. RECOMPRESS
# Per pattern by expression: the TTL expression is ordinary SQL, so the age at
# which a row is recompressed can be read off its message type.
# Three variants, because the obvious two do not separate the mechanism from
# the schema. `policy` declares CODEC(ZSTD(1)) on Body exactly as the ClickStack
# schema does; `nocodec` is identical but leaves the column codec unset.
say "1. recompress harder, per message type, keeping every line"
for variant in control policy nocodec; do
  ttl=""; codec=" CODEC(ZSTD(1))"
  [ "$variant" = "control" ] || ttl="TTL Timestamp + toIntervalDay(multiIf(templateHash = 'debug_exporter', 1, templateHash = 'healthcheck', 7, 30)) RECOMPRESS CODEC(ZSTD(12))"
  [ "$variant" = "nocodec" ] && codec=""
  ch --multiquery --query "
  DROP TABLE IF EXISTS policy.recompress_$variant SYNC;
  CREATE TABLE policy.recompress_$variant (
    Timestamp DateTime,
    templateHash LowCardinality(String),
    ServiceName LowCardinality(String),
    Body String$codec
  ) ENGINE = MergeTree ORDER BY (templateHash, Timestamp)
  PARTITION BY (templateHash, toYYYYMMDD(Timestamp))
  $ttl
  SETTINGS min_rows_for_wide_part = 0, min_bytes_for_wide_part = 0;
  INSERT INTO policy.recompress_$variant SELECT * FROM policy.seed
    SETTINGS max_partitions_per_insert_block = 5000;
  OPTIMIZE TABLE policy.recompress_$variant FINAL;"
done
sleep 3
ch --query "
SELECT
  table,
  sum(rows) AS rows_kept,
  sum(column_data_compressed_bytes) AS body_bytes,
  formatReadableSize(sum(column_data_compressed_bytes)) AS body_on_disk,
  (SELECT any(default_compression_codec) FROM system.parts AS p
   WHERE p.database = 'policy' AND p.table = c.table AND p.active) AS part_codec
FROM system.parts_columns AS c
WHERE database = 'policy' AND table LIKE 'recompress_%' AND active AND column = 'Body'
GROUP BY table ORDER BY table FORMAT PrettyCompactMonoBlock"
echo "  A part whose default_compression_codec reads ZSTD(12) has had the TTL applied."
echo "  Whether the COLUMN shrank is a separate question, and the answer is above."

# ------------------------------------------------------------- 2. TO VOLUME
# A TTL move is decided for a whole part, so a part holding a spread of ages
# never expires and nothing moves. Partitioning by time, which is what the
# ClickStack schema already does, makes each part age-homogeneous. The age
# itself is an expression over the message type.
say "2. move to a cheaper volume at a different age per message type"
ch --multiquery --query "
DROP TABLE IF EXISTS policy.tiered SYNC;
CREATE TABLE policy.tiered (
  Timestamp DateTime,
  templateHash LowCardinality(String),
  ServiceName LowCardinality(String),
  Body String
) ENGINE = MergeTree
PARTITION BY (templateHash, toYYYYMMDD(Timestamp))
ORDER BY (templateHash, Timestamp)
TTL Timestamp + toIntervalDay(multiIf(templateHash = 'debug_exporter', 1,
                                      templateHash = 'healthcheck', 7, 60)) TO VOLUME 'cold'
SETTINGS storage_policy = 'hot_cold';
INSERT INTO policy.tiered SELECT * FROM policy.seed
  SETTINGS max_partitions_per_insert_block = 5000;
OPTIMIZE TABLE policy.tiered FINAL;"
# Moves run on a background task. Wait for it to drain rather than forcing it.
for _ in $(seq 1 30); do
  moving="$(ch --query "SELECT count() FROM system.moves WHERE database='policy'" 2>/dev/null || echo 0)"
  [ "$moving" = "0" ] && sleep 2 && break
  sleep 2
done
sleep 5
ch --query "
SELECT
  splitByChar('-', partition)[1] AS templateHash,
  disk_name,
  count() AS parts,
  sum(rows) AS rows
FROM system.parts WHERE database='policy' AND table='tiered' AND active
GROUP BY templateHash, disk_name ORDER BY templateHash, disk_name
FORMAT PrettyCompactMonoBlock"

# ------------------------------------------------------------- 3. GROUP BY
say "3. roll one message type up into counts, and keep the counts forever"
ch --multiquery --query "
DROP TABLE IF EXISTS policy.rollup SYNC;
CREATE TABLE policy.rollup (
  Timestamp DateTime,
  templateHash LowCardinality(String),
  ServiceName LowCardinality(String),
  Body String,
  events UInt64 DEFAULT 1
) ENGINE = MergeTree
ORDER BY (templateHash, Timestamp)
TTL Timestamp + INTERVAL 30 DAY
    GROUP BY templateHash SET events = sum(events), Body = any(Body);
INSERT INTO policy.rollup SELECT Timestamp, templateHash, ServiceName, Body, 1 FROM policy.seed;
OPTIMIZE TABLE policy.rollup FINAL;"
ch --query "
SELECT templateHash, count() AS rows_now, sum(events) AS events_represented
FROM policy.rollup GROUP BY templateHash ORDER BY templateHash FORMAT PrettyCompactMonoBlock"

# ------------------------------------------------- 4. DELETE WHERE per pattern
say "4. a different retention for each message type, from one expression"
ch --multiquery --query "
DROP TABLE IF EXISTS policy.retention SYNC;
CREATE TABLE policy.retention (
  Timestamp DateTime,
  templateHash LowCardinality(String),
  ServiceName LowCardinality(String),
  Body String
) ENGINE = MergeTree ORDER BY (templateHash, Timestamp)
TTL Timestamp + toIntervalDay(multiIf(templateHash = 'debug_exporter', 7,
                                      templateHash = 'healthcheck', 30, 60)) DELETE;
INSERT INTO policy.retention SELECT * FROM policy.seed;
OPTIMIZE TABLE policy.retention FINAL;"
ch --query "
SELECT templateHash,
       count() AS rows_kept,
       toUInt32(dateDiff('day', min(Timestamp), now())) AS oldest_day
FROM policy.retention GROUP BY templateHash ORDER BY templateHash FORMAT PrettyCompactMonoBlock"
ch --query "
SELECT 'seed rows: ' || toString((SELECT count() FROM policy.seed)) ||
       ', after per-pattern retention: ' || toString(count()) FROM policy.retention"

say "done. container $CTR left up; remove with: docker rm -f $CTR"
