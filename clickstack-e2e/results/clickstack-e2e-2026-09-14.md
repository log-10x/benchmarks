# ClickStack end to end, 2026-09-14

One run of `run.sh`: the released capture through a collector into the 10x
receiver, the marked slice into an object store, everything else into
ClickStack's own ClickHouse exporter, both sides read back as one table.

## Components

| Part | Image | Digest |
|---|---|---|
| clickstack | `clickhouse/clickstack-all-in-one:2.38.0` | `sha256:7b3bd9eec4e61aded56f705af7ddb2e8e49c54098d21aaaa7de6fde4d7c1f267` |
| engine | `ghcr.io/log-10x/edge-10x:latest` | `sha256:4d6f596ed0c943d282a63def579a13d877e8e8dda252d4ee254566f656ea3f0d` |
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

Records returned by the receiver: **37519**.

| Field on the returned record | Records carrying it |
|---|---:|
| `k8s_namespace` | 18083 |
| `log.file.name` | 18083 |
| `stream` | 18083 |
| `k8s_container` | 18083 |
| `docker` | 18083 |
| `kubernetes` | 18083 |
| `tenx_tag` | 18083 |
| `routeState` | 18083 |
| `tenx_hash` | 18051 |
| `message_pattern` | 18034 |
| `service.name` | 2253 |
| `taenx_resource_keys` | 2070 |
| `_tes` | 39 |
| `_eys` | 17 |
| `_ts` | 2 |
| `tagnx_resource_keys` | 2 |
| `eys` | 1 |
| `_teys` | 1 |
| `_tens` | 1 |

| Route marked | Records |
|---|---:|
| `(no routeState)` | 19436 |
| `pass` | 10253 |
| `offload` | 7830 |

One returned record, its attributes flattened and the fields this
harness is about listed first:

```json
{
 "timeUnixNano": null,
 "body": "[2025-10-01 20:34:05,556] INFO [ProducerStateManager partition=__cluster_metadata-0] Wrote producer snapshot at offset 2583 with 0 producer ids in 0 ms. (org.apache.kafka.storage.internals.log.ProducerStateManager)",
 "attributes": {
  "routeState": "offload",
  "tenx_hash": "5dKRMhpQfK4",
  "message_pattern": "partition_cluster_Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager",
  "k8s_container": "kafka",
  "kubernetes": {
   "namespace_name": "default",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "host": "ip-192-168-42-205.ec2.internal",
   "labels": {
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka",
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569"
   },
   "container_name": "kafka",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "pod_ip": "192.168.37.206"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "k8s_namespace": "default",
  "log.file.name": "slice.log",
  "stream": "stdout",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  }
 }
}
```

## Where the rows went

| Service | Hot rows |
|---|---:|
| (none) | 19436 |
| kafka | 2228 |
| grafana | 1750 |
| ad | 1551 |
| opentelemetry-collector | 947 |
| cart | 886 |
| recommendation | 750 |
| frontend | 501 |
| fluentd-10x | 371 |
| opensearch | 314 |

| Service | Offloaded rows |
|---|---:|
| kafka | 4500 |
| cart | 3320 |
| opentelemetry-collector | 10 |

| Object | Rows |
|---|---:|
| `coldlogs/service=cart/day=2026-09-14/logs_122374753.json` | 1695 |
| `coldlogs/service=cart/day=2026-09-14/logs_659607350.json` | 730 |
| `coldlogs/service=cart/day=2026-09-14/logs_778176706.json` | 410 |
| `coldlogs/service=cart/day=2026-09-14/logs_807897378.json` | 484 |
| `coldlogs/service=cart/day=2026-09-14/logs_934176245.json` | 1 |
| `coldlogs/service=kafka/day=2026-09-14/logs_360752432.json` | 1 |
| `coldlogs/service=kafka/day=2026-09-14/logs_455650303.json` | 1820 |
| `coldlogs/service=kafka/day=2026-09-14/logs_581273049.json` | 1237 |
| `coldlogs/service=kafka/day=2026-09-14/logs_594098964.json` | 12 |
| `coldlogs/service=kafka/day=2026-09-14/logs_677517601.json` | 790 |
| `coldlogs/service=kafka/day=2026-09-14/logs_708085035.json` | 640 |
| `coldlogs/service=opentelemetry-collector/day=2026-09-14/logs_530750926.json` | 10 |

## Queries

Every row is a cold cache: the filesystem, mark and uncompressed caches are
dropped before each query. The last two columns are the same query run again
straight after, warm.

| Query | Rows read | Bytes read | S3 GET | S3 LIST | ms | ms again | S3 GET again |
|---|---:|---:|---:|---:|---:|---:|---:|
| hot only, last hour, count | 18260 | 146088 | 0 | 0 | 8 | 8 | 0 |
| merge, service kafka, last hour | 15548 | 6676533 | 6 | 1 | 39 | 41 | 6 |
| merge, service kafka and one day | 15548 | 6610493 | 6 | 1 | 27 | 26 | 6 |
| merge, time only, the shape HyperDX sends | 37519 | 11310291 | 12 | 1 | 52 | 56 | 12 |
| merge, text search, no other filter | 37519 | 44283961 | 12 | 1 | 68 | 50 | 12 |
| merge, one pattern text, no time filter | 28640 | 12261018 | 12 | 1 | 74 | 70 | 12 |
| merge, one pattern hash, hot and cold side by side | 26089 | 11252548 | 12 | 1 | 66 | 86 | 12 |
| counts table, count all by service, last hour | 2551 | 34611 | 0 | 0 | 10 | 8 | 0 |
| cold only, service kafka and one day | 4500 | 6576725 | 6 | 1 | 22 | 19 | 6 |

## Counts per type

| Source | Records counted | Distinct pattern hashes |
|---|---:|---:|
| cold | 7830 | 17 |
| hot | 29689 | 2416 |

## Lossless check

| Measure | Count |
|---|---:|
| Records the receiver returned | 37519 |
| Rows in the hot table | 29689 |
| Rows in the offloaded objects | 7830 |
| Hot plus cold | 37519 |
| Gap | 0 |
| Distinct pattern hashes on the wire | 2416 |
| Distinct pattern hashes stored | 2416 |


## What did not work, or was skipped

**The marker does not survive a message that is itself JSON with a `body` key.** 19436 of 37519 returned records came back with no attributes at all: no `routeState`, no pattern hash, no pattern text, and an empty OTLP resource. Every one of them has a message that is itself a JSON object whose first key is `body`, which is the name the OpenTelemetry Collector forwarder input gives its message field. The router cannot route what carries no mark, so every one of them took the default route into the hot table. Nothing was lost and nothing could be offloaded. The run exits 0 and logs no error.

**The service arrives in two different places.** Of the records that did carry fields, the OTLP resource carried `service.name` on 15830 and a log attribute carried it on 2253. The harness lifts the attribute back onto the resource with the `groupbyattrs` processor; without that step the offloaded objects land under a prefix of `service=<nil>` and the hot rows have an empty `ServiceName`.

**The route arrives more often than the pattern does.** 18083 records came back carrying a route, 18051 carrying the pattern hash and 18034 carrying the pattern text. A record that is routed but unnamed can be shipped and cannot be counted per type.

**Field names arrive corrupted.** Beside the fields the config asks for, the returned records carry 8 names nothing configured: `taenx_resource_keys` (2070), `_tes` (39), `_eys` (17), `_ts` (2), `tagnx_resource_keys` (2), `eys` (1), `_teys` (1), `_tens` (1). Each is a damaged spelling of `tenx_resource_keys`, the field holding the name of the resource attribute the engine folded into the record, and the damage differs from record to record. Reported, not worked around: nothing downstream reads that field.

**A returned record carries either the marks or a record time, never both.** 19436 of 37519 records came back with `timeUnixNano` set, and they are exactly the 19436 that came back with no attributes. Every record that carried a route carried no time. The collector stamps ingest time on both routes; the capture's envelope has no timestamp field either, so nothing here reconstructs the time a line was written.

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

