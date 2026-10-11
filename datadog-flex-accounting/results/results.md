# Datadog Flex Logs accounting

Computed from the engine's counts at Datadog list prices read 2026-10-11. Nothing here was metered by Datadog.

- engine image: `log10x/pipeline-10x@sha256:e2db543265cddd30a959c729c19e61d5f1b97e8be74a8d8e65dcb71a6466491c`
- MCP: log10x-mcp 1.30.46
- capture: `otel-sample-200mb.log`, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`, 197,430 lines, 157,228 events after grouping, 0.215 GB, 10 hours; a month is 720 hours; 1 GB = 1,000,000,000 bytes

## The result

| Target | Patterns planned | Containers capped | Events to Flex | GB to Flex | Events in Standard | Errors and warnings to Flex | Events to Flex per month | Standard indexing avoided per month, 15-day annual | Flex storage added per month, annual | Flex compute tier | Custom metrics, one node |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 30% | 2 | 1 | 57,163 | 0.073 | 100,065 | 0 | 4,115,736 | $7.00 | $0.21 | Starter | 10,848 |
| 50% | 4 | 1 | 57,193 | 0.073 | 100,035 | 0 | 4,117,896 | $7.00 | $0.21 | Starter | 10,848 |
| 70% | 12 | 4 | 57,270 | 0.073 | 99,958 | 0 | 4,123,440 | $7.01 | $0.21 | Starter | 10,848 |

Ingestion is unchanged by a move to Flex: every event is ingested once, at $0.10 per GB, before any index or Flex routing.

## What one million moved events cost at list

| Line | Annual | On-demand | Datadog's wording | Read |
|---|---:|---:|---|---|
| Standard indexing avoided, 3-day retention, per million events | $1.06 | $1.59 | Per 1M indexed logs (3-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Standard indexing avoided, 7-day retention, per million events | $1.27 | $1.91 | Per 1M indexed logs (7-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Standard indexing avoided, 15-day retention, per million events | $1.70 | $2.55 | Per 1M indexed logs (15-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Standard indexing avoided, 30-day retention, per million events | $2.50 | $3.75 | Per 1M indexed logs (30-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Flex storage added, per million events stored per month | $0.05 | $0.075 | Per 1 M events stored, per month; Each million events stored is billed for a minimum of 30 days, or a minimum of $0.05. | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Flex Starter, per million events stored per month, compute bundled | $0.60 | $0.90 | Per 1 M events stored (6, 12 or 15 months retention), per month; Bundled Starter Compute for log volumes below 2B per month (10B total stored) | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Flex compute, XS to L | Contact Us for Pricing | Contact Us for Pricing | Per instance-hour, per month | [2026-10-11](https://www.datadoghq.com/pricing/?product=log-management) |
| Ingestion, per GB, unchanged | $0.10 | $0.10 | Per ingested logs (1GB), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Custom metrics, per 100 per month above the allotment | $5.00 | $5.00 | Per 100 custom metrics, per month; Pro: 100 ingested custom metrics per host and 100 indexed custom metrics per host; Enterprise: 200 ingested custom metrics per host and 200 indexed custom metrics per host | [2026-10-11](https://www.datadoghq.com/pricing/list/) |

Flex compute sizes by cumulative events stored, from Datadog's own table: Starter under 10 billion, XS 10 to 50 billion, XS+ 50 to 100 billion, S 100 to 200 billion, M 200 to 500 billion, L 500 to 1000 billion. Starter is bundled storage and compute for volumes below 2 billion events a month. [2026-10-11](https://docs.datadoghq.com/logs/log_configuration/flex_logs/)

## Target 30%

**The plan.** The MCP sampled 9,563 events of the capture and planned 2 patterns for Flex, stating 39.74% of the Standard-index volume moved: `Traces` (INFO), `Logs` (INFO).
Its cap row reads `<container>,63128:tier_down:MCP poc_from_local soft`: 63,128 bytes per pattern per 240 s window, keyed `<container>`. The patterns are placed in the containers that produced them in the control run, and the cap is multiplied by 150 because the replay delivers the 10-hour capture inside one window: 9,469,200 bytes per pattern.

| Container | Action | Patterns of the plan it hosts |
|---|---|---|
| `opentelemetry-collector` | tier_down | `Traces`, `Logs` |

**The engine.** 157,228 events replayed in 24 s; the records and the engine's aggregators agree on every one of 2,712 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 100,065 | 0.142 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 85,292, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 57,163 | 0.073 | INFO 57,163 |

Errors and warnings marked tier_down: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Events | GB |
|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | 26,017 | 0.033 |
| `Logs` | `opentelemetry-collector` | INFO | 25,019 | 0.032 |
| `Metrics` | `opentelemetry-collector` | INFO | 6,127 | 0.008 |

**A month at list.** 4,115,736 events to Flex (5.230 GB), 7,204,680 in Standard, 15.472 GB ingested.

| Line | Per month |
|---|---:|
| Standard indexing avoided, 15-day, annual | $7.00 |
| Standard indexing avoided, 15-day, on-demand | $10.50 |
| Standard indexing avoided, 30-day, annual | $10.29 |
| Standard indexing avoided, 30-day, on-demand | $15.43 |
| Flex storage added, held 30 days, annual | $0.21 |
| Flex storage added, held 30 days, on-demand | $0.31 |
| Flex Starter instead of storage plus compute, annual | $2.47 |
| Flex compute tier at 4,115,736 events stored | Starter, within Starter; Contact Us for Pricing for XS and above |
| Ingestion, unchanged | $1.55 |
| Custom metrics from the engine's Datadog metric output, one node | 10,848 series; 10,748 above a Pro host's allotment ($537.40), 10,648 above Enterprise ($532.40) |

## Target 50%

**The plan.** The MCP sampled 9,563 events of the capture and planned 4 patterns for Flex, stating 57.02% of the Standard-index volume moved: `Traces` (INFO), `Logs` (INFO), `cart_cartstore_ValkeyCartStore` (INFO), `Metrics` (INFO).
Its cap row reads `<container>,63128:tier_down:MCP poc_from_local soft`: 63,128 bytes per pattern per 240 s window, keyed `<container>`. The patterns are placed in the containers that produced them in the control run, and the cap is multiplied by 150 because the replay delivers the 10-hour capture inside one window: 9,469,200 bytes per pattern.

| Container | Action | Patterns of the plan it hosts |
|---|---|---|
| `opentelemetry-collector` | tier_down | `Traces`, `Logs`, `Metrics` |

**The engine.** 157,228 events replayed in 25 s; the records and the engine's aggregators agree on every one of 2,712 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 100,035 | 0.142 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 85,262, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 57,193 | 0.073 | INFO 57,193 |

Errors and warnings marked tier_down: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Events | GB |
|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | 26,065 | 0.033 |
| `Logs` | `opentelemetry-collector` | INFO | 24,978 | 0.032 |
| `Metrics` | `opentelemetry-collector` | INFO | 6,150 | 0.008 |

**A month at list.** 4,117,896 events to Flex (5.232 GB), 7,202,520 in Standard, 15.472 GB ingested.

| Line | Per month |
|---|---:|
| Standard indexing avoided, 15-day, annual | $7.00 |
| Standard indexing avoided, 15-day, on-demand | $10.50 |
| Standard indexing avoided, 30-day, annual | $10.29 |
| Standard indexing avoided, 30-day, on-demand | $15.44 |
| Flex storage added, held 30 days, annual | $0.21 |
| Flex storage added, held 30 days, on-demand | $0.31 |
| Flex Starter instead of storage plus compute, annual | $2.47 |
| Flex compute tier at 4,117,896 events stored | Starter, within Starter; Contact Us for Pricing for XS and above |
| Ingestion, unchanged | $1.55 |
| Custom metrics from the engine's Datadog metric output, one node | 10,848 series; 10,748 above a Pro host's allotment ($537.40), 10,648 above Enterprise ($532.40) |

## Target 70%

**The plan.** The MCP sampled 9,563 events of the capture and planned 12 patterns for Flex, stating 70.35% of the Standard-index volume moved: `Traces` (INFO), `Logs` (INFO), `cart_cartstore_ValkeyCartStore` (INFO), `Metrics` (INFO), `Receive_ListRecommendations_for_product_ids` (INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (INFO), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (INFO), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (INFO), `Deleted_snapshot_files_for_offset_epoch_org_apache_kafka_Snapshots` (INFO), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (INFO).
Its cap row reads `<container>,63128:tier_down:MCP poc_from_local soft`: 63,128 bytes per pattern per 240 s window, keyed `<container>`. The patterns are placed in the containers that produced them in the control run, and the cap is multiplied by 150 because the replay delivers the 10-hour capture inside one window: 9,469,200 bytes per pattern.

| Container | Action | Patterns of the plan it hosts |
|---|---|---|
| `ad` | tier_down | `oteldemo_AdService_Targeted_ad_request_received_for`, `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` |
| `kafka` | tier_down | `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment`, `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager`, `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog`, `Deleted_snapshot_files_for_offset_epoch_org_apache_kafka_Snapshots`, `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` |
| `opentelemetry-collector` | tier_down | `Traces`, `Logs`, `Metrics` |
| `recommendation` | tier_down | `Receive_ListRecommendations_for_product_ids` |

**The engine.** 157,228 events replayed in 25 s; the records and the engine's aggregators agree on every one of 2,712 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 99,958 | 0.142 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 85,185, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 57,270 | 0.073 | INFO 57,270 |

Errors and warnings marked tier_down: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Events | GB |
|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | 26,131 | 0.033 |
| `Logs` | `opentelemetry-collector` | INFO | 24,953 | 0.032 |
| `Metrics` | `opentelemetry-collector` | INFO | 6,186 | 0.008 |

**A month at list.** 4,123,440 events to Flex (5.239 GB), 7,196,976 in Standard, 15.472 GB ingested.

| Line | Per month |
|---|---:|
| Standard indexing avoided, 15-day, annual | $7.01 |
| Standard indexing avoided, 15-day, on-demand | $10.51 |
| Standard indexing avoided, 30-day, annual | $10.31 |
| Standard indexing avoided, 30-day, on-demand | $15.46 |
| Flex storage added, held 30 days, annual | $0.21 |
| Flex storage added, held 30 days, on-demand | $0.31 |
| Flex Starter instead of storage plus compute, annual | $2.47 |
| Flex compute tier at 4,123,440 events stored | Starter, within Starter; Contact Us for Pricing for XS and above |
| Ingestion, unchanged | $1.55 |
| Custom metrics from the engine's Datadog metric output, one node | 10,848 series; 10,748 above a Pro host's allotment ($537.40), 10,648 above Enterprise ($532.40) |

## Custom metrics

The engine's Datadog metric output publishes two counters, event volume and bytes, for each label set of two aggregators, `all_events` and `emitted_events`. A custom metric is uniquely identified by a combination of a metric name and tag values (including the host tag). On this capture the control run produced 2,709 label sets in `all_events` and 2,709 in `emitted_events`, 10,836 custom metrics from one node. A move splits label sets by route, so each target's count is in its table. Custom metrics are counted hourly and averaged monthly across your entire account, not on a per-host basis. Metrics created from ingested logs are billed as Custom Metrics.

## Counting conditions

- Datadog counts indexed events: "At the end of the month, Datadog computes the total number of log events that have been indexed" ([2026-10-11](https://docs.datadoghq.com/account_management/billing/log_management/)). With the shipped forwarder path one record is one event; the Receiver groups the lines of a multi-line event into one record, and the engine counted 157,228 records from 197,430 lines here.
- The Flex route is the documented index filter on `@routeState:tier_down`, applied to a Flex index listed before the Standard one. Every event the engine marks `tier_down` carries that field to Datadog.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its pattern's cap takes the container's action. Patterns under 5% of their container's bytes in the window are not capped, the first 5 events of a pattern in a window pass, and the severity floors keep a share of each level: a tenth of INFO, DEBUG and TRACE, three tenths of WARN, half of ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within that noise.
- The replay delivers the capture inside one window; the plan's cap is scaled by the window the MCP was told the capture covers, as the policy files record.
- Events and GB are the engine's counts of the records it emitted; dollars are those counts at list price. A month is 720 hours; the capture covers 10.

## Reproduce

```sh
./run.sh                 # everything
./run.sh plan replay     # some stages, in the order given
```

Stages: `data plan control policy replay count report`. Needs Docker, Node 18 or later and about 1 GB of disk. `plan` installs the pinned log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; the server runs the pinned engine image for its own sampling. Every other stage runs the engine image on the capture. `ACCT_TARGETS` sets the targets (default `30 50 70`), `ACCT_WINDOW` the span the capture covers (default `10h`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `prices.json` | every price used, with its URL and the date read |
| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |
| `../accounting-lib/plan.mjs` | asks the released MCP for its plan over stdio and keeps what it wrote |
| `../accounting-lib/replay.config.yaml` | the engine run: shipped enrichment, regulator and aggregators, file in, file out |
| `../accounting-lib/policy.py` | the plan's patterns and cap mapped onto the engine's per-container files, with the arithmetic recorded |
| `../accounting-lib/count.py` | the two counts, records and aggregators, required to agree |
| `results/plan-<target>.json` | the plan the MCP wrote, its notes and the caps row it rendered |
| `results/policy-<target>.caps.csv`, `.actions.csv`, `.json` | the files the engine read |
| `results/<target>.tally.json`, `results/control.tally.json` | the counts per route, container, severity and pattern |

## Data

`otel-sample-200mb.log` from [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1), 215,039,161 bytes, 197,430 lines, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`: Kubernetes container output captured through Fluentd from a cluster running the OpenTelemetry demo, 36 containers, about ten hours. The same asset the [`splunk-license/`](../splunk-license/) and [`otel-denominators/`](../otel-denominators/) benchmarks run on.
