#!/usr/bin/env bash
#
# Gap 6: does the per-type policy beat a competent collector-only policy on hot
# compute, at equal or better answers?
#
# Three arms, the whole capture each time, on one ClickHouse, with
# `system.query_log` and `system.part_log` truncated before each so insert and
# merge CPU belong to that arm alone:
#
#   a_none       no offload. Every record into the hot table. The receiver is in
#                the path with a policy that regulates nothing, so the arm
#                differs from the others only in what the policy says.
#   b_collector  the policy a competent engineer writes with no 10x: the two
#                chattiest services' INFO and DEBUG lines to the object store,
#                everything else into the hot table. Severity is parsed out of
#                the line by the collector, because these logs carry none. No
#                per-type identity anywhere.
#   c_10x        the per-type policy: a byte cap per type per container, the
#                overflow marked and offloaded.
#
# Per arm: rows and bytes in the hot table, insert plus merge CPU seconds, the
# objects written, and the three questions gap 5 asks. The comparison that
# matters is c against b, not c against a.
#
#   ./gap6_incremental_economics.sh                 all three
#   ./gap6_incremental_economics.sh b_collector     one arm
#
# Environment: as lib.sh.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUT="$RESULTS/gap6.json"

trap g_teardown EXIT
g_require
say "input"; g_input
g_render_harness_conf
g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$JRE_IMAGE" "$EDGE_IMAGE"
g_net

say "object store"; g_minio_up
say "ClickStack"; g_clickstack_up

mkdir -p "$BUILD/policy_none" "$BUILD/policy_10x"
printf 'container,cap\nno-such-container,999999999\n' > "$BUILD/policy_none/caps.csv"
printf 'container,action\nno-such-container,offload\n' > "$BUILD/policy_none/actions.csv"
cp "$BUILD/conf/caps.csv" "$BUILD/conf/actions.csv" "$BUILD/policy_10x/"
touch "$BUILD/policy_none/caps.csv" "$BUILD/policy_none/actions.csv" \
      "$BUILD/policy_10x/caps.csv" "$BUILD/policy_10x/actions.csv"

ARMS=("$@")
[ ${#ARMS[@]} -gt 0 ] || ARMS=(a_none b_collector c_10x)

reset_arm() {
  chq "TRUNCATE TABLE default.otel_logs"
  chq "TRUNCATE TABLE default.counts_by_type"
  chq "DROP TABLE IF EXISTS default.otel_logs_cold SYNC"
  chq "DROP VIEW IF EXISTS default.otel_logs_coldv"
  chq "DROP TABLE IF EXISTS default.otel_logs_all SYNC"
  mc "mc rm -r --force m/$BUCKET >/dev/null 2>&1 || true; mc mb -p m/$BUCKET >/dev/null"
  chq "SYSTEM FLUSH LOGS"
  chq "TRUNCATE TABLE IF EXISTS system.query_log"
  chq "TRUNCATE TABLE IF EXISTS system.part_log"
}

# The collector-only policy needs to know which services are the chattiest. That
# is read off the first arm's hot table, which is every record, so the policy is
# written from the same census an engineer would run in ClickHouse.
write_collector_conf() {
  local top1="$1" top2="$2"
  python3 - "$BUILD/conf/router.yaml" "$BUILD/conf/router_collector.yaml" "$top1" "$top2" \
    "$CS" "$MINIO" "$FEED_NAME" <<'PY'
import sys
src, dst, top1, top2, cs, minio, feed = sys.argv[1:8]
# Written from the harness route, with the receiver taken out of it: the
# collector reads the file, parses a severity out of the line, and routes on
# service and severity alone. Nothing marks a type, so nothing can be routed by
# one.
conf = f"""# The collector-only policy: no 10x anywhere in the route. The collector reads
# the capture, parses a severity out of the line the way an engineer would when
# the logs carry none, and sends the two chattiest services' INFO and DEBUG to
# the object store. Everything else goes to ClickStack's own OTLP endpoint.

extensions:
  json_log_encoding/cold:
    mode: body_with_inline_attributes

receivers:
  filelog:
    include: [ /data/{feed} ]
    start_at: beginning
    max_log_size: 4MiB
    operators:
      - type: json_parser
        parse_from: body
      - type: move
        from: attributes.log
        to: body
      - type: copy
        from: attributes.kubernetes.container_name
        to: attributes.k8s_container
      - type: copy
        from: attributes.kubernetes.namespace_name
        to: attributes.k8s_namespace
      - type: copy
        from: attributes.kubernetes.container_name
        to: resource["service.name"]

processors:
  transform/stamp:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(log.time_unix_nano, log.observed_time_unix_nano) where log.time_unix_nano == 0
  # The severity an engineer would parse. The capture's lines carry the level in
  # the text, so the collector reads it out of the text.
  transform/severity:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(log.severity_text, "ERROR") where IsMatch(log.body, "(?i)(\\\\bERROR\\\\b|\\\\bERR\\\\b|\\\\bFATAL\\\\b)")
          - set(log.severity_text, "WARN")  where log.severity_text == "" and IsMatch(log.body, "(?i)\\\\bWARN(ING)?\\\\b")
          - set(log.severity_text, "INFO")  where log.severity_text == "" and IsMatch(log.body, "(?i)\\\\bINFO\\\\b")
          - set(log.severity_text, "DEBUG") where log.severity_text == "" and IsMatch(log.body, "(?i)(\\\\bDEBUG\\\\b|\\\\bTRACE\\\\b)")
          - set(log.severity_text, "INFO")  where log.severity_text == ""
  transform/cold:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(log.attributes["ServiceName"], resource.attributes["service.name"])
          - set(log.attributes["SeverityText"], log.severity_text)
          - set(log.attributes["TimestampNano"], UnixNano(log.time))
          - set(log.attributes["TimestampSec"], UnixSeconds(log.time))
      - context: resource
        statements:
          - set(resource.attributes["s3.prefix"], Concat(["service=", resource.attributes["service.name"]], ""))
  batch/cold:
    send_batch_size: 5000
    timeout: 5s

exporters:
  otlp/clickstack:
    endpoint: {cs}:4317
    tls:
      insecure: true
    headers:
      authorization: ${{env:HDX_API_KEY}}
  awss3/cold:
    s3uploader:
      region: us-east-1
      s3_bucket: coldlogs
      s3_prefix: cold
      s3_partition_format: 'day=%Y-%m-%d'
      endpoint: http://{minio}:9000
      s3_force_path_style: true
      disable_ssl: true
      compression: none
    encoding: json_log_encoding/cold
    encoding_file_extension: json
    resource_attrs_to_s3:
      s3_prefix: s3.prefix

connectors:
  routing/policy:
    default_pipelines: [ logs/hot ]
    error_mode: ignore
    table:
      - context: log
        condition: resource.attributes["service.name"] == "{top1}" and (log.severity_text == "INFO" or log.severity_text == "DEBUG")
        pipelines: [ logs/cold ]
      - context: log
        condition: resource.attributes["service.name"] == "{top2}" and (log.severity_text == "INFO" or log.severity_text == "DEBUG")
        pipelines: [ logs/cold ]

service:
  extensions: [ json_log_encoding/cold ]
  telemetry:
    logs:
      level: warn
    metrics:
      level: basic
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
  pipelines:
    logs/in:
      receivers: [ filelog ]
      processors: [ transform/stamp, transform/severity ]
      exporters: [ routing/policy ]
    logs/hot:
      receivers: [ routing/policy ]
      exporters: [ otlp/clickstack ]
    logs/cold:
      receivers: [ routing/policy ]
      processors: [ transform/cold, batch/cold ]
      exporters: [ awss3/cold ]
"""
open(dst, "w").write(conf)
print(f"  collector-only policy written: {top1} and {top2}, INFO and DEBUG to the object store")
PY
}

measure_arm() {
  local arm="$1" has_cold="$2"
  chq "SYSTEM FLUSH LOGS"
  local rows bytes parts insert_cpu merge_cpu inserts merges objects cold_rows
  rows="$(chq "SELECT count() FROM default.otel_logs")"
  bytes="$(chq "SELECT sum(bytes_on_disk) FROM system.parts
                WHERE database='default' AND table='otel_logs' AND active")"
  parts="$(chq "SELECT count() FROM system.parts
                WHERE database='default' AND table='otel_logs' AND active")"
  insert_cpu="$(chq "SELECT sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds'])
                     FROM system.query_log
                     WHERE type='QueryFinish' AND query_kind='Insert'
                       AND (has(tables, 'default.otel_logs') OR position(query, 'otel_logs') > 0)")"
  inserts="$(chq "SELECT count() FROM system.query_log
                  WHERE type='QueryFinish' AND query_kind='Insert'
                       AND (has(tables, 'default.otel_logs') OR position(query, 'otel_logs') > 0)")"
  merge_cpu="$(chq "SELECT sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds'])
                    FROM system.part_log
                    WHERE database='default' AND table='otel_logs' AND event_type='MergeParts'")"
  merges="$(chq "SELECT count() FROM system.part_log
                 WHERE database='default' AND table='otel_logs' AND event_type='MergeParts'")"
  local counts_cpu
  counts_cpu="$(chq "SELECT sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds'])
                     FROM system.part_log
                     WHERE database='default' AND table='counts_by_type' AND event_type='MergeParts'")"
  objects="$(g_objects)"
  cold_rows=0
  if [ "$has_cold" = "1" ]; then
    cold_rows="$(chq "SELECT count() FROM default.otel_logs_coldv" 2>/dev/null || echo 0)"
  fi
  python3 - "$BUILD/gap6_$arm.json" <<PY
import json
json.dump({"arm": "$arm", "hot_rows": ${rows:-0}, "hot_bytes": ${bytes:-0}, "hot_parts": ${parts:-0},
           "insert_cpu_us": ${insert_cpu:-0}, "inserts": ${inserts:-0},
           "merge_cpu_us": ${merge_cpu:-0}, "merges": ${merges:-0},
           "counts_merge_cpu_us": ${counts_cpu:-0},
           "objects": "$objects", "cold_rows": ${cold_rows:-0}},
          open("$BUILD/gap6_$arm.json", "w"), indent=1)
PY
  printf '  %s: hot %s rows, %s bytes, insert %s us, merge %s us, objects %s, cold %s\n' \
    "$arm" "$rows" "${bytes:-0}" "${insert_cpu:-0}" "${merge_cpu:-0}" "$objects" "$cold_rows"
}

# The two chattiest services come from the first arm. A run of one arm on its
# own takes them from the environment instead.
TOP1="${TOP1:-}"; TOP2="${TOP2:-}"
for arm in "${ARMS[@]}"; do
  say "arm $arm"
  reset_arm
  case "$arm" in
    a_none)
      g_engine_up "$BUILD/policy_none"
      g_router_up "$BUILD/conf/router.yaml"
      g_wait_settle default.otel_logs 4
      g_flush_cold
      TOP1="$(chq "SELECT ServiceName FROM default.otel_logs WHERE ServiceName != ''
                   GROUP BY ServiceName ORDER BY count() DESC LIMIT 1")"
      TOP2="$(chq "SELECT ServiceName FROM default.otel_logs WHERE ServiceName != ''
                   GROUP BY ServiceName ORDER BY count() DESC LIMIT 1 OFFSET 1")"
      echo "  chattiest services: $TOP1, $TOP2"
      chq "DROP TABLE IF EXISTS gaps.hot_none SYNC"
      chq "CREATE DATABASE IF NOT EXISTS gaps"
      chq "CREATE TABLE gaps.hot_none ENGINE = MergeTree ORDER BY (ServiceName, Timestamp) AS
           SELECT Timestamp, ServiceName, Body, SeverityText, LogAttributes FROM default.otel_logs"
      measure_arm "$arm" 0
      ;;
    b_collector)
      [ -n "$TOP1" ] || { TOP1="$(chq "SELECT ServiceName FROM gaps.hot_none WHERE ServiceName != ''
                                       GROUP BY ServiceName ORDER BY count() DESC LIMIT 1")"; }
      [ -n "$TOP2" ] || { TOP2="$(chq "SELECT ServiceName FROM gaps.hot_none WHERE ServiceName != ''
                                       GROUP BY ServiceName ORDER BY count() DESC LIMIT 1 OFFSET 1")"; }
      write_collector_conf "$TOP1" "$TOP2"
      docker rm -f -v "$ENGINE" >/dev/null 2>&1 || true
      g_router_up "$BUILD/conf/router_collector.yaml"
      g_wait_settle default.otel_logs 4
      g_flush_cold
      docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"
      measure_arm "$arm" 1
      ;;
    c_10x)
      g_engine_up "$BUILD/policy_10x"
      g_router_up "$BUILD/conf/router.yaml"
      g_wait_settle default.otel_logs 4
      g_flush_cold
      docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"
      measure_arm "$arm" 1
      g_export_cold "gap6 c_10x"
      ;;
  esac

  # The three questions, on this arm's surfaces.
  if [ -z "${HASH:-}" ]; then
    HASH="$(chq "SELECT LogAttributes['tenx_hash'] FROM default.otel_logs
                 WHERE LogAttributes['tenx_hash'] != '' GROUP BY 1 ORDER BY count() DESC LIMIT 1" 2>/dev/null || true)"
  fi
  [ -n "${WORD:-}" ] || WORD=snapshot
  python3 - "$BUILD/gap6_${arm}_queries.json" "${HASH:-}" "$WORD" "$arm" <<'PY'
import json, sys
out, h, word, arm = sys.argv[1:5]
tables = [("hot table", "default.otel_logs")]
if arm != "a_none":
    tables.append(("merge table", "default.otel_logs_all"))
rows = []
for label, t in tables:
    rows.append({"name": f"Q1 count all by service, last 4 hours: {label}",
                 "sql": f"SELECT ServiceName, count() AS c FROM {t} "
                        "WHERE Timestamp >= now() - INTERVAL 4 HOUR GROUP BY ServiceName "
                        "ORDER BY c DESC, ServiceName LIMIT 8"})
    rows.append({"name": f"Q3 text search for '{word}': {label}",
                 "sql": f"SELECT count() FROM {t} WHERE positionCaseInsensitive(Body, '{word}') > 0"})
    if h:
        rows.append({"name": f"Q2 count of one type by hash: {label}",
                     "sql": f"SELECT count() FROM {t} WHERE LogAttributes['tenx_hash'] = '{h}'"})
rows.append({"name": "Q1 count all by service, last 4 hours: counts table",
             "sql": "SELECT ServiceName, sum(cnt) AS c FROM default.counts_by_type "
                    "WHERE Minute >= now() - INTERVAL 4 HOUR GROUP BY ServiceName "
                    "ORDER BY c DESC, ServiceName LIMIT 8"})
json.dump(rows, open(out, "w"), indent=1)
PY
  python3 "$GAPS_HERE/measure.py" --container "$CS" --spec "$BUILD/gap6_${arm}_queries.json" \
    --out "$BUILD/gap6_${arm}_queries_out.json"
done

python3 - "$OUT" "$BUILD" "$FEED_LINES" "$TOP1" "$TOP2" "${HASH:-}" "$WORD" "${ARMS[@]}" <<'PY'
import json, pathlib, sys
out, build, lines, top1, top2, h, word = sys.argv[1:8]
build = pathlib.Path(build)
arms = sys.argv[8:]
payload = {"gap": 6, "feed_lines": int(lines), "chattiest": [top1, top2],
           "type_hash": h, "word": word, "arms": []}
for a in arms:
    entry = json.loads((build / f"gap6_{a}.json").read_text())
    qp = build / f"gap6_{a}_queries_out.json"
    entry["queries"] = json.loads(qp.read_text()) if qp.exists() else []
    payload["arms"].append(entry)
json.dump(payload, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
