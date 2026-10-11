# CloudWatch Logs Infrequent Access accounting

Computed from the engine's counts at AWS list prices for us-east-1, read 2026-10-11. Nothing here was metered by AWS.

- engine image: `log10x/pipeline-10x@sha256:fd9c98384a775df13ed41921c2cf95ef1d1313f62f1300aac61da55ca64feb67`
- MCP: log10x-mcp 1.30.48
- capture: `otel-sample-200mb.log`, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`, 197,430 lines, 157,228 events after grouping, 0.215 GB, 10 hours; a month is 720 hours; 1 GB = 1,000,000,000 bytes

## Dollars per GB at list

| Line | Per GB | AWS's wording | Read |
|---|---:|---|---|
| Ingest, Standard | $0.50 | $0.50 per GB custom log data ingested in Standard log class - US East (Northern Virginia) | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/) |
| Ingest, Infrequent Access | $0.25 | $0.25 per GB custom log data ingested in Infrequent Access log class -US East (Northern Virginia) | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/) |
| Storage, per GB-month, both classes | $0.03 | $0.03 per GB-mo of log storage - US East (Northern Virginia); *0.15 compression ratio for each uncompressed byte; For charges, the Standard and Infrequent Access log classes differ in ingestion costs only. Storage charges and CloudWatch Logs Insights charges are the same in each log class. | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/), [classes](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Logs_Log_Classes.html) |
| Logs Insights, per GB scanned | $0.005 | $0.005 per GB log data scanned by CloudWatch Logs Insights queries - US East (Northern Virginia) | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/) |
| S3 Standard storage, per GB-month | $0.023 | $0.023 per GB - first 50 TB / month of storage used | [2026-10-11](https://aws.amazon.com/s3/pricing/) |
| S3 PUT, per 1,000 requests | $0.005 | $0.005 per 1,000 PUT, COPY, POST, or LIST requests | [2026-10-11](https://aws.amazon.com/s3/pricing/) |

A GB moved from Standard to Infrequent Access costs $0.25 instead of $0.50 to ingest, and the same to store; a GB offloaded costs nothing to ingest, $0.023 per month in S3. The price list carries publication date 2026-10-07T11:55:40Z ([index.json](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/us-east-1/index.json)). After a log group is created, its log class can't be changed.

## What moves, per target

| Target | Patterns planned | Containers | GB the plan states to IA | GB the engine marked to IA | GB offloaded | GB in Standard | Errors and warnings moved |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30% | 22 | 5 | 0.136 | 0.150 | 0.000 | 0.065 | 0 |
| 50% | 55 | 17 | 0.071 | 0.067 | 0.099 | 0.048 | 53 |
| 70% | 55 | 17 | 0.030 | 0.002 | 0.165 | 0.048 | 51 |

The engine moves each pattern's excess over its container's cap; the plan sets the cap at the largest pattern the container keeps and states the excess, less the share the severity floors keep. Offload acts on the whole container: its cap is the one-byte minimum.

## A month at this capture's volume, an illustration

The capture's 10 hours scaled to a 720-hour month, at the rates above. The volume is one small demo cluster's; the rates are what carry.

| Target | GB to IA per month | Ingest at the IA rate | Ingest at Standard the same GB would cost | GB offloaded per month | Ingest avoided by offload |
|---:|---:|---:|---:|---:|---:|
| 30% | 10.776 | $2.69 | $5.39 | 0.000 | $0.00 |
| 50% | 4.832 | $1.21 | $2.42 | 7.150 | $3.58 |
| 70% | 0.127 | $0.03 | $0.06 | 11.895 | $5.95 |

## Target 30%

**The plan.** The MCP sampled 9,563 events of the capture and planned 22 patterns, stating 30.37% of the bill: `Traces` (tier_down, INFO), `Logs` (tier_down, INFO), `Metrics` (tier_down, INFO), `cart_cartstore_ValkeyCartStore` (tier_down, INFO), `Receive_ListRecommendations_for_product_ids` (tier_down, INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (tier_down, TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (tier_down, TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (tier_down, INFO), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (tier_down, INFO), `Deleted_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (tier_down, INFO), and 10 more.
Its engine files, as written (a cap is bytes per pattern per 240 s window over the 1 hours the plan covers; the replay multiplies each cap by 15 because it delivers the capture inside one window):

```
container,cap
ad,50331::MCP poc_from_local plan 30 pct
cart,22315::MCP poc_from_local plan 30 pct
kafka,4288::MCP poc_from_local plan 30 pct
opentelemetry-collector,304617::MCP poc_from_local plan 30 pct
recommendation,1::MCP poc_from_local plan 30 pct
container,action
ad,tier_down::MCP poc_from_local plan 30 pct
cart,tier_down::MCP poc_from_local plan 30 pct
kafka,tier_down::MCP poc_from_local plan 30 pct
opentelemetry-collector,tier_down::MCP poc_from_local plan 30 pct
recommendation,tier_down::MCP poc_from_local plan 30 pct
```

**The engine.** 157,228 events replayed in 30 s; the records and the engine's aggregators agree on every one of 2,730 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 40,855 | 0.065 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 30,603, TRACE 2,592, WARN 217, none 1,087 |
| tier_down | 116,373 | 0.150 | INFO 111,852, TRACE 4,521 |

Errors and warnings moved: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Route | Events | GB |
|---|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | tier_down | 29,476 | 0.037 |
| `Logs` | `opentelemetry-collector` | INFO | tier_down | 28,513 | 0.036 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | tier_down | 11,241 | 0.019 |
| `Metrics` | `opentelemetry-collector` | INFO | tier_down | 9,572 | 0.012 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | tier_down | 6,080 | 0.011 |
| `Receive_ListRecommendations_for_product_ids` | `recommendation` | INFO | tier_down | 3,106 | 0.004 |
| `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` | `ad` | TRACE | tier_down | 2,455 | 0.002 |
| `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` | `kafka` | INFO | tier_down | 2,169 | 0.002 |
| `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` | `kafka` | INFO | tier_down | 2,154 | 0.002 |
| `Rolled_new_log_segment_at_offset_in_ms_kafka_LocalLog` | `kafka` | INFO | tier_down | 2,138 | 0.002 |

**A month at this volume, an illustration.** 10.776 GB to Infrequent Access (8,378,856 events), 0.000 GB offloaded (0 events), 4.695 GB in Standard.

| Line | Per month |
|---|---:|
| Ingest, Standard, for what stays | $2.35 |
| Ingest, Infrequent Access, for the moved slice | $2.69 |
| Ingest at Standard, what the moved slice would have cost | $5.39 |
| Ingest avoided by offload | $0.00 |
| Storage for one month of data held one month, both classes, compressed at AWS's stated ratio | $0.07 |
| Logs Insights, one full scan of the IA slice | $0.05 |
| S3 storage for one month of offloaded data held one month | $0.00 |
| S3 PUT, 0 objects | $0.0000 |
| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | 217,850,256 bytes; not a billed quantity on any AWS page read |

## Target 50%

**The plan.** The MCP sampled 9,563 events of the capture and planned 55 patterns, stating 56.85% of the bill: `Traces` (offload, INFO), `Logs` (offload, INFO), `Metrics` (tier_down, INFO), `cart_cartstore_ValkeyCartStore` (tier_down, INFO), `Receive_ListRecommendations_for_product_ids` (tier_down, INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (tier_down, TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (tier_down, TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (tier_down, INFO), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (tier_down, INFO), `Deleted_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (tier_down, INFO), and 43 more.
Its engine files, as written (a cap is bytes per pattern per 240 s window over the 1 hours the plan covers; the replay multiplies each cap by 15 because it delivers the capture inside one window):

```
container,cap
accounting,2018::MCP poc_from_local plan 50 pct
ad,2957::MCP poc_from_local plan 50 pct
aws-node,1::MCP poc_from_local plan 50 pct
cart,22315::MCP poc_from_local plan 50 pct
coredns,5013::MCP poc_from_local plan 50 pct
email,991::MCP poc_from_local plan 50 pct
flagd,1088::MCP poc_from_local plan 50 pct
fluentd-10x,1::MCP poc_from_local plan 50 pct
fraud-detection,1::MCP poc_from_local plan 50 pct
frontend-proxy,2491::MCP poc_from_local plan 50 pct
image-provider,1::MCP poc_from_local plan 50 pct
jaeger,2322::MCP poc_from_local plan 50 pct
kafka,4288::MCP poc_from_local plan 50 pct
opensearch,1::MCP poc_from_local plan 50 pct
opentelemetry-collector,1::MCP poc_from_local plan 50 pct
recommendation,1::MCP poc_from_local plan 50 pct
valkey-cart,1::MCP poc_from_local plan 50 pct
container,action
accounting,tier_down::MCP poc_from_local plan 50 pct
ad,tier_down::MCP poc_from_local plan 50 pct
aws-node,tier_down::MCP poc_from_local plan 50 pct
cart,tier_down::MCP poc_from_local plan 50 pct
coredns,tier_down::MCP poc_from_local plan 50 pct
email,tier_down::MCP poc_from_local plan 50 pct
flagd,tier_down::MCP poc_from_local plan 50 pct
fluentd-10x,tier_down::MCP poc_from_local plan 50 pct
fraud-detection,tier_down::MCP poc_from_local plan 50 pct
frontend-proxy,tier_down::MCP poc_from_local plan 50 pct
image-provider,tier_down::MCP poc_from_local plan 50 pct
jaeger,tier_down::MCP poc_from_local plan 50 pct
kafka,tier_down::MCP poc_from_local plan 50 pct
opensearch,tier_down::MCP poc_from_local plan 50 pct
opentelemetry-collector,offload::MCP poc_from_local plan 50 pct
recommendation,tier_down::MCP poc_from_local plan 50 pct
valkey-cart,tier_down::MCP poc_from_local plan 50 pct
```

**The engine.** 157,228 events replayed in 30 s; the records and the engine's aggregators agree on every one of 2,746 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| offload | 76,770 | 0.099 | ERROR 53, INFO 76,717 |
| pass | 28,174 | 0.048 | CRITICAL 2,324, DEBUG 2, ERROR 3,977, INFO 20,249, TRACE 823, WARN 217, none 582 |
| tier_down | 52,284 | 0.067 | INFO 45,489, TRACE 6,290, none 505 |

Errors and warnings moved: 53. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Route | Events | GB |
|---|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | offload | 32,654 | 0.041 |
| `Logs` | `opentelemetry-collector` | INFO | offload | 31,554 | 0.040 |
| `Metrics` | `opentelemetry-collector` | INFO | offload | 12,509 | 0.016 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | tier_down | 11,261 | 0.019 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | tier_down | 6,064 | 0.011 |
| `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` | `ad` | TRACE | tier_down | 3,172 | 0.003 |
| `Receive_ListRecommendations_for_product_ids` | `recommendation` | INFO | tier_down | 3,096 | 0.004 |
| `oteldemo_AdService_Targeted_ad_request_received_for` | `ad` | TRACE | tier_down | 2,712 | 0.003 |
| `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` | `kafka` | INFO | tier_down | 2,159 | 0.002 |
| `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` | `kafka` | INFO | tier_down | 2,146 | 0.002 |

**A month at this volume, an illustration.** 4.832 GB to Infrequent Access (3,764,448 events), 7.150 GB offloaded (5,527,440 events), 3.489 GB in Standard.

| Line | Per month |
|---|---:|
| Ingest, Standard, for what stays | $1.74 |
| Ingest, Infrequent Access, for the moved slice | $1.21 |
| Ingest at Standard, what the moved slice would have cost | $2.42 |
| Ingest avoided by offload | $3.58 |
| Storage for one month of data held one month, both classes, compressed at AWS's stated ratio | $0.04 |
| Logs Insights, one full scan of the IA slice | $0.02 |
| S3 storage for one month of offloaded data held one month | $0.16 |
| S3 PUT, 4,320 objects | $0.0216 |
| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | 97,875,648 bytes; not a billed quantity on any AWS page read |

## Target 70%

**The plan.** The MCP sampled 9,563 events of the capture and planned 55 patterns, stating 70.64% of the bill: `Traces` (offload, INFO), `Logs` (offload, INFO), `Metrics` (offload, INFO), `cart_cartstore_ValkeyCartStore` (offload, INFO), `Receive_ListRecommendations_for_product_ids` (offload, INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (offload, TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (offload, TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (offload, INFO), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (offload, INFO), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (tier_down, INFO), `Deleted_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (tier_down, INFO), and 43 more.
Its engine files, as written (a cap is bytes per pattern per 240 s window over the 1 hours the plan covers; the replay multiplies each cap by 15 because it delivers the capture inside one window):

```
container,cap
accounting,2018::MCP poc_from_local plan 70 pct
ad,1::MCP poc_from_local plan 70 pct
aws-node,1::MCP poc_from_local plan 70 pct
cart,1::MCP poc_from_local plan 70 pct
coredns,5013::MCP poc_from_local plan 70 pct
email,991::MCP poc_from_local plan 70 pct
flagd,1088::MCP poc_from_local plan 70 pct
fluentd-10x,1::MCP poc_from_local plan 70 pct
fraud-detection,1::MCP poc_from_local plan 70 pct
frontend-proxy,2491::MCP poc_from_local plan 70 pct
image-provider,1::MCP poc_from_local plan 70 pct
jaeger,2322::MCP poc_from_local plan 70 pct
kafka,1::MCP poc_from_local plan 70 pct
opensearch,1::MCP poc_from_local plan 70 pct
opentelemetry-collector,1::MCP poc_from_local plan 70 pct
recommendation,1::MCP poc_from_local plan 70 pct
valkey-cart,1::MCP poc_from_local plan 70 pct
container,action
accounting,tier_down::MCP poc_from_local plan 70 pct
ad,offload::MCP poc_from_local plan 70 pct
aws-node,tier_down::MCP poc_from_local plan 70 pct
cart,offload::MCP poc_from_local plan 70 pct
coredns,tier_down::MCP poc_from_local plan 70 pct
email,tier_down::MCP poc_from_local plan 70 pct
flagd,tier_down::MCP poc_from_local plan 70 pct
fluentd-10x,tier_down::MCP poc_from_local plan 70 pct
fraud-detection,tier_down::MCP poc_from_local plan 70 pct
frontend-proxy,tier_down::MCP poc_from_local plan 70 pct
image-provider,tier_down::MCP poc_from_local plan 70 pct
jaeger,tier_down::MCP poc_from_local plan 70 pct
kafka,offload::MCP poc_from_local plan 70 pct
opensearch,tier_down::MCP poc_from_local plan 70 pct
opentelemetry-collector,offload::MCP poc_from_local plan 70 pct
recommendation,offload::MCP poc_from_local plan 70 pct
valkey-cart,tier_down::MCP poc_from_local plan 70 pct
```

**The engine.** 157,228 events replayed in 32 s; the records and the engine's aggregators agree on every one of 2,755 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| offload | 127,680 | 0.165 | ERROR 51, INFO 121,264, TRACE 6,365 |
| pass | 27,763 | 0.048 | CRITICAL 2,324, DEBUG 2, ERROR 3,979, INFO 19,915, TRACE 748, WARN 217, none 578 |
| tier_down | 1,785 | 0.002 | INFO 1,276, none 509 |

Errors and warnings moved: 51. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Route | Events | GB |
|---|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | offload | 32,589 | 0.041 |
| `Logs` | `opentelemetry-collector` | INFO | offload | 31,510 | 0.040 |
| `Metrics` | `opentelemetry-collector` | INFO | offload | 12,494 | 0.016 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | offload | 11,394 | 0.020 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | offload | 6,262 | 0.011 |
| `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` | `ad` | TRACE | offload | 3,183 | 0.003 |
| `Receive_ListRecommendations_for_product_ids` | `recommendation` | INFO | offload | 3,062 | 0.004 |
| `oteldemo_AdService_Targeted_ad_request_received_for` | `ad` | TRACE | offload | 2,735 | 0.003 |
| `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` | `kafka` | INFO | offload | 2,173 | 0.002 |
| `Rolled_new_log_segment_at_offset_in_ms_kafka_LocalLog` | `kafka` | INFO | offload | 2,156 | 0.002 |

**A month at this volume, an illustration.** 0.127 GB to Infrequent Access (128,520 events), 11.895 GB offloaded (9,192,960 events), 3.450 GB in Standard.

| Line | Per month |
|---|---:|
| Ingest, Standard, for what stays | $1.72 |
| Ingest, Infrequent Access, for the moved slice | $0.03 |
| Ingest at Standard, what the moved slice would have cost | $0.06 |
| Ingest avoided by offload | $5.95 |
| Storage for one month of data held one month, both classes, compressed at AWS's stated ratio | $0.02 |
| Logs Insights, one full scan of the IA slice | $0.00 |
| S3 storage for one month of offloaded data held one month | $0.27 |
| S3 PUT, 4,320 objects | $0.0216 |
| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | 3,341,520 bytes; not a billed quantity on any AWS page read |

## What Infrequent Access lacks

From AWS's log class table ([2026-10-11](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Logs_Log_Classes.html)), marked "No" for Infrequent Access: Facets, Natural language query assist, CloudWatch Logs Anomaly Detection, Live Tail, Field indexing, Compare to previous time range, Subscription filters, Metric filters, Container Insights log ingestion, Lambda Insights log ingestion, Embedded metrics format, GetLogEvents and FilterLogEvents API operations, Logs Insights commands pattern, diff, filterIndex and unmask.
Supported in both classes: CloudWatch Logs Insights queries, most commands, CloudWatch pipelines, Export to Amazon S3, S3 Tables integration, Scheduled queries, Encryption with AWS KMS, Sensitive data protection with masking, Cross-account features.

## Counting conditions

- CloudWatch bills ingestion by the bytes of each event message. Bytes here are the UTF-8 size of each record the engine emitted; with the shipped forwarder path the forwarder sends that record as the event message.
- The 26 bytes per event in the PutLogEvents batch-size rule are shown as a separate line. No sentence on the pricing page or the billing page says these bytes are billed; the billed usage type is DataProcessing-Bytes for PutLogEvents. ([2026-10-11](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutLogEvents.html))
- The split is forwarder-side: the `tenx.tier_down` tag goes to a log group in the Infrequent Access class, `tenx.offload` to the S3 output, and the class is fixed when the group is created.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its pattern's cap takes the container's action. Patterns under 5% of their container's bytes in the window are not capped, the first 5 events of a pattern in a window pass, and the severity floors keep a share of each level: a tenth of INFO, DEBUG and TRACE, three tenths of WARN, half of ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within that noise.
- The replay delivers the capture inside one window; each cap the plan wrote is multiplied by the span the plan covers over 240 s, and nothing else in the plan's files is changed. `results/policy-*.json` records the files and the factor.
- A month is 720 hours; the capture covers 10. Storage and S3 storage accrue per GB-month and are shown per GB-month of data held.

## Reproduce

```sh
./run.sh                 # everything
./run.sh plan replay     # some stages, in the order given
```

Stages: `data plan control policy replay count report`. Needs Docker, Node 18 or later and about 1 GB of disk. `plan` installs the pinned log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio with the S3 retriever declared installed, so the plan can offload; the server runs the pinned engine image for its own sampling. Every other stage runs the engine image on the capture. `ACCT_TARGETS` sets the targets (default `30 50 70`), `ACCT_WINDOW` the span the capture covers (default `10h`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `prices.json` | every price used, with its URL and the date read |
| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |
| `../accounting-lib/` | the MCP driver, the engine run, the policy mapping and the two-way count, shared with [`datadog-flex-accounting/`](../datadog-flex-accounting/) |
| `results/plan-<target>.json` | the plan the MCP wrote, its notes and the caps row it rendered |
| `results/policy-<target>.caps.csv`, `.actions.csv`, `.json` | the files the engine read |
| `results/<target>.tally.json`, `results/control.tally.json` | the counts per route, container, severity and pattern |

## Data

`otel-sample-200mb.log` from [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1), 215,039,161 bytes, 197,430 lines, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`: Kubernetes container output captured through Fluentd from a cluster running the OpenTelemetry demo, 36 containers, about ten hours. The same asset the [`splunk-license/`](../splunk-license/) and [`otel-denominators/`](../otel-denominators/) benchmarks run on.
