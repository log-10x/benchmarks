# CloudWatch Logs Infrequent Access accounting

Computed from the engine's counts at AWS list prices for us-east-1, read 2026-10-11. Nothing here was metered by AWS.

- engine image: `log10x/pipeline-10x@sha256:e2db543265cddd30a959c729c19e61d5f1b97e8be74a8d8e65dcb71a6466491c`
- MCP: log10x-mcp 1.30.46
- capture: `otel-sample-200mb.log`, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`, 197,430 lines, 157,228 events after grouping, 0.215 GB, 10 hours; a month is 720 hours; 1 GB = 1,000,000,000 bytes

## The result

| Target | Patterns planned | Containers | GB to IA | GB offloaded | GB in Standard | Errors and warnings moved | GB to IA per month | Ingest, IA rate per month | Ingest at Standard the same GB would cost | Ingest avoided by offload per month |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30% | 8 | 4 | 0.073 | 0.000 | 0.142 | 0 | 5.221 | $1.31 | $2.61 | $0.00 |
| 50% | 1005 | 24 | 0.014 | 0.072 | 0.129 | 0 | 0.980 | $0.24 | $0.49 | $2.61 |
| 70% | 1005 | 24 | 0.014 | 0.073 | 0.129 | 0 | 0.985 | $0.25 | $0.49 | $2.61 |

## Dollars per GB at list

| Line | Per GB | AWS's wording | Read |
|---|---:|---|---|
| Ingest, Standard | $0.50 | $0.50 per GB custom log data ingested in Standard log class - US East (Northern Virginia) | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/) |
| Ingest, Infrequent Access | $0.25 | $0.25 per GB custom log data ingested in Infrequent Access log class -US East (Northern Virginia) | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/) |
| Storage, per GB-month, both classes | $0.03 | $0.03 per GB-mo of log storage - US East (Northern Virginia); *0.15 compression ratio for each uncompressed byte; For charges, the Standard and Infrequent Access log classes differ in ingestion costs only. Storage charges and CloudWatch Logs Insights charges are the same in each log class. | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/), [classes](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Logs_Log_Classes.html) |
| Logs Insights, per GB scanned | $0.005 | $0.005 per GB log data scanned by CloudWatch Logs Insights queries - US East (Northern Virginia) | [2026-10-11](https://aws.amazon.com/cloudwatch/pricing/) |
| S3 Standard storage, per GB-month | $0.023 | $0.023 per GB - first 50 TB / month of storage used | [2026-10-11](https://aws.amazon.com/s3/pricing/) |
| S3 PUT, per 1,000 requests | $0.005 | $0.005 per 1,000 PUT, COPY, POST, or LIST requests | [2026-10-11](https://aws.amazon.com/s3/pricing/) |

The price list carries publication date 2026-10-07T11:55:40Z ([index.json](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/us-east-1/index.json)). After a log group is created, its log class can't be changed.

## Target 30%

**The plan.** The MCP sampled 9,563 events of the capture and planned 8 patterns, stating 30.7% of the bill: `Traces` (tier_down, INFO), `Logs` (tier_down, INFO), `cart_cartstore_ValkeyCartStore` (tier_down, INFO), `Metrics` (tier_down, INFO), `Receive_ListRecommendations_for_product_ids` (tier_down, INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (tier_down, TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (tier_down, TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO).
Its cap row reads `<container>,63128:tier_down:MCP poc_from_local soft`: 63,128 bytes per pattern per 240 s window, keyed `<container>`. The patterns are placed in the containers that produced them in the control run, a container takes the strongest action among its patterns (offload before tier_down), and the cap is multiplied by 150 because the replay delivers the 10-hour capture inside one window: 9,469,200 bytes per pattern.

| Container | Action | Patterns of the plan it hosts |
|---|---|---:|
| `ad` | tier_down | 2 |
| `kafka` | tier_down | 1 |
| `opentelemetry-collector` | tier_down | 3 |
| `recommendation` | tier_down | 1 |

**The engine.** 157,228 events replayed in 25 s; the records and the engine's aggregators agree on every one of 2,712 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 100,161 | 0.142 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 85,388, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 57,067 | 0.073 | INFO 57,067 |

Errors and warnings moved: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Route | Events | GB |
|---|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | tier_down | 25,959 | 0.033 |
| `Logs` | `opentelemetry-collector` | INFO | tier_down | 24,980 | 0.032 |
| `Metrics` | `opentelemetry-collector` | INFO | tier_down | 6,128 | 0.008 |

**A month at list.** 5.221 GB to Infrequent Access (4,108,824 events), 0.000 GB offloaded (0 events), 10.251 GB in Standard.

| Line | Per month |
|---|---:|
| Ingest, Standard, for what stays | $5.13 |
| Ingest, Infrequent Access, for the moved slice | $1.31 |
| Ingest at Standard, what the moved slice would have cost | $2.61 |
| Ingest avoided by offload | $0.00 |
| Storage for one month of data held one month, both classes, compressed at AWS's stated ratio | $0.07 |
| Logs Insights, one full scan of the IA slice | $0.03 |
| S3 storage for one month of offloaded data held one month | $0.00 |
| S3 PUT, 0 objects | $0.0000 |
| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | 106,829,424 bytes; not a billed quantity on any AWS page read |

## Target 50%

**The plan.** The MCP sampled 9,563 events of the capture and planned 1005 patterns, stating 52.42% of the bill: `Traces` (offload, INFO), `Logs` (tier_down, INFO), `cart_cartstore_ValkeyCartStore` (tier_down, INFO), `Metrics` (tier_down, INFO), `Receive_ListRecommendations_for_product_ids` (tier_down, INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (tier_down, TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (tier_down, TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (tier_down, INFO), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (tier_down, INFO), `Deleted_snapshot_files_for_offset_epoch_org_apache_kafka_Snapshots` (tier_down, INFO), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (tier_down, INFO), and 993 more.
Its cap row reads `<container>,63128:tier_down:MCP poc_from_local soft`: 63,128 bytes per pattern per 240 s window, keyed `<container>`. The patterns are placed in the containers that produced them in the control run, a container takes the strongest action among its patterns (offload before tier_down), and the cap is multiplied by 150 because the replay delivers the 10-hour capture inside one window: 9,469,200 bytes per pattern.

| Container | Action | Patterns of the plan it hosts |
|---|---|---:|
| `accounting` | tier_down | 23 |
| `ad` | tier_down | 3 |
| `aws-node` | tier_down | 2 |
| `aws-vpc-cni-init` | tier_down | 3 |
| `cart` | tier_down | 2 |
| `coredns` | tier_down | 4 |
| `email` | tier_down | 1 |
| `flagd` | tier_down | 5 |
| `flagd-ui` | tier_down | 1 |
| `fluentd-10x` | tier_down | 1 |
| `fraud-detection` | tier_down | 1 |
| `frontend-proxy` | tier_down | 55 |
| `grafana` | tier_down | 733 |
| `grafana-sc-alerts` | tier_down | 1 |
| `grafana-sc-dashboard` | tier_down | 2 |
| `grafana-sc-datasources` | tier_down | 5 |
| `image-provider` | tier_down | 1 |
| `jaeger` | tier_down | 27 |
| `kafka` | tier_down | 76 |
| `opensearch` | tier_down | 3 |
| `opentelemetry-collector` | offload | 3 |
| `prometheus-server` | tier_down | 5 |
| `recommendation` | tier_down | 1 |
| `valkey-cart` | tier_down | 5 |

**The engine.** 157,228 events replayed in 26 s; the records and the engine's aggregators agree on every one of 2,714 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| offload | 57,002 | 0.072 | INFO 57,002 |
| pass | 92,331 | 0.129 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 77,558, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 7,895 | 0.014 | INFO 7,895 |

Errors and warnings moved: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Route | Events | GB |
|---|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | offload | 26,007 | 0.033 |
| `Logs` | `opentelemetry-collector` | INFO | offload | 24,881 | 0.032 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | tier_down | 6,490 | 0.011 |
| `Metrics` | `opentelemetry-collector` | INFO | offload | 6,114 | 0.008 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | tier_down | 1,405 | 0.002 |

**A month at list.** 0.980 GB to Infrequent Access (568,440 events), 5.215 GB offloaded (4,104,144 events), 9.277 GB in Standard.

| Line | Per month |
|---|---:|
| Ingest, Standard, for what stays | $4.64 |
| Ingest, Infrequent Access, for the moved slice | $0.24 |
| Ingest at Standard, what the moved slice would have cost | $0.49 |
| Ingest avoided by offload | $2.61 |
| Storage for one month of data held one month, both classes, compressed at AWS's stated ratio | $0.05 |
| Logs Insights, one full scan of the IA slice | $0.00 |
| S3 storage for one month of offloaded data held one month | $0.12 |
| S3 PUT, 4,320 objects | $0.0216 |
| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | 14,779,440 bytes; not a billed quantity on any AWS page read |

## Target 70%

**The plan.** The MCP sampled 9,563 events of the capture and planned 1005 patterns, stating 70.34% of the bill: `Traces` (offload, INFO), `Logs` (offload, INFO), `cart_cartstore_ValkeyCartStore` (offload, INFO), `Metrics` (offload, INFO), `Receive_ListRecommendations_for_product_ids` (tier_down, INFO), `oteldemo_AdService_Targeted_ad_request_received_for` (tier_down, TRACE), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (tier_down, TRACE), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (tier_down, INFO), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (tier_down, INFO), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (tier_down, INFO), `Deleted_snapshot_files_for_offset_epoch_org_apache_kafka_Snapshots` (tier_down, INFO), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (tier_down, INFO), and 993 more.
Its cap row reads `<container>,63128:tier_down:MCP poc_from_local soft`: 63,128 bytes per pattern per 240 s window, keyed `<container>`. The patterns are placed in the containers that produced them in the control run, a container takes the strongest action among its patterns (offload before tier_down), and the cap is multiplied by 150 because the replay delivers the 10-hour capture inside one window: 9,469,200 bytes per pattern.

| Container | Action | Patterns of the plan it hosts |
|---|---|---:|
| `accounting` | tier_down | 23 |
| `ad` | tier_down | 3 |
| `aws-node` | tier_down | 2 |
| `aws-vpc-cni-init` | tier_down | 3 |
| `cart` | tier_down | 2 |
| `coredns` | tier_down | 4 |
| `email` | tier_down | 1 |
| `flagd` | tier_down | 5 |
| `flagd-ui` | tier_down | 1 |
| `fluentd-10x` | tier_down | 1 |
| `fraud-detection` | tier_down | 1 |
| `frontend-proxy` | tier_down | 55 |
| `grafana` | tier_down | 733 |
| `grafana-sc-alerts` | tier_down | 1 |
| `grafana-sc-dashboard` | tier_down | 2 |
| `grafana-sc-datasources` | tier_down | 5 |
| `image-provider` | tier_down | 1 |
| `jaeger` | tier_down | 27 |
| `kafka` | tier_down | 76 |
| `opensearch` | tier_down | 3 |
| `opentelemetry-collector` | offload | 3 |
| `prometheus-server` | tier_down | 5 |
| `recommendation` | tier_down | 1 |
| `valkey-cart` | tier_down | 5 |

**The engine.** 157,228 events replayed in 27 s; the records and the engine's aggregators agree on every one of 2,714 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| offload | 57,113 | 0.073 | INFO 57,113 |
| pass | 92,181 | 0.129 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 77,408, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 7,934 | 0.014 | INFO 7,934 |

Errors and warnings moved: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Route | Events | GB |
|---|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | offload | 26,046 | 0.033 |
| `Logs` | `opentelemetry-collector` | INFO | offload | 24,939 | 0.032 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | tier_down | 6,533 | 0.011 |
| `Metrics` | `opentelemetry-collector` | INFO | offload | 6,128 | 0.008 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | tier_down | 1,401 | 0.002 |

**A month at list.** 0.985 GB to Infrequent Access (571,248 events), 5.225 GB offloaded (4,112,136 events), 9.262 GB in Standard.

| Line | Per month |
|---|---:|
| Ingest, Standard, for what stays | $4.63 |
| Ingest, Infrequent Access, for the moved slice | $0.25 |
| Ingest at Standard, what the moved slice would have cost | $0.49 |
| Ingest avoided by offload | $2.61 |
| Storage for one month of data held one month, both classes, compressed at AWS's stated ratio | $0.05 |
| Logs Insights, one full scan of the IA slice | $0.00 |
| S3 storage for one month of offloaded data held one month | $0.12 |
| S3 PUT, 4,320 objects | $0.0216 |
| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | 14,852,448 bytes; not a billed quantity on any AWS page read |

## What Infrequent Access lacks

From AWS's log class table ([2026-10-11](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Logs_Log_Classes.html)), marked "No" for Infrequent Access: Facets, Natural language query assist, CloudWatch Logs Anomaly Detection, Live Tail, Field indexing, Compare to previous time range, Subscription filters, Metric filters, Container Insights log ingestion, Lambda Insights log ingestion, Embedded metrics format, GetLogEvents and FilterLogEvents API operations, Logs Insights commands pattern, diff, filterIndex and unmask.
Supported in both classes: CloudWatch Logs Insights queries, most commands, CloudWatch pipelines, Export to Amazon S3, S3 Tables integration, Scheduled queries, Encryption with AWS KMS, Sensitive data protection with masking, Cross-account features.

## Counting conditions

- CloudWatch bills ingestion by the bytes of each event message. Bytes here are the UTF-8 size of each record the engine emitted; with the shipped forwarder path the forwarder sends that record as the event message.
- The 26 bytes per event in the PutLogEvents batch-size rule are shown as a separate line. No sentence on the pricing page or the billing page says these bytes are billed; the billed usage type is DataProcessing-Bytes for PutLogEvents. ([2026-10-11](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutLogEvents.html))
- The split is forwarder-side: the `tenx.tier_down` tag goes to a log group in the Infrequent Access class, `tenx.offload` to the S3 output, and the class is fixed when the group is created.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its pattern's cap takes the container's action. Patterns under 5% of their container's bytes in the window are not capped, the first 5 events of a pattern in a window pass, and the severity floors keep a share of each level: a tenth of INFO, DEBUG and TRACE, three tenths of WARN, half of ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within that noise.
- The replay delivers the capture inside one window; the plan's cap is scaled by the window the MCP was told the capture covers, as the policy files record.
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
