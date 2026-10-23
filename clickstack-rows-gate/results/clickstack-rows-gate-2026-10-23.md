# ClickHouse rows gate, 2026-10-23: which meter equals the hot count

Engine `ghcr.io/log-10x/edge-10x:1.1.147`, ClickHouse 26.5.7.64, 197430 lines fed in 216 s, regulator in events with the shipped baseline of 5, totals rewritten in place at 2026-10-23T11:20:32 UTC.

## The count to match

- Hot rows (`SELECT count() FROM default.otel_logs`): **22367**
- Cold rows through the S3 view: 134720; hot plus cold: 157087
- Wire records the Receiver returned: 157087, by route: {"offload": 134720, "pass": 22367}
- Active rows in `system.parts`: 22367 (equal)

## Meter candidates

| Candidate | Rows | Statements | Against hot |
|---|---:|---:|---|
| `query_log` written_rows, kind Insert, tables has otel_logs | 24315 | 22 | off by +1948 |
| `query_log` written_rows, kind AsyncInsertFlush, tables has otel_logs | 14848 | 21 | off by -7519 |
| `query_log` written_rows, both kinds, `otel_logs` in the query text | 39163 | | off by +16796 |
| `part_log` NewPart rows, otel_logs | 22367 | 22 parts | equal |
| `part_log` NewPart rows, counts_by_type | 3000 | | (the materialized view's own parts) |

`part_log` rows for otel_logs before the feed: 0. Counts table hot side: 2494 rows summing to 22367.

Insert statements by the `tables` they name (`query_log`):

| tables | statements | written_rows |
|---|---:|---:|
| `default.counts_by_type,default.otel_logs,default.otel_logs_kv_rollup_15m` | 43 | 39163 |

## The policy reload mid-window

Feed span by insert time: ['2026-10-23 11:20:28.765', '2026-10-23 11:22:13.803']. Totals file rewritten at 2026-10-23T11:20:32; hot rows then 9171.

| Service | cap | total | hot rows | before reload | after reload | cold | patterns in hot | error patterns | floor 5 x patterns + 50 x error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| opentelemetry-collector | 1500 | 2000 | 2050 | 2050 | 0 | 87689 | 34 | 5 | 420 |
| kafka | 800 | 1000 | 1000 | 1000 | 0 | 27785 | 168 | 0 | 840 |
| cart | 300 | 400 | 400 | 400 | 0 | 19246 | 11 | 0 | 55 |

Hot rows per 4-minute insert window, capped services:

| window (UTC) | service | hot rows |
|---|---|---:|
| 2026-10-23 11:20:00 | cart | 400 |
| 2026-10-23 11:20:00 | kafka | 1000 |
| 2026-10-23 11:20:00 | opentelemetry-collector | 2050 |

## The Receiver's own counters (Prometheus scrape)

Label keys whose value is a capped container name: {"k8s_container": 80, "tenx_user_service": 80}

- `all_events_summaryBytes_total` by routeState: {"offload": 205120629.0, "pass": 35140421.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']
- `all_events_summaryVolume_total` by routeState: {"offload": 134720.0, "pass": 16255.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']
- `emitted_events_summaryBytes_total` by routeState: {"offload": 205120629.0, "pass": 35141746.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']
- `emitted_events_summaryVolume_total` by routeState: {"offload": 134720.0, "pass": 16256.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']

The scrape was taken 5 seconds after the collector stopped. Its `offload` count equals the wire's (134,720); its `pass` count (16,255) is 6,112 under the wire's 22,367, so the counters lag the wire at the moment of a scrape. A run that reads the last complete hour, as the rows run does, reads them after they have settled.

Label keys whose value is a capped container name: {"k8s_container": 80, "tenx_user_service": 80}

- `all_events_summaryBytes_total` by routeState: {"offload": 205120629.0, "pass": 35140421.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']
- `all_events_summaryVolume_total` by routeState: {"offload": 134720.0, "pass": 16255.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']
- `emitted_events_summaryBytes_total` by routeState: {"offload": 205120629.0, "pass": 35141746.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']
- `emitted_events_summaryVolume_total` by routeState: {"offload": 134720.0, "pass": 16256.0}; labels ['http_code', 'http_message', 'k8s_container', 'k8s_namespace', 'message_pattern', 'routeState', 'severity_level', 'tenx_app', 'tenx_env', 'tenx_fwd_input', 'tenx_hash', 'tenx_reported_name', 'tenx_user_service']

## Harness patches on 1.1.147

```
patched otel-collector forwarder input enabled
  patched prometheus scrape output enabled
  patched regulator unit set to events
  patched pattern text added to the offload splice list
```

## Images

```
clickhouse/clickstack-all-in-one:2.38.0              sha256:7b3bd9eec4e61aded56f705af7ddb2e8e49c54098d21aaaa7de6fde4d7c1f267
  ghcr.io/log-10x/edge-10x:1.1.147                     sha256:a043ccd828742c4eccee09abb654ce6a7357b6123f73300ed04f8605e874b8c4
  otel/opentelemetry-collector-contrib:0.160.0         sha256:799dc6cf12c96192af37b5bdba804da8c10b3bc563b43cb90c3f3c58d9572ad6
  rustfs/rustfs:latest                                 sha256:9ca9559533b537d10482fe923288b676ad08f92a7069d9a17327fbae3cab688b
  amazon/aws-cli:latest                                sha256:c8156a0e74e13929a42d7e60f0d4e14e7d28d980cd21822505d4bff80e5460c1
```

## Queries, in order

- `SELECT count() FROM default.otel_logs` -> `22367`
- `SELECT count() FROM default.otel_logs_coldv` -> `134720`
- `SELECT count() FROM default.counts_by_type WHERE source = 'hot'` -> `2494`
- `SELECT sum(cnt) FROM default.counts_by_type WHERE source = 'hot'` -> `22367`
- `SELECT sum(written_rows) FROM system.query_log WHERE type = 'QueryFinish' AND query_kind = 'Insert' AND has(tables, 'default.otel_logs')` -> `24315`
- `SELECT count() FROM system.query_log WHERE type = 'QueryFinish' AND query_kind = 'Insert' AND has(tables, 'default.otel_logs')` -> `22`
- `SELECT sum(written_rows) FROM system.query_log WHERE type = 'QueryFinish' AND query_kind = 'AsyncInsertFlush' AND has(tables, 'default.otel_logs')` -> `14848`
- `SELECT count() FROM system.query_log WHERE type = 'QueryFinish' AND query_kind = 'AsyncInsertFlush' AND has(tables, 'default.otel_logs')` -> `21`
- `SELECT sum(written_rows) FROM system.query_log WHERE type = 'QueryFinish' AND query_kind IN ('Insert','AsyncInsertFlush') AND position(query, 'otel_logs') > 0` -> `39163`
- `SELECT arrayStringConcat(arraySort(tables), ','), count(), sum(written_rows) FROM system.query_log WHERE type = 'QueryFinish' AND query_kind IN ('Insert','AsyncInsertFlush') AND (has(tables, 'default.otel_logs') OR has(tables, 'default.counts_by_type')) GROUP BY 1 ORDER BY 2 DESC FORMAT TSV` -> `default.counts_by_type,default.otel_logs,default.otel_logs_kv_rollup_15m	43	39163`
- `SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs'` -> `22367`
- `SELECT count() FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs'` -> `22`
- `SELECT sum(rows) FROM system.part_log WHERE event_type = 'NewPart' AND database = 'default' AND table = 'counts_by_type'` -> `3000`
- `SELECT sum(rows) FROM system.parts WHERE database = 'default' AND table = 'otel_logs' AND active` -> `22367`
- `SELECT count() FROM default.otel_logs WHERE ServiceName = 'opentelemetry-collector'` -> `2050`
- `SELECT count() FROM default.otel_logs WHERE ServiceName = 'opentelemetry-collector' AND ins <= toDateTime64('2026-10-23 11:20:32', 3, 'UTC')` -> `2050`
- `SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = 'opentelemetry-collector'` -> `34`
- `SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = 'opentelemetry-collector' AND SeverityText IN ('ERROR','FATAL','CRITICAL','error','fatal','critical','Error','Fatal','Critical')` -> `5`
- `SELECT count() FROM default.otel_logs_coldv WHERE ServiceName = 'opentelemetry-collector'` -> `87689`
- `SELECT count() FROM default.otel_logs WHERE ServiceName = 'kafka'` -> `1000`
- `SELECT count() FROM default.otel_logs WHERE ServiceName = 'kafka' AND ins <= toDateTime64('2026-10-23 11:20:32', 3, 'UTC')` -> `1000`
- `SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = 'kafka'` -> `168`
- `SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = 'kafka' AND SeverityText IN ('ERROR','FATAL','CRITICAL','error','fatal','critical','Error','Fatal','Critical')` -> `0`
- `SELECT count() FROM default.otel_logs_coldv WHERE ServiceName = 'kafka'` -> `27785`
- `SELECT count() FROM default.otel_logs WHERE ServiceName = 'cart'` -> `400`
- `SELECT count() FROM default.otel_logs WHERE ServiceName = 'cart' AND ins <= toDateTime64('2026-10-23 11:20:32', 3, 'UTC')` -> `400`
- `SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = 'cart'` -> `11`
- `SELECT uniqExact(LogAttributes['tenx_hash']) FROM default.otel_logs WHERE ServiceName = 'cart' AND SeverityText IN ('ERROR','FATAL','CRITICAL','error','fatal','critical','Error','Fatal','Critical')` -> `0`
- `SELECT count() FROM default.otel_logs_coldv WHERE ServiceName = 'cart'` -> `19246`
- `SELECT toStartOfInterval(ins, INTERVAL 4 MINUTE) AS w, ServiceName, count() FROM default.otel_logs WHERE ServiceName IN ('opentelemetry-collector','kafka','cart') GROUP BY w, ServiceName ORDER BY w, ServiceName FORMAT TSV` -> `2026-10-23 11:20:00	cart	400
2026-10-23 11:20:00	kafka	1000
2026-10-23 11:20:00	opentelemetry-collector	2050`
- `SELECT min(ins), max(ins) FROM default.otel_logs FORMAT TSV` -> `2026-10-23 11:20:28.765	2026-10-23 11:22:13.803`
