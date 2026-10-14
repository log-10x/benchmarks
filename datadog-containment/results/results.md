# Containment demo: a fleet-default cap on the OpenTelemetry demo's own incidents

All figures below come from this run's files in `results/` and are rendered by `rig/report.py` from `rig/analyze.py`'s `analysis.json`.

## What ran

- OpenTelemetry demo 3.1.0 (`compose.yaml` + `compose.full.yaml`), every container's stdout and stderr through the Docker `fluentd` driver to Fluent Bit 4.2, which keeps a raw copy, hands each record to the log10x Receiver and writes what comes back to one file per `routeState`.
- Receiver: `log10x/edge-10x:1.1.141@sha256:45157d0bdf506615aa015db7b8b7251ae39be5f4330233d2d2d659c69d1f93d1`, the released image with its own config and modules, launched with the values log10x-mcp 1.30.54 renders (below).
- Plan: log10x-mcp 1.30.54 `poc_from_local` on the quiet capture with `{"headroom": 2, "action": "offload", "error_floor": 0.5}`, engine `log10x/edge-10x:1.1.141@sha256:45157d0bdf506615aa015db7b8b7251ae39be5f4330233d2d2d659c69d1f93d1`.
- Scheduler: flagd-ui, seed 20261014, interval 600 s, hold 240 to 480 s, one flag at a time, flags kafkaQueueProblems (on), cartFailure (100%), paymentFailure (100%), recommendationCacheFailure (on), loadGeneratorFloodHomepage (on), emailMemoryLeak (1000x). Scheduled run 21:12:28 to 22:27:44 UTC on 2026-10-14.

## Timeline (UTC)

| event | at |
|---|---|
| receiver_ready | 20:35:53 |
| demo_up | 20:46:45 |
| demo_healthy | 20:47:17 |
| quiet_start | 20:49:17 |
| quiet_end | 21:11:20 |
| receiver_ready | 21:11:55 |
| scheduler_start | 21:12:28 |
| planned_end | 22:27:37 |
| scheduler_stop | 22:27:40 |
| run_end | 22:27:44 |
| demo_down | 22:29:45 |

## Quiet run and the fleet default

Quiet run 20:49:17 to 21:11:20 UTC, no flag active, Receiver with no cap: 9,054 raw lines, 7,979 returned records, 46 (container, pattern) pairs in 16 containers, 5 full 4-minute windows, 0 records held.

The POC on that capture: `met: true`, 70.3% reached against the 70% target, keep-everything lever `tier_down`; 28 planned and 19 kept statements.

| fleet default | value |
|---|---|
| `cap_bytes_per_window_per_node` | **10,288** |
| baseline | 5,144.1 bytes per window: `error_Error_scraping_metrics` in otel-collector |
| headroom, action, error floor | 2, `offload`, 0.5 |
| sentence | Any service not listed: a statement above 2,878 lines a day goes to the offload bucket. Up to 1,800 lines a day of every statement always reach Standard on each node. |
| the baseline statement in the Receiver's unit (quiet run) | 7,103 record bytes per window on average, 7,811 at most |

The 20 largest (container, pattern) pairs of the quiet run, by their largest 4-minute window in the bytes the Receiver counts (the compact JSON of the record as it arrives), with the rule that covers each in the scheduled run:

| container | pattern | rule | largest window: events | bytes |
|---|---|---|---|---|
| otel-collector | `KG8Fq0QFuoY` Logs | plan row: otel-collector, cap 15,726, tier_down | 243 | 127,826 |
| otel-collector | `Gl3Gtr_SH5w` Traces | plan row: otel-collector, cap 15,726, tier_down | 240 | 126,060 |
| frontend | `INl44sUgFeY` API_request_completed | plan row: frontend, cap 5,551, tier_down | 223 | 110,168 |
| otel-collector | `PuWB8kkVbfw` Metrics | plan row: otel-collector, cap 15,726, tier_down | 191 | 105,707 |
| cart | `YZplfQ4a1Xw` GetCartAsync_called_with_userId | plan row: cart, cap 1, tier_down | 80 | 22,988 |
| cart | `eDSYlCMPqVY` AddItemAsync_called_with_userId_productId_quantity | plan row: cart, cap 1, tier_down | 46 | 15,094 |
| accounting | `-FtZD9XArpU` Order_details | plan row: accounting, cap 1, tier_down | 17 | 14,858 |
| recommendation | `bzLB1zZCTIw` Receive_ListRecommendations_for_product_ids | plan row: recommendation, cap 1, tier_down | 27 | 13,176 |
| telemetry-docs | `zxRYTKQNyBY` GET_HTTP_Wget | plan row: telemetry-docs, cap 1, tier_down | 48 | 12,528 |
| astronomy-db | `oUkuI8QT6s8` role_root_does_not_exist | fleet default: 10,288, offload | 47 | 11,750 |
| payment | `9WbTsopbiXk` Transaction_complete | plan row: payment, cap 2,583, tier_down | 17 | 11,497 |
| ad | `xHrytxJfUdw` oteldemo_AdService_Targeted_ad_request_received_fo | plan row: ad, cap 1,164, tier_down | 24 | 8,127 |
| otel-collector | `fhu6rrW86b4` error_Error_scraping_metrics | plan row: otel-collector, cap 15,726, tier_down | 5 | 7,811 |
| frontend | `KSy6KmHbgEc` Order_placed_successfully | plan row: frontend, cap 5,551, tier_down | 17 | 7,735 |
| payment | `fg1YkiyrF3Q` Charge_request_received | plan row: payment, cap 2,583, tier_down | 17 | 7,293 |
| shipping | `kAB8PMmHyKM` shipping_service_Requesting_quote_http_getquote | plan row: shipping, cap 765, tier_down | 17 | 7,123 |
| shipping | `LnOvjJt0La4` Tracking_ID_Created | plan row: shipping, cap 765, tier_down | 17 | 7,106 |
| shipping | `PX-oZ7rxgZo` Sending_Quote | plan row: shipping, cap 765, tier_down | 17 | 7,055 |
| fraud-detection | `GKfNbCrpxxI` fraud_detection_Consumed_record_with_orderId_and_u | plan row: fraud-detection, cap 1, tier_down | 17 | 6,851 |
| kafka | `pFokWfyJRLU` Deleting_segments_due_to_log_start_offset_breach_L | plan row: kafka, cap 4,163, tier_down | 13 | 6,715 |

## The values the Receiver ran with

Rendered by log10x-mcp 1.30.54 (`receiverFleetValues` with the POC's `fleet_default`, then the Fluent Bit Receiver overlay's `renderValues`, the two calls `log10x_advise_install` makes; `results/values-fleet/values.yaml` is the overlay verbatim). Arguments, in order:

```text
@run/input/forwarder/fluentbit
@apps/receiver
symbolMessageHashField
tenx_hash
rateReceiverAbsoluteCap
10288
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
accounting,1::accounting every statement goes to Flex. Today that is these 60 statements about $0.22 a month.
ad,1164::ad any statement above 1177 lines a day goes to Flex. Today that is these 6 statements about $0.32 a month.
cart,1::cart every statement goes to Flex. Today that is these 6 statements about $2.1 a month.
fraud-detection,1::fraud-detection every statement goes to Flex. Today that is this one statement about $0.22 a month.
frontend,5551::frontend any statement above 4382 lines a day goes to Flex. Today that is these 7 statements about $3.9 a month.
kafka,4163::kafka any statement above 4448 lines a day goes to Flex. Today that is these 16 statements about $2.9 a month.
otel-collector,15726::otel-collector any statement above 1439 lines a day goes to Flex. Today that is these 10 statements about $12 a month.
payment,2583::payment any statement above 262 lines a day goes to Flex. Today that is these 21 statements about $0.38 a month.
recommendation,1::recommendation every statement goes to Flex. Today that is these 6 statements about $0.4 a month.
shipping,765::shipping any statement above 523 lines a day goes to Flex. Today that is these 11 statements about $0.67 a month.
telemetry-docs,1::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.87 a month.
```

```text
container,action
accounting,tier_down::accounting every statement goes to Flex. Today that is these 60 statements about $0.22 a month.
ad,tier_down::ad any statement above 1177 lines a day goes to Flex. Today that is these 6 statements about $0.32 a month.
cart,tier_down::cart every statement goes to Flex. Today that is these 6 statements about $2.1 a month.
fraud-detection,tier_down::fraud-detection every statement goes to Flex. Today that is this one statement about $0.22 a month.
frontend,tier_down::frontend any statement above 4382 lines a day goes to Flex. Today that is these 7 statements about $3.9 a month.
kafka,tier_down::kafka any statement above 4448 lines a day goes to Flex. Today that is these 16 statements about $2.9 a month.
otel-collector,tier_down::otel-collector any statement above 1439 lines a day goes to Flex. Today that is these 10 statements about $12 a month.
payment,tier_down::payment any statement above 262 lines a day goes to Flex. Today that is these 21 statements about $0.38 a month.
recommendation,tier_down::recommendation every statement goes to Flex. Today that is these 6 statements about $0.4 a month.
shipping,tier_down::shipping any statement above 523 lines a day goes to Flex. Today that is these 11 statements about $0.67 a month.
telemetry-docs,tier_down::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.87 a month.
```

## Flag timeline

| # | flag | variant | on | off | planned s | actual s |
|---|---|---|---|---|---|---|
| 1 | cartFailure | 100% | 21:13:32 | 21:20:27 | 415 | 415 |
| 2 | kafkaQueueProblems | on | 21:23:56 | 21:31:35 | 459 | 459 |
| 3 | paymentFailure | 100% | 21:35:54 | 21:40:56 | 301 | 301 |
| 4 | emailMemoryLeak | 1000x | 21:44:28 | 21:52:20 | 472 | 472 |
| 5 | emailMemoryLeak | 1000x | 21:52:47 | 21:59:37 | 410 | 410 |
| 6 | recommendationCacheFailure | on | 22:05:18 | 22:12:17 | 419 | 419 |
| 7 | loadGeneratorFloodHomepage | on | 22:13:23 | 22:18:51 | 329 | 329 |
| 8 | recommendationCacheFailure | on | 22:23:20 | 22:27:39 | 345 | 259 |

## Held records, scheduled run

40,575 returned records: offload 4,836, pass 8,555, tier_down 27,184. Every hold is labelled with the rule that made it: a plan row (the container, its cap from caps.csv, `tier_down` from actions.csv) or the fleet default (a container with no row, the fleet cap, `offload`).

| rule | container | pattern | held | held bytes | severity | in a flag's causal span | outside | windows | quiet max events / bytes |
|---|---|---|---|---|---|---|---|---|---|
| fleet default: 10,288, offload | astronomy-db | `6_l3eh1v8RE` DETAIL_Key_order_already_exists | 1,930 | 563,560 | none 1,930 | 1,930 | 0 | 2 | 0 / 0 |
| fleet default: 10,288, offload | astronomy-db | `GlK5AsFvcXg` STATEMENT_INSERT_INTO_accounting_order_id_VALUES | 1,928 | 547,552 | none 1,928 | 1,928 | 0 | 2 | 0 / 0 |
| fleet default: 10,288, offload | astronomy-db | `KSTuhseaGEc` duplicate_key_value_violates_unique_constraint_order_pkey | 926 | 262,058 | ERROR 926 | 926 | 0 | 2 | 0 / 0 |
| fleet default: 10,288, offload | astronomy-db | `oUkuI8QT6s8` role_root_does_not_exist | 52 | 13,009 | CRITICAL 52 | 9 | 43 | 19 | 47 / 11,750 |
| plan row: accounting, cap 1, tier_down | accounting | `-FtZD9XArpU` Order_details | 2,144 | 1,900,550 | INFO 2,144 | 2,020 | 124 | 18 | 17 / 14,858 |
| plan row: accounting, cap 1, tier_down | accounting | `XXzlsXqzuqc` Duplicate_order_received_skipping | 1,990 | 511,430 | INFO 1,990 | 1,990 | 0 | 2 | 0 / 0 |
| plan row: ad, cap 1,164, tier_down | ad | `xHrytxJfUdw` oteldemo_AdService_Targeted_ad_request_received_for | 253 | 85,607 | TRACE 253 | 37 | 216 | 19 | 24 / 8,127 |
| plan row: ad, cap 1,164, tier_down | ad | `jN_dDVWoa78` oteldemo_AdService_Non_targeted_ad_request_received_preparin | 4 | 1,420 | TRACE 4 | 2 | 2 | 2 | 5 / 1,775 |
| plan row: cart, cap 1, tier_down | cart | `YZplfQ4a1Xw` GetCartAsync_called_with_userId | 1,287 | 365,949 | INFO 1,287 | 313 | 974 | 19 | 80 / 22,988 |
| plan row: cart, cap 1, tier_down | cart | `eDSYlCMPqVY` AddItemAsync_called_with_userId_productId_quantity | 638 | 209,372 | INFO 638 | 149 | 489 | 19 | 46 / 15,094 |
| plan row: cart, cap 1, tier_down | cart | `h3qY1nS1uxY` EmptyCartAsync_called_with_userId | 144 | 43,158 | INFO 144 | 33 | 111 | 18 | 17 / 5,032 |
| plan row: cart, cap 1, tier_down | cart | `9-GL0Pp_Cts` Error_code_FailedPrecondition_detail_Can_access_cart_storage | 1 | 632 | INFO 1 | 1 | 0 | 1 | 0 / 0 |
| plan row: fraud-detection, cap 1, tier_down | fraud-detection | `GKfNbCrpxxI` fraud_detection_Consumed_record_with_orderId_and_updated_tot | 2,644 | 1,069,915 | TRACE 2,644 | 2,520 | 124 | 18 | 17 / 6,851 |
| plan row: fraud-detection, cap 1, tier_down | fraud-detection | `eT4avs-RfM8` fraud_detection_FeatureFlag_kafkaQueueProblems_is_enabled_sl | 446 | 163,682 | TRACE 446 | 446 | 0 | 2 | 0 / 0 |
| plan row: frontend, cap 5,551, tier_down | frontend | `INl44sUgFeY` API_request_completed | 3,947 | 1,948,551 | TRACE 3,947 | 2,122 | 1,825 | 19 | 223 / 110,168 |
| plan row: frontend, cap 5,551, tier_down | frontend | `KSy6KmHbgEc` Order_placed_successfully | 40 | 18,200 | TRACE 40 | 18 | 22 | 9 | 17 / 7,735 |
| plan row: frontend, cap 5,551, tier_down | frontend | `SJz5BYn_Kzo` Checkout_payment_declined | 6 | 3,426 | TRACE 6 | 6 | 0 | 1 | 0 / 0 |
| plan row: kafka, cap 4,163, tier_down | kafka | `wyR-oWD2-hk` Rolled_new_log_segment_at_offset_in_ms_org_apache_kafka_stor | 113 | 43,314 | INFO 113 | 17 | 96 | 19 | 16 / 6,129 |
| plan row: kafka, cap 4,163, tier_down | kafka | `VnqlcNA_PIM` Wrote_snapshot_offset_producer_ids_ms_org_apache_kafka_stora | 113 | 43,649 | INFO 113 | 18 | 95 | 19 | 16 / 6,176 |
| plan row: kafka, cap 4,163, tier_down | kafka | `hl_fK-uzMu8` Deleted_offset_index_tmp_cluster_org_apache_kafka_storage_in | 94 | 32,712 | INFO 94 | 15 | 79 | 19 | 16 / 5,568 |
| plan row: kafka, cap 4,163, tier_down | kafka | `q20KpyVGjSM` Deleted_index_tmp_cluster_org_apache_kafka_storage_internals | 94 | 32,900 | INFO 94 | 15 | 79 | 19 | 16 / 5,600 |
| plan row: kafka, cap 4,163, tier_down | kafka | `AMFi23Ga9wY` Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_a | 94 | 34,122 | INFO 94 | 15 | 79 | 19 | 16 / 5,808 |
| plan row: kafka, cap 4,163, tier_down | kafka | `pFokWfyJRLU` Deleting_segments_due_to_log_start_offset_breach_LogSegment_ | 88 | 45,828 | INFO 88 | 15 | 73 | 19 | 13 / 6,715 |
| plan row: kafka, cap 4,163, tier_down | kafka | `-Jf8QdAufSM` Deleting_segment_files_LogSegment_baseOffset_size_lastModifi | 80 | 40,218 | INFO 80 | 13 | 67 | 19 | 13 / 6,414 |
| plan row: kafka, cap 4,163, tier_down | kafka | `WlIY0QjIiEg` Deleted_tmp_cluster_org_apache_kafka_storage_internals_log_L | 75 | 25,275 | INFO 75 | 12 | 63 | 19 | 16 / 5,392 |
| plan row: kafka, cap 4,163, tier_down | kafka | `BVtz4xhx64s` older_than_retention_org_apache_kafka_raft_internals_KafkaRa | 61 | 28,137 | INFO 61 | 10 | 51 | 19 | 13 / 5,993 |
| plan row: kafka, cap 4,163, tier_down | kafka | `YJTvxN0rObQ` Creating_new_KRaft_snapshot_file_because_we_have_replayed_at | 42 | 16,800 | INFO 42 | 6 | 36 | 19 | 13 / 5,200 |
| plan row: kafka, cap 4,163, tier_down | kafka | `3AOokQ1Sq7k` Incremented_log_start_offset_to_due_snapshot_generated_org_a | 42 | 16,055 | INFO 42 | 7 | 35 | 19 | 13 / 4,966 |
| plan row: kafka, cap 4,163, tier_down | kafka | `TM6TaR-b4oE` Successfully_wrote_snapshot_org_apache_kafka_image_publisher | 4 | 1,344 | INFO 4 | 0 | 4 | 4 | 13 / 4,368 |
| plan row: otel-collector, cap 15,726, tier_down | otel-collector | `KG8Fq0QFuoY` Logs | 3,974 | 2,090,531 | INFO 3,974 | 0 | 3,974 | 19 | 243 / 127,826 |
| plan row: otel-collector, cap 15,726, tier_down | otel-collector | `Gl3Gtr_SH5w` Traces | 3,968 | 2,084,037 | INFO 3,968 | 0 | 3,968 | 19 | 240 / 126,060 |
| plan row: otel-collector, cap 15,726, tier_down | otel-collector | `PuWB8kkVbfw` Metrics | 2,967 | 1,642,057 | INFO 2,967 | 0 | 2,967 | 19 | 191 / 105,707 |
| plan row: payment, cap 2,583, tier_down | payment | `9WbTsopbiXk` Transaction_complete | 143 | 96,729 | TRACE 143 | 3 | 140 | 18 | 17 / 11,497 |
| plan row: payment, cap 2,583, tier_down | payment | `fg1YkiyrF3Q` Charge_request_received | 139 | 59,631 | TRACE 139 | 15 | 124 | 19 | 17 / 7,293 |
| plan row: payment, cap 2,583, tier_down | payment | `_N7fwt_uqyQ` Payment_request_failed_Invalid_token_demo_user_context_loyal | 4 | 3,720 | ERROR 4 | 4 | 0 | 1 | 0 / 0 |
| plan row: recommendation, cap 1, tier_down | recommendation | `bzLB1zZCTIw` Receive_ListRecommendations_for_product_ids | 275 | 134,200 | INFO 275 | 65 | 210 | 19 | 27 / 13,176 |
| plan row: recommendation, cap 1, tier_down | recommendation | `QE9Wwe64YPk` get_product_list_cache_hit | 14 | 5,614 | INFO 14 | 14 | 0 | 3 | 0 / 0 |
| plan row: recommendation, cap 1, tier_down | recommendation | `pQCM0VaOm6U` get_product_list_cache_miss | 5 | 2,010 | INFO 5 | 5 | 0 | 2 | 0 / 0 |
| plan row: shipping, cap 765, tier_down | shipping | `kAB8PMmHyKM` shipping_service_Requesting_quote_http_getquote | 158 | 66,202 | none 158 | 0 | 158 | 19 | 17 / 7,123 |
| plan row: shipping, cap 765, tier_down | shipping | `PX-oZ7rxgZo` Sending_Quote | 158 | 65,591 | none 158 | 0 | 158 | 19 | 17 / 7,055 |
| plan row: shipping, cap 765, tier_down | shipping | `LnOvjJt0La4` Tracking_ID_Created | 143 | 59,774 | none 143 | 0 | 143 | 18 | 17 / 7,106 |
| plan row: telemetry-docs, cap 1, tier_down | telemetry-docs | `zxRYTKQNyBY` GET_HTTP_Wget | 792 | 206,712 | none 792 | 0 | 792 | 19 | 48 / 12,528 |

## Per flag activation

Span: flag on to one 4-minute window after it reverts, or the next flag on. Rows are the containers on the flag's causal path (demo 3.1.0 source). "New" holds are patterns with no hold in the 10 minutes before the flag (or since the fleet Receiver started); "steady" holds are patterns already held then, such as every statement of a plan row with cap 1. "First noisy" is the first record of the first pattern whose records in a minute reach 5 and 5 times its rate in those 10 minutes.

| # | flag | on to off | container | rule | first noisy | first new hold | new held (offload / tier_down) | kept, same patterns | bytes held (new) | steady held | patterns newly held |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | cartFailure | 21:13:32 to 21:20:27 | cart | plan row: cart, cap 1, tier_down | 21:16:50 Error_code_FailedPrecondition_ | 21:17:37 | 1 (0 / 1) | 12 | 632 | 224 | Error_code_FailedPrecondition_detail_Can x1 |
| 2 | kafkaQueueProblems | 21:23:56 to 21:31:35 | astronomy-db | fleet default: 10,288, offload | 21:23:58 duplicate_key_value_violates_u | 21:23:58 | 4,784 (4,784 / 0) | 1,216 | 1,373,170 | 9 | DETAIL_Key_order_already_exists x1,930; STATEMENT_INSERT_INTO_accounting_order_i x1,928; duplicate_key_value_violates_unique_cons x926 |
| 2 | kafkaQueueProblems | 21:23:56 to 21:31:35 | accounting | plan row: accounting, cap 1, tier_down | 21:23:58 Order_details | 21:23:58 | 1,990 (0 / 1,990) | 10 | 511,430 | 2,020 | Duplicate_order_received_skipping x1,990 |
| 2 | kafkaQueueProblems | 21:23:56 to 21:31:35 | fraud-detection | plan row: fraud-detection, cap 1, tier_down | 21:23:58 fraud_detection_FeatureFlag_ka | 21:24:03 | 446 (0 / 446) | 10 | 163,682 | 2,520 | fraud_detection_FeatureFlag_kafkaQueuePr x446 |
| 3 | paymentFailure | 21:35:54 to 21:40:56 | frontend | plan row: frontend, cap 5,551, tier_down | 21:35:59 Checkout_payment_declined | 21:38:07 | 6 (0 / 6) | 12 | 3,426 | 466 | Checkout_payment_declined x6 |
| 3 | paymentFailure | 21:35:54 to 21:40:56 | payment | plan row: payment, cap 2,583, tier_down | 21:35:59 Payment_request_failed_Invalid | 21:37:27 | 4 (0 / 4) | 14 | 3,720 | 18 | Payment_request_failed_Invalid_token_dem x4 |
| 4 | emailMemoryLeak | 21:44:28 to 21:52:20 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 5 | emailMemoryLeak | 21:52:47 to 21:59:37 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 6 | recommendationCacheFailure | 22:05:18 to 22:12:17 | recommendation | plan row: recommendation, cap 1, tier_down | 22:07:22 get_product_list_cache_hit | 22:07:17 | 12 (0 / 12) | 22 | 4,817 | 28 | get_product_list_cache_hit x7; get_product_list_cache_miss x5 |
| 7 | loadGeneratorFloodHomepage | 22:13:23 to 22:18:51 | ad | plan row: ad, cap 1,164, tier_down |   | 22:15:31 | 2 (0 / 2) | 8 | 710 | 37 | oteldemo_AdService_Non_targeted_ad_reque x2 |
| 8 | recommendationCacheFailure | 22:23:20 to 22:27:39 | recommendation | plan row: recommendation, cap 1, tier_down | 22:25:37 get_product_list_cache_hit | 22:26:02 | 7 (0 / 7) | 5 | 2,807 | 8 | get_product_list_cache_hit x7 |

New holds in containers off the flag's causal path, inside its span: #1 kafka 145 (Rolled_new_log_segment_at_offset_in_ms_org_apache_kafka_storage_internals_LocalLog, Wrote_snapshot_offset_producer_ids_m; plan row: kafka, cap 4,163, tier_down); #1 astronomy-db 8 (role_root_does_not_exist; fleet default: 10,288, offload); #1 ad 2 (oteldemo_AdService_Non_targeted_ad_request_received_preparing_random_response_trace_id_span_flags; plan row: ad, cap 1,164, tier_down); #2 frontend 1 (Order_placed_successfully; plan row: frontend, cap 5,551, tier_down); #6 kafka 1 (Successfully_wrote_snapshot_org_apache_kafka_image_publisher_SnapshotEmitter; plan row: kafka, cap 4,163, tier_down).

## False holds and the plan's moves

Fleet-default holds outside every flag's causal span: 43 records in 1 (container, pattern) pairs.

| container | pattern | held outside a causal span | windows | quiet run: max events, max bytes, median bytes per window |
|---|---|---|---|---|
| astronomy-db | `oUkuI8QT6s8` role_root_does_not_exist | 43 | 19 | 47, 11,750, 11,750 |

The plan's rows (`tier_down`), per container per Receiver window:

| container | cap in caps.csv | windows | median per window | max | total |
|---|---|---|---|---|---|
| otel-collector | 15726.0 | 19 | 576 | 583 | 10,909 |
| accounting | 1.0 | 18 | 8.0 | 2403 | 4,134 |
| frontend | 5551.0 | 19 | 208 | 272 | 3,993 |
| fraud-detection | 1.0 | 18 | 8.0 | 2499 | 3,090 |
| cart | 1.0 | 19 | 103 | 170 | 2,070 |
| kafka | 4163.0 | 19 | 46 | 55 | 900 |
| telemetry-docs | 1.0 | 19 | 42 | 43 | 792 |
| shipping | 765.0 | 19 | 20 | 54 | 459 |
| recommendation | 1.0 | 19 | 15 | 31 | 294 |
| payment | 2583.0 | 19 | 13 | 35 | 286 |
| ad | 1164.0 | 19 | 12 | 22 | 257 |

## Errors against the 0.5 floor

ERROR and CRITICAL records held: 982; passed: 1,999.

| rule | container | pattern | severity | held | passed | flags |
|---|---|---|---|---|---|---|
| fleet default: 10,288, offload | astronomy-db | `KSTuhseaGEc` duplicate_key_value_violates_unique_constraint_order_pkey | ERROR | offload 926 | 1,074 | kafkaQueueProblems 926 |
| fleet default: 10,288, offload | astronomy-db | `oUkuI8QT6s8` role_root_does_not_exist | CRITICAL | offload 52 | 821 | kafkaQueueProblems 9 |
| plan row: payment, cap 2,583, tier_down | payment | `_N7fwt_uqyQ` Payment_request_failed_Invalid_token_demo_user_context_loyal | ERROR | tier_down 4 | 14 | paymentFailure 4 |

Records over the cap in a replay of each Receiver window (rb_ts order; the first 5 pass, then pass while the window's bytes stay within the cap), by severity and what the Receiver did:

| severity | over the cap: passed | held | passed share | floor |
|---|---|---|---|---|
| CRITICAL | 59 | 45 | 0.567 | 0.5 |
| ERROR | 1,007 | 930 | 0.520 | 0.5 |
| INFO | 174 | 18,127 | 0.010 | 0.0 |
| TRACE | 84 | 7,536 | 0.011 | 0.0 |
| none | 21 | 5,085 | 0.004 | 0 |

Replay against the Receiver: under the cap and passed 7,210, under and held 297, over and passed 1,345, over and held 31,723. Windows start 235.5 s past a multiple of 240 s of epoch time (receiver.log connect); the phase read from the data alone (first pass after a run of holds) is 239 s, with 44.9% of 1,009 resets within 20 s of it.

## Latency

Seconds from `fb_ts` (the Docker driver's event time for the line) to `rb_ts` (when Fluent Bit's return-path filter received the record back from the Receiver). For a record that joins several lines, `fb_ts` is its first line's.

Scheduled run (40,575 records): median 2.01, p99 28.86, max 472.3; 1,714 over 10 s.

| container | records | median | p99 | max | over 10 s |
|---|---|---|---|---|---|
| accounting | 4,230 | 1.80 | 32.00 | 309.0 | 139 |
| ad | 405 | 9.22 | 55.49 | 70.9 | 187 |
| astronomy-db | 6,903 | 2.00 | 7.69 | 9.9 | 0 |
| cart | 2,349 | 2.05 | 19.21 | 32.4 | 170 |
| email | 230 | 12.96 | 94.63 | 309.0 | 140 |
| flagd | 15 | 302.98 | 469.69 | 471.5 | 15 |
| flagd-ui | 33 | 3.12 | 468.13 | 472.3 | 16 |
| fraud-detection | 3,186 | 2.03 | 34.67 | 309.0 | 129 |
| frontend | 4,394 | 2.31 | 7.25 | 12.4 | 2 |
| kafka | 3,409 | 1.94 | 16.53 | 17.9 | 266 |
| otel-collector | 12,551 | 1.82 | 5.52 | 8.1 | 0 |
| payment | 497 | 2.55 | 85.08 | 130.6 | 150 |
| quote | 248 | 13.35 | 87.87 | 130.8 | 150 |
| recommendation | 414 | 8.63 | 58.75 | 95.5 | 186 |
| shipping | 760 | 2.00 | 70.60 | 130.6 | 150 |
| telemetry-docs | 882 | 6.67 | 8.05 | 11.0 | 1 |
| valkey-cart | 69 | 1.53 | 369.94 | 399.7 | 13 |

What the scheduled run's 1,714 records over 10 s waited for: 1,691 came back within 5 s after their own container's next raw line (median 1.66 s after it), 23 later than that, 0 had no next line before the stop. The Receiver seals an open event on its source's next head line, on the group size limit, or after 5 s with nothing arriving on the whole input, a timer that is not per source (E81). The waits measured here match the first case: a record came back once its container wrote again.

Every returned record from the first Receiver start (52,324): median 2.05, p99 54.80, max 901.5; 3,134 over 10 s, by when the line was written: before the quiet run 802, quiet run 527, between quiet end and scheduler start 91, scheduled run 1,714. `latency-over-10s.csv` lists every one with its container.

| container | records | median | p99 | max | over 10 s |
|---|---|---|---|---|---|
| accounting | 4,341 | 1.85 | 38.11 | 309.0 | 212 |
| ad | 549 | 9.22 | 58.36 | 106.6 | 257 |
| astronomy-db | 7,334 | 2.07 | 8.10 | 111.7 | 38 |
| cart | 3,119 | 2.06 | 20.46 | 41.4 | 252 |
| currency | 1 | 47.59 | 47.59 | 47.6 | 1 |
| email | 333 | 12.75 | 87.90 | 309.0 | 195 |
| flagd | 33 | 9.05 | 467.35 | 471.5 | 16 |
| flagd-ui | 36 | 4.57 | 467.74 | 472.3 | 17 |
| fraud-detection | 3,275 | 2.08 | 42.16 | 309.0 | 186 |
| frontend | 5,850 | 2.33 | 7.81 | 29.2 | 20 |
| frontend-proxy | 128 | 13.65 | 438.90 | 901.5 | 128 |
| image-provider | 65 | 3.28 | 117.72 | 250.5 | 13 |
| kafka | 5,179 | 1.89 | 117.05 | 117.9 | 562 |
| otel-collector | 18,072 | 1.86 | 35.33 | 118.6 | 299 |
| payment | 662 | 2.61 | 85.38 | 130.6 | 206 |
| product-catalog | 1 | 250.74 | 250.74 | 250.7 | 1 |
| quote | 332 | 13.79 | 87.28 | 130.8 | 205 |
| recommendation | 557 | 9.10 | 58.59 | 95.5 | 260 |
| shipping | 1,031 | 2.02 | 70.63 | 130.6 | 210 |
| telemetry-docs | 1,325 | 6.67 | 44.41 | 119.0 | 37 |
| valkey-cart | 101 | 1.77 | 355.95 | 399.7 | 19 |

## Delivery

Scheduled run (21:12:28 to 22:27:44 UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).

| container | raw lines | returned records | lines covered | covered minus raw |
|---|---|---|---|---|
| accounting | 8,462 | 4,230 | 8,460 | -2 |
| ad | 452 | 405 | 451 | -1 |
| astronomy-db | 8,903 | 6,903 | 8,903 | +0 |
| cart | 4,752 | 2,349 | 4,750 | -2 |
| email | 462 | 230 | 460 | -2 |
| flagd | 16 | 15 | 15 | -1 |
| flagd-ui | 34 | 33 | 33 | -1 |
| fraud-detection | 3,187 | 3,186 | 3,186 | -1 |
| frontend | 4,394 | 4,394 | 4,394 | +0 |
| kafka | 3,409 | 3,409 | 3,409 | +0 |
| otel-collector | 13,633 | 12,551 | 13,633 | +0 |
| payment | 498 | 497 | 497 | -1 |
| quote | 249 | 248 | 248 | -1 |
| recommendation | 415 | 414 | 414 | -1 |
| shipping | 761 | 760 | 760 | -1 |
| telemetry-docs | 883 | 882 | 882 | -1 |
| valkey-cart | 70 | 69 | 69 | -1 |
| total | 50,580 | 40,575 | 50,564 | -16 |

Whole run, from the first Receiver start (20:35:53 to 22:27:44 UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).

| container | raw lines | returned records | lines covered | covered minus raw |
|---|---|---|---|---|
| accounting | 8,659 | 4,341 | 8,657 | -2 |
| ad | 623 | 549 | 622 | -1 |
| astronomy-db | 9,364 | 7,334 | 9,364 | +0 |
| cart | 6,286 | 3,119 | 6,284 | -2 |
| currency | 1 | 1 | 1 | +0 |
| email | 653 | 333 | 652 | -1 |
| flagd | 34 | 33 | 33 | -1 |
| flagd-ui | 37 | 36 | 36 | -1 |
| fraud-detection | 3,276 | 3,275 | 3,275 | -1 |
| frontend | 5,849 | 5,849 | 5,849 | +0 |
| frontend-proxy | 135 | 128 | 135 | +0 |
| image-provider | 65 | 65 | 65 | +0 |
| kafka | 6,377 | 5,178 | 6,377 | +0 |
| otel-collector | 21,196 | 18,066 | 21,196 | +0 |
| payment | 664 | 662 | 663 | -1 |
| product-catalog | 1 | 1 | 1 | +0 |
| quote | 353 | 332 | 352 | -1 |
| recommendation | 558 | 557 | 557 | -1 |
| shipping | 1,032 | 1,031 | 1,031 | -1 |
| telemetry-docs | 1,326 | 1,325 | 1,325 | -1 |
| valkey-cart | 102 | 101 | 101 | -1 |
| total | 66,591 | 52,316 | 66,576 | -15 |

Lines written up to 60 s before the stop: 66,255 raw, 66,255 covered. In the last 60 s: 336 raw, 321 covered; the difference is each container's last event, still open in the Receiver when the demo stopped.

## What the fleet default would hold alone

The same replay with the install seed in place of the plan's rows, so every container takes the fleet default (10,288 bytes): 28,019 records held (expected, floors applied), 13,831 of them inside a flag's causal span, 1,018 ERROR or CRITICAL.

## Reading

**Which rule held what.** Of the 40,575 records the Receiver returned in the scheduled run, 27,184 were held by the plan's rows (`tier_down`), 4,836 by the fleet default (`offload`), and 8,555 passed. The fleet default acted on one container: astronomy-db, the only container with no row whose patterns went above 10,288 bytes in a window.

**kafkaQueueProblems, 21:23:56 to 21:31:35.** Causal path (demo 3.1.0 source): checkout publishes each order 100 extra times to Kafka; accounting logs `Order details` and `Duplicate order received, skipping.` for each copy, and its INSERT fails on the primary key, so Postgres (astronomy-db) writes an ERROR, a DETAIL and a STATEMENT line for each copy; fraud-detection logs `FeatureFlag 'kafkaQueueProblems' is enabled, sleeping 1 second` and `Consumed record` for each copy.

- astronomy-db, fleet default (10,288 bytes, offload): the first duplicate-key line came at 21:23:58 and was held 0.18 s later. Held 4,784 records, 1,373,170 bytes: DETAIL 1,930, STATEMENT 1,928, ERROR 926. Kept 70, 72 and 1,074 of the same patterns. Last hold 21:30:31.
- accounting, plan row (cap 1, tier_down): `Duplicate order received` 1,990 held, 10 kept, first at 21:23:58. `Order details` was already held before the flag; 2,020 of it were held in the span.
- fraud-detection, plan row (cap 1, tier_down): the `sleeping 1 second` line 446 held, 10 kept, first held at 21:24:03, 5 s after it first appeared. `Consumed record` was already held; 2,520 of it were held in the span.

**The other seven activations.** Their new lines fell in containers with a plan row, held at the row's cap: cart's `FailedPrecondition ... Can't access cart storage` (1 held, 12 kept), payment's `Payment request failed. Invalid token` (a pino line with `"level":"warn"` and an `err` object, which the Receiver labelled ERROR; 4 held, 14 passed), frontend's `Checkout payment declined` (6 held, 12 kept), recommendation's cache hit and miss lines (12 held in activation 6, 7 in activation 8). The two emailMemoryLeak activations held nothing new on their path: email has no row and its lines stayed under 10,288. The homepage flood held 2 of ad's non-targeted ad lines.

**False holds.** One fleet-default pair, astronomy-db `FATAL: role "root" does not exist` (CRITICAL): 52 held, 43 of them outside every flag's causal span and 9 inside the kafka span; 821 passed. Its rate is the same in both runs: 47 lines and 11,750 bytes in every Receiver window of the scheduled run, and 47 lines and 11,750 bytes in its largest quiet-run window. That is above 10,288, so about 3 lines a window fall above the cap and the CRITICAL floor passes half of them.

**The plan's own moves.** The plan's rows held otel-collector's debug-exporter dumps (`Logs` 3,974, `Traces` 3,968, `Metrics` 2,967) and frontend's `API request completed` (3,947). They also held every statement past the first 5 a window in the five containers whose row is cap 1 (accounting, cart, fraud-detection, recommendation, telemetry-docs), and shipping's, kafka's, payment's and ad's routine lines above their caps.

**Errors.** 982 ERROR and CRITICAL records were held: astronomy-db's duplicate key 926 and `role "root"` 52 (fleet default, offload), and payment's `Payment request failed` 4 (plan row, tier_down). 1,999 passed. Above the cap, 1,007 of 1,937 ERROR records passed (0.520) and 59 of 104 CRITICAL records (0.567), against a floor of 0.5. The DETAIL and STATEMENT lines that go with each duplicate-key ERROR carry no level, so they take `rateReceiverMinRetentionThreshold` 0 and are held (1,930 and 1,928 held, 70 and 72 kept). An ERROR line the floor passes arrives without its DETAIL and STATEMENT lines.

**The cap's unit.** The MCP's baseline, 5,144 bytes per window for otel-collector's `Error scraping metrics`, counts the unwrapped log payload (the POC's note: "analysed bytes count the unwrapped payload"). The Receiver counts the record as it arrives, and in the quiet run the same statement averaged 7,103 of those bytes per window. So 10,288 is 1.45 times that statement in the Receiver's unit, not 2.

**Latency.** In the scheduled run the median is 2.0 s and p99 28.9 s. 1,714 records came back more than 10 s after `fb_ts`. 1,691 of them came back within 5 s after their own container's next line, so the lower-rate containers (ad, recommendation, quote, payment, shipping, email) wait for their next line. accounting, email and fraud-detection share a 309 s maximum: their last order lines before paymentFailure (21:35:53) came back with the next completed order (21:41:00). flagd and flagd-ui, which write once per flag change, reach 472 s.

**Delivery.** Every raw line written up to 60 s before the stop came back (66,255 of 66,255, counting the lines inside joined records). In the last 60 s, 15 lines did not: one or two per container, each container's last event, still open when the demo stopped. Relaunching the Receiver at 21:11:55 lost no line.

**The fleet default alone.** Replaying the same records with the install seed in place of the plan's rows, so that every container takes 10,288 bytes, holds 28,019 records (floors applied). 13,831 of those fall inside a flag's causal span and 1,018 are ERROR or CRITICAL.

