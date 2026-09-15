#!/usr/bin/env bash
#
# The same per-message-type tier-down as run_policy.sh, but the cold volume is
# an S3-compatible bucket rather than a second directory on the same disk.
#
# run_policy.sh proved the TTL move fires per message type and that moved rows
# stay queryable. It did not prove the destination can be object storage, which
# is the only version of the move that saves money. This one runs MinIO beside
# ClickHouse, declares the bucket as a ClickHouse disk of type s3, and repeats
# the move. Everything is read back from system.parts and from the table.
#
#   ./run_policy_s3.sh
#
# Needs Docker. About three minutes on its own two containers.

set -euo pipefail
NET=ch-s3-net; MINIO=ch-minio; CTR=ch-policy-s3
IMAGE="${CCS_CH_IMAGE:-clickhouse/clickhouse-server:latest}"
say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec -i "$CTR" clickhouse-client "$@"; }

say "containers"
docker rm -f "$MINIO" "$CTR" >/dev/null 2>&1 || true
docker network create "$NET" >/dev/null 2>&1 || true
docker run -d --name "$MINIO" --network "$NET" \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data >/dev/null
until docker exec "$MINIO" sh -c 'curl -sf http://localhost:9000/minio/health/live' >/dev/null 2>&1; do sleep 1; done
docker run --rm --network "$NET" --entrypoint sh quay.io/minio/mc -c \
  "mc alias set m http://$MINIO:9000 minioadmin minioadmin >/dev/null && mc mb -p m/logs >/dev/null && echo '  bucket logs created'"

docker run -d --name "$CTR" --network "$NET" --memory 4g --cpus 4 "$IMAGE" >/dev/null
until docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1; do sleep 2; done
docker exec -i "$CTR" bash -c 'cat > /etc/clickhouse-server/config.d/s3.xml' <<XML
<clickhouse>
  <storage_configuration>
    <disks>
      <s3cold>
        <type>s3</type>
        <endpoint>http://$MINIO:9000/logs/clickhouse/</endpoint>
        <access_key_id>minioadmin</access_key_id>
        <secret_access_key>minioadmin</secret_access_key>
      </s3cold>
    </disks>
    <policies>
      <hot_s3>
        <volumes>
          <hot><disk>default</disk></hot>
          <cold><disk>s3cold</disk></cold>
        </volumes>
      </hot_s3>
    </policies>
  </storage_configuration>
</clickhouse>
XML
docker restart "$CTR" >/dev/null
until docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1; do sleep 2; done
say "ClickHouse $(ch --query 'SELECT version()'), disks:"
ch --query "SELECT name, type, path FROM system.disks FORMAT PrettyCompactMonoBlock"

say "three message types, 300,000 rows over ninety days, moved to S3 at 1 / 7 / 60 days"
ch --multiquery --query "
CREATE DATABASE IF NOT EXISTS policy;
DROP TABLE IF EXISTS policy.tiered_s3 SYNC;
CREATE TABLE policy.tiered_s3 (
  Timestamp DateTime,
  templateHash LowCardinality(String),
  ServiceName LowCardinality(String),
  Body String
) ENGINE = MergeTree
PARTITION BY (templateHash, toYYYYMMDD(Timestamp))
ORDER BY (templateHash, Timestamp)
TTL Timestamp + toIntervalDay(multiIf(templateHash = 'debug_exporter', 1,
                                      templateHash = 'healthcheck', 7, 60)) TO VOLUME 'cold'
SETTINGS storage_policy = 'hot_s3';
INSERT INTO policy.tiered_s3
SELECT now() - toIntervalDay(number % 90) - toIntervalMinute(number % 1440),
       ['debug_exporter','healthcheck','order_placed'][(number % 3) + 1],
       ['collector','frontend','checkout'][(number % 3) + 1],
       concat('line ', toString(number), ' value=', toString(number % 997))
FROM numbers(300000) SETTINGS max_partitions_per_insert_block = 5000;
OPTIMIZE TABLE policy.tiered_s3 FINAL;"
for _ in $(seq 1 60); do
  [ "$(ch --query "SELECT count() FROM system.moves")" = "0" ] && break; sleep 2
done
sleep 5

say "where the parts are"
ch --query "
SELECT splitByChar(',', replaceAll(partition,'(',''))[1] AS pattern, disk_name, count() AS parts, sum(rows) AS rows
FROM system.parts WHERE database='policy' AND table='tiered_s3' AND active
GROUP BY pattern, disk_name ORDER BY pattern, disk_name FORMAT PrettyCompactMonoBlock"

say "objects actually in the bucket"
docker run --rm --network "$NET" --entrypoint sh quay.io/minio/mc -c \
  "mc alias set m http://$MINIO:9000 minioadmin minioadmin >/dev/null && mc du m/logs && echo '  objects:' \$(mc ls -r m/logs | wc -l)"

say "read rows back from S3-resident parts"
ch --query "
SELECT count() AS rows_read, min(Timestamp) AS oldest, max(Timestamp) AS newest
FROM policy.tiered_s3 WHERE templateHash = 'debug_exporter' AND Timestamp < now() - INTERVAL 30 DAY FORMAT Vertical"
ch --query "SELECT templateHash, Timestamp, Body FROM policy.tiered_s3 WHERE templateHash='debug_exporter' AND Timestamp < now() - INTERVAL 60 DAY ORDER BY Timestamp LIMIT 2"
ch --query "SELECT 'total rows still in table: ' || toString(count()) FROM policy.tiered_s3"

say "done. tear down with: docker rm -f $CTR $MINIO; docker network rm $NET"
