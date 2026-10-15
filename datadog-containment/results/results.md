# Containment demo: a fleet-default cap on the OpenTelemetry demo's own incidents

All figures below come from this run's files in `results/` and are rendered by `rig/report.py` from `rig/analyze.py`'s `analysis.json`.

## What ran

- OpenTelemetry demo 3.1.0 (`compose.yaml` + `compose.full.yaml`), every container's stdout and stderr through the Docker `fluentd` driver to Fluent Bit 4.2, which keeps a raw copy, hands each record to the log10x Receiver and writes what comes back to one file per `routeState`.
- Receiver: `log10x/edge-10x:1.1.142@sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`, the released image with its own config and modules, launched with the values log10x-mcp 1.30.58 renders (below).
- Plan: log10x-mcp 1.30.58 `poc_from_local` on the quiet capture with `{"headroom": 2, "action": "offload", "error_floor": 0.5}`, engine `log10x/edge-10x:1.1.142@sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`.
- Scheduler: flagd-ui, seed 20261014, interval 600 s, hold 240 to 480 s, one flag at a time, flags kafkaQueueProblems (on), cartFailure (100%), paymentFailure (100%), recommendationCacheFailure (on), loadGeneratorFloodHomepage (on), emailMemoryLeak (1000x). Scheduled run 10:56:11 to 12:11:16 UTC on 2026-10-15.

## Timeline (UTC)

| event | at |
|---|---|
| receiver_ready | 10:28:16 |
| demo_up | 10:30:52 |
| demo_healthy | 10:31:48 |
| quiet_start | 10:33:48 |
| quiet_end | 10:55:48 |
| receiver_ready | 10:56:09 |
| scheduler_start | 10:56:11 |
| planned_end | 12:11:11 |
| scheduler_stop | 12:11:14 |
| run_end | 12:11:16 |
| demo_down | 12:11:57 |

## Quiet run and the fleet default

Quiet run 10:33:48 to 10:55:48 UTC, no flag active, Receiver with no cap: 9,676 raw lines, 8,424 returned records, 47 (container, pattern) pairs in 16 containers, 5 full 4-minute windows, 0 records held.

The POC on that capture: `met: true`, 70.3% reached against the 70% target, keep-everything lever `tier_down`; 39 planned and 9 kept statements.

| fleet default | value |
|---|---|
| `cap_bytes_per_window_per_node` | **25,960** |
| baseline | 12,979.8 bytes per window: `error_Error_scraping_metrics` in otel-collector |
| headroom, action, error floor | 2, `offload`, 0.5 |
| sentence | Any service not listed: a statement above 6,084 lines a day goes to the offload bucket. Up to 1,800 lines a day of every statement always reach Standard on each node. |
| the baseline statement in the Receiver's unit (quiet run) | 8,518 record bytes per window on average, 11,444 at most |

The 20 largest (container, pattern) pairs of the quiet run, by their largest 4-minute window in the bytes the Receiver counts (the compact JSON of the record as it arrives), with the rule that covers each in the scheduled run:

| container | pattern | rule | largest window: events | bytes |
|---|---|---|---|---|
| otel-collector | `KG8Fq0QFuoY` Logs | plan row: otel-collector, cap 37,330, tier_down | 240 | 126,260 |
| otel-collector | `Gl3Gtr_SH5w` Traces | plan row: otel-collector, cap 37,330, tier_down | 240 | 126,055 |
| frontend | `INl44sUgFeY` API_request_completed | plan row: frontend, cap 1, tier_down | 253 | 124,788 |
| otel-collector | `PuWB8kkVbfw` Metrics | plan row: otel-collector, cap 37,330, tier_down | 190 | 105,153 |
| cart | `YZplfQ4a1Xw` GetCartAsync_called_with_userId | plan row: cart, cap 1, tier_down | 98 | 28,010 |
| accounting | `-FtZD9XArpU` Order_details | plan row: accounting, cap 3,866, tier_down | 19 | 17,769 |
| cart | `eDSYlCMPqVY` AddItemAsync_called_with_userId_productId_quantity | plan row: cart, cap 1, tier_down | 54 | 17,720 |
| recommendation | `bzLB1zZCTIw` Receive_ListRecommendations_for_product_ids | plan row: recommendation, cap 1, tier_down | 30 | 14,640 |
| payment | `9WbTsopbiXk` Transaction_complete | plan row: payment, cap 2,731, tier_down | 19 | 12,860 |
| telemetry-docs | `zxRYTKQNyBY` GET_HTTP_Wget | plan row: telemetry-docs, cap 1, tier_down | 48 | 12,528 |
| astronomy-db | `oUkuI8QT6s8` role_root_does_not_exist | fleet default: 25,960, offload | 48 | 12,000 |
| otel-collector | `fhu6rrW86b4` error_Error_scraping_metrics | plan row: otel-collector, cap 37,330, tier_down | 7 | 11,444 |
| frontend | `KSy6KmHbgEc` Order_placed_successfully | plan row: frontend, cap 1, tier_down | 19 | 8,645 |
| ad | `xHrytxJfUdw` oteldemo_AdService_Targeted_ad_request_received_fo | plan row: ad, cap 1, tier_down | 25 | 8,460 |
| payment | `fg1YkiyrF3Q` Charge_request_received | plan row: payment, cap 2,731, tier_down | 19 | 8,151 |
| shipping | `kAB8PMmHyKM` shipping_service_Requesting_quote_http_getquote | plan row: shipping, cap 3,879, tier_down | 19 | 7,961 |
| shipping | `LnOvjJt0La4` Tracking_ID_Created | plan row: shipping, cap 3,879, tier_down | 19 | 7,942 |
| shipping | `PX-oZ7rxgZo` Sending_Quote | plan row: shipping, cap 3,879, tier_down | 19 | 7,890 |
| fraud-detection | `GKfNbCrpxxI` fraud_detection_Consumed_record_with_orderId_and_u | plan row: fraud-detection, cap 1, tier_down | 19 | 7,657 |
| kafka | `pFokWfyJRLU` Deleting_segments_due_to_log_start_offset_breach_L | plan row: kafka, cap 1,669, tier_down | 13 | 6,715 |

## The values the Receiver ran with

Rendered by log10x-mcp 1.30.58 (`receiverFleetValues` with the POC's `fleet_default`, then the Fluent Bit Receiver overlay's `renderValues`, the two calls `log10x_advise_install` makes; `results/values-fleet/values.yaml` is the overlay verbatim). Arguments, in order:

```text
@run/input/forwarder/fluentbit
@apps/receiver
symbolMessageHashField
tenx_hash
rateReceiverAbsoluteCap
25960
rateReceiverDefaultAction
offload
rateReceiverMinSharePercent
0
rateReceiverWarmupMs
0
rateReceiverBaselineCount
5
rateReceiverMinRetentionThreshold
0
rateReceiverSeverityFloors
TRACE=0
rateReceiverSeverityFloors
DEBUG=0
rateReceiverSeverityFloors
INFO=0
rateReceiverSeverityFloors
WARN=0
rateReceiverSeverityFloors
ERROR=0.5
rateReceiverSeverityFloors
CRITICAL=0.5
rateReceiverSeverityFloors
FATAL=0.5
```

Environment from the values: `TENX_AIRGAPPED=true`, `outputOffload=true`. Substituted because there is no cluster (the MCP's own floor check does the same): `CAP_LOOKUP_FILE` points at the mounted `/etc/tenx/lookups/caps.csv` instead of `/tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/caps.csv`, `ACTION_LOOKUP_FILE` points at the mounted `/etc/tenx/lookups/actions.csv` instead of `/tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/actions.csv`; left out: `K8S_NAMESPACE`, `K8S_ENABLED`, `K8S_CONFIGMAP`, `CONFIG_GENERATION_FILE` (the ConfigMap pull). Rig plumbing: `TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit`. Measurement only, after the MCP's arguments: `outputEncodeField fullText("tenx_hash","routeState","message_pattern","severity_level")`. Resource limits from the values: 0.5 CPU, 512M.

Policy files: the POC's log10x-caps.csv and log10x-actions.csv.

```text
container,cap
accounting,3866::accounting any statement above 329 lines a day goes to Flex. Today that is these 71 statements about $0.26 a month.
ad,1::ad every statement goes to Flex. Today that is these 7 statements about $0.41 a month.
cart,1::cart every statement goes to Flex. Today that is these 5 statements about $2.7 a month.
email,1::email every statement goes to Flex. Today that is these 3 statements about $0.26 a month.
fraud-detection,1::fraud-detection every statement goes to Flex. Today that is this one statement about $0.26 a month.
frontend,1::frontend every statement goes to Flex. Today that is these 8 statements about $4.6 a month.
kafka,1669::kafka any statement above 171 lines a day goes to Flex. Today that is these 16 statements about $3.3 a month.
otel-collector,37330::otel-collector any statement above 4145 lines a day goes to Flex. Today that is these 8 statements about $12 a month.
payment,2731::payment any statement above 237 lines a day goes to Flex. Today that is these 24 statements about $0.52 a month.
quote,1::quote every statement goes to Flex. Today that is this one statement about $0.26 a month.
recommendation,1::recommendation every statement goes to Flex. Today that is these 6 statements about $0.41 a month.
shipping,3879::shipping any statement above 807 lines a day goes to Flex. Today that is these 10 statements about $0.79 a month.
telemetry-docs,1::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.87 a month.
valkey-cart,1::valkey-cart every statement goes to Flex. Today that is these 6 statements about $0.08 a month.
```

```text
container,action
accounting,tier_down::accounting any statement above 329 lines a day goes to Flex. Today that is these 71 statements about $0.26 a month.
ad,tier_down::ad every statement goes to Flex. Today that is these 7 statements about $0.41 a month.
cart,tier_down::cart every statement goes to Flex. Today that is these 5 statements about $2.7 a month.
email,tier_down::email every statement goes to Flex. Today that is these 3 statements about $0.26 a month.
fraud-detection,tier_down::fraud-detection every statement goes to Flex. Today that is this one statement about $0.26 a month.
frontend,tier_down::frontend every statement goes to Flex. Today that is these 8 statements about $4.6 a month.
kafka,tier_down::kafka any statement above 171 lines a day goes to Flex. Today that is these 16 statements about $3.3 a month.
otel-collector,tier_down::otel-collector any statement above 4145 lines a day goes to Flex. Today that is these 8 statements about $12 a month.
payment,tier_down::payment any statement above 237 lines a day goes to Flex. Today that is these 24 statements about $0.52 a month.
quote,tier_down::quote every statement goes to Flex. Today that is this one statement about $0.26 a month.
recommendation,tier_down::recommendation every statement goes to Flex. Today that is these 6 statements about $0.41 a month.
shipping,tier_down::shipping any statement above 807 lines a day goes to Flex. Today that is these 10 statements about $0.79 a month.
telemetry-docs,tier_down::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.87 a month.
valkey-cart,tier_down::valkey-cart every statement goes to Flex. Today that is these 6 statements about $0.08 a month.
```

Where each row's cap sits (`plan.containerCaps`; bytes per 4-minute window over the capture, the figure caps.csv is written from): between the largest statement the plan keeps and the smallest it moves, at their geometric mean, so the margin is the same each way. A row with no kept statement gets cap 1: every statement past the first 5 a window takes the row's action.

| container | cap in caps.csv | largest kept statement | bytes per window | smallest moved statement | bytes per window | margin each way |
|---|---|---|---|---|---|---|
| accounting | 3,866 | info: Accounting.Consumer[$] | 770 | Order_details | 19,410 | 5.0x |
| payment | 2,731 | Transaction_complete_Order_confirmation_email_sent | 756 | Charge_request_received | 9,867 | 3.6x |
| otel-collector | 37,330 | error_Error_scraping_metrics | 12,980 | Metrics | 107,363 | 2.9x |
| kafka | 1,669 | Node_disconnected_org_apache_kafka_clients_Network | 638 | Successfully_wrote_snapshot_org_apache_kafka_image | 4,368 | 2.6x |
| shipping | 3,879 | flagd_off | 1,575 | Sending_Quote | 9,552 | 2.5x |
| ad | 1 | (none) | 0 | oteldemo_AdService_Non_targeted_ad_request_receive | 2,485 | none |
| cart | 1 | (none) | 0 | EmptyCartAsync_called_with_userId | 6,512 | none |
| email | 1 | (none) | 0 | POST_send_order_confirmation_HTTP | 7,700 | none |
| fraud-detection | 1 | (none) | 0 | fraud_detection_Consumed_record_with_orderId_and_u | 8,866 | none |
| frontend | 1 | (none) | 0 | Order_placed_successfully | 10,465 | none |
| quote | 1 | (none) | 0 | POST_getquote_HTTP | 5,148 | none |
| recommendation | 1 | (none) | 0 | Receive_ListRecommendations_for_product_ids | 14,640 | none |
| telemetry-docs | 1 | (none) | 0 | GET_HTTP_Wget | 12,528 | none |
| valkey-cart | 1 | (none) | 0 | DB_saved_on_disk | 228 | none |

## Flag timeline

| # | flag | variant | on | off | planned s | actual s |
|---|---|---|---|---|---|---|
| 1 | cartFailure | 100% | 10:57:15 | 11:04:10 | 415 | 415 |
| 2 | kafkaQueueProblems | on | 11:07:39 | 11:15:18 | 459 | 459 |
| 3 | paymentFailure | 100% | 11:19:38 | 11:24:39 | 301 | 301 |
| 4 | emailMemoryLeak | 1000x | 11:28:11 | 11:36:03 | 472 | 472 |
| 5 | emailMemoryLeak | 1000x | 11:36:30 | 11:43:20 | 410 | 410 |
| 6 | recommendationCacheFailure | on | 11:49:01 | 11:56:00 | 419 | 419 |
| 7 | loadGeneratorFloodHomepage | on | 11:57:06 | 12:02:35 | 329 | 329 |
| 8 | recommendationCacheFailure | on | 12:07:04 | (stopped) | 345 | 252 |

## Held records, scheduled run

28,018 returned records: pass 8,347, tier_down 19,671. Every hold is labelled with the rule that made it: a plan row (the container, its cap from caps.csv, `tier_down` from actions.csv) or the fleet default (a container with no row, the fleet cap, `offload`).

| rule | container | pattern | held | held bytes | severity | in a flag's causal span | outside | windows | quiet max events / bytes |
|---|---|---|---|---|---|---|---|---|---|
| plan row: accounting, cap 3,866, tier_down | accounting | `-FtZD9XArpU` Order_details | 134 | 123,655 | INFO 134 | 24 | 110 | 18 | 19 / 17,769 |
| plan row: ad, cap 1, tier_down | ad | `xHrytxJfUdw` oteldemo_AdService_Targeted_ad_request_received_for | 221 | 74,777 | TRACE 221 | 33 | 188 | 19 | 25 / 8,460 |
| plan row: ad, cap 1, tier_down | ad | `jN_dDVWoa78` oteldemo_AdService_Non_targeted_ad_request_received_preparin | 1 | 355 | TRACE 1 | 0 | 1 | 1 | 7 / 2,485 |
| plan row: cart, cap 1, tier_down | cart | `YZplfQ4a1Xw` GetCartAsync_called_with_userId | 1,266 | 360,906 | INFO 1,266 | 339 | 927 | 19 | 98 / 28,010 |
| plan row: cart, cap 1, tier_down | cart | `eDSYlCMPqVY` AddItemAsync_called_with_userId_productId_quantity | 635 | 208,381 | INFO 635 | 178 | 457 | 19 | 54 / 17,720 |
| plan row: cart, cap 1, tier_down | cart | `h3qY1nS1uxY` EmptyCartAsync_called_with_userId | 136 | 41,858 | INFO 136 | 33 | 103 | 17 | 19 / 5,624 |
| plan row: cart, cap 1, tier_down | cart | `9-GL0Pp_Cts` Error_code_FailedPrecondition_detail_Can_access_cart_storage | 17 | 10,744 | INFO 17 | 17 | 0 | 3 | 0 / 0 |
| plan row: email, cap 1, tier_down | email | `1zhBPd1E9Bc` POST_send_order_confirmation_HTTP | 136 | 39,644 | none 136 | 37 | 99 | 18 | 19 / 5,480 |
| plan row: email, cap 1, tier_down | email | `shf1OAS338c` Order_confirmation_email_sent_for_order | 84 | 20,832 | none 84 | 25 | 59 | 16 | 15 / 3,720 |
| plan row: fraud-detection, cap 1, tier_down | fraud-detection | `GKfNbCrpxxI` fraud_detection_Consumed_record_with_orderId_and_updated_tot | 134 | 54,131 | TRACE 134 | 24 | 110 | 18 | 19 / 7,657 |
| plan row: fraud-detection, cap 1, tier_down | fraud-detection | `eT4avs-RfM8` fraud_detection_FeatureFlag_kafkaQueueProblems_is_enabled_sl | 20 | 7,340 | TRACE 20 | 20 | 0 | 2 | 0 / 0 |
| plan row: frontend, cap 1, tier_down | frontend | `INl44sUgFeY` API_request_completed | 3,979 | 1,964,503 | TRACE 3,979 | 2,151 | 1,828 | 19 | 253 / 124,788 |
| plan row: frontend, cap 1, tier_down | frontend | `KSy6KmHbgEc` Order_placed_successfully | 136 | 61,880 | TRACE 136 | 70 | 66 | 17 | 19 / 8,645 |
| plan row: frontend, cap 1, tier_down | frontend | `SJz5BYn_Kzo` Checkout_payment_declined | 9 | 5,139 | TRACE 9 | 9 | 0 | 2 | 0 / 0 |
| plan row: kafka, cap 1,669, tier_down | kafka | `WlIY0QjIiEg` Deleted_tmp_cluster_org_apache_kafka_storage_internals_log_L | 207 | 69,759 | INFO 207 | 33 | 174 | 19 | 17 / 5,729 |
| plan row: kafka, cap 1,669, tier_down | kafka | `hl_fK-uzMu8` Deleted_offset_index_tmp_cluster_org_apache_kafka_storage_in | 207 | 72,036 | INFO 207 | 33 | 174 | 19 | 17 / 5,916 |
| plan row: kafka, cap 1,669, tier_down | kafka | `q20KpyVGjSM` Deleted_index_tmp_cluster_org_apache_kafka_storage_internals | 207 | 72,450 | INFO 207 | 33 | 174 | 19 | 17 / 5,950 |
| plan row: kafka, cap 1,669, tier_down | kafka | `AMFi23Ga9wY` Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_a | 207 | 75,141 | INFO 207 | 33 | 174 | 19 | 17 / 6,171 |
| plan row: kafka, cap 1,669, tier_down | kafka | `wyR-oWD2-hk` Rolled_new_log_segment_at_offset_in_ms_org_apache_kafka_stor | 204 | 78,193 | INFO 204 | 32 | 172 | 19 | 16 / 6,128 |
| plan row: kafka, cap 1,669, tier_down | kafka | `VnqlcNA_PIM` Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_stora | 204 | 78,796 | INFO 204 | 32 | 172 | 19 | 16 / 6,176 |
| plan row: kafka, cap 1,669, tier_down | kafka | `3AOokQ1Sq7k` Incremented_log_start_offset_to_due_snapshot_generated_org_a | 138 | 52,748 | INFO 138 | 22 | 116 | 19 | 13 / 4,966 |
| plan row: kafka, cap 1,669, tier_down | kafka | `BVtz4xhx64s` older_than_retention_org_apache_kafka_raft_internals_KafkaRa | 138 | 63,649 | INFO 138 | 22 | 116 | 19 | 13 / 5,993 |
| plan row: kafka, cap 1,669, tier_down | kafka | `1Eg3qHK6Z9w` Deleted_snapshot_files_for_apache_kafka_Snapshots | 138 | 43,360 | INFO 138 | 22 | 116 | 19 | 13 / 4,082 |
| plan row: kafka, cap 1,669, tier_down | kafka | `pFokWfyJRLU` Deleting_segments_due_to_log_start_offset_breach_LogSegment_ | 137 | 70,820 | INFO 137 | 22 | 115 | 19 | 13 / 6,715 |
| plan row: kafka, cap 1,669, tier_down | kafka | `-Jf8QdAufSM` Deleting_segment_files_LogSegment_baseOffset_size_lastModifi | 137 | 68,882 | INFO 137 | 22 | 115 | 19 | 13 / 6,524 |
| plan row: kafka, cap 1,669, tier_down | kafka | `YJTvxN0rObQ` Creating_new_KRaft_snapshot_file_because_we_have_replayed_at | 136 | 54,400 | INFO 136 | 21 | 115 | 19 | 13 / 5,200 |
| plan row: kafka, cap 1,669, tier_down | kafka | `TM6TaR-b4oE` Successfully_wrote_snapshot_org_apache_kafka_image_publisher | 135 | 45,360 | INFO 135 | 21 | 114 | 19 | 13 / 4,368 |
| plan row: kafka, cap 1,669, tier_down | kafka | `Y_71jRCq5Cw` Scheduling_unloading_of_metadata_for_consumer_with_epoch_Opt | 45 | 16,911 | INFO 45 | 0 | 45 | 1 | 0 / 0 |
| plan row: kafka, cap 1,669, tier_down | kafka | `VvBjD4t0T7w` Started_unloading_metadata_for_consumer_with_epoch_OptionalI | 45 | 16,686 | INFO 45 | 0 | 45 | 1 | 0 / 0 |
| plan row: kafka, cap 1,669, tier_down | kafka | `wfraEN4ubTY` Finished_unloading_metadata_for_consumer_with_epoch_Optional | 45 | 16,731 | INFO 45 | 0 | 45 | 1 | 0 / 0 |
| plan row: kafka, cap 1,669, tier_down | kafka | `lfxNT0TdHRU` Scheduling_loading_of_metadata_from_consumer_with_epoch_org_ | 45 | 16,281 | INFO 45 | 0 | 45 | 1 | 0 / 0 |
| plan row: kafka, cap 1,669, tier_down | kafka | `KjKx7VN7snY` was_spent_in_the_scheduler_Loaded_records_which_total_to_byt | 45 | 20,178 | INFO 45 | 0 | 45 | 1 | 0 / 0 |
| plan row: otel-collector, cap 37,330, tier_down | otel-collector | `KG8Fq0QFuoY` Logs | 3,160 | 1,662,308 | INFO 3,160 | 0 | 3,160 | 19 | 240 / 126,260 |
| plan row: otel-collector, cap 37,330, tier_down | otel-collector | `Gl3Gtr_SH5w` Traces | 3,157 | 1,658,122 | INFO 3,157 | 0 | 3,157 | 19 | 240 / 126,055 |
| plan row: otel-collector, cap 37,330, tier_down | otel-collector | `PuWB8kkVbfw` Metrics | 2,278 | 1,260,727 | INFO 2,278 | 0 | 2,278 | 19 | 190 / 105,153 |
| plan row: otel-collector, cap 37,330, tier_down | otel-collector | `fhu6rrW86b4` error_Error_scraping_metrics | 3 | 14,635 | ERROR 3 | 0 | 3 | 2 | 7 / 11,444 |
| plan row: payment, cap 2,731, tier_down | payment | `9WbTsopbiXk` Transaction_complete | 136 | 92,026 | TRACE 136 | 8 | 128 | 18 | 19 / 12,860 |
| plan row: payment, cap 2,731, tier_down | payment | `fg1YkiyrF3Q` Charge_request_received | 128 | 54,912 | TRACE 128 | 17 | 111 | 18 | 19 / 8,151 |
| plan row: payment, cap 2,731, tier_down | payment | `_N7fwt_uqyQ` Payment_request_failed_Invalid_token_demo_user_context_loyal | 3 | 2,790 | ERROR 3 | 3 | 0 | 1 | 0 / 0 |
| plan row: quote, cap 1, tier_down | quote | `c4yR2F2cVfk` POST_getquote_HTTP | 146 | 34,164 | none 146 | 0 | 146 | 19 | 19 / 4,446 |
| plan row: recommendation, cap 1, tier_down | recommendation | `bzLB1zZCTIw` Receive_ListRecommendations_for_product_ids | 299 | 145,912 | INFO 299 | 79 | 220 | 19 | 30 / 14,640 |
| plan row: recommendation, cap 1, tier_down | recommendation | `QE9Wwe64YPk` get_product_list_cache_hit | 13 | 5,213 | INFO 13 | 13 | 0 | 3 | 0 / 0 |
| plan row: recommendation, cap 1, tier_down | recommendation | `pQCM0VaOm6U` get_product_list_cache_miss | 10 | 4,020 | INFO 10 | 10 | 0 | 3 | 0 / 0 |
| plan row: shipping, cap 3,879, tier_down | shipping | `kAB8PMmHyKM` shipping_service_Requesting_quote_http_getquote | 75 | 31,425 | none 75 | 0 | 75 | 17 | 19 / 7,961 |
| plan row: shipping, cap 3,879, tier_down | shipping | `PX-oZ7rxgZo` Sending_Quote | 75 | 31,140 | none 75 | 0 | 75 | 17 | 19 / 7,890 |
| plan row: shipping, cap 3,879, tier_down | shipping | `LnOvjJt0La4` Tracking_ID_Created | 70 | 29,260 | none 70 | 0 | 70 | 16 | 19 / 7,942 |
| plan row: telemetry-docs, cap 1, tier_down | telemetry-docs | `zxRYTKQNyBY` GET_HTTP_Wget | 790 | 206,190 | none 790 | 0 | 790 | 19 | 48 / 12,528 |

## Per flag activation

Span: flag on to one 4-minute window after it reverts, or the next flag on. Rows are the containers on the flag's causal path (demo 3.1.0 source). "New" holds are patterns with no hold in the 10 minutes before the flag (or since the fleet Receiver started); "steady" holds are patterns already held then, such as every statement of a plan row with cap 1. "First noisy" is the first record of the first pattern whose records in a minute reach 5 and 5 times its rate in those 10 minutes.

| # | flag | on to off | container | rule | first noisy | first new hold | new held (offload / tier_down) | kept, same patterns | bytes held (new) | steady held | patterns newly held |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | cartFailure | 10:57:15 to 11:04:10 | cart | plan row: cart, cap 1, tier_down | 10:58:17 AddItemAsync_called_with_userI | 10:57:37 | 138 (0 / 138) | 35 | 51,473 | 199 | AddItemAsync_called_with_userId_productI x103; EmptyCartAsync_called_with_userId x18; Error_code_FailedPrecondition_detail_Can x17 |
| 1 | cartFailure | 10:57:15 to 11:04:10 | frontend | plan row: frontend, cap 1, tier_down | 11:00:27 Order_placed_successfully | 10:58:28 | 18 (0 / 18) | 14 | 8,190 | 598 | Order_placed_successfully x18 |
| 2 | kafkaQueueProblems | 11:07:39 to 11:15:18 | fraud-detection | plan row: fraud-detection, cap 1, tier_down | 11:10:56 fraud_detection_FeatureFlag_ka | 11:10:26 | 20 (0 / 20) | 10 | 7,340 | 24 | fraud_detection_FeatureFlag_kafkaQueuePr x20 |
| 3 | paymentFailure | 11:19:38 to 11:24:39 | frontend | plan row: frontend, cap 1, tier_down | 11:21:42 Checkout_payment_declined | 11:22:02 | 9 (0 / 9) | 6 | 5,139 | 449 | Checkout_payment_declined x9 |
| 3 | paymentFailure | 11:19:38 to 11:24:39 | payment | plan row: payment, cap 2,731, tier_down | 11:21:42 Payment_request_failed_Invalid | 11:22:11 | 3 (0 / 3) | 12 | 2,790 | 25 | Payment_request_failed_Invalid_token_dem x3 |
| 4 | emailMemoryLeak | 11:28:11 to 11:36:03 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 5 | emailMemoryLeak | 11:36:30 to 11:43:20 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 6 | recommendationCacheFailure | 11:49:01 to 11:56:00 | recommendation | plan row: recommendation, cap 1, tier_down | 11:51:29 get_product_list_cache_miss | 11:50:25 | 18 (0 / 18) | 20 | 7,225 | 36 | get_product_list_cache_hit x11; get_product_list_cache_miss x7 |
| 7 | loadGeneratorFloodHomepage | 11:57:06 to 12:02:35 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 8 | recommendationCacheFailure | 12:07:04 to  | recommendation | plan row: recommendation, cap 1, tier_down | 12:08:12 get_product_list_cache_hit | 12:08:58 | 5 (0 / 5) | 16 | 2,008 | 16 | get_product_list_cache_miss x3; get_product_list_cache_hit x2 |

New holds in containers off the flag's causal path, inside its span: #1 otel-collector 343 (Metrics; plan row: otel-collector, cap 37,330, tier_down); #1 kafka 104 (Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_storage_internals_log_ProducerStateManager, Rolled_new_log_segmen; plan row: kafka, cap 1,669, tier_down); #1 ad 41 (oteldemo_AdService_Targeted_ad_request_received_for; plan row: ad, cap 1, tier_down); #1 payment 34 (Transaction_complete, Charge_request_received; plan row: payment, cap 2,731, tier_down); #1 shipping 30 (Tracking_ID_Created, Sending_Quote, shipping_service_Requesting_quote_http_getquote; plan row: shipping, cap 3,879, tier_down); #1 email 27 (POST_send_order_confirmation_HTTP, Order_confirmation_email_sent_for_order; plan row: email, cap 1, tier_down); #1 accounting 18 (Order_details; plan row: accounting, cap 3,866, tier_down); #1 fraud-detection 18 (fraud_detection_Consumed_record_with_orderId_and_updated_total_count_to_trace_id_span_flags; plan row: fraud-detection, cap 1, tier_down); #1 quote 18 (POST_getquote_HTTP; plan row: quote, cap 1, tier_down); #2 otel-collector 3 (error_Error_scraping_metrics; plan row: otel-collector, cap 37,330, tier_down); #7 kafka 225 (was_spent_in_the_scheduler_Loaded_records_which_total_to_bytes_org_apache_kafka_coordinator_common_runtime_CoordinatorRu; plan row: kafka, cap 1,669, tier_down); #8 ad 1 (oteldemo_AdService_Non_targeted_ad_request_received_preparing_random_response_trace_id_span_flags; plan row: ad, cap 1, tier_down).

## False holds and the plan's moves

Fleet-default holds outside every flag's causal span: 0 records in 0 (container, pattern) pairs.

The plan's rows (`tier_down`), per container per Receiver window:

| container | cap in caps.csv | windows | median per window | max | total |
|---|---|---|---|---|---|
| otel-collector | 37330.0 | 19 | 459 | 481 | 8,598 |
| frontend | 1.0 | 19 | 217 | 276 | 4,124 |
| kafka | 1669.0 | 19 | 115 | 335 | 2,420 |
| cart | 1.0 | 19 | 107 | 164 | 2,054 |
| telemetry-docs | 1.0 | 19 | 42 | 43 | 790 |
| recommendation | 1.0 | 19 | 17 | 28 | 322 |
| payment | 2731.0 | 19 | 13 | 25 | 267 |
| ad | 1.0 | 19 | 12 | 22 | 222 |
| email | 1.0 | 18 | 12.0 | 22 | 220 |
| shipping | 3879.0 | 18 | 10.0 | 27 | 220 |
| fraud-detection | 1.0 | 18 | 7.0 | 24 | 154 |
| quote | 1.0 | 19 | 8 | 13 | 146 |
| accounting | 3866.0 | 18 | 7.0 | 13 | 134 |

## Errors against the 0.5 floor

ERROR and CRITICAL records held: 6; passed: 972.

| rule | container | pattern | severity | held | passed | flags |
|---|---|---|---|---|---|---|
| plan row: otel-collector, cap 37,330, tier_down | otel-collector | `fhu6rrW86b4` error_Error_scraping_metrics | ERROR | tier_down 3 | 85 |  |
| plan row: payment, cap 2,731, tier_down | payment | `_N7fwt_uqyQ` Payment_request_failed_Invalid_token_demo_user_context_loyal | ERROR | tier_down 3 | 12 | paymentFailure 3 |

Records over the cap in a replay of each Receiver window (rb_ts order; the first 5 pass, then pass while the window's bytes stay within the cap), by severity and what the Receiver did:

| severity | over the cap: passed | held | passed share | floor |
|---|---|---|---|---|
| ERROR | 5 | 5 | 0.500 | 0.5 |
| INFO | 635 | 12,826 | 0.047 | 0.0 |
| TRACE | 69 | 4,688 | 0.015 | 0.0 |
| none | 36 | 1,337 | 0.026 | 0 |

Replay against the Receiver: under the cap and passed 7,602, under and held 815, over and passed 745, over and held 18,856. Windows start 9.2 s past a multiple of 240 s of epoch time (receiver.log connect); the phase read from the data alone (first pass after a run of holds) is 12 s, with 62.9% of 598 resets within 20 s of it.

## Latency

Seconds from `fb_ts` (the Docker driver's event time for the line) to `rb_ts` (when Fluent Bit's return-path filter received the record back from the Receiver). For a record that joins several lines, `fb_ts` is its first line's.

Scheduled run (28,018 records): median 2.02, p99 7.44, max 17.2; 59 over 10 s.

| container | records | median | p99 | max | over 10 s |
|---|---|---|---|---|---|
| accounting | 225 | 6.29 | 7.87 | 8.0 | 0 |
| ad | 371 | 6.12 | 7.71 | 12.2 | 1 |
| astronomy-db | 901 | 6.05 | 6.97 | 14.5 | 4 |
| cart | 2,341 | 1.95 | 7.42 | 11.5 | 1 |
| email | 400 | 3.69 | 7.70 | 7.9 | 0 |
| flagd | 15 | 6.78 | 7.76 | 7.8 | 0 |
| flagd-ui | 33 | 2.47 | 8.07 | 8.4 | 0 |
| fraud-detection | 254 | 6.04 | 7.76 | 7.9 | 0 |
| frontend | 4,310 | 2.23 | 6.52 | 15.1 | 2 |
| kafka | 3,668 | 1.68 | 8.17 | 17.2 | 35 |
| otel-collector | 12,637 | 1.79 | 5.71 | 14.9 | 15 |
| payment | 482 | 2.51 | 7.73 | 7.9 | 0 |
| quote | 241 | 6.24 | 7.81 | 8.0 | 0 |
| recommendation | 454 | 5.80 | 7.78 | 8.0 | 0 |
| shipping | 733 | 1.91 | 7.62 | 7.9 | 0 |
| telemetry-docs | 883 | 6.05 | 6.90 | 13.7 | 1 |
| valkey-cart | 70 | 1.70 | 8.71 | 8.9 | 0 |

What the scheduled run's 59 records over 10 s waited for, from each record's last raw line and its container's next one: back more than 5 s after its container's next line 54, back within 5 s after its container's next line 4, back before its container wrote again 1 (median 2.65 s after that line).

Records after which their container wrote nothing for 10 s or more: 1,544. 1,544 came back before the container's next line, so a timer released them, 6.50 s after their last line at the median, 5.07 s at least, 7.93 s at p99 and 12.23 s at most; 0 came back only with or after that next line. The Receiver's group step seals a source's open event on the source's next head line, on the group size limit (20,000 lines), or 5 s (`groupFlushTimeout`, which the values leave at its default) after the batch that carried the source's last line; a batch leaves the forwarder input up to 2 s after its last line (`parallelEventFlushInterval`).

Against the earlier runs (`previous-runs.json`: each run's committed captures measured by this `analyze.py`), scheduled run, seconds as median / p99 / max:

| container | 1.1.141 run (1.1.141, MCP 1.30.54) | this run |
|---|---|---|
| all | 2.01 / 28.86 / 472.3 (40,575) | 2.02 / 7.44 / 17.2 (28,018) |
| accounting | 1.80 / 32.00 / 309.0 (4,230) | 6.29 / 7.87 / 8.0 (225) |
| ad | 9.22 / 55.49 / 70.9 (405) | 6.12 / 7.71 / 12.2 (371) |
| astronomy-db | 2.00 / 7.69 / 9.9 (6,903) | 6.05 / 6.97 / 14.5 (901) |
| cart | 2.05 / 19.21 / 32.4 (2,349) | 1.95 / 7.42 / 11.5 (2,341) |
| email | 12.96 / 94.63 / 309.0 (230) | 3.69 / 7.70 / 7.9 (400) |
| flagd | 302.98 / 469.69 / 471.5 (15) | 6.78 / 7.76 / 7.8 (15) |
| flagd-ui | 3.12 / 468.13 / 472.3 (33) | 2.47 / 8.07 / 8.4 (33) |
| fraud-detection | 2.03 / 34.67 / 309.0 (3,186) | 6.04 / 7.76 / 7.9 (254) |
| frontend | 2.31 / 7.25 / 12.4 (4,394) | 2.23 / 6.52 / 15.1 (4,310) |
| kafka | 1.94 / 16.53 / 17.9 (3,409) | 1.68 / 8.17 / 17.2 (3,668) |
| otel-collector | 1.82 / 5.52 / 8.1 (12,551) | 1.79 / 5.71 / 14.9 (12,637) |
| payment | 2.55 / 85.08 / 130.6 (497) | 2.51 / 7.73 / 7.9 (482) |
| quote | 13.35 / 87.87 / 130.8 (248) | 6.24 / 7.81 / 8.0 (241) |
| recommendation | 8.63 / 58.75 / 95.5 (414) | 5.80 / 7.78 / 8.0 (454) |
| shipping | 2.00 / 70.60 / 130.6 (760) | 1.91 / 7.62 / 7.9 (733) |
| telemetry-docs | 6.67 / 8.05 / 11.0 (882) | 6.05 / 6.90 / 13.7 (883) |
| valkey-cart | 1.53 / 369.94 / 399.7 (69) | 1.70 / 8.71 / 8.9 (70) |

Every returned record from the first Receiver start (38,785): median 2.08, p99 38.10, max 76.1; 958 over 10 s, by when the line was written: before the quiet run 846, between quiet end and scheduler start 53, scheduled run 59. `latency-over-10s.csv` lists every one with its container.

| container | records | median | p99 | max | over 10 s |
|---|---|---|---|---|---|
| accounting | 339 | 6.37 | 51.34 | 51.4 | 23 |
| ad | 518 | 6.15 | 7.84 | 15.3 | 3 |
| astronomy-db | 1,262 | 6.07 | 13.51 | 74.5 | 19 |
| cart | 3,245 | 1.97 | 7.50 | 14.5 | 4 |
| currency | 1 | 8.86 | 8.86 | 8.9 | 0 |
| email | 580 | 4.42 | 7.84 | 16.9 | 3 |
| flagd | 33 | 8.37 | 11.99 | 13.2 | 1 |
| flagd-ui | 36 | 2.93 | 8.20 | 8.4 | 0 |
| fraud-detection | 351 | 6.09 | 7.90 | 61.4 | 3 |
| frontend | 5,860 | 2.24 | 6.61 | 48.3 | 9 |
| frontend-proxy | 128 | 30.37 | 30.37 | 33.3 | 127 |
| image-provider | 47 | 3.92 | 10.32 | 12.9 | 1 |
| kafka | 5,300 | 1.85 | 73.08 | 73.5 | 535 |
| otel-collector | 17,157 | 1.83 | 13.18 | 74.3 | 214 |
| payment | 663 | 2.52 | 7.66 | 7.9 | 0 |
| quote | 331 | 6.24 | 7.82 | 8.0 | 0 |
| recommendation | 599 | 5.86 | 7.80 | 10.6 | 1 |
| shipping | 1,020 | 1.93 | 7.62 | 8.1 | 0 |
| telemetry-docs | 1,213 | 6.07 | 12.45 | 76.1 | 15 |
| valkey-cart | 102 | 1.70 | 8.86 | 9.2 | 0 |

## Multi-line events closed by a source's pause

A line of a kind the Receiver joins to the record before it anywhere in the run is not a group head. A record that begins with such a line was opened after its source's previous group had been sealed by something other than a head line, which in a running demo is the per-source flush timer. Each is set against the record before it from the same container; the pause runs from that record's last raw line to this record's first. Blank lines are left out. `early-close.csv` lists every one.

Scheduled run: 173 records opened by a line that is not a head; over 7 s 157, 5 to 7 s 13, 3 to 5 s 3; 16 within 7 s of the previous record's first line, 0 of them with the previous record's pattern.

1.1.141 run, same measure: 0 records, 0 within 7 s of the previous record's first line, 0 with its pattern.

| container | previous record's pattern | first line of the record opened | records | by pause | within 7 s | same pattern | shortest pause s | example |
|---|---|---|---|---|---|---|---|---|
| email | POST_send_order_confirmation_HTTP | `Order confirmation email sent for order 0-0-0-0-` | 173 | over 7 s 157, 5 to 7 s 13, 3 to 5 s 3 | 16 | 0 | 4.47 | 10:58:06 Order confirmation email sent for order 4d0f9d1c-c887-11f1-a |

## Delivery

Scheduled run (10:56:11 to 12:11:16 UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).

| container | raw lines | returned records | lines covered | covered minus raw |
|---|---|---|---|---|
| accounting | 449 | 225 | 449 | +0 |
| ad | 417 | 371 | 417 | +0 |
| astronomy-db | 902 | 901 | 901 | -1 |
| cart | 4,790 | 2,341 | 4,790 | +0 |
| email | 452 | 400 | 452 | +0 |
| flagd | 16 | 15 | 15 | -1 |
| flagd-ui | 34 | 33 | 33 | -1 |
| fraud-detection | 254 | 254 | 254 | +0 |
| frontend | 4,311 | 4,310 | 4,310 | -1 |
| kafka | 3,670 | 3,668 | 3,669 | -1 |
| otel-collector | 13,699 | 12,637 | 13,699 | +0 |
| payment | 482 | 482 | 482 | +0 |
| quote | 241 | 241 | 241 | +0 |
| recommendation | 454 | 454 | 454 | +0 |
| shipping | 733 | 733 | 733 | +0 |
| telemetry-docs | 884 | 883 | 883 | -1 |
| valkey-cart | 70 | 70 | 70 | +0 |
| total | 31,858 | 28,018 | 31,852 | -6 |

Whole run, from the first Receiver start (10:28:16 to 12:11:16 UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).

| container | raw lines | returned records | lines covered | covered minus raw |
|---|---|---|---|---|
| accounting | 662 | 339 | 662 | +0 |
| ad | 568 | 518 | 568 | +0 |
| astronomy-db | 1,300 | 1,262 | 1,299 | -1 |
| cart | 6,598 | 3,245 | 6,598 | +0 |
| currency | 1 | 1 | 1 | +0 |
| email | 659 | 580 | 659 | +0 |
| flagd | 34 | 33 | 33 | -1 |
| flagd-ui | 37 | 36 | 36 | -1 |
| fraud-detection | 351 | 351 | 351 | +0 |
| frontend | 5,866 | 5,860 | 5,865 | -1 |
| frontend-proxy | 135 | 128 | 135 | +0 |
| image-provider | 47 | 47 | 47 | +0 |
| kafka | 6,501 | 5,300 | 6,500 | -1 |
| otel-collector | 19,070 | 17,148 | 19,070 | +0 |
| payment | 664 | 663 | 664 | +0 |
| quote | 331 | 331 | 331 | +0 |
| recommendation | 599 | 599 | 599 | +0 |
| shipping | 1,020 | 1,020 | 1,020 | +0 |
| telemetry-docs | 1,214 | 1,213 | 1,213 | -1 |
| valkey-cart | 102 | 102 | 102 | +0 |
| total | 45,759 | 38,776 | 45,753 | -6 |

Lines written up to 60 s before the stop: 45,258 raw, 45,258 covered. In the last 60 s: 501 raw, 495 covered; the difference is each container's last event, still open in the Receiver when the demo stopped.

## What the fleet default would hold alone

The same replay with the install seed in place of the plan's rows, so every container takes the fleet default (25,960 bytes): 12,880 records held (expected, floors applied), 1,709 of them inside a flag's causal span, 1 ERROR or CRITICAL.

## Against the earlier runs

`previous-runs.json`: 1.1.141 run, commit 8e416c6. Each run's committed captures are measured by this `analyze.py`.

| measure | 1.1.141 run | this run |
|---|---|---|
| Receiver | log10x/edge-10x:1.1.141 | log10x/edge-10x:1.1.142 |
| log10x-mcp | 1.30.54 | 1.30.58 |
| fleet default cap, bytes per window per node | 10,288 | 25,960 |
| plan rows in caps.csv | 11 | 14 |
| returned records, scheduled run | 40,575 | 28,018 |
| routes | offload 4,836, pass 8,555, tier_down 27,184 | pass 8,347, tier_down 19,671 |
| kafkaQueueProblems: new holds on the causal path | #2: astronomy-db 4,784, accounting 1,990, fraud-detection 446 | #2: fraud-detection 20 |
| fleet-default holds outside every causal span (outside of held) | astronomy-db `role_root_does_not_exist` 43 of 52 | none |
| ERROR and CRITICAL held / passed | 982 / 1,999 | 6 / 972 |
| ERROR over the cap, share passed | 0.520 of 1,937 | 0.500 of 10 |
| CRITICAL over the cap, share passed | 0.567 of 104 | 0.000 of 0 |
| latency median / p99 / max, s | 2.01 / 28.86 / 472.3 | 2.02 / 7.44 / 17.2 |
| records over 10 s | 1,714 | 59 |
| records opened by a line that is not a head (within 7 s) | 0 (0; same pattern 0) | 173 (16; same pattern 0) |
| lines written up to 60 s before the stop: raw / covered | 66,255 / 66,255 | 45,258 / 45,258 |

## Reading

**Which rule held what.** Of the 28,018 records the Receiver returned in the scheduled run, 19,671 were held by the plan's rows (`tier_down`) and 8,347 passed. The fleet default (25,960 bytes, `offload`) held nothing: no container without a row went above it in any window.

**kafkaQueueProblems, 11:07:39 to 11:15:18.** The flag reached fraud-detection, which logged `FeatureFlag 'kafkaQueueProblems' is enabled, sleeping 1 second` 29 times (20 held by its plan row, cap 1). It did not reach checkout: the duplicate-order flood that the flag drives (checkout publishing each order 100 extra times) did not happen, and raw has no `Duplicate order received` and no `duplicate key` line. flagd's metrics counted 4 resolutions of the flag through the Go provider's `ResolveInt` (3 `off`, 1 `on`) over the whole run, so checkout's provider answered from its cache. checkout writes nothing to stdout, so its side is not visible here. With no flood there was no astronomy-db, accounting or fraud-detection surge for any rule to hold.

**The other activations.** cartFailure: cart's row (cap 1) held 17 `FailedPrecondition ... Can't access cart storage` lines and kept 10; its other new holds in the span (`AddItemAsync` 103, `EmptyCartAsync` 18) are routine statements whose first hold came within 2 minutes of the Receiver's relaunch at 10:56:09, so the 10-minute look-back that defines "new" had little to look at. paymentFailure: frontend's `Checkout payment declined` (9 held) and payment's `Payment request failed` (3 held, ERROR) by their rows. recommendationCacheFailure: recommendation's cache hit and miss lines by its row (cap 1). emailMemoryLeak and loadGeneratorFloodHomepage: no new hold on their causal paths.

**False holds.** None. The previous run's one false-hold pattern, astronomy-db `FATAL: role "root" does not exist` (11,750 bytes a window), sits under this run's 25,960-byte fleet default.

**Latency.** Scheduled run: median 2.02 s, p99 7.44 s, max 17.2 s, 59 records over 10 s, against median 2.01 s, p99 28.86 s, max 472.3 s and 1,714 records over 10 s in the 1.1.141 run. 57 of the 59 were written 12:02:03 to 12:02:10 and all came back at 12:02:2x, in every busy container at once (kafka 35, otel-collector 15); receiver.log and fluent-bit.log show nothing at that time. 1,544 records were followed by 10 s or more of silence from their container and came back before its next line, 5.07 s to 12.2 s after their last line (median 6.5 s, p99 7.9 s); in the 1.1.141 run all 1,323 such records waited for the container's next line.

**Records opened by a line that is not a head.** 173, all in email: its `Order confirmation email sent for order ...` line carries no timestamp or level, so the Receiver joins it to the record before it, the access-log line of the previous request. When email pauses after that access-log line, the per-source flush seals the record and the next `Order confirmation` line opens its own record. The pause was over 7 s for 157 of them, 5 to 7 s for 13 and 3 to 5 s for 3 (shortest 4.47 s). None shares the previous record's pattern. No other multi-line event (cart's and accounting's two- and three-line .NET records, astronomy-db's STATEMENT records, otel-collector's stack traces) was split.

**Errors.** 6 ERROR records held (payment's `Payment request failed` 3 and otel-collector's `Error scraping metrics` 3, both by plan rows, `tier_down`), 972 ERROR and CRITICAL passed. Above a cap, 5 of 10 ERROR records passed (0.500).

**Delivery.** Every raw line written up to 60 s before the stop came back (45,258 of 45,258, counting the lines inside joined records). In the last 60 s, 6 lines did not.

