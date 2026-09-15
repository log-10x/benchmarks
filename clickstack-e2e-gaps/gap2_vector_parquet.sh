#!/usr/bin/env bash
#
# Gap 2: the cold branch written by Vector instead of the OpenTelemetry
# Collector, the path the MCP recipe marks NOT EXERCISED.
#
# The route is the harness's, with one change: the returned stream is also sent
# to Vector over OTLP, and Vector makes the cold decision itself with a `route`
# transform on `routeState`, then writes the offloaded records to MinIO through
# its `aws_s3` sink with the service and the day in `key_prefix`.
#
# The first thing the run does is ask Vector's own binary whether it will accept
# `encoding.codec: parquet`, and it records the answer verbatim. Whatever that
# answer is, the run then writes the objects with the codec Vector does carry,
# reads them through the same S3 table and the same Merge table the harness
# uses, and times the same queries. A Parquet copy of the same rows is written
# afterwards by ClickHouse itself and queried the same way, so the query table
# has a Parquet row even where Vector cannot produce one. That row is labelled
# as converted, because ClickHouse wrote it and Vector did not.
#
#   ./gap2_vector_parquet.sh
#
# Environment: as lib.sh.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUT="$RESULTS/gap2.json"
PARQUET_BUCKET=coldparquet

trap g_teardown EXIT
g_require
say "input"; g_input
g_render_harness_conf
g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$JRE_IMAGE" "$EDGE_IMAGE" "$VECTOR_IMAGE"

# ------------------------------------------------- does this build take parquet
say "does this Vector build carry the parquet codec"
VECTOR_VERSION="$(docker run --rm "$VECTOR_IMAGE" --version | head -1)"
mkdir -p "$BUILD/vector"
cat > "$BUILD/vector/probe.yaml" <<'YAML'
sources:
  in:
    type: demo_logs
    format: syslog
sinks:
  out:
    type: aws_s3
    inputs: [ in ]
    bucket: coldlogs
    region: us-east-1
    encoding:
      codec: parquet
YAML
set +e
docker run --rm -v "$BUILD/vector/probe.yaml":/etc/vector/probe.yaml:ro "$VECTOR_IMAGE" \
  validate --no-environment /etc/vector/probe.yaml > "$BUILD/vector/probe.out" 2>&1
PARQUET_PROBE_RC=$?
set -e
PARQUET_CODEC_OK=0
if [ "$PARQUET_PROBE_RC" = "0" ]; then PARQUET_CODEC_OK=1; fi
sed 's/^/  /' "$BUILD/vector/probe.out" | tail -5

# ------------------------------------------------------------ the two configs
# Vector 0.50 has no `ndjson` codec: newline delimited JSON is the `json` codec
# with newline framing, which is what the S3 table reads as JSONEachRow.
CODEC=json
if [ "$PARQUET_CODEC_OK" = "1" ]; then CODEC=parquet; fi
cat > "$BUILD/vector/vector.yaml" <<YAML
# The cold branch, in Vector. The OpenTelemetry source takes the stream the
# routing collector forwards, the route transform makes the offload decision on
# the mark the receiver put on the record, and the aws_s3 sink writes the
# service and the day into the object path.
data_dir: /vector-data

sources:
  otlp:
    type: opentelemetry
    # End to end acknowledgements would hold the gRPC response until the S3
    # batch flushed, and the collector's exporter would then hold the whole
    # route behind it. The first run of this script moved 1,425 records for
    # that reason.
    acknowledgements:
      enabled: false
    grpc:
      address: 0.0.0.0:4319
    http:
      address: 0.0.0.0:4320
      keepalive:
        max_connection_age_secs: 600

transforms:
  split:
    type: route
    inputs: [ otlp.logs ]
    route:
      cold: '.attributes.routeState == "offload"'

  # The shape the harness's cold table reads: the body and a flat attribute map,
  # with the service, the severity and the record time folded into it, because
  # the object carries no resource and no timestamp of its own.
  shape:
    type: remap
    inputs: [ split.cold ]
    source: |
      svc = string!(.resources."service.name" || .attributes.k8s_container || "unknown")
      stamp = now()
      if is_timestamp(.timestamp) { stamp = timestamp!(.timestamp) }
      ts = to_unix_timestamp(stamp)
      attrs = object!(.attributes || {})
      attrs.ServiceName = svc
      attrs.SeverityText = string(.severity_text) ?? ""
      attrs.TimestampSec = to_string(ts)
      attrs.TimestampNano = to_string(ts * 1000000000)
      body = string(.message) ?? string(.body) ?? ""
      . = { "body": body, "logAttributes": attrs, "svc": svc }

sinks:
  cold:
    type: aws_s3
    inputs: [ shape ]
    bucket: $BUCKET
    region: us-east-1
    endpoint: http://$MINIO:9000
    auth:
      access_key_id: minioadmin
      secret_access_key: minioadmin
    key_prefix: "service={{ svc }}/day=%F/"
    filename_extension: json
    compression: none
    encoding:
      codec: $CODEC
      except_fields: [ svc ]
    framing:
      method: newline_delimited
    batch:
      max_bytes: 33554432
      timeout_secs: 5
YAML

# The router, with the returned stream forwarded to Vector as well.
python3 - "$BUILD/conf/router.yaml" "$BUILD/conf/router_vector.yaml" "$VECTOR" <<'PY'
import sys
src, dst, vector = sys.argv[1], sys.argv[2], sys.argv[3]
t = open(src).read()
t = t.replace("exporters:\n  otlp/engine:",
              f"exporters:\n  otlp/vector:\n    endpoint: {vector}:4319\n    tls:\n      insecure: true\n"
              "  otlp/engine:", 1)
t = t.replace("      exporters: [ routing/state ]",
              "      exporters: [ routing/state, otlp/vector ]", 1)
# The awss3 exporter stays defined but nothing feeds it: Vector writes the cold
# side in this variant, and the cold pipeline is left with the file tap only so
# the route still runs and the hot side is unchanged.
t = t.replace("      exporters: [ awss3/cold ]", "      exporters: [ nop ]", 1)
t = t.replace("exporters:\n  otlp/vector:", "exporters:\n  nop:\n  otlp/vector:", 1)
open(dst, "w").write(t)
print("  router config with the Vector fork written")
PY

docker run --rm -v "$BUILD/vector/vector.yaml":/etc/vector/vector.yaml:ro "$VECTOR_IMAGE" \
  validate --no-environment /etc/vector/vector.yaml > "$BUILD/vector/validate.out" 2>&1 || true
sed 's/^/  /' "$BUILD/vector/validate.out" | tail -6

# ---------------------------------------------------------------------- the run
g_net
say "object store"; g_minio_up
mc "mc mb -p m/$PARQUET_BUCKET >/dev/null && echo '  bucket $PARQUET_BUCKET created'"
say "ClickStack"; g_clickstack_up

mkdir -p "$BUILD/policy" "$BUILD/vector-data"
chmod 777 "$BUILD/vector-data"
cp "$BUILD/conf/caps.csv" "$BUILD/conf/actions.csv" "$BUILD/policy/"
touch "$BUILD/policy/caps.csv" "$BUILD/policy/actions.csv"

say "Vector"
docker rm -f -v "$VECTOR" >/dev/null 2>&1 || true
docker run -d --name "$VECTOR" --network "$NET" --memory 768m --cpus 2 \
  -v "$BUILD/vector/vector.yaml":/etc/vector/vector.yaml:ro \
  -v "$BUILD/vector-data":/vector-data \
  "$VECTOR_IMAGE" --config /etc/vector/vector.yaml >/dev/null
sleep 5
docker logs "$VECTOR" 2>&1 | tail -3 | sed 's/^/  /'

say "receiver"; g_engine_up "$BUILD/policy"
say "collector: read, route, forward to Vector"; g_router_up "$BUILD/conf/router_vector.yaml"
g_wait_settle default.otel_logs 4
g_flush_cold
# Vector flushes what it holds on a graceful stop.
docker stop "$VECTOR" >/dev/null
sleep 5
docker logs "$VECTOR" > "$BUILD/vector/vector.log" 2>&1 || true

VECTOR_OBJECTS="$(g_objects)"
VECTOR_BYTES="$(g_object_bytes)"
HOT_ROWS="$(chq "SELECT count() FROM default.otel_logs")"
python3 "$GAPS_HERE/wire_hashes.py" --wire "$BUILD/wire/returned.json" --out "$BUILD/gap2_wire.json"
echo "  Vector wrote $VECTOR_OBJECTS objects, $VECTOR_BYTES; hot rows $HOT_ROWS"

say "the same S3 table and the same Merge table, over Vector's objects"
docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"
COLD_ROWS="$(chq "SELECT count() FROM default.otel_logs_coldv")"
echo "  rows readable through the S3 table: $COLD_ROWS"
g_export_cold "gap2"

# ---------------------------------------------------- the same rows as Parquet
say "the same rows again as Parquet, written by ClickHouse"
SERVICES="$(chq "SELECT DISTINCT service FROM default.otel_logs_cold ORDER BY service" | tr '\n' ' ')"
DAY="$(chq "SELECT toString(today())")"
for svc in $SERVICES; do
  chq "INSERT INTO FUNCTION s3('http://$MINIO:9000/$PARQUET_BUCKET/service=$svc/day=$DAY/part.parquet',
         'minioadmin','minioadmin','Parquet')
       SELECT body, logAttributes FROM default.otel_logs_cold WHERE service = '$svc'"
done
PARQUET_OBJECTS="$(mc "mc ls -r m/$PARQUET_BUCKET | wc -l" | tr -d ' \r')"
PARQUET_BYTES="$(mc "mc du m/$PARQUET_BUCKET" | awk '{print $1}')"
docker exec -i "$CS" clickhouse-client --multiquery <<SQL
DROP TABLE IF EXISTS default.otel_logs_coldp;
CREATE TABLE default.otel_logs_coldp
(
  body           String,
  logAttributes  Map(String, String),
  service        LowCardinality(String),
  day            Date
) ENGINE = S3('http://$MINIO:9000/$PARQUET_BUCKET/**.parquet', 'minioadmin', 'minioadmin', 'Parquet')
SETTINGS use_hive_partitioning = 1;

DROP VIEW IF EXISTS default.otel_logs_coldpv;
CREATE VIEW default.otel_logs_coldpv AS
SELECT toDateTime64(toUInt64OrZero(logAttributes['TimestampSec']), 9) AS Timestamp,
       CAST(service AS LowCardinality(String))                        AS ServiceName,
       body                                                           AS Body,
       CAST(logAttributes['SeverityText'] AS LowCardinality(String))  AS SeverityText,
       logAttributes                                                  AS LogAttributes,
       day                                                            AS day
FROM default.otel_logs_coldp;

DROP TABLE IF EXISTS default.otel_logs_allp;
CREATE TABLE default.otel_logs_allp
(
  Timestamp     DateTime64(9),
  ServiceName   LowCardinality(String),
  Body          String,
  SeverityText  LowCardinality(String),
  LogAttributes Map(String, String),
  day           Date
) ENGINE = Merge(default, '^(otel_logs|otel_logs_coldpv)\$');
SQL
PARQUET_ROWS="$(chq "SELECT count() FROM default.otel_logs_coldp")"
echo "  Parquet: $PARQUET_OBJECTS objects, $PARQUET_BYTES, $PARQUET_ROWS rows"

SVC="$(chq "SELECT service FROM default.otel_logs_cold GROUP BY service ORDER BY count() DESC LIMIT 1")"
HASH="$(chq "SELECT LogAttributes['tenx_hash'] FROM default.otel_logs_coldv
             WHERE LogAttributes['tenx_hash'] != '' GROUP BY 1 ORDER BY count() DESC LIMIT 1")"

say "queries, over the Vector objects and over the Parquet copy"
python3 - "$BUILD/gap2_queries.json" "$SVC" "$HASH" <<'PY'
import json, sys
out, svc, h = sys.argv[1], sys.argv[2], sys.argv[3]
rows = [{"name": "hot only, last 4 hours, count",
         "sql": "SELECT count() FROM default.otel_logs WHERE Timestamp >= now() - INTERVAL 4 HOUR"}]
for label, t in (("Vector objects, json", "default.otel_logs_all"),
                 ("Parquet copy", "default.otel_logs_allp")):
    rows += [
      {"name": f"merge, service {svc} and one day: {label}",
       "sql": f"SELECT count() FROM {t} WHERE ServiceName = '{svc}' AND day = today()"},
      {"name": f"merge, time only, the shape HyperDX sends: {label}",
       "sql": f"SELECT count() FROM {t} WHERE Timestamp >= now() - INTERVAL 4 HOUR"},
      {"name": f"merge, text search, no other filter: {label}",
       "sql": f"SELECT count() FROM {t} WHERE positionCaseInsensitive(Body, 'snapshot') > 0"},
      {"name": f"merge, one pattern hash: {label}",
       "sql": f"SELECT count() FROM {t} WHERE LogAttributes['tenx_hash'] = '{h}'"},
    ]
json.dump(rows, open(out, "w"), indent=1)
PY
python3 "$GAPS_HERE/measure.py" --container "$CS" --spec "$BUILD/gap2_queries.json" \
  --out "$BUILD/gap2_queries_out.json"

python3 - "$OUT" "$BUILD/gap2_queries_out.json" "$BUILD/gap2_wire.json" \
  "$BUILD/vector/probe.out" "$BUILD/vector/validate.out" <<PY
import json, pathlib, sys
out, queries, wire, probe, validate = sys.argv[1:6]
json.dump({
 "gap": 2,
 "vector_version": "$VECTOR_VERSION",
 "parquet_codec_accepted": bool($PARQUET_CODEC_OK),
 "parquet_probe_output": pathlib.Path(probe).read_text()[-800:],
 "vector_config_validates": pathlib.Path(validate).read_text()[-800:],
 "codec_used": "$CODEC",
 "feed_lines": $FEED_LINES,
 "wire": json.load(open(wire)),
 "hot_rows": $HOT_ROWS,
 "vector_objects": "$VECTOR_OBJECTS", "vector_bytes": "$VECTOR_BYTES",
 "cold_rows_readable": $COLD_ROWS,
 "parquet_objects": $PARQUET_OBJECTS, "parquet_bytes": "$PARQUET_BYTES",
 "parquet_rows": $PARQUET_ROWS,
 "queries": json.load(open(queries)),
}, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
