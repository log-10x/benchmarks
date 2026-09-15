# ClickStack end to end, 2026-09-15

One run of `run.sh`: the released capture through a collector into the 10x
receiver, the marked slice into an object store, everything else into
ClickStack's own ClickHouse exporter, both sides read back as one table.

## Components

| Part | Image | Digest |
|---|---|---|
| clickstack | `clickhouse/clickstack-all-in-one:2.38.0` | `sha256:7b3bd9eec4e61aded56f705af7ddb2e8e49c54098d21aaaa7de6fde4d7c1f267` |
| engine | `ghcr.io/log-10x/edge-10x@sha256:14357d8d570cb36ba6ca254802a1b8eedb11d8acf6916a936893f8e3babb41f4` | `sha256:14357d8d570cb36ba6ca254802a1b8eedb11d8acf6916a936893f8e3babb41f4` |
| collector | `otel/opentelemetry-collector-contrib:0.160.0` | `sha256:799dc6cf12c96192af37b5bdba804da8c10b3bc563b43cb90c3f3c58d9572ad6` |
| minio | `quay.io/minio/minio:latest` | `sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` |

ClickHouse 26.5.7.64. Input: `otel-sample-200mb.log` sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`, first 50000 lines.

ClickStack's own collector build reports itself as `0.155.0`.
The harness needs these components; the ones its build does not carry are why
a second, stock contrib collector runs as the routing hop.

| Component | Kind | Needed for | In ClickStack's collector |
|---|---|---|---|
| `file_log` | receiver | read the capture | yes |
| `otlp` | receiver | take the receiver's return path | yes |
| `routing` | connector | split the stream on routeState | yes |
| `clickhouse` | exporter | insert the rows that stayed | yes |
| `awss3` | exporter | write the rows that left | NO |
| `json_log_encoding` | extension | encode the offloaded object | NO |
| `otlp_encoding` | extension | the alternative encoding | NO |
| `groupbyattrs` | processor | lift the service back onto the resource | yes |
| `transform` | processor | stamp the record time | yes |

## What arrived on the wire

Records returned by the receiver: **37536**.

| Field on the returned record | Records carrying it |
|---|---:|
| `log.file.name` | 37536 |
| `tenx_tag` | 37536 |
| `stream` | 37536 |
| `k8s_container` | 37536 |
| `docker` | 37536 |
| `kubernetes` | 37536 |
| `k8s_namespace` | 37536 |
| `routeState` | 37536 |
| `tenx_hash` | 37486 |
| `message_pattern` | 37469 |

| Route marked | Records |
|---|---:|
| `offload` | 24526 |
| `pass` | 13010 |

One returned record, its attributes flattened and the fields this
harness is about listed first:

```json
{
 "timeUnixNano": "1789478116109282352",
 "body": "[2025-10-01 20:34:05,556] INFO [ProducerStateManager partition=__cluster_metadata-0] Wrote producer snapshot at offset 2583 with 0 producer ids in 0 ms. (org.apache.kafka.storage.internals.log.ProducerStateManager)",
 "attributes": {
  "routeState": "offload",
  "tenx_hash": "5dKRMhpQfK4",
  "message_pattern": "partition_cluster_Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager",
  "k8s_container": "kafka",
  "log.file.name": "slice.log",
  "kubernetes": {
   "container_name": "kafka",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "pod_ip": "192.168.37.206",
   "namespace_name": "default",
   "host": "ip-192-168-42-205.ec2.internal",
   "labels": {
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka",
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569"
   }
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "stream": "stdout",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "k8s_namespace": "default"
 }
}
```

## Where the rows went

| Service | Hot rows |
|---|---:|
| opentelemetry-collector | 3381 |
| kafka | 2206 |
| grafana | 1778 |
| ad | 1551 |
| cart | 1058 |
| recommendation | 750 |
| frontend | 501 |
| fluentd-10x | 372 |
| opensearch | 327 |
| kube-proxy | 239 |

| Service | Offloaded rows |
|---|---:|
| opentelemetry-collector | 16856 |
| kafka | 4522 |
| cart | 3148 |

| Object | Rows |
|---|---:|
| `coldlogs/service=cart/day=2026-09-15/logs_108588021.json` | 1991 |
| `coldlogs/service=cart/day=2026-09-15/logs_212942478.json` | 823 |
| `coldlogs/service=cart/day=2026-09-15/logs_885915541.json` | 1 |
| `coldlogs/service=cart/day=2026-09-15/logs_983687260.json` | 333 |
| `coldlogs/service=kafka/day=2026-09-15/logs_306714977.json` | 1 |
| `coldlogs/service=kafka/day=2026-09-15/logs_374632464.json` | 2524 |
| `coldlogs/service=kafka/day=2026-09-15/logs_482827663.json` | 1425 |
| `coldlogs/service=kafka/day=2026-09-15/logs_824770237.json` | 572 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-15/logs_299611851.json` | 1 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-15/logs_417650440.json` | 564 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-15/logs_835250109.json` | 5059 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-15/logs_840422240.json` | 3383 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-15/logs_843091333.json` | 2805 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-15/logs_951485650.json` | 5044 |

## Queries

Every row is a cold cache: the filesystem, mark and uncompressed caches are
dropped before each query. The last two columns are the same query run again
straight after, warm.

| Query | Rows read | Bytes read | S3 GET | S3 LIST | ms | ms again | S3 GET again |
|---|---:|---:|---:|---:|---:|---:|---:|
| hot only, last hour, count | 12012 | 96104 | 0 | 0 | 8 | 8 | 0 |
| merge, service opentelemetry-collector, last hour | 25793 | 28741648 | 6 | 1 | 77 | 102 | 6 |
| merge, service opentelemetry-collector and one day | 25793 | 28688266 | 6 | 1 | 43 | 74 | 6 |
| merge, time only, the shape HyperDX sends | 37536 | 39586778 | 14 | 1 | 118 | 103 | 14 |
| merge, text search, no other filter | 37536 | 42621755 | 14 | 1 | 99 | 76 | 14 |
| merge, one pattern text, no time filter | 40075 | 40483054 | 14 | 1 | 136 | 132 | 14 |
| merge, one pattern hash, hot and cold side by side | 37536 | 39676012 | 14 | 1 | 123 | 244 | 14 |
| counts table, count all by service, last hour | 2539 | 33776 | 0 | 0 | 6 | 6 | 0 |
| cold only, service opentelemetry-collector and one day | 16856 | 28660670 | 6 | 1 | 43 | 50 | 6 |

## Counts per type

| Source | Records counted | Distinct pattern hashes |
|---|---:|---:|
| cold | 24526 | 21 |
| hot | 13010 | 2495 |

## Lossless check

| Measure | Count |
|---|---:|
| Records the receiver returned | 37536 |
| Rows in the hot table | 13010 |
| Rows in the offloaded objects | 24526 |
| Hot plus cold | 37536 |
| Gap | 0 |
| Distinct pattern hashes on the wire | 2495 |
| Distinct pattern hashes stored | 2495 |


## What the earlier run reported and this run does not

**Every returned record carries the marks.** 37536 of 37536 came back with attributes, messages that are themselves JSON objects with a `body` key included, so every record is routable. The 2026-09-14 run returned 19,436 of 37,519 with no attributes at all.

**The service arrives in one place.** The OTLP resource carried `service.name` on 37536 records and a log attribute carried it on 0, so the `groupbyattrs` hop had nothing to lift. The hop stays in the config: a record that carries the service only as an attribute lands under a prefix of `service=<nil>` without it.

**A returned record carries the marks and a record time.** 37536 of 37536 came back with `timeUnixNano` set, the marked records included. The 2026-09-14 run set it only on the unmarked ones.

## What did not work, or was skipped

**The route arrives more often than the pattern does.** 37536 records came back carrying a route, 37486 carrying the pattern hash and 37469 carrying the pattern text. A record that is routed but unnamed can be shipped and cannot be counted per type.

**The offload encoding drops everything but the body and the attributes.** The `jsonlogencodingextension` in `body_with_inline_attributes` mode writes `{"body": ..., "logAttributes": {...}}` and nothing else: no record time, no resource attributes, no severity. The harness copies the service, the severity and the record time into log attributes before the write, or the cold rows have no timestamp and no service at all. `otlp_json` was not used; it keeps all three but puts every record inside a nested OTLP envelope that needs unpicking in SQL.

**A repeated count over the same objects costs nothing, which would have flattered the table.** ClickHouse keeps a per-object row count and answers a second `count()` over the same objects from it, with no object-store request. That is a real saving for a dashboard that asks the same question twice, and it would also have hidden what the first ask costs, so the query table is measured with `use_cache_for_count_from_files = 0` and a dropped cache before every row.

**The object path carries the write time, not the record time.** `s3_partition_format` is evaluated when the object is uploaded, so a run writes one day partition whatever the records say. Pruning across many days and many objects is not measured here.

**ClickStack's `otel_logs` has no day column**, so a day predicate over the merge table would exclude every hot row. The harness adds `day Date MATERIALIZED toDate(Timestamp)` to the shipped table. That is a change to ClickStack's schema and it is the harness that makes it.

**The S3 table engine rejects ALIAS columns**, so the cold table carries the JSON's own column names and a view renames them to ClickStack's. The Merge table reads the view, not the S3 table.

**The counts table is fed twice, not once.** The materialized view covers the rows that are inserted into ClickHouse. The offloaded rows never pass through an insert, so their counts are added by one `INSERT ... SELECT` over the S3 table after the run. A deployment would run that on a schedule or feed the cold side from the receiver's own metrics; the receiver's Prometheus endpoint is scraped here and its counters are in `results.json`, but the counts table is not fed from it.

**ClickStack's collector build is missing `awss3`, `json_log_encoding`, `otlp_encoding`**, so the route and the offload write run in a second, stock `opentelemetry-collector-contrib` container. The rows that stay go back to ClickStack's own OTLP endpoint and are inserted by ClickStack's own ClickHouse exporter.

**HyperDX got the merge table as a second source over its API** (HTTP 200), so no click is needed. The hot table stays the default source: a query against the merge table pays object-store requests and a query against the hot table pays none.

**Skipped.** No alert is defined or fired, so nothing here says alerts are unchanged. No compute term, no bill and no autoscaler, so nothing here is a cost. No Retriever, so value-level fetch-back is not exercised. The query list is written here rather than taken from an estate's own query log.

## The configs, as they ran

The collector, both pipelines:

```yaml
# The routing hop. ClickStack's own collector build carries the routing
# connector but no S3 exporter and no encoding extension, so the route and the
# offload write run in a second, stock opentelemetry-collector-contrib
# container. Everything that is not marked `offload` goes back to ClickStack's
# shipped OTLP endpoint and is inserted by ClickStack's own ClickHouse exporter.

extensions:
  json_log_encoding/cold:
    mode: body_with_inline_attributes

receivers:
  # The released capture, one JSON record per line: the envelope is Fluent's,
  # the log line is the `log` value.
  filelog:
    include: [ /data/slice.log ]
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

  # The return path from the receiver.
  otlp/back:
    protocols:
      grpc:
        endpoint: 0.0.0.0:24225
        max_recv_msg_size_mib: 32

processors:
  # The capture's envelope carries no timestamp, so records arrive with none and
  # would land on 1970-01-01. Ingest time is used instead, on both routes.
  transform/stamp:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(log.time_unix_nano, log.observed_time_unix_nano) where log.time_unix_nano == 0

  # Part of the returned stream carries the service as a log attribute rather
  # than on the OTLP resource. groupbyattrs lifts it back onto the resource so
  # ServiceName is set on the ClickHouse side and the offload path can key the
  # object prefix on it.
  transform/service:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(log.attributes["service.name"], log.attributes["k8s_container"]) where log.attributes["service.name"] == nil and log.attributes["k8s_container"] != nil
  groupbyattrs/service:
    keys: [ service.name ]

  # The offloaded object carries body and log attributes only, so the service,
  # the record time and the severity are copied into attributes before the
  # write or they do not survive the encoding.
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
  otlp/engine:
    endpoint: cse-engine:4317
    tls:
      insecure: true
  otlp/clickstack:
    endpoint: cse-clickstack:4317
    tls:
      insecure: true
    headers:
      authorization: ${env:HDX_API_KEY}
  awss3/cold:
    s3uploader:
      region: us-east-1
      s3_bucket: coldlogs
      s3_prefix: cold
      s3_partition_format: 'day=%Y-%m-%d'
      endpoint: http://cse-minio:9000
      s3_force_path_style: true
      disable_ssl: true
      compression: none
    encoding: json_log_encoding/cold
    encoding_file_extension: json
    resource_attrs_to_s3:
      s3_prefix: s3.prefix
  # The measurement tap: every record the receiver returned, before the route.
  # It is what the lossless check counts against, and it is not part of the
  # design being tested.
  file/wire:
    path: /wire/returned.json

connectors:
  routing/state:
    default_pipelines: [ logs/hot ]
    error_mode: ignore
    table:
      - context: log
        condition: attributes["routeState"] == "offload"
        pipelines: [ logs/cold ]

service:
  extensions: [ json_log_encoding/cold ]
  telemetry:
    logs:
      level: warn
  pipelines:
    logs/in:
      receivers: [ filelog ]
      exporters: [ otlp/engine ]
    # The measurement tap reads the same receiver as logs/back but runs no
    # processor, so the file holds the records as the receiver returned them.
    logs/wire:
      receivers: [ otlp/back ]
      exporters: [ file/wire ]
    logs/back:
      receivers: [ otlp/back ]
      processors: [ transform/stamp, transform/service, groupbyattrs/service ]
      exporters: [ routing/state ]
    logs/hot:
      receivers: [ routing/state ]
      exporters: [ otlp/clickstack ]
    logs/cold:
      receivers: [ routing/state ]
      processors: [ transform/cold, batch/cold ]
      exporters: [ awss3/cold ]
```

The per-service policy the receiver read:

```
caps.csv
container,cap
opentelemetry-collector,200000
kafka,100000
cart,50000

actions.csv
container,action
opentelemetry-collector,offload
kafka,offload
cart,offload
```

The counts table, created before any data flowed:

```sql
-- Counts per type, fed from the hot inserts. Created BEFORE any data flows, so
-- the materialized view sees every hot insert. The cold rows never pass through
-- an insert into ClickHouse, so their counts are added after the run by the
-- INSERT ... SELECT in schema_cold.sql.
CREATE TABLE IF NOT EXISTS default.counts_by_type
(
  Minute DateTime,
  ServiceName LowCardinality(String),
  tenx_hash String,
  message_pattern String,
  source LowCardinality(String),
  cnt UInt64
) ENGINE = SummingMergeTree(cnt)
ORDER BY (Minute, ServiceName, tenx_hash, message_pattern, source);

CREATE MATERIALIZED VIEW IF NOT EXISTS default.counts_by_type_hot_mv
TO default.counts_by_type (Minute DateTime, ServiceName LowCardinality(String), tenx_hash String, message_pattern String, source LowCardinality(String), cnt UInt64) AS
SELECT toStartOfMinute(Timestamp)          AS Minute,
       ServiceName,
       LogAttributes['tenx_hash']          AS tenx_hash,
       LogAttributes['message_pattern']    AS message_pattern,
       'hot'                               AS source,
       count()                             AS cnt
FROM default.otel_logs
GROUP BY Minute, ServiceName, tenx_hash, message_pattern;
```

The offloaded objects, the rename and the merge table:

```sql
-- The offloaded objects, read in place.
--
-- The S3 engine takes the column names from the JSON the collector wrote:
-- the jsonlogencoding extension in body_with_inline_attributes mode writes
-- {"body": ..., "logAttributes": {...}} per record, as one JSON array per
-- object. `service` and `day` are not in the file at all; they come from the
-- object path, which is why use_hive_partitioning is on.
DROP TABLE IF EXISTS default.otel_logs_cold;
CREATE TABLE default.otel_logs_cold
(
  body           String,
  logAttributes  Map(String, String),
  service        LowCardinality(String),
  day            Date
) ENGINE = S3('http://cse-minio:9000/coldlogs/**.json', 'minioadmin', 'minioadmin', 'JSONEachRow')
SETTINGS use_hive_partitioning = 1;

-- The S3 engine rejects ALIAS columns, so the rename to the ClickStack column
-- names is a view. The Merge table below reads the view, not the S3 table.
DROP VIEW IF EXISTS default.otel_logs_coldv;
CREATE VIEW default.otel_logs_coldv AS
SELECT toDateTime64(toUInt64OrZero(logAttributes['TimestampSec']), 9) AS Timestamp,
       CAST(service AS LowCardinality(String))                        AS ServiceName,
       body                                                           AS Body,
       CAST(logAttributes['SeverityText'] AS LowCardinality(String))  AS SeverityText,
       logAttributes                                                  AS LogAttributes,
       day                                                            AS day
FROM default.otel_logs_cold;

-- Hot and cold as one table. `_table` names the side a row came from.
DROP TABLE IF EXISTS default.otel_logs_all;
CREATE TABLE default.otel_logs_all
(
  Timestamp     DateTime64(9),
  ServiceName   LowCardinality(String),
  Body          String,
  SeverityText  LowCardinality(String),
  LogAttributes Map(String, String),
  day           Date
) ENGINE = Merge(default, '^(otel_logs|otel_logs_coldv)$');

-- The cold side of the counts table, one pass over the objects.
INSERT INTO default.counts_by_type (Minute, ServiceName, tenx_hash, message_pattern, source, cnt)
SELECT toStartOfMinute(Timestamp)       AS Minute,
       ServiceName,
       LogAttributes['tenx_hash']       AS tenx_hash,
       LogAttributes['message_pattern'] AS message_pattern,
       'cold'                           AS source,
       count()                          AS cnt
FROM default.otel_logs_coldv
GROUP BY Minute, ServiceName, tenx_hash, message_pattern;
```

The engine's own config is the tree inside the pinned image with the four
edits `patch_engine_config.py` makes, each of which fails the run if the
shipped text has moved: the OpenTelemetry Collector forwarder input and the
Prometheus scrape output enabled, the regulator's warmup and baseline count
set to zero for a short run, and the pattern text added to the `fullText`
splice list beside the pattern hash and the route. The shipped expression
splices the hash and the route only.

