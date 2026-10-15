# Containment demo: a fleet-default cap on the OpenTelemetry demo's own incidents

All figures below come from this run's files in `results/` and are rendered by `rig/report.py` from `rig/analyze.py`'s `analysis.json`.

## What ran

- OpenTelemetry demo 3.1.0 (`compose.yaml` + `compose.full.yaml`), every container's stdout and stderr through the Docker `fluentd` driver to Fluent Bit 4.2, which keeps a raw copy, hands each record to the log10x Receiver and writes what comes back to one file per `routeState`.
- Receiver: `log10x/edge-10x:1.1.142@sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`, the released image with its own config and modules, launched with the values log10x-mcp 1.30.58 renders (below).
- Plan: log10x-mcp 1.30.58 `poc_from_local` on the quiet capture with `{"headroom": 2, "action": "offload", "error_floor": 0.5}`, engine `log10x/edge-10x:1.1.142@sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`.
- Demo setting from the rig: `FLAGD_CACHE=disabled` on checkout, so its flagd provider asks flagd on every order and a scheduled kafkaQueueProblems change reaches it (`rig/README.md`, "checkout's flag cache").
- Scheduler: flagd-ui, seed 20261014, interval 600 s, hold 240 to 480 s, one flag at a time, flags kafkaQueueProblems (on), cartFailure (100%), paymentFailure (100%), recommendationCacheFailure (on), loadGeneratorFloodHomepage (on), emailMemoryLeak (1000x). Scheduled run 12:47:51 to 14:02:55 UTC on 2026-10-15.

## Timeline (UTC)

| event | at |
|---|---|
| receiver_ready | 12:14:29 |
| demo_up | 12:21:15 |
| demo_healthy | 12:22:23 |
| quiet_start | 12:24:23 |
| quiet_end | 12:46:23 |
| receiver_ready | 12:47:16 |
| scheduler_start | 12:47:51 |
| planned_end | 14:02:52 |
| scheduler_stop | 14:02:53 |
| run_end | 14:02:55 |
| demo_down | 14:03:34 |

## Quiet run and the fleet default

Quiet run 12:24:23 to 12:46:23 UTC, no flag active, Receiver with no cap: 9,118 raw lines, 7,938 returned records, 70 (container, pattern) pairs in 17 containers, 5 full 4-minute windows, 0 records held.

The POC on that capture: `met: false`, 49.7% reached against the 70% target, keep-everything lever `tier_down`; 31 planned and 40 kept statements.

| fleet default | value |
|---|---|
| `cap_bytes_per_window_per_node` | **71,247** |
| baseline | 35,623.7 bytes per window: `error_Error_scraping_metrics` in otel-collector |
| headroom, action, error floor | 2, `offload`, 0.5 |
| sentence | Any service not listed: a statement above 16,699 lines a day goes to the offload bucket. Up to 1,800 lines a day of every statement always reach Standard on each node. |
| the baseline statement in the Receiver's unit (quiet run) | 15,630 record bytes per window on average, 37,370 at most |

The 20 largest (container, pattern) pairs of the quiet run, by their largest 4-minute window in the bytes the Receiver counts (the compact JSON of the record as it arrives), with the rule that covers each in the scheduled run:

| container | pattern | rule | largest window: events | bytes |
|---|---|---|---|---|
| otel-collector | `KG8Fq0QFuoY` Logs | plan row: otel-collector, cap 61,996, tier_down | 240 | 126,257 |
| otel-collector | `Gl3Gtr_SH5w` Traces | plan row: otel-collector, cap 61,996, tier_down | 240 | 126,053 |
| frontend | `INl44sUgFeY` API_request_completed | plan row: frontend, cap 30,210, tier_down | 215 | 106,272 |
| otel-collector | `PuWB8kkVbfw` Metrics | plan row: otel-collector, cap 61,996, tier_down | 191 | 105,712 |
| kafka | `Y_71jRCq5Cw` Scheduling_unloading_of_metadata_for_consumer_with | plan row: kafka, cap 20,074, tier_down | 100 | 37,580 |
| otel-collector | `fhu6rrW86b4` error_Error_scraping_metrics | plan row: otel-collector, cap 61,996, tier_down | 19 | 37,370 |
| kafka | `KjKx7VN7snY` was_spent_in_the_scheduler_Loaded_records_which_to | plan row: kafka, cap 20,074, tier_down | 83 | 37,255 |
| kafka | `wfraEN4ubTY` Finished_unloading_metadata_for_consumer_with_epoc | plan row: kafka, cap 20,074, tier_down | 100 | 37,180 |
| kafka | `VvBjD4t0T7w` Started_unloading_metadata_for_consumer_with_epoch | plan row: kafka, cap 20,074, tier_down | 100 | 37,080 |
| kafka | `lfxNT0TdHRU` Scheduling_loading_of_metadata_from_consumer_with_ | plan row: kafka, cap 20,074, tier_down | 100 | 36,180 |
| cart | `YZplfQ4a1Xw` GetCartAsync_called_with_userId | plan row: cart, cap 1, tier_down | 63 | 17,829 |
| telemetry-docs | `zxRYTKQNyBY` GET_HTTP_Wget | plan row: telemetry-docs, cap 1, tier_down | 47 | 12,267 |
| cart | `eDSYlCMPqVY` AddItemAsync_called_with_userId_productId_quantity | plan row: cart, cap 1, tier_down | 36 | 11,817 |
| astronomy-db | `oUkuI8QT6s8` role_root_does_not_exist | fleet default: 71,247, offload | 47 | 11,728 |
| kafka | `JUW-7iX1rdw` consumer_because_the_partition_is_not_online_or_no | plan row: kafka, cap 20,074, tier_down | 17 | 11,143 |
| recommendation | `bzLB1zZCTIw` Receive_ListRecommendations_for_product_ids | plan row: recommendation, cap 2,330, tier_down | 21 | 10,248 |
| accounting | `-FtZD9XArpU` Order_details | plan row: accounting, cap 2,765, tier_down | 11 | 10,050 |
| ad | `xHrytxJfUdw` oteldemo_AdService_Targeted_ad_request_received_fo | plan row: ad, cap 1, tier_down | 22 | 7,438 |
| payment | `9WbTsopbiXk` Transaction_complete | plan row: payment, cap 2,344, tier_down | 11 | 7,435 |
| kafka | `pFokWfyJRLU` Deleting_segments_due_to_log_start_offset_breach_L | plan row: kafka, cap 20,074, tier_down | 12 | 6,232 |

## The values the Receiver ran with

Rendered by log10x-mcp 1.30.58 (`receiverFleetValues` with the POC's `fleet_default`, then the Fluent Bit Receiver overlay's `renderValues`, the two calls `log10x_advise_install` makes; `results/values-fleet/values.yaml` is the overlay verbatim). Arguments, in order:

```text
@run/input/forwarder/fluentbit
@apps/receiver
symbolMessageHashField
tenx_hash
rateReceiverAbsoluteCap
71247
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
accounting,2765::accounting any statement above 691 lines a day goes to Flex. Today that is these 45 statements about $0.16 a month.
ad,1::ad every statement goes to Flex. Today that is these 7 statements about $0.32 a month.
cart,1::cart every statement goes to Flex. Today that is these 9 statements about $1.8 a month.
email,1::email every statement goes to Flex. Today that is these 4 statements about $0.16 a month.
fraud-detection,1::fraud-detection every statement goes to Flex. Today that is these 2 statements about $0.16 a month.
frontend,30210::frontend any statement above 8189 lines a day goes to Flex. Today that is these 7 statements about $3.5 a month.
frontend-proxy,1::frontend-proxy every statement goes to Flex. Today that is this one statement about $0 a month.
kafka,20074::kafka any statement above 1889 lines a day goes to Flex. Today that is these 12 statements about $1.6 a month.
otel-collector,61996::otel-collector any statement above 2508 lines a day goes to Flex. Today that is these 9 statements about $12 a month.
payment,2344::payment any statement above 204 lines a day goes to Flex. Today that is these 27 statements about $0.31 a month.
quote,1::quote every statement goes to Flex. Today that is this one statement about $0.16 a month.
recommendation,2330::recommendation any statement above 315 lines a day goes to Flex. Today that is these 6 statements about $0.32 a month.
shipping,2721::shipping any statement above 849 lines a day goes to Flex. Today that is these 13 statements about $0.47 a month.
telemetry-docs,1::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.81 a month.
valkey-cart,1::valkey-cart every statement goes to Flex. Today that is these 5 statements about $0.07 a month.
```

```text
container,action
accounting,tier_down::accounting any statement above 691 lines a day goes to Flex. Today that is these 45 statements about $0.16 a month.
ad,tier_down::ad every statement goes to Flex. Today that is these 7 statements about $0.32 a month.
cart,tier_down::cart every statement goes to Flex. Today that is these 9 statements about $1.8 a month.
email,tier_down::email every statement goes to Flex. Today that is these 4 statements about $0.16 a month.
fraud-detection,tier_down::fraud-detection every statement goes to Flex. Today that is these 2 statements about $0.16 a month.
frontend,tier_down::frontend any statement above 8189 lines a day goes to Flex. Today that is these 7 statements about $3.5 a month.
frontend-proxy,tier_down::frontend-proxy every statement goes to Flex. Today that is this one statement about $0 a month.
kafka,tier_down::kafka any statement above 1889 lines a day goes to Flex. Today that is these 12 statements about $1.6 a month.
otel-collector,tier_down::otel-collector any statement above 2508 lines a day goes to Flex. Today that is these 9 statements about $12 a month.
payment,tier_down::payment any statement above 204 lines a day goes to Flex. Today that is these 27 statements about $0.31 a month.
quote,tier_down::quote every statement goes to Flex. Today that is this one statement about $0.16 a month.
recommendation,tier_down::recommendation any statement above 315 lines a day goes to Flex. Today that is these 6 statements about $0.32 a month.
shipping,tier_down::shipping any statement above 849 lines a day goes to Flex. Today that is these 13 statements about $0.47 a month.
telemetry-docs,tier_down::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.81 a month.
valkey-cart,tier_down::valkey-cart every statement goes to Flex. Today that is these 5 statements about $0.07 a month.
```

Where each row's cap sits (`plan.containerCaps`, in bytes per 4-minute window: each statement at its busiest quiet window in the Receiver's unit, the figure caps.csv is written from): between the largest statement the plan keeps and the smallest it moves, at their geometric mean, so the margin is the same each way. A row with no kept statement gets cap 1: every statement past the first 5 a window takes the row's action.

| container | cap in caps.csv | largest kept statement | bytes per window | smallest moved statement | bytes per window | margin each way |
|---|---|---|---|---|---|---|
| accounting | 2,765 | brokers_are_down | 524 | Order_details | 14,596 | 5.3x |
| recommendation | 2,330 | Failed_to_export_metrics_otel_collector_error_code | 484 | Receive_ListRecommendations_for_product_ids | 11,224 | 4.8x |
| frontend | 30,210 | Order_placed_successfully | 7,735 | API_request_completed | 118,045 | 3.9x |
| payment | 2,344 | Transaction_complete_Order_confirmation_email_sent | 754 | Charge_request_received | 7,293 | 3.1x |
| shipping | 2,721 | flagd_off | 1,050 | Sending_Quote | 7,057 | 2.6x |
| kafka | 20,074 | consumer_because_the_partition_is_not_online_or_no | 11,143 | Scheduling_loading_of_metadata_from_consumer_with_ | 36,180 | 1.8x |
| otel-collector | 61,996 | error_Error_scraping_metrics | 35,632 | Metrics | 107,918 | 1.7x |
| ad | 1 | (none) | 0 | oteldemo_AdService_Non_targeted_ad_request_receive | 1,420 | none |
| cart | 1 | (none) | 0 | EmptyCartAsync_called_with_userId | 5,032 | none |
| email | 1 | (none) | 0 | POST_send_order_confirmation_HTTP | 5,950 | none |
| fraud-detection | 1 | (none) | 0 | fraud_detection_Consumed_record_with_orderId_and_u | 6,851 | none |
| frontend-proxy | 1 | (none) | 0 | shutting_down_parent_after_drain | 296 | none |
| quote | 1 | (none) | 0 | POST_getquote_HTTP | 3,978 | none |
| telemetry-docs | 1 | (none) | 0 | GET_HTTP_Wget | 12,528 | none |
| valkey-cart | 1 | (none) | 0 | DB_saved_on_disk | 228 | none |

## Flag timeline

| # | flag | variant | on | off | planned s | actual s |
|---|---|---|---|---|---|---|
| 1 | cartFailure | 100% | 12:48:55 | 12:55:50 | 415 | 415 |
| 2 | kafkaQueueProblems | on | 12:59:19 | 13:06:58 | 459 | 459 |
| 3 | paymentFailure | 100% | 13:11:18 | 13:16:19 | 301 | 301 |
| 4 | emailMemoryLeak | 1000x | 13:19:51 | 13:27:43 | 472 | 472 |
| 5 | emailMemoryLeak | 1000x | 13:28:10 | 13:35:00 | 410 | 410 |
| 6 | recommendationCacheFailure | on | 13:40:41 | 13:47:40 | 419 | 419 |
| 7 | loadGeneratorFloodHomepage | on | 13:48:46 | 13:54:14 | 329 | 329 |
| 8 | recommendationCacheFailure | on | 13:58:44 | 14:02:53 | 345 | 249 |

## Held records, scheduled run

44,767 returned records: offload 5,555, pass 16,480, tier_down 22,732. Every hold is labelled with the rule that made it: a plan row (the container, its cap from caps.csv, `tier_down` from actions.csv) or the fleet default (a container with no row, the fleet cap, `offload`).

| rule | container | pattern | held | held bytes | severity | in a flag's causal span | outside | windows | quiet max events / bytes |
|---|---|---|---|---|---|---|---|---|---|
| fleet default: 71,247, offload | astronomy-db | `6_l3eh1v8RE` DETAIL_Key_order_already_exists | 2,214 | 646,488 | none 2,214 | 2,214 | 0 | 2 | 0 / 0 |
| fleet default: 71,247, offload | astronomy-db | `GlK5AsFvcXg` STATEMENT_INSERT_INTO_accounting_order_id_VALUES | 2,200 | 624,800 | none 2,200 | 2,200 | 0 | 2 | 0 / 0 |
| fleet default: 71,247, offload | astronomy-db | `KSTuhseaGEc` duplicate_key_value_violates_unique_constraint_order_pkey | 1,141 | 322,903 | ERROR 1,141 | 1,141 | 0 | 2 | 0 / 0 |
| plan row: accounting, cap 2,765, tier_down | accounting | `-FtZD9XArpU` Order_details | 2,849 | 2,577,487 | INFO 2,849 | 2,720 | 129 | 18 | 11 / 10,050 |
| plan row: accounting, cap 2,765, tier_down | accounting | `XXzlsXqzuqc` Duplicate_order_received_skipping | 2,680 | 688,760 | INFO 2,680 | 2,680 | 0 | 2 | 0 / 0 |
| plan row: ad, cap 1, tier_down | ad | `xHrytxJfUdw` oteldemo_AdService_Targeted_ad_request_received_for | 218 | 73,780 | TRACE 218 | 20 | 198 | 19 | 22 / 7,438 |
| plan row: ad, cap 1, tier_down | ad | `jN_dDVWoa78` oteldemo_AdService_Non_targeted_ad_request_received_preparin | 3 | 1,065 | TRACE 3 | 0 | 3 | 1 | 4 / 1,420 |
| plan row: cart, cap 1, tier_down | cart | `YZplfQ4a1Xw` GetCartAsync_called_with_userId | 1,273 | 363,655 | INFO 1,273 | 351 | 922 | 19 | 63 / 17,829 |
| plan row: cart, cap 1, tier_down | cart | `eDSYlCMPqVY` AddItemAsync_called_with_userId_productId_quantity | 661 | 216,909 | INFO 661 | 191 | 470 | 19 | 36 / 11,817 |
| plan row: cart, cap 1, tier_down | cart | `h3qY1nS1uxY` EmptyCartAsync_called_with_userId | 149 | 45,973 | INFO 149 | 50 | 99 | 18 | 11 / 3,256 |
| plan row: cart, cap 1, tier_down | cart | `9-GL0Pp_Cts` Error_code_FailedPrecondition_detail_Can_access_cart_storage | 16 | 10,112 | INFO 16 | 16 | 0 | 3 | 0 / 0 |
| plan row: email, cap 1, tier_down | email | `1zhBPd1E9Bc` POST_send_order_confirmation_HTTP | 149 | 43,492 | none 149 | 42 | 107 | 18 | 11 / 3,304 |
| plan row: email, cap 1, tier_down | email | `shf1OAS338c` Order_confirmation_email_sent_for_order | 83 | 20,584 | none 83 | 24 | 59 | 18 | 7 / 1,736 |
| plan row: fraud-detection, cap 1, tier_down | fraud-detection | `GKfNbCrpxxI` fraud_detection_Consumed_record_with_orderId_and_updated_tot | 3,349 | 1,355,393 | TRACE 3,349 | 3,220 | 129 | 18 | 11 / 4,433 |
| plan row: fraud-detection, cap 1, tier_down | fraud-detection | `eT4avs-RfM8` fraud_detection_FeatureFlag_kafkaQueueProblems_is_enabled_sl | 437 | 160,379 | TRACE 437 | 437 | 0 | 2 | 0 / 0 |
| plan row: frontend, cap 30,210, tier_down | frontend | `INl44sUgFeY` API_request_completed | 2,914 | 1,438,595 | TRACE 2,914 | 1,620 | 1,294 | 19 | 215 / 106,272 |
| plan row: otel-collector, cap 61,996, tier_down | otel-collector | `KG8Fq0QFuoY` Logs | 2,287 | 1,203,067 | INFO 2,287 | 0 | 2,287 | 19 | 240 / 126,257 |
| plan row: otel-collector, cap 61,996, tier_down | otel-collector | `Gl3Gtr_SH5w` Traces | 2,272 | 1,193,317 | INFO 2,272 | 0 | 2,272 | 19 | 240 / 126,053 |
| plan row: otel-collector, cap 61,996, tier_down | otel-collector | `PuWB8kkVbfw` Metrics | 1,446 | 800,318 | INFO 1,446 | 0 | 1,446 | 19 | 191 / 105,712 |
| plan row: payment, cap 2,344, tier_down | payment | `fg1YkiyrF3Q` Charge_request_received | 159 | 68,211 | TRACE 159 | 16 | 143 | 19 | 11 / 4,719 |
| plan row: payment, cap 2,344, tier_down | payment | `9WbTsopbiXk` Transaction_complete | 149 | 100,761 | TRACE 149 | 6 | 143 | 18 | 11 / 7,435 |
| plan row: payment, cap 2,344, tier_down | payment | `_N7fwt_uqyQ` Payment_request_failed_Invalid_token_demo_user_context_loyal | 7 | 6,510 | ERROR 7 | 7 | 0 | 1 | 0 / 0 |
| plan row: quote, cap 1, tier_down | quote | `c4yR2F2cVfk` POST_getquote_HTTP | 159 | 37,206 | none 159 | 0 | 159 | 19 | 11 / 2,574 |
| plan row: recommendation, cap 2,330, tier_down | recommendation | `bzLB1zZCTIw` Receive_ListRecommendations_for_product_ids | 275 | 134,200 | INFO 275 | 60 | 215 | 19 | 21 / 10,248 |
| plan row: recommendation, cap 2,330, tier_down | recommendation | `QE9Wwe64YPk` get_product_list_cache_hit | 8 | 3,208 | INFO 8 | 8 | 0 | 3 | 0 / 0 |
| plan row: recommendation, cap 2,330, tier_down | recommendation | `pQCM0VaOm6U` get_product_list_cache_miss | 8 | 3,216 | INFO 8 | 8 | 0 | 3 | 0 / 0 |
| plan row: shipping, cap 2,721, tier_down | shipping | `kAB8PMmHyKM` shipping_service_Requesting_quote_http_getquote | 140 | 58,660 | none 140 | 0 | 140 | 19 | 11 / 4,609 |
| plan row: shipping, cap 2,721, tier_down | shipping | `PX-oZ7rxgZo` Sending_Quote | 140 | 58,117 | none 140 | 0 | 140 | 19 | 11 / 4,567 |
| plan row: shipping, cap 2,721, tier_down | shipping | `LnOvjJt0La4` Tracking_ID_Created | 131 | 54,758 | none 131 | 0 | 131 | 18 | 11 / 4,598 |
| plan row: telemetry-docs, cap 1, tier_down | telemetry-docs | `zxRYTKQNyBY` GET_HTTP_Wget | 770 | 200,970 | none 770 | 0 | 770 | 19 | 47 / 12,267 |

## Per flag activation

Span: flag on to one 4-minute window after it reverts, or the next flag on. Rows are the containers on the flag's causal path (demo 3.1.0 source). "New" holds are patterns with no hold in the 10 minutes before the flag (or since the fleet Receiver started); "steady" holds are patterns already held then, such as every statement of a plan row with cap 1. "First noisy" is the first record of the first pattern whose records in a minute reach 5 and 5 times its rate in those 10 minutes.

| # | flag | on to off | container | rule | first noisy | first new hold | new held (offload / tier_down) | kept, same patterns | bytes held (new) | steady held | patterns newly held |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | cartFailure | 12:48:55 to 12:55:50 | cart | plan row: cart, cap 1, tier_down | 12:53:57 Error_code_FailedPrecondition_ | 12:50:00 | 16 (0 / 16) | 12 | 10,112 | 362 | Error_code_FailedPrecondition_detail_Can x16 |
| 2 | kafkaQueueProblems | 12:59:19 to 13:06:58 | astronomy-db | fleet default: 71,247, offload | 12:59:30 duplicate_key_value_violates_u | 12:59:56 | 5,555 (5,555 / 0) | 2,545 | 1,594,191 | 0 | DETAIL_Key_order_already_exists x2,214; STATEMENT_INSERT_INTO_accounting_order_i x2,200; duplicate_key_value_violates_unique_cons x1,141 |
| 2 | kafkaQueueProblems | 12:59:19 to 13:06:58 | accounting | plan row: accounting, cap 2,765, tier_down | 12:59:30 Order_details | 12:59:31 | 2,680 (0 / 2,680) | 20 | 688,760 | 2,720 | Duplicate_order_received_skipping x2,680 |
| 2 | kafkaQueueProblems | 12:59:19 to 13:06:58 | fraud-detection | plan row: fraud-detection, cap 1, tier_down | 12:59:30 fraud_detection_FeatureFlag_ka | 12:59:35 | 437 (0 / 437) | 10 | 160,379 | 3,220 | fraud_detection_FeatureFlag_kafkaQueuePr x437 |
| 3 | paymentFailure | 13:11:18 to 13:16:19 | payment | plan row: payment, cap 2,344, tier_down | 13:13:58 Payment_request_failed_Invalid | 13:13:59 | 7 (0 / 7) | 8 | 6,510 | 22 | Payment_request_failed_Invalid_token_dem x7 |
| 3 | paymentFailure | 13:11:18 to 13:16:19 | frontend | plan row: frontend, cap 30,210, tier_down | 13:13:58 Checkout_payment_declined |  | 0 (0 / 0) | 0 | 0 | 322 |  |
| 4 | emailMemoryLeak | 13:19:51 to 13:27:43 | email | plan row: email, cap 1, tier_down | 13:25:54 Order_confirmation_email_sent_ |  | 0 (0 / 0) | 0 | 0 | 32 |  |
| 5 | emailMemoryLeak | 13:28:10 to 13:35:00 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 6 | recommendationCacheFailure | 13:40:41 to 13:47:40 | recommendation | plan row: recommendation, cap 2,330, tier_down |   | 13:42:48 | 12 (0 / 12) | 20 | 4,818 | 25 | get_product_list_cache_hit x6; get_product_list_cache_miss x6 |
| 7 | loadGeneratorFloodHomepage | 13:48:46 to 13:54:14 | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |
| 8 | recommendationCacheFailure | 13:58:44 to 14:02:53 | recommendation | plan row: recommendation, cap 2,330, tier_down |   | 14:01:30 | 4 (0 / 4) | 12 | 1,606 | 12 | get_product_list_cache_hit x2; get_product_list_cache_miss x2 |

New holds in containers off the flag's causal path, inside its span: #1 otel-collector 637 (Logs, Metrics; plan row: otel-collector, cap 61,996, tier_down); #1 email 19 (Order_confirmation_email_sent_for_order; plan row: email, cap 1, tier_down); #8 ad 3 (oteldemo_AdService_Non_targeted_ad_request_received_preparing_random_response_trace_id_span_flags; plan row: ad, cap 1, tier_down).

## False holds and the plan's moves

Fleet-default holds outside every flag's causal span: 0 records in 0 (container, pattern) pairs.

The plan's rows (`tier_down`), per container per Receiver window:

| container | cap in caps.csv | windows | median per window | max | total |
|---|---|---|---|---|---|
| otel-collector | 61996.0 | 19 | 318 | 356 | 6,005 |
| accounting | 2765.0 | 18 | 7.5 | 3603 | 5,529 |
| fraud-detection | 1.0 | 18 | 7.5 | 3221 | 3,786 |
| frontend | 30210.0 | 19 | 152 | 196 | 2,914 |
| cart | 1.0 | 19 | 104 | 158 | 2,099 |
| telemetry-docs | 1.0 | 19 | 42 | 43 | 770 |
| shipping | 2721.0 | 19 | 18 | 39 | 411 |
| payment | 2344.0 | 19 | 15 | 28 | 315 |
| recommendation | 2330.0 | 19 | 15 | 26 | 291 |
| email | 1.0 | 18 | 12.0 | 21 | 232 |
| ad | 1.0 | 19 | 12 | 18 | 221 |
| quote | 1.0 | 19 | 7 | 14 | 159 |

## Errors against the 0.5 floor

ERROR and CRITICAL records held: 1,148; passed: 2,510.

| rule | container | pattern | severity | held | passed | flags |
|---|---|---|---|---|---|---|
| fleet default: 71,247, offload | astronomy-db | `KSTuhseaGEc` duplicate_key_value_violates_unique_constraint_order_pkey | ERROR | offload 1,141 | 1,559 | kafkaQueueProblems 1,141 |
| plan row: payment, cap 2,344, tier_down | payment | `_N7fwt_uqyQ` Payment_request_failed_Invalid_token_demo_user_context_loyal | ERROR | tier_down 7 | 8 | paymentFailure 7 |

Records over the cap in a replay of each Receiver window (rb_ts order; the first 5 pass, then pass while the window's bytes stay within the cap), by severity and what the Receiver did:

| severity | over the cap: passed | held | passed share | floor |
|---|---|---|---|---|
| ERROR | 1,059 | 1,148 | 0.480 | 0.5 |
| INFO | 448 | 13,414 | 0.032 | 0.0 |
| TRACE | 104 | 7,091 | 0.014 | 0.0 |
| none | 34 | 5,941 | 0.006 | 0 |

Replay against the Receiver: under the cap and passed 14,835, under and held 693, over and passed 1,645, over and held 27,594. Windows start 196.1 s past a multiple of 240 s of epoch time (receiver.log connect); the phase read from the data alone (first pass after a run of holds) is 201 s, with 29.6% of 901 resets within 20 s of it.

## Latency

Seconds from `fb_ts` (the Docker driver's event time for the line) to `rb_ts` (when Fluent Bit's return-path filter received the record back from the Receiver). For a record that joins several lines, `fb_ts` is its first line's.

Scheduled run (44,767 records): median 2.15, p99 7.16, max 10.3; 3 over 10 s.

| container | records | median | p99 | max | over 10 s |
|---|---|---|---|---|---|
| accounting | 5,635 | 2.16 | 6.84 | 9.9 | 0 |
| ad | 375 | 6.02 | 7.43 | 7.9 | 0 |
| astronomy-db | 8,971 | 2.27 | 6.72 | 8.7 | 0 |
| cart | 2,377 | 2.03 | 7.45 | 8.9 | 0 |
| email | 407 | 4.51 | 7.72 | 10.0 | 1 |
| flagd | 15 | 6.72 | 8.42 | 8.5 | 0 |
| flagd-ui | 33 | 2.89 | 8.52 | 8.8 | 0 |
| fraud-detection | 3,882 | 2.83 | 7.00 | 10.0 | 0 |
| frontend | 4,271 | 2.21 | 6.55 | 8.4 | 0 |
| kafka | 3,392 | 1.79 | 7.33 | 8.6 | 0 |
| otel-collector | 12,550 | 1.70 | 5.36 | 7.5 | 0 |
| payment | 500 | 2.61 | 7.66 | 10.3 | 1 |
| quote | 250 | 6.25 | 7.87 | 8.2 | 0 |
| recommendation | 416 | 6.02 | 7.69 | 7.8 | 0 |
| shipping | 758 | 2.03 | 7.57 | 10.3 | 1 |
| telemetry-docs | 860 | 6.02 | 7.38 | 8.2 | 0 |
| valkey-cart | 75 | 1.92 | 7.23 | 7.5 | 0 |

What the scheduled run's 3 records over 10 s waited for, from each record's last raw line and its container's next one: back within 5 s after its container's next line 3 (median 1.32 s after that line).

Records after which their container wrote nothing for 10 s or more: 1,501. 1,501 came back before the container's next line, so a timer released them, 6.55 s after their last line at the median, 5.16 s at least, 7.91 s at p99 and 8.83 s at most; 0 came back only with or after that next line. The Receiver's group step seals a source's open event on the source's next head line, on the group size limit (20,000 lines), or 5 s (`groupFlushTimeout`, which the values leave at its default) after the batch that carried the source's last line; a batch leaves the forwarder input up to 2 s after its last line (`parallelEventFlushInterval`).

Against the earlier runs (`previous-runs.json`: each run's committed captures measured by this `analyze.py`), scheduled run, seconds as median / p99 / max:

| container | 1.1.141 run (1.1.141, MCP 1.30.54) | first 1.1.142 run (1.1.142, MCP 1.30.58) | this run |
|---|---|---|---|
| all | 2.01 / 28.86 / 472.3 (40,575) | 2.02 / 7.44 / 17.2 (28,018) | 2.15 / 7.16 / 10.3 (44,767) |
| accounting | 1.80 / 32.00 / 309.0 (4,230) | 6.29 / 7.87 / 8.0 (225) | 2.16 / 6.84 / 9.9 (5,635) |
| ad | 9.22 / 55.49 / 70.9 (405) | 6.12 / 7.71 / 12.2 (371) | 6.02 / 7.43 / 7.9 (375) |
| astronomy-db | 2.00 / 7.69 / 9.9 (6,903) | 6.05 / 6.97 / 14.5 (901) | 2.27 / 6.72 / 8.7 (8,971) |
| cart | 2.05 / 19.21 / 32.4 (2,349) | 1.95 / 7.42 / 11.5 (2,341) | 2.03 / 7.45 / 8.9 (2,377) |
| email | 12.96 / 94.63 / 309.0 (230) | 3.69 / 7.70 / 7.9 (400) | 4.51 / 7.72 / 10.0 (407) |
| flagd | 302.98 / 469.69 / 471.5 (15) | 6.78 / 7.76 / 7.8 (15) | 6.72 / 8.42 / 8.5 (15) |
| flagd-ui | 3.12 / 468.13 / 472.3 (33) | 2.47 / 8.07 / 8.4 (33) | 2.89 / 8.52 / 8.8 (33) |
| fraud-detection | 2.03 / 34.67 / 309.0 (3,186) | 6.04 / 7.76 / 7.9 (254) | 2.83 / 7.00 / 10.0 (3,882) |
| frontend | 2.31 / 7.25 / 12.4 (4,394) | 2.23 / 6.52 / 15.1 (4,310) | 2.21 / 6.55 / 8.4 (4,271) |
| kafka | 1.94 / 16.53 / 17.9 (3,409) | 1.68 / 8.17 / 17.2 (3,668) | 1.79 / 7.33 / 8.6 (3,392) |
| otel-collector | 1.82 / 5.52 / 8.1 (12,551) | 1.79 / 5.71 / 14.9 (12,637) | 1.70 / 5.36 / 7.5 (12,550) |
| payment | 2.55 / 85.08 / 130.6 (497) | 2.51 / 7.73 / 7.9 (482) | 2.61 / 7.66 / 10.3 (500) |
| quote | 13.35 / 87.87 / 130.8 (248) | 6.24 / 7.81 / 8.0 (241) | 6.25 / 7.87 / 8.2 (250) |
| recommendation | 8.63 / 58.75 / 95.5 (414) | 5.80 / 7.78 / 8.0 (454) | 6.02 / 7.69 / 7.8 (416) |
| shipping | 2.00 / 70.60 / 130.6 (760) | 1.91 / 7.62 / 7.9 (733) | 2.03 / 7.57 / 10.3 (758) |
| telemetry-docs | 6.67 / 8.05 / 11.0 (882) | 6.05 / 6.90 / 13.7 (883) | 6.02 / 7.38 / 8.2 (860) |
| valkey-cart | 1.53 / 369.94 / 399.7 (69) | 1.70 / 8.71 / 8.9 (70) | 1.92 / 7.23 / 7.5 (75) |

Every returned record from the first Receiver start (56,345): median 2.17, p99 27.47, max 63.5; 1,280 over 10 s, by when the line was written: before the quiet run 852, quiet run 206, between quiet end and scheduler start 219, scheduled run 3. `latency-over-10s.csv` lists every one with its container.

| container | records | median | p99 | max | over 10 s |
|---|---|---|---|---|---|
| accounting | 5,729 | 2.17 | 7.21 | 27.9 | 27 |
| ad | 502 | 6.03 | 24.34 | 42.5 | 9 |
| astronomy-db | 9,356 | 2.29 | 7.08 | 56.0 | 23 |
| cart | 3,007 | 2.09 | 7.81 | 45.0 | 22 |
| currency | 1 | 9.45 | 9.45 | 9.4 | 0 |
| email | 520 | 5.38 | 9.63 | 45.3 | 6 |
| flagd | 33 | 5.75 | 9.43 | 9.9 | 0 |
| flagd-ui | 36 | 4.21 | 8.93 | 9.0 | 0 |
| fraud-detection | 3,947 | 2.84 | 7.10 | 57.3 | 5 |
| frontend | 5,566 | 2.24 | 7.19 | 38.7 | 37 |
| frontend-proxy | 128 | 27.94 | 27.95 | 30.3 | 127 |
| image-provider | 58 | 4.12 | 9.57 | 9.7 | 0 |
| kafka | 5,933 | 2.03 | 51.47 | 54.1 | 613 |
| otel-collector | 17,793 | 1.75 | 24.05 | 54.0 | 350 |
| payment | 617 | 2.67 | 8.07 | 40.4 | 6 |
| product-catalog | 2 | 10.66 | 13.05 | 13.1 | 1 |
| quote | 310 | 6.25 | 11.35 | 45.1 | 5 |
| recommendation | 528 | 6.02 | 7.89 | 32.6 | 3 |
| shipping | 947 | 2.10 | 8.02 | 63.5 | 8 |
| telemetry-docs | 1,230 | 6.05 | 23.49 | 54.8 | 31 |
| valkey-cart | 102 | 2.04 | 16.21 | 21.1 | 7 |

## Multi-line events closed by a source's pause

A line of a kind the Receiver joins to the record before it anywhere in the run is not a group head. A record that begins with such a line was opened after its source's previous group had been sealed by something other than a head line, which in a running demo is the per-source flush timer. Each is set against the record before it from the same container; the pause runs from that record's last raw line to this record's first. Blank lines are left out. `early-close.csv` lists every one.

Scheduled run: 172 records opened by a line that is not a head; over 7 s 153, 5 to 7 s 18, 3 to 5 s 1; 19 within 7 s of the previous record's first line, 0 of them with the previous record's pattern.

1.1.141 run, same measure: 0 records, 0 within 7 s of the previous record's first line, 0 with its pattern.

First 1.1.142 run, same measure: 173 records, 16 within 7 s of the previous record's first line, 0 with its pattern.

| container | previous record's pattern | first line of the record opened | records | by pause | within 7 s | same pattern | shortest pause s | example |
|---|---|---|---|---|---|---|---|---|
| email | POST_send_order_confirmation_HTTP | `Order confirmation email sent for order 0-0-0-0-` | 172 | over 7 s 153, 5 to 7 s 18, 3 to 5 s 1 | 19 | 0 | 4.95 | 12:48:00 Order confirmation email sent for order a776d3ac-c896-11f1-b |

## Delivery

Scheduled run (12:47:51 to 14:02:55 UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).

| container | raw lines | returned records | lines covered | covered minus raw |
|---|---|---|---|---|
| accounting | 11,270 | 5,635 | 11,270 | +0 |
| ad | 559 | 375 | 559 | +0 |
| astronomy-db | 11,672 | 8,971 | 11,671 | -1 |
| cart | 4,866 | 2,377 | 4,866 | +0 |
| email | 470 | 407 | 470 | +0 |
| flagd | 16 | 15 | 15 | -1 |
| flagd-ui | 34 | 33 | 33 | -1 |
| fraud-detection | 3,882 | 3,882 | 3,882 | +0 |
| frontend | 4,271 | 4,271 | 4,271 | +0 |
| kafka | 3,392 | 3,392 | 3,392 | +0 |
| otel-collector | 13,774 | 12,550 | 13,774 | +0 |
| payment | 500 | 500 | 500 | +0 |
| quote | 250 | 250 | 250 | +0 |
| recommendation | 416 | 416 | 416 | +0 |
| shipping | 758 | 758 | 758 | +0 |
| telemetry-docs | 860 | 860 | 860 | +0 |
| valkey-cart | 75 | 75 | 75 | +0 |
| total | 57,065 | 44,767 | 57,062 | -3 |

Whole run, from the first Receiver start (12:14:29 to 14:02:55 UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).

| container | raw lines | returned records | lines covered | covered minus raw |
|---|---|---|---|---|
| accounting | 11,426 | 5,729 | 11,426 | +0 |
| ad | 690 | 502 | 690 | +0 |
| astronomy-db | 12,086 | 9,356 | 12,085 | -1 |
| cart | 6,126 | 3,007 | 6,126 | +0 |
| currency | 1 | 1 | 1 | +0 |
| email | 613 | 520 | 613 | +0 |
| flagd | 34 | 33 | 33 | -1 |
| flagd-ui | 37 | 36 | 36 | -1 |
| fraud-detection | 3,947 | 3,947 | 3,947 | +0 |
| frontend | 5,569 | 5,564 | 5,569 | +0 |
| frontend-proxy | 135 | 128 | 135 | +0 |
| image-provider | 58 | 58 | 58 | +0 |
| kafka | 7,207 | 5,933 | 7,207 | +0 |
| otel-collector | 20,891 | 17,775 | 20,891 | +0 |
| payment | 618 | 617 | 618 | +0 |
| product-catalog | 2 | 2 | 2 | +0 |
| quote | 320 | 310 | 320 | +0 |
| recommendation | 528 | 528 | 528 | +0 |
| shipping | 947 | 947 | 947 | +0 |
| telemetry-docs | 1,230 | 1,230 | 1,230 | +0 |
| valkey-cart | 102 | 102 | 102 | +0 |
| total | 72,567 | 56,325 | 72,564 | -3 |

Lines written up to 60 s before the stop: 72,187 raw, 72,187 covered. In the last 60 s: 380 raw, 377 covered; the difference is each container's last event, still open in the Receiver when the demo stopped.

## What the fleet default would hold alone

The same replay with the install seed in place of the plan's rows, so every container takes the fleet default (71,247 bytes): 19,475 records held (expected, floors applied), 13,929 of them inside a flag's causal span, 1,099 ERROR or CRITICAL.

## Against the earlier runs

`previous-runs.json`: 1.1.141 run, commit 8e416c6; first 1.1.142 run, commit 4c2b610. Each run's committed captures are measured by this `analyze.py`.

| measure | 1.1.141 run | first 1.1.142 run | this run |
|---|---|---|---|
| Receiver | log10x/edge-10x:1.1.141 | log10x/edge-10x:1.1.142 | log10x/edge-10x:1.1.142 |
| log10x-mcp | 1.30.54 | 1.30.58 | 1.30.58 |
| fleet default cap, bytes per window per node | 10,288 | 25,960 | 71,247 |
| plan rows in caps.csv | 11 | 14 | 15 |
| returned records, scheduled run | 40,575 | 28,018 | 44,767 |
| routes | offload 4,836, pass 8,555, tier_down 27,184 | pass 8,347, tier_down 19,671 | offload 5,555, pass 16,480, tier_down 22,732 |
| kafkaQueueProblems: new holds on the causal path | #2: astronomy-db 4,784, accounting 1,990, fraud-detection 446 | #2: fraud-detection 20 | #2: astronomy-db 5,555, accounting 2,680, fraud-detection 437 |
| fleet-default holds outside every causal span (outside of held) | astronomy-db `role_root_does_not_exist` 43 of 52 | none | none |
| ERROR and CRITICAL held / passed | 982 / 1,999 | 6 / 972 | 1,148 / 2,510 |
| ERROR over the cap, share passed | 0.520 of 1,937 | 0.500 of 10 | 0.480 of 2,207 |
| CRITICAL over the cap, share passed | 0.567 of 104 | 0.000 of 0 | 0.000 of 0 |
| latency median / p99 / max, s | 2.01 / 28.86 / 472.3 | 2.02 / 7.44 / 17.2 | 2.15 / 7.16 / 10.3 |
| records over 10 s | 1,714 | 59 | 3 |
| records opened by a line that is not a head (within 7 s) | 0 (0; same pattern 0) | 173 (16; same pattern 0) | 172 (19; same pattern 0) |
| lines written up to 60 s before the stop: raw / covered | 66,255 / 66,255 | 45,258 / 45,258 | 72,187 / 72,187 |

## Reading

**Two runs on the released software.** Both ran edge-10x 1.1.142 with the values log10x-mcp 1.30.58 writes, seed 20261014, the same six flags, a 22-minute quiet run and a 75-minute schedule. In the first (scheduled 10:56:11 to 12:11:16 UTC, commit 4c2b610) kafkaQueueProblems never reached checkout: its Go flagd provider answered from its cache, and flagd counted 4 resolutions of the flag through it for the whole run, so there was no duplicate-order flood. That run stands for latency and false holds: median 2.02 s, p99 7.44 s, max 17.2 s, 59 records over 10 s, no fleet-default hold at all. This run (the one on this page) sets `FLAGD_CACHE=disabled` on checkout (README, "checkout's flag cache") and stands for the incident. Everything above is this run.

**Which rule held what.** Of the 44,767 records the Receiver returned in the scheduled run, 22,732 were held by the plan's rows (`tier_down`), 5,555 by the fleet default (`offload`), and 16,480 passed. The fleet default (71,247 bytes, 2 x 35,623.7 for otel-collector's `Error scraping metrics`) acted on one container, astronomy-db, and only inside the kafkaQueueProblems span.

**kafkaQueueProblems, 12:59:19 to 13:06:58.** Causal path (demo 3.1.0 source): checkout publishes each order 100 extra times to Kafka; accounting logs `Duplicate order received, skipping.` for each copy and its INSERT fails on the primary key, so Postgres (astronomy-db) writes an ERROR, a DETAIL and a STATEMENT line for each copy; fraud-detection logs `FeatureFlag 'kafkaQueueProblems' is enabled, sleeping 1 second` for each copy.

- astronomy-db, fleet default (71,247 bytes, offload): the first duplicate-key line came at 12:59:30 and the first hold at 12:59:56, once the flood had filled the window's 71,247 bytes. Held 5,555 records, 1,594,191 bytes: DETAIL 2,214, STATEMENT 2,200, ERROR 1,141. Kept 486, 500 and 1,559 of the same patterns. Last hold 13:06:54.
- accounting, plan row (cap 2,765, tier_down): `Duplicate order received` 2,680 held, 20 kept, first held 12:59:31. `Order details` was already held above the row's cap; 2,720 of it were held in the span.
- fraud-detection, plan row (cap 1, tier_down): the `sleeping 1 second` line 437 held, 10 kept, first held 12:59:35. `Consumed record` was already held; 3,220 of it were held in the span.

**The other activations.** cartFailure: cart's row (cap 1) held 16 `FailedPrecondition ... Can't access cart storage` lines and kept 12. paymentFailure: payment's row held 7 `Payment request failed` lines (ERROR) and kept 8; frontend's `Checkout payment declined` was not held (frontend's row is 30,210 bytes this run). recommendationCacheFailure: its row held 12 cache hit and miss lines in activation 6 and 4 in activation 8. The two emailMemoryLeak activations and the homepage flood held nothing new on their paths.

**False holds.** None in either 1.1.142 run. In the 1.1.141 run one fleet-default pattern was held outside every causal span: astronomy-db `FATAL: role "root" does not exist` (43 of 52 holds), whose 11,750 bytes a window sat above that run's 10,288-byte fleet default. Both 1.1.142 runs' fleet defaults (25,960 and 71,247) sit above it.

**The cap's unit.** The MCP's baseline, 35,623.7 bytes per window for `Error scraping metrics`, is its busiest quiet window in the Receiver's unit; the Receiver's own count of that statement peaked at 37,370 in a quiet window (15,630 on average). So 71,247 is 1.9 times the statement's busiest window as the Receiver counts it; in the 1.1.141 run the cap was 1.45 times the statement's average. Each plan row now sits between its largest kept and smallest moved statement with the same margin each way: 1.7x (otel-collector) to 5.3x (accounting) for the seven rows that keep a statement; the other eight rows are cap 1.

**Errors.** 1,148 ERROR records were held: astronomy-db's duplicate key 1,141 (fleet default, offload) and payment's `Payment request failed` 7 (plan row, tier_down). 2,510 ERROR and CRITICAL records passed. Above the cap, 1,059 of 2,207 ERROR records passed (0.480) against a floor of 0.5. The DETAIL and STATEMENT lines that go with each duplicate-key ERROR carry no level, so they take a 0 floor; an ERROR line the floor passes arrives without them.

**Latency.** Scheduled run: median 2.15 s, p99 7.16 s, max 10.3 s, 3 records over 10 s (none over 10.3 s), against median 2.01 s, p99 28.86 s, max 472.3 s and 1,714 over 10 s in the 1.1.141 run, and 2.02 s, 7.44 s, 17.2 s and 59 in the first 1.1.142 run, whose 57 slowest records were written 12:02:03 to 12:02:10 in every busy container at once and came back together at 12:02:2x. 1,501 records were followed by 10 s or more of silence from their container; every one came back before the container's next line, 5.16 s to 8.83 s after its own last line (median 6.55 s). In the 1.1.141 run all 1,323 such records waited for the container's next line, which is what gave flagd, flagd-ui and valkey-cart their 400 s to 472 s maxima.

**Multi-line events closed by a pause.** None. The 172 records opened by a line that is not a head are all email's `Order confirmation email sent for order ...` line, which carries no timestamp or level and is joined to the record before it, the previous request's access-log line, when email writes without a pause. After a pause the per-source flush seals that record first: the pause was over 7 s for 153, 5 to 7 s for 18 and 4.95 s for 1; none shares the previous record's pattern. No two-line .NET record (cart, accounting), STATEMENT record (astronomy-db) or stack trace (otel-collector) was split. The first 1.1.142 run shows the same: 173, all email, 16 within 7 s.

**Delivery.** Every raw line written up to 60 s before the stop came back (72,187 of 72,187, counting the lines inside joined records). In the last 60 s, 3 lines did not: each container's last event, still open when the demo stopped. Relaunching the Receiver at 12:47:16 lost no line.

**The fleet default alone.** Replaying the same records with the install seed in place of the plan's rows, so that every container takes 71,247 bytes, holds 19,475 records (floors applied), 13,929 of them inside a flag's causal span and 1,099 ERROR or CRITICAL.

**The POC.** On this run's quiet capture the plan reached 49.7% against the 70% target (`met: false`), with 31 statements planned and 40 kept; on the first 1.1.142 run's capture it reached 70.3% with 39 planned and 9 kept. The largest kept statement, otel-collector's `Error scraping metrics`, which sets the fleet default, came to 35,623.7 bytes in its busiest window here against 12,979.8 there.

