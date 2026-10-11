# Datadog Flex Logs accounting

Computed from the engine's counts at Datadog list prices read 2026-10-11. Nothing here was metered by Datadog.

- engine image: `log10x/pipeline-10x@sha256:fd9c98384a775df13ed41921c2cf95ef1d1313f62f1300aac61da55ca64feb67`
- MCP: log10x-mcp 1.30.48
- capture: `otel-sample-200mb.log`, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`, 197,430 lines, 157,228 events after grouping, 0.215 GB, 10 hours; a month is 720 hours; 1 GB = 1,000,000,000 bytes

## What a moved event costs at list

| Line | Annual | On-demand | Datadog's wording | Read |
|---|---:|---:|---|---|
| Standard indexing avoided, 3-day retention, per million events | $1.06 | $1.59 | Per 1M indexed logs (3-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Standard indexing avoided, 7-day retention, per million events | $1.27 | $1.91 | Per 1M indexed logs (7-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Standard indexing avoided, 15-day retention, per million events | $1.70 | $2.55 | Per 1M indexed logs (15-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Standard indexing avoided, 30-day retention, per million events | $2.50 | $3.75 | Per 1M indexed logs (30-day retention), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Flex storage added, per million events stored per month | $0.05 | $0.075 | Per 1 M events stored, per month; Each million events stored is billed for a minimum of 30 days, or a minimum of $0.05. | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Flex Starter, per million events stored per month, compute bundled | $0.60 | $0.90 | Per 1 M events stored (6, 12 or 15 months retention), per month; Bundled Starter Compute for log volumes below 2B per month (10B total stored) | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Flex compute, XS to L | Contact Us for Pricing | Contact Us for Pricing | Per instance-hour, per month | [2026-10-11](https://www.datadoghq.com/pricing/?product=log-management) |
| Ingestion, per GB, unchanged by a move | $0.10 | $0.10 | Per ingested logs (1GB), per month | [2026-10-11](https://www.datadoghq.com/pricing/list/) |
| Custom metrics, per 100 per month above the allotment | $5.00 | $5.00 | Per 100 custom metrics, per month; Pro: 100 ingested custom metrics per host and 100 indexed custom metrics per host; Enterprise: 200 ingested custom metrics per host and 200 indexed custom metrics per host | [2026-10-11](https://www.datadoghq.com/pricing/list/) |

Flex compute sizes by cumulative events stored, from Datadog's own table: Starter under 10 billion, XS 10 to 50 billion, XS+ 50 to 100 billion, S 100 to 200 billion, M 200 to 500 billion, L 500 to 1000 billion. Starter is bundled storage and compute for volumes below 2 billion events a month. [2026-10-11](https://docs.datadoghq.com/logs/log_configuration/flex_logs/)

## What moves, per target

| Target | Patterns planned | Containers capped | Events the plan states | Events the engine marked tier_down | GB to Flex | Events in Standard | Errors and warnings to Flex | Custom metrics the output publishes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30% | 3 | 1 | 60,783 | 67,505 | 0.086 | 89,723 | 0 | 768 |
| 50% | 7 | 4 | 82,585 | 90,555 | 0.121 | 66,673 | 0 | 786 |
| 70% | 55 | 17 | 112,944 | 119,833 | 0.153 | 37,395 | 0 | 780 |

The engine moves each pattern's excess over its container's cap; the plan sets the cap at the largest pattern the container keeps and states the excess, less the share the severity floors keep. Ingestion is unchanged: every event is ingested once, at $0.10 per GB, before any index routing.

## A month at this capture's volume, an illustration

The capture's 10 hours scaled to a 720-hour month, at the rates above. The volume is one small demo cluster's; the rates are what carry.

| Target | Events to Flex per month | Standard indexing avoided, 15-day annual | Flex storage added, annual | Flex compute tier | Ingestion, unchanged | Custom metrics above a Pro allotment, 10 to 300 nodes |
|---:|---:|---:|---:|---|---:|---:|
| 30% | 4,860,360 | $8.26 | $0.24 | Starter | $1.55 | $0 to $0 |
| 50% | 6,519,960 | $11.08 | $0.33 | Starter | $1.55 | $0 to $0 |
| 70% | 8,627,976 | $14.67 | $0.43 | Starter | $1.55 | $0 to $0 |

**Custom metrics.** The engine's shipped Datadog output, posting to a local stand-in for Datadog's intake, tagged each series with the pattern and where it ran (`k8s_container`, `k8s_namespace`, `message_pattern`, `routeState`, `severity_level`, `statistic`, `tenx_hash`, `tenx_reported_name`, `tenx_user_service`) and with nothing that names a node or a process, and published the 200 tag sets with the most bytes, each from both aggregators: at most 768 series in one post, whatever the node count; the top 200 label sets carry 98.8% of the bytes. Above a Pro plan's allotment of 100 per host that is $0 a month at 10 nodes, $0 at 100 and $0 at 300. Every tag set from every node would be 10,848 per node: $5,374, $53,740 and $161,220 a month.

## Target 30%

**The plan.** The MCP sampled 9,563 events of the capture and planned 3 patterns for Flex, stating 40.32% of the Standard-index volume and 60,783 events moved: `Traces` (INFO, `opentelemetry-collector`), `Logs` (INFO, `opentelemetry-collector`), `Metrics` (INFO, `opentelemetry-collector`).
Its engine files, as written (a cap is bytes per pattern per 240 s window over the 1 hours the plan covers; the replay multiplies each cap by 15 because it delivers the capture inside one window):

```
container,cap
opentelemetry-collector,304617::MCP poc_from_local plan 30 pct
container,action
opentelemetry-collector,tier_down::MCP poc_from_local plan 30 pct
```

**The engine.** 157,228 events replayed in 28 s; the records and the engine's aggregators agree on every one of 2,712 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 89,723 | 0.129 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 74,950, TRACE 7,113, WARN 217, none 1,087 |
| tier_down | 67,505 | 0.086 | INFO 67,505 |

Errors and warnings marked tier_down: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Events | GB |
|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | 29,521 | 0.037 |
| `Logs` | `opentelemetry-collector` | INFO | 28,460 | 0.036 |
| `Metrics` | `opentelemetry-collector` | INFO | 9,524 | 0.012 |

**A month at this volume, an illustration.** 4,860,360 events to Flex (6.180 GB), 6,460,056 in Standard, 15.472 GB ingested.

| Line | Per month |
|---|---:|
| Standard indexing avoided, 15-day, annual | $8.26 |
| Standard indexing avoided, 15-day, on-demand | $12.39 |
| Standard indexing avoided, 30-day, annual | $12.15 |
| Standard indexing avoided, 30-day, on-demand | $18.23 |
| Flex storage added, held 30 days, annual | $0.24 |
| Flex storage added, held 30 days, on-demand | $0.36 |
| Flex Starter instead of storage plus compute, annual | $2.92 |
| Flex compute tier at 4,860,360 events stored | Starter, within Starter; Contact Us for Pricing for XS and above |
| Ingestion, unchanged | $1.55 |
| Custom metrics from the engine's Datadog metric output, measured | at most 768 series in one of 4 posts, 1,386 distinct over the replay while ranks settle, the same from every node; above a Pro allotment $0 at 10 nodes, $0 at 300. Every tag set would be 10,848 per node |

## Target 50%

**The plan.** The MCP sampled 9,563 events of the capture and planned 7 patterns for Flex, stating 50.56% of the Standard-index volume and 82,585 events moved: `Traces` (INFO, `opentelemetry-collector`), `Logs` (INFO, `opentelemetry-collector`), `Metrics` (INFO, `opentelemetry-collector`), `cart_cartstore_ValkeyCartStore` (INFO, `cart`), `Receive_ListRecommendations_for_product_ids` (INFO, `recommendation`), `oteldemo_AdService_Targeted_ad_request_received_for` (TRACE, `ad`), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (TRACE, `ad`).
Its engine files, as written (a cap is bytes per pattern per 240 s window over the 1 hours the plan covers; the replay multiplies each cap by 15 because it delivers the capture inside one window):

```
container,cap
ad,50331::MCP poc_from_local plan 50 pct
cart,134598::MCP poc_from_local plan 50 pct
opentelemetry-collector,304617::MCP poc_from_local plan 50 pct
recommendation,1::MCP poc_from_local plan 50 pct
container,action
ad,tier_down::MCP poc_from_local plan 50 pct
cart,tier_down::MCP poc_from_local plan 50 pct
opentelemetry-collector,tier_down::MCP poc_from_local plan 50 pct
recommendation,tier_down::MCP poc_from_local plan 50 pct
```

**The engine.** 157,228 events replayed in 29 s; the records and the engine's aggregators agree on every one of 2,717 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 66,673 | 0.094 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 56,403, TRACE 2,610, WARN 217, none 1,087 |
| tier_down | 90,555 | 0.121 | INFO 86,052, TRACE 4,503 |

Errors and warnings marked tier_down: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Events | GB |
|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | 29,488 | 0.037 |
| `Logs` | `opentelemetry-collector` | INFO | 28,392 | 0.036 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | 10,375 | 0.018 |
| `Metrics` | `opentelemetry-collector` | INFO | 9,514 | 0.012 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | 5,206 | 0.009 |
| `Receive_ListRecommendations_for_product_ids` | `recommendation` | INFO | 3,077 | 0.004 |
| `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` | `ad` | TRACE | 2,468 | 0.002 |
| `oteldemo_AdService_Targeted_ad_request_received_for` | `ad` | TRACE | 2,035 | 0.002 |

**A month at this volume, an illustration.** 6,519,960 events to Flex (8.686 GB), 4,800,456 in Standard, 15.472 GB ingested.

| Line | Per month |
|---|---:|
| Standard indexing avoided, 15-day, annual | $11.08 |
| Standard indexing avoided, 15-day, on-demand | $16.63 |
| Standard indexing avoided, 30-day, annual | $16.30 |
| Standard indexing avoided, 30-day, on-demand | $24.45 |
| Flex storage added, held 30 days, annual | $0.33 |
| Flex storage added, held 30 days, on-demand | $0.49 |
| Flex Starter instead of storage plus compute, annual | $3.91 |
| Flex compute tier at 6,519,960 events stored | Starter, within Starter; Contact Us for Pricing for XS and above |
| Ingestion, unchanged | $1.55 |
| Custom metrics from the engine's Datadog metric output, measured | at most 786 series in one of 5 posts, 1,424 distinct over the replay while ranks settle, the same from every node; above a Pro allotment $0 at 10 nodes, $0 at 300. Every tag set would be 10,868 per node |

## Target 70%

**The plan.** The MCP sampled 9,563 events of the capture and planned 55 patterns for Flex, stating 68.4% of the Standard-index volume and 112,944 events moved: `Traces` (INFO, `opentelemetry-collector`), `Logs` (INFO, `opentelemetry-collector`), `Metrics` (INFO, `opentelemetry-collector`), `cart_cartstore_ValkeyCartStore` (INFO, `cart`), `Receive_ListRecommendations_for_product_ids` (INFO, `recommendation`), `oteldemo_AdService_Targeted_ad_request_received_for` (TRACE, `ad`), `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` (TRACE, `ad`), `Deleted_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (INFO, `kafka`), `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` (INFO, `kafka`), `Deleting_segments_due_to_log_start_offset_breach_LogSegment_baseOffset_size_lastModifiedTime_kafka_UnifiedLog` (INFO, `kafka`), `Deleted_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (INFO, `kafka`), `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_apache_storage_internals_log_SnapshotFile` (INFO, `kafka`), `Rolled_new_log_segment_at_offset_in_ms_kafka_LocalLog` (INFO, `kafka`), `Deleted_snapshot_files_for_offset_epoch_org_apache_kafka_Snapshots` (INFO, `kafka`), `Deleted_offset_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` (INFO, `kafka`), `Successfully_wrote_snapshot_org_apache_kafka_image_publisher_SnapshotEmitter` (INFO, `kafka`), `GetCartAsync_called_with_userId` (INFO, `cart`), `Creating_new_KRaft_snapshot_file_because_we_have_replayed_at_least_bytes_org_apache_kafka_image_publisher_SnapshotGenerator` (INFO, `kafka`), `older_than_the` (INFO, `kafka`), `Deleting_segment_files_LogSegment_baseOffset_size_lastModifiedTime_kafka_LocalLog` (INFO, `kafka`), `AddItemAsync_called_with_userId_productId_quantity` (INFO, `cart`), `Incremented_log_start_offset_to_due_snapshot_generated_kafka_UnifiedLog` (INFO, `kafka`), `stats_cache_size_pod_api_updates_id_miss` (INFO, `fluentd-10x`), `oteldemo_AdService_Non_targeted_ad_request_received_preparing_random_response_trace_id_span_flags` (TRACE, `ad`), `description_Fail_product_catalog_service_on_a_specific` (no level, `flagd`), `fail_Accounting_Consumer` (INFO, `accounting`), `javaagent_tooling_VersionLogger_opentelemetry_version_Defaulting_to_no_operation_NOP_logger_implementation_waiting_for_kafka` (INFO, `fraud-detection`), `stream_stdout_log_docker` (no level, `image-provider`), `Loading_producer_state_till_offset_with_message_format_version_kafka_log_UnifiedLog` (INFO, `(unattributed)`), `Background_saving_terminated_with_success` (no level, `valkey-cart`), `Created_log_for_partition_consumer_in_tmp_kafka_logs_with_properties_LogManager` (INFO, `(unattributed)`), `plugin_kubernetes_waiting_for_Kubernetes_API_before_starting_server` (INFO, `coredns`), `Log_loaded_for_partition_consumer_with_initial_high_watermark_kafka_cluster_Partition` (INFO, `(unattributed)`), `No_checkpointed_highwatermark_is_found_for_partition_consumer_kafka_cluster_Partition` (INFO, `(unattributed)`), `Running_full_sweep` (INFO, `opensearch`), `Fork_CoW_RDB_current_peak_MB_average` (no level, `valkey-cart`), `changes_seconds_Saving` (no level, `valkey-cart`), `DB_saved_on_disk` (no level, `valkey-cart`), `Background_saving_started_by_pid` (no level, `valkey-cart`), `OTEL_COLLECTOR_PORT` (no level, `accounting`), `Starting_housekeeping_task_for_auto_refresh_streaming_jobs` (INFO, `opensearch`), `OTEL_COLLECTOR_tcp` (no level, `accounting`), `OpenTelemetry_Instrumentation_Sinatra_was_successfully_installed_with_the_following_options` (INFO, `email`), `runtime_layers_static_layer_resource_limits_example_listener_name` (INFO, `frontend-proxy`), `stream_stdout_log_docker_kubernetes_image` (no level, `image-provider`), `Finished_housekeeping_task_for_auto_refresh_streaming_jobs` (INFO, `opensearch`), `Resolver_state_updated_Addresses_Addr_localhost_ServerName_Attributes_null_BalancerAttributes_Metadata_Endpoints_ServiceConfig_resolver` (INFO, `jaeger`), `Subchannel_Connectivity_change_to_READY_system_grpc_log_true_User_Setting_default_values_of_environment_variables_if_not_already` (INFO, `jaeger`), `Subchannel_picks_a_new_address_localhost_to_connect_system_grpc_log_true` (INFO, `jaeger`), `Serving_metrics_on_port_Installed_host_opt_cni_bin_egress` (INFO, `aws-node`), `Successfully_copied_CNI_plugin_binary_and_config_file` (INFO, `aws-node`), `Checking_for_IPAM_connectivity` (INFO, `aws-node`), `Copied_all_CNI_plugin_binaries_to_host_opt_cni_bin` (INFO, `aws-node`), `Updated_net_tcp_early_demux_to_n` (INFO, `aws-node`), `Found_eth` (INFO, `aws-node`).
Its engine files, as written (a cap is bytes per pattern per 240 s window over the 1 hours the plan covers; the replay multiplies each cap by 15 because it delivers the capture inside one window):

```
container,cap
accounting,2018::MCP poc_from_local plan 70 pct
ad,2957::MCP poc_from_local plan 70 pct
aws-node,1::MCP poc_from_local plan 70 pct
cart,22315::MCP poc_from_local plan 70 pct
coredns,5013::MCP poc_from_local plan 70 pct
email,991::MCP poc_from_local plan 70 pct
flagd,1088::MCP poc_from_local plan 70 pct
fluentd-10x,1::MCP poc_from_local plan 70 pct
fraud-detection,1::MCP poc_from_local plan 70 pct
frontend-proxy,2491::MCP poc_from_local plan 70 pct
image-provider,1::MCP poc_from_local plan 70 pct
jaeger,2322::MCP poc_from_local plan 70 pct
kafka,4288::MCP poc_from_local plan 70 pct
opensearch,1::MCP poc_from_local plan 70 pct
opentelemetry-collector,304617::MCP poc_from_local plan 70 pct
recommendation,1::MCP poc_from_local plan 70 pct
valkey-cart,1::MCP poc_from_local plan 70 pct
container,action
accounting,tier_down::MCP poc_from_local plan 70 pct
ad,tier_down::MCP poc_from_local plan 70 pct
aws-node,tier_down::MCP poc_from_local plan 70 pct
cart,tier_down::MCP poc_from_local plan 70 pct
coredns,tier_down::MCP poc_from_local plan 70 pct
email,tier_down::MCP poc_from_local plan 70 pct
flagd,tier_down::MCP poc_from_local plan 70 pct
fluentd-10x,tier_down::MCP poc_from_local plan 70 pct
fraud-detection,tier_down::MCP poc_from_local plan 70 pct
frontend-proxy,tier_down::MCP poc_from_local plan 70 pct
image-provider,tier_down::MCP poc_from_local plan 70 pct
jaeger,tier_down::MCP poc_from_local plan 70 pct
kafka,tier_down::MCP poc_from_local plan 70 pct
opensearch,tier_down::MCP poc_from_local plan 70 pct
opentelemetry-collector,tier_down::MCP poc_from_local plan 70 pct
recommendation,tier_down::MCP poc_from_local plan 70 pct
valkey-cart,tier_down::MCP poc_from_local plan 70 pct
```

**The engine.** 157,228 events replayed in 32 s; the records and the engine's aggregators agree on every one of 2,743 keys.

| Route | Events | GB | Events by severity |
|---|---:|---:|---|
| pass | 37,395 | 0.062 | CRITICAL 2,324, DEBUG 2, ERROR 4,030, INFO 29,447, TRACE 820, WARN 217, none 555 |
| tier_down | 119,833 | 0.153 | INFO 113,008, TRACE 6,293, none 532 |

Errors and warnings marked tier_down: 0. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container's action.

| Pattern moved | Container | Severity | Events | GB |
|---|---|---|---:|---:|
| `Traces` | `opentelemetry-collector` | INFO | 29,490 | 0.037 |
| `Logs` | `opentelemetry-collector` | INFO | 28,413 | 0.036 |
| `GetCartAsync_called_with_userId` | `cart` | INFO | 11,306 | 0.019 |
| `Metrics` | `opentelemetry-collector` | INFO | 9,570 | 0.012 |
| `AddItemAsync_called_with_userId_productId_quantity` | `cart` | INFO | 6,036 | 0.011 |
| `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags` | `ad` | TRACE | 3,161 | 0.003 |
| `Receive_ListRecommendations_for_product_ids` | `recommendation` | INFO | 3,107 | 0.004 |
| `oteldemo_AdService_Targeted_ad_request_received_for` | `ad` | TRACE | 2,719 | 0.003 |
| `Deleted_offset_index_tmp_cluster_org_apache_kafka_storage_internals_log_LogSegment` | `kafka` | INFO | 2,150 | 0.002 |
| `Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager` | `kafka` | INFO | 2,141 | 0.002 |

**A month at this volume, an illustration.** 8,627,976 events to Flex (11.016 GB), 2,692,440 in Standard, 15.472 GB ingested.

| Line | Per month |
|---|---:|
| Standard indexing avoided, 15-day, annual | $14.67 |
| Standard indexing avoided, 15-day, on-demand | $22 |
| Standard indexing avoided, 30-day, annual | $21.57 |
| Standard indexing avoided, 30-day, on-demand | $32.35 |
| Flex storage added, held 30 days, annual | $0.43 |
| Flex storage added, held 30 days, on-demand | $0.65 |
| Flex Starter instead of storage plus compute, annual | $5.18 |
| Flex compute tier at 8,627,976 events stored | Starter, within Starter; Contact Us for Pricing for XS and above |
| Ingestion, unchanged | $1.55 |
| Custom metrics from the engine's Datadog metric output, measured | at most 780 series in one of 4 posts, 1,590 distinct over the replay while ranks settle, the same from every node; above a Pro allotment $0 at 10 nodes, $0 at 300. Every tag set would be 10,972 per node |

## Custom metrics

The engine's Datadog metric output publishes two counters, event volume and bytes, for each label set of two aggregators, `all_events` and `emitted_events`. A custom metric is uniquely identified by a combination of a metric name and tag values (including the host tag). On this capture the control run produced 2,709 label sets in `all_events` and 2,709 in `emitted_events`, 10,836 custom metrics from one node. A move splits label sets by route, so each target's count is in its table. Custom metrics are counted hourly and averaged monthly across your entire account, not on a per-host basis. Metrics created from ingested logs are billed as Custom Metrics.

## Counting conditions

- Datadog counts indexed events: "At the end of the month, Datadog computes the total number of log events that have been indexed" ([2026-10-11](https://docs.datadoghq.com/account_management/billing/log_management/)). With the shipped forwarder path one record is one event; the Receiver groups the lines of a multi-line event into one record, and the engine counted 157,228 records from 197,430 lines here.
- The Flex route is the documented index filter on `@routeState:tier_down`, applied to a Flex index listed before the Standard one. Every event the engine marks `tier_down` carries that field to Datadog.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its pattern's cap takes the container's action. Patterns under 5% of their container's bytes in the window are not capped, the first 5 events of a pattern in a window pass, and the severity floors keep a share of each level: a tenth of INFO, DEBUG and TRACE, three tenths of WARN, half of ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within that noise.
- The replay delivers the capture inside one window; each cap the plan wrote is multiplied by the span the plan covers over 240 s, and nothing else in the plan's files is changed. `results/policy-*.json` records the files and the factor.
- Events and GB are the engine's counts of the records it emitted; dollars are those counts at list price. A month is 720 hours; the capture covers 10.

## Reproduce

```sh
./run.sh                 # everything
./run.sh plan replay     # some stages, in the order given
```

Stages: `data plan control policy replay count metrics report`. Needs Docker, Node 18 or later and about 1 GB of disk. `plan` installs the pinned log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; the server runs the pinned engine image for its own sampling. Every other stage runs the engine image on the capture. `ACCT_TARGETS` sets the targets (default `30 50 70`), `ACCT_WINDOW` the span the capture covers (default `10h`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `prices.json` | every price used, with its URL and the date read |
| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |
| `../accounting-lib/plan.mjs` | asks the released MCP for its plan over stdio and keeps what it wrote |
| `../accounting-lib/replay.config.yaml` | the engine run: shipped enrichment, regulator and aggregators, file in, file out |
| `../accounting-lib/policy.py` | the engine files the tool wrote, caps scaled to the one-window replay |
| `../accounting-lib/count.py` | the two counts, records and aggregators, required to agree |
| `../accounting-lib/ddcapture.py`, `datadog_config.py`, `datadog_series.py` | the `metrics` stage: a local stand-in for Datadog's intake, the shipped Datadog config with only its URI pointed at it, and the count of what was posted |
| `results/datadog-series-<run>.json`, `results/datadog-config.diff` | the series each post carried, and the one line changed in the shipped config |
| `results/plan-<target>.json` | the plan the MCP wrote, its notes and the caps row it rendered |
| `results/policy-<target>.caps.csv`, `.actions.csv`, `.json` | the files the engine read |
| `results/<target>.tally.json`, `results/control.tally.json` | the counts per route, container, severity and pattern |

## Data

`otel-sample-200mb.log` from [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1), 215,039,161 bytes, 197,430 lines, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`: Kubernetes container output captured through Fluentd from a cluster running the OpenTelemetry demo, 36 containers, about ten hours. The same asset the [`splunk-license/`](../splunk-license/) and [`otel-denominators/`](../otel-denominators/) benchmarks run on.
