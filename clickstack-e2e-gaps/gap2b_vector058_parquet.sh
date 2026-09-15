#!/usr/bin/env bash
#
# Gap 2, second pass: Vector 0.58.0, and Parquet written by Vector itself.
#
# `gap2_vector_parquet.sh` pinned `timberio/vector:0.50.0-debian`, published
# 2025-09-23, and asked whether it would take `encoding.codec: parquet`. Two
# things were wrong with that question. `encoding.codec` names the per event
# serializer and has never taken a columnar codec, and the build was a year old.
# Vector writes Parquet on the `aws_s3` sink through a separate option,
# `batch_encoding.codec`, added in v0.55.0 on 2026-04-22 and carried by the
# official release binaries from v0.56.0 on 2026-06-03; upstream issue 1374
# closed on 2026-04-28, by pull requests 25156 and 25321.
#
# So this script asks the question again on the current build, three ways:
#
#   1. `encoding.codec: parquet`          the key the first pass probed
#   2. `batch_encoding.codec: parquet`    alone, no `encoding`
#   3. both, which is the documented form
#
# and then runs the route once with Vector writing BOTH containers from the same
# stream: newline delimited JSON into one bucket, Parquet into another. Both are
# read by S3 tables and Merge tables of the same shape, and the same queries run
# over each, with the Parquet reader's own row group and page counters read out
# of `system.query_log` beside the S3 request counters.
#
# One shape difference between the two arms, stated here and in the results
# rather than in a footnote. The JSON arm writes `{"body": ..., "logAttributes":
# {...}}` and ClickHouse reads `logAttributes` as a `Map(String, String)`. The
# Parquet arm flattens the fields the queries name into their own columns,
# because a columnar container wants columns and a schema inferred from a free
# map would carry one field per attribute key seen. The rows are the same rows
# and the answers must match; the containers differ.
#
#   ./gap2b_vector058_parquet.sh
#
# Environment: as lib.sh.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUT="$RESULTS/gap2b.json"
PQ_BUCKET=coldparquetv

trap g_teardown EXIT
g_require
say "input"; g_input
g_render_harness_conf
g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$EDGE_IMAGE" "$VECTOR_IMAGE"

# ------------------------------------------------------- the three probes
say "what this Vector build takes"
VECTOR_VERSION="$(docker run --rm "$VECTOR_IMAGE" --version | head -1)"
echo "  $VECTOR_VERSION"
mkdir -p "$BUILD/vector058"

probe() { # probe <name> <sink body>
  local name="$1" body="$2" rc
  { echo "sources:"; echo "  in:"; echo "    type: demo_logs"; echo "    format: syslog";
    echo "sinks:"; echo "  out:"; echo "    type: aws_s3"; echo "    inputs: [ in ]";
    echo "    bucket: coldlogs"; echo "    region: us-east-1"; printf '%s\n' "$body";
  } > "$BUILD/vector058/probe-$name.yaml"
  set +e
  docker run --rm -v "$BUILD/vector058/probe-$name.yaml":/etc/vector/probe.yaml:ro \
    "$VECTOR_IMAGE" validate --no-environment /etc/vector/probe.yaml \
    > "$BUILD/vector058/probe-$name.out" 2>&1
  rc=$?
  set -e
  echo "  $name: exit $rc"
  sed 's/^/    /' "$BUILD/vector058/probe-$name.out" | tail -3
  return 0
}

probe encoding_codec_parquet '    encoding:
      codec: parquet'
PROBE_ENCODING_RC="$(grep -c 'unknown variant' "$BUILD/vector058/probe-encoding_codec_parquet.out" || true)"

probe batch_encoding_only '    batch_encoding:
      codec: parquet'
probe batch_encoding_with_encoding '    compression: none
    encoding:
      codec: json
    batch_encoding:
      codec: parquet
      schema_mode: auto_infer
      compression:
        algorithm: snappy'

rc_of() {
  docker run --rm -v "$BUILD/vector058/probe-$1.yaml":/etc/vector/probe.yaml:ro \
    "$VECTOR_IMAGE" validate --no-environment /etc/vector/probe.yaml >/dev/null 2>&1 \
    && echo 1 || echo 0
}
OK_ENCODING="$(rc_of encoding_codec_parquet)"
OK_BATCH_ONLY="$(rc_of batch_encoding_only)"
OK_BOTH="$(rc_of batch_encoding_with_encoding)"
echo "  accepted: encoding.codec=$OK_ENCODING batch_encoding alone=$OK_BATCH_ONLY both=$OK_BOTH"
[ "$OK_BOTH" = "1" ] || { echo "the documented Parquet config does not validate on this build" >&2;
                          cat "$BUILD/vector058/probe-batch_encoding_with_encoding.out" >&2; exit 1; }

# -------------------------------------------------------------- the config
# Two sinks off one transform. The JSON sink is the first pass's sink,
# unchanged. The Parquet sink is the documented form: `compression: none` at the
# sink because Parquet compresses per column page, `encoding.codec: json`
# because the field is required and ignored for the batch, and
# `batch_encoding.codec: parquet` with `schema_mode: auto_infer` and snappy.
cat > "$BUILD/vector058/vector.yaml" <<YAML
data_dir: /vector-data

sources:
  otlp:
    type: opentelemetry
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

  # The Parquet arm's columns. The same rows, with the fields the queries name
  # lifted out of the map, because a Parquet schema inferred from a free map
  # would carry one field per attribute key the batch happened to see.
  columns:
    type: remap
    inputs: [ shape ]
    source: |
      attrs = object!(.logAttributes)
      . = {
        "body":          string!(.body),
        "ServiceName":   string!(.svc),
        "SeverityText":  string(attrs.SeverityText) ?? "",
        "TimestampSec":  string(attrs.TimestampSec) ?? "0",
        "TimestampNano": string(attrs.TimestampNano) ?? "0",
        "tenx_hash":     string(attrs.tenx_hash) ?? "",
        "svc":           string!(.svc)
      }

sinks:
  cold_json:
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
      codec: json
      except_fields: [ svc ]
    framing:
      method: newline_delimited
    batch:
      max_bytes: 33554432
      timeout_secs: 5

  cold_parquet:
    type: aws_s3
    inputs: [ columns ]
    bucket: $PQ_BUCKET
    region: us-east-1
    endpoint: http://$MINIO:9000
    auth:
      access_key_id: minioadmin
      secret_access_key: minioadmin
    key_prefix: "service={{ svc }}/day=%F/"
    filename_extension: parquet
    compression: none
    encoding:
      codec: json
      except_fields: [ svc ]
    batch_encoding:
      codec: parquet
      schema_mode: auto_infer
      compression:
        algorithm: snappy
    batch:
      max_bytes: 33554432
      timeout_secs: 5
YAML

docker run --rm -v "$BUILD/vector058/vector.yaml":/etc/vector/vector.yaml:ro "$VECTOR_IMAGE" \
  validate --no-environment /etc/vector/vector.yaml > "$BUILD/vector058/validate.out" 2>&1 || true
sed 's/^/  /' "$BUILD/vector058/validate.out" | tail -6

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
t = t.replace("      exporters: [ awss3/cold ]", "      exporters: [ nop ]", 1)
t = t.replace("exporters:\n  otlp/vector:", "exporters:\n  nop:\n  otlp/vector:", 1)
open(dst, "w").write(t)
print("  router config with the Vector fork written")
PY

# ---------------------------------------------------------------------- the run
g_net
say "object store"; g_minio_up
mc "mc mb -p m/$PQ_BUCKET >/dev/null && echo '  bucket $PQ_BUCKET created'"
say "ClickStack"; g_clickstack_up

mkdir -p "$BUILD/policy" "$BUILD/vector-data"
chmod 777 "$BUILD/vector-data"
cp "$BUILD/conf/caps.csv" "$BUILD/conf/actions.csv" "$BUILD/policy/"
touch "$BUILD/policy/caps.csv" "$BUILD/policy/actions.csv"

say "Vector"
docker rm -f -v "$VECTOR" >/dev/null 2>&1 || true
docker run -d --name "$VECTOR" --network "$NET" --memory 1g --cpus 2 \
  -v "$BUILD/vector058/vector.yaml":/etc/vector/vector.yaml:ro \
  -v "$BUILD/vector-data":/vector-data \
  "$VECTOR_IMAGE" --config /etc/vector/vector.yaml >/dev/null
sleep 5
docker logs "$VECTOR" 2>&1 | tail -3 | sed 's/^/  /'

say "receiver"; g_engine_up "$BUILD/policy"
say "collector: read, route, forward to Vector"; g_router_up "$BUILD/conf/router_vector.yaml"
g_wait_settle default.otel_logs 4
g_flush_cold
docker stop "$VECTOR" >/dev/null
sleep 5
docker logs "$VECTOR" > "$BUILD/vector058/vector.log" 2>&1 || true

JSON_OBJECTS="$(g_objects)"
JSON_BYTES="$(g_object_bytes)"
PQ_OBJECTS="$(mc "mc ls -r m/$PQ_BUCKET | wc -l" | tr -d ' \r')"
PQ_BYTES="$(mc "mc du m/$PQ_BUCKET" | awk '{print $1}')"
HOT_ROWS="$(chq "SELECT count() FROM default.otel_logs")"
python3 "$GAPS_HERE/wire_hashes.py" --wire "$BUILD/wire/returned.json" --out "$BUILD/gap2b_wire.json"
echo "  Vector wrote $JSON_OBJECTS JSON objects ($JSON_BYTES) and $PQ_OBJECTS Parquet objects ($PQ_BYTES); hot rows $HOT_ROWS"
[ "$PQ_OBJECTS" != "0" ] || { echo "Vector wrote no Parquet object" >&2; tail -40 "$BUILD/vector058/vector.log" >&2; exit 1; }

say "the JSON arm: the harness's own cold tables, unchanged"
docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"
JSON_ROWS="$(chq "SELECT count() FROM default.otel_logs_coldv")"
echo "  rows readable through the JSON S3 table: $JSON_ROWS"

say "the Parquet arm: an S3 table over what Vector wrote"
# The guard for ClickHouse issue 116888: an S3 table created with an explicit
# schema and use_hive_partitioning before any object exists caches an empty
# listing and every path predicate then returns nothing, for the table's
# lifetime. Objects are already written above, and this asserts it.
g_wait_for_object "$PQ_BUCKET"
docker exec -i "$CS" clickhouse-client --multiquery <<SQL
DROP TABLE IF EXISTS default.otel_logs_coldpq;
CREATE TABLE default.otel_logs_coldpq
(
  body           String,
  ServiceName    String,
  SeverityText   String,
  TimestampSec   String,
  TimestampNano  String,
  tenx_hash      String,
  service        LowCardinality(String),
  day            Date
) ENGINE = S3('http://$MINIO:9000/$PQ_BUCKET/**.parquet', 'minioadmin', 'minioadmin', 'Parquet')
SETTINGS use_hive_partitioning = 1;

DROP VIEW IF EXISTS default.otel_logs_coldpqv;
CREATE VIEW default.otel_logs_coldpqv AS
SELECT toDateTime64(toUInt64OrZero(TimestampSec), 9)          AS Timestamp,
       CAST(service AS LowCardinality(String))                AS ServiceName,
       body                                                   AS Body,
       CAST(SeverityText AS LowCardinality(String))           AS SeverityText,
       map('tenx_hash', tenx_hash)                            AS LogAttributes,
       day                                                    AS day
FROM default.otel_logs_coldpq;

DROP TABLE IF EXISTS default.otel_logs_allpq;
CREATE TABLE default.otel_logs_allpq
(
  Timestamp     DateTime64(9),
  ServiceName   LowCardinality(String),
  Body          String,
  SeverityText  LowCardinality(String),
  LogAttributes Map(String, String),
  day           Date
) ENGINE = Merge(default, '^(otel_logs|otel_logs_coldpqv)\$');
SQL
PQ_ROWS="$(chq "SELECT count() FROM default.otel_logs_coldpq")"
echo "  rows readable through the Parquet S3 table: $PQ_ROWS"

SVC="$(chq "SELECT service FROM default.otel_logs_cold GROUP BY service ORDER BY count() DESC LIMIT 1")"
HASH="$(chq "SELECT LogAttributes['tenx_hash'] FROM default.otel_logs_coldv
             WHERE LogAttributes['tenx_hash'] != '' GROUP BY 1 ORDER BY count() DESC LIMIT 1")"
echo "  service $SVC, hash $HASH"

say "queries, over Vector's JSON objects and over Vector's Parquet objects"
python3 - "$BUILD/gap2b_queries.json" "$SVC" "$HASH" <<'PY'
import json, sys
out, svc, h = sys.argv[1], sys.argv[2], sys.argv[3]
rows = [{"name": "hot only, last 4 hours, count",
         "sql": "SELECT count() FROM default.otel_logs WHERE Timestamp >= now() - INTERVAL 4 HOUR"}]
for label, t in (("Vector json", "default.otel_logs_all"),
                 ("Vector parquet", "default.otel_logs_allpq")):
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
python3 "$GAPS_HERE/measure.py" --container "$CS" --spec "$BUILD/gap2b_queries.json" \
  --out "$BUILD/gap2b_queries_out.json"

# Which Parquet counters this server actually carries. A ProfileEvents key that
# does not exist reads as zero, so the names are checked rather than assumed.
PQ_EVENTS="$(chq "SELECT arrayStringConcat(groupArray(name), ', ') FROM system.events WHERE name LIKE 'Parquet%'")"
echo "  Parquet counters this server has moved: $PQ_EVENTS"

python3 - "$OUT" "$BUILD/gap2b_queries_out.json" "$BUILD/gap2b_wire.json" <<PY
import json, pathlib, sys
out, queries, wire = sys.argv[1:4]
b = pathlib.Path("$BUILD/vector058")
json.dump({
 "gap": "2b",
 "vector_version": "$VECTOR_VERSION",
 "probes": {
   "encoding.codec: parquet": {"accepted": bool($OK_ENCODING),
     "output": (b / "probe-encoding_codec_parquet.out").read_text()[-700:]},
   "batch_encoding.codec: parquet, no encoding": {"accepted": bool($OK_BATCH_ONLY),
     "output": (b / "probe-batch_encoding_only.out").read_text()[-700:]},
   "batch_encoding.codec: parquet with encoding.codec: json": {"accepted": bool($OK_BOTH),
     "output": (b / "probe-batch_encoding_with_encoding.out").read_text()[-700:]},
 },
 "feed_lines": $FEED_LINES,
 "wire": json.load(open(wire)),
 "hot_rows": $HOT_ROWS,
 "json_objects": "$JSON_OBJECTS", "json_bytes": "$JSON_BYTES", "json_rows": $JSON_ROWS,
 "parquet_objects": "$PQ_OBJECTS", "parquet_bytes": "$PQ_BYTES", "parquet_rows": $PQ_ROWS,
 "parquet_counters_present": "$PQ_EVENTS",
 "batch_max_bytes": 33554432,
 "queries": json.load(open(queries)),
}, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
