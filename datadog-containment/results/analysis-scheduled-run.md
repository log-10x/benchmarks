# Scheduled run analysis: 2026-10-14, 14:07 to 17:35 UTC

This file answers five questions about the unattended scheduled run: the flag timeline, every held record by class, the false holds, the held errors and delivery. Every figure comes from `results/data/raw.jsonl`, `pass.jsonl` and `offload.jsonl`, `results/scheduler.log`, `results/scheduler-state.txt`, `results/timeline.jsonl`, `results/receiver.log`, `results/fluent-bit.log` and `results/disk.log` as they stood after `run.sh down` at 17:35 UTC.

## Scope and method

- **Span.** Records with `fb_ts` from the scheduler start (14:07:14, epoch 1791986834) to `run_end` (17:35:42, epoch 1791999342). The Receiver for this run started at 13:52:58 with `rateReceiverAbsoluteCap 48862`, default action `offload`, floors 0, baseline 5, warm-up 0 and share guard 0. Records from the morning's earlier runs fall before 13:53 and are excluded.
- **Pattern.** Each held record is named by its `message_pattern` and `tenx_hash`. The Receiver keys its counters on `message_pattern` per `container_name`.
- **Receiver windows.** The windows start at 13:53:51 UTC and repeat every 240 s (14:05:51, 14:09:51, ..., 17:33:51). Three facts establish this:
  - `receiver.log` has one non-metric line after start-up: the Forward client connected at 13:53:51.166.
  - The counter resets of the four patterns held in every window land at the same phase. The first `pass` after a run of `offload` falls 107 to 120 s past a multiple of 240 s of epoch time in 215 of 216 resets (the exception is at 13:56:29, before the scheduled run), and 13:53:51 sits at 111 s. Lower-rate held patterns reset in the same windows, at their next record.
  - A replay of the cap rule (5 events per window always pass, then pass while the window's cumulative bytes stay at or under 48,862, else offload) on those windows reproduces the actual holds of the 11 non-shipping held patterns to within 3 records each. The byte measure is the compact JSON of the record as Fluent Bit sent it (NOTES.md, smoke test 3).
- **Shipping.** Shipping's records came back from the Receiver hours after their `fb_ts`, so for shipping the Receiver's window is set by when the Receiver handled them, not by `fb_ts` (section 2b).
- **What-if numbers** in section 3 come from the same replay with a different cap. At 48,862 the replay gives 60,421 held records against 60,426 actual.

## 1. Flag timeline

The scheduler started at 14:07:14 with seed 20261014, interval 600 s, hold 240 to 480 s, concurrency 1, and the six flags in `scheduler.sh`. It fired **21 activations**. The first was cartFailure at 14:08:17 and the last was kafkaQueueProblems at 17:30:11. `run.sh down` stopped the scheduler at 17:35:33, which reverted the last activation after 322 s of its planned 413 s. Times below are the flagd-ui log stamps from `scheduler.log`.

| # | flag | variant | on (UTC) | off (UTC) | planned s | actual s |
|---|---|---|---|---|---|---|
| 1 | cartFailure | 100% | 14:08:17 | 14:15:13 | 415 | 415 |
| 2 | kafkaQueueProblems | on | 14:18:42 | 14:26:20 | 459 | 459 |
| 3 | paymentFailure | 100% | 14:30:40 | 14:35:41 | 301 | 301 |
| 4 | emailMemoryLeak | 1000x | 14:39:13 | 14:47:05 | 472 | 472 |
| 5 | emailMemoryLeak | 1000x | 14:47:33 | 14:54:23 | 410 | 410 |
| 6 | recommendationCacheFailure | on | 15:00:03 | 15:07:02 | 419 | 419 |
| 7 | loadGeneratorFloodHomepage | on | 15:08:08 | 15:13:37 | 329 | 329 |
| 8 | recommendationCacheFailure | on | 15:18:06 | 15:23:51 | 345 | 345 |
| 9 | emailMemoryLeak | 1000x | 15:29:15 | 15:35:44 | 389 | 389 |
| 10 | loadGeneratorFloodHomepage | on | 15:40:12 | 15:44:51 | 279 | 279 |
| 11 | cartFailure | 100% | 15:48:45 | 15:55:02 | 377 | 377 |
| 12 | recommendationCacheFailure | on | 15:57:54 | 16:05:28 | 454 | 454 |
| 13 | loadGeneratorFloodHomepage | on | 16:07:59 | 16:13:16 | 317 | 317 |
| 14 | recommendationCacheFailure | on | 16:19:36 | 16:25:44 | 368 | 368 |
| 15 | cartFailure | 100% | 16:29:38 | 16:35:53 | 374 | 374 |
| 16 | emailMemoryLeak | 1000x | 16:38:42 | 16:43:46 | 303 | 303 |
| 17 | loadGeneratorFloodHomepage | on | 16:48:59 | 16:53:31 | 272 | 272 |
| 18 | emailMemoryLeak | 1000x | 16:59:27 | 17:05:54 | 387 | 387 |
| 19 | paymentFailure | 100% | 17:07:23 | 17:11:28 | 245 | 245 |
| 20 | kafkaQueueProblems | on | 17:20:32 | 17:25:37 | 305 | 305 |
| 21 | kafkaQueueProblems | on | 17:30:11 | 17:35:33 | 413 | 322 |

Counts by flag: emailMemoryLeak 5, recommendationCacheFailure 4, loadGeneratorFloodHomepage 4, cartFailure 3, kafkaQueueProblems 3, paymentFailure 2. Every activation reverted at its planned duration except number 21.

**Activation count.** The scheduler fired more activations than planned, not fewer. The snapshot written by this run's `run.sh down` (`results/scheduler-state.txt`, working tree) shows `interval_count: 21`, `running: false` and `next_trigger_at: nil`. The scheduler had been stopped when the snapshot was taken, which is why `next_trigger_at` is nil. The copy committed at 482b273 (`interval_count: 1`, `history: []`, `interval_ms: 900000`) is the snapshot of the earlier 13:29:55 run. The disk guard stopped that run at 13:35:58, before its first planned activation. The snapshot's `history` lists only the last ten activations; `scheduler.log` has all 21.

**Why the run went to 21 activations instead of 4.** `run-scheduled.sh` was meant to stop after 4 completed activations plus one window (the fourth revert was at 14:47:05, so the stop would have come at about 14:51), or at 75 minutes (about 15:22). It did neither:

- `run-scheduled.log` ends with the scheduler start's `:ok` (file time 14:07 UTC). The driver never printed its "activations completed" line or its "stopping" line.
- `disk-guard.sh` logs every 5 minutes, and its last line in `disk.log` is 14:12:21.

Both background processes therefore stopped running between 14:12:21 and 14:17:21. The files do not record what ended them. The scheduler runs inside flagd-ui, so it kept firing until `run.sh down` ran at 17:35:33 (`timeline.jsonl`: `scheduler_stop` 17:35:33, `run_end` 17:35:42, `demo_down` 17:36:46).

## 2. Held records

The scheduled run has **60,426 held (`offload`) records in 14 (container, pattern) pairs**:

| class | pairs | held records |
|---|---|---|
| (a) during kafkaQueueProblems, in its causal path | 7 | 33,274 |
| (b) false hold, no flag in the causal path | 3 (shipping) | 1,293 |
| (c) otel-collector debug-exporter dumps (`Logs`, `Traces`, `Metrics`) | 3 | 19,535 |
| the plan's fourth move: frontend `API_request_completed` (tier_down in the plan) | 1 | 6,324 |

The frontend pattern sits on its own row because it fits neither (b) nor (c) as defined. It is held in every window, flag or no flag, and the plan moves it. Counted as a false hold, it would bring (b) to 7,617.

| class | container | pattern (message_pattern) | tenx_hash | held | held bytes | severity_level | windows with a hold | first held (fb_ts) | last held (fb_ts) |
|---|---|---|---|---|---|---|---|---|---|
| a | accounting | Order_details | -FtZD9XArpU | 6,036 | 5,388,953 | INFO 6,036 | 6 | 14:18:51 | 17:35:35 |
| a | accounting | Duplicate_order_received_skipping | XXzlsXqzuqc | 5,104 | 1,250,480 | INFO 5,104 | 6 | 14:19:12 | 17:35:35 |
| a | astronomy-db | DETAIL_Key_order_already_exists | 6_l3eh1v8RE | 5,259 | 1,475,701 | none 5,259 | 6 | 14:19:11 | 17:35:35 |
| a | astronomy-db | STATEMENT_INSERT_INTO_accounting_order_id_VALUES | GlK5AsFvcXg | 5,229 | 1,425,454 | none 5,229 | 6 | 14:19:11 | 17:35:35 |
| a | astronomy-db | duplicate_key_value_violates_unique_constraint_order_pkey | KSTuhseaGEc | 5,223 | 1,418,596 | ERROR 5,223 | 6 | 14:19:11 | 17:35:35 |
| a | fraud-detection | fraud_detection_Consumed_record_with_orderId_and_updated_total_count_to_trace_id_span_flags | GKfNbCrpxxI | 6,134 | 2,410,090 | TRACE 6,134 | 6 | 14:20:53 | 17:35:35 |
| a | fraud-detection | fraud_detection_FeatureFlag_kafkaQueueProblems_is_enabled_sleeping_second_trace_id_span_flags | eT4avs-RfM8 | 289 | 102,595 | TRACE 289 | 4 | 14:21:08 | 17:33:48 |
| b | shipping | shipping_service_Requesting_quote_http_getquote | kAB8PMmHyKM | 437 | 177,859 | none 437 | 32 | 15:15:14 | 17:21:48 |
| b | shipping | Sending_Quote | PX-oZ7rxgZo | 436 | 175,789 | none 436 | 32 | 15:15:37 | 17:21:48 |
| b | shipping | Tracking_ID_Created | LnOvjJt0La4 | 420 | 170,520 | none 420 | 32 | 15:15:12 | 17:21:49 |
| c | otel-collector | Traces | Gl3Gtr_SH5w | 7,517 | 3,857,820 | INFO 7,517 | 53 | 14:07:29 | 17:35:40 |
| c | otel-collector | Logs | KG8Fq0QFuoY | 7,476 | 3,843,012 | INFO 7,476 | 53 | 14:07:31 | 17:35:34 |
| c | otel-collector | Metrics | PuWB8kkVbfw | 4,542 | 2,459,237 | INFO 4,542 | 52 | 14:07:59 | 17:33:48 |
| c (plan move 4) | frontend | API_request_completed | INl44sUgFeY | 6,324 | 3,046,140 | TRACE 6,324 | 53 | 14:07:41 | 17:35:41 |

### 2a. Class (a): kafkaQueueProblems, three activations

Every class (a) hold falls in a Receiver window that overlaps one of the three kafkaQueueProblems activations, or in the drain that follows one. The causal path, from the demo 3.1.0 source:

1. With the flag at `on` (value 100), checkout publishes each order 100 extra times to Kafka (`src/checkout/main.go` lines 716 to 725). Checkout's flag message does not reach stdout, so `raw.jsonl` has no checkout line for it.
2. accounting logs `Order details` for each copy. The INSERT into `accounting.order` fails on the primary key, and accounting logs `Duplicate order received, skipping.` (`src/accounting/Consumer.cs` line 134, `Log.cs` line 38).
3. For each failed INSERT, astronomy-db (Postgres) writes three lines: `ERROR: duplicate key value violates unique constraint "order_pkey"`, `DETAIL: Key (order_id)=(...) already exists` and `STATEMENT: INSERT INTO accounting."order" ...`.
4. fraud-detection logs `Consumed record with orderId` for each copy. While the flag is on it also logs `FeatureFlag 'kafkaQueueProblems' is enabled, sleeping 1 second` and sleeps 1 s per record (`src/fraud-detection/.../main.kt` lines 66 to 71), so it logs one `Consumed record` line per second. When the flag reverts it drains the backlog at once: 2,679 lines stamped 14:26:20 to 14:26:29, 706 at 17:25:38 to 17:25:39, and 2,512 at 17:35:34 to 17:35:35.

Once a pattern's window is over the cap, every later record of that pattern in the window is held. That is why holds continue after a revert until the window resets. After activation 2, accounting's `Order details` was held until 14:29:42 for 4 ordinary orders with no duplicate, and fraud-detection's `Consumed record` likewise.

No `Duplicate order received` line appears outside the three activations (6,300 such raw lines in the run, all within 10 minutes of a kafkaQueueProblems activation).

Held / kept per Receiver window, for the class (a) patterns:

| window (UTC) | flag in window | fraud Consumed record | fraud FeatureFlag sleeping | acct Order details | acct Duplicate order | db DETAIL key exists | db STATEMENT INSERT | db ERROR duplicate key |
|---|---|---|---|---|---|---|---|---|
| 14:17:51 to 14:21:51 | kafkaQueueProblems | 57 / 123 | 42 / 137 | 1,254 / 61 | 1,100 / 200 | 1,126 / 174 | 1,121 / 179 | 1,120 / 180 |
| 14:21:51 to 14:25:51 | kafkaQueueProblems | 116 / 124 | 103 / 137 | 964 / 46 | 801 / 199 | 826 / 174 | 821 / 179 | 820 / 180 |
| 14:25:51 to 14:29:51 | kafkaQueueProblems | 2,595 / 124 | 0 / 30 | 261 / 53 | 102 / 198 | 126 / 174 | 121 / 179 | 120 / 180 |
| 17:21:51 to 17:25:51 | kafkaQueueProblems | 786 / 124 | 68 / 137 | 857 / 53 | 700 / 200 | 727 / 173 | 722 / 178 | 721 / 179 |
| 17:29:51 to 17:33:51 | kafkaQueueProblems | 90 / 124 | 76 / 139 | 1,553 / 63 | 1,400 / 200 | 1,427 / 173 | 1,422 / 178 | 1,421 / 179 |
| 17:33:51 to 17:37:51 | kafkaQueueProblems | 2,490 / 123 | 0 / 102 | 1,147 / 65 | 1,001 / 198 | 1,027 / 173 | 1,022 / 178 | 1,021 / 179 |

Per activation. "kept" counts the pattern's passed records from flag on to the next flag on. Times are minutes from flag on, and from flag off for the last hold.

| activation | container | pattern | held | kept | flag on to first hold (min) | last hold vs flag off (min) |
|---|---|---|---|---|---|---|
| 14:18:42 to 14:26:20 | fraud-detection | fraud Consumed record | 2,768 | 372 | +2.18 | +3.35 |
| 14:18:42 to 14:26:20 | fraud-detection | fraud FeatureFlag sleeping | 145 | 304 | +2.43 | -0.51 |
| 14:18:42 to 14:26:20 | accounting | acct Order details | 2,479 | 161 | +0.15 | +3.35 |
| 14:18:42 to 14:26:20 | accounting | acct Duplicate order | 2,003 | 597 | +0.50 | -0.16 |
| 14:18:42 to 14:26:20 | astronomy-db | db DETAIL key exists | 2,078 | 522 | +0.48 | -0.16 |
| 14:18:42 to 14:26:20 | astronomy-db | db STATEMENT INSERT | 2,063 | 537 | +0.48 | -0.16 |
| 14:18:42 to 14:26:20 | astronomy-db | db ERROR duplicate key | 2,060 | 540 | +0.48 | -0.16 |
| 17:20:32 to 17:25:37 | fraud-detection | fraud Consumed record | 786 | 145 | +3.73 | +0.02 |
| 17:20:32 to 17:25:37 | fraud-detection | fraud FeatureFlag sleeping | 68 | 138 | +3.95 | -0.02 |
| 17:20:32 to 17:25:37 | accounting | acct Order details | 857 | 74 | +1.70 | -0.08 |
| 17:20:32 to 17:25:37 | accounting | acct Duplicate order | 700 | 200 | +2.05 | -0.08 |
| 17:20:32 to 17:25:37 | astronomy-db | db DETAIL key exists | 727 | 173 | +2.05 | -0.08 |
| 17:20:32 to 17:25:37 | astronomy-db | db STATEMENT INSERT | 722 | 178 | +2.05 | -0.08 |
| 17:20:32 to 17:25:37 | astronomy-db | db ERROR duplicate key | 721 | 179 | +2.05 | -0.08 |
| 17:30:11 to 17:35:33 | fraud-detection | fraud Consumed record | 2,580 | 247 | +2.15 | +0.03 |
| 17:30:11 to 17:35:33 | fraud-detection | fraud FeatureFlag sleeping | 76 | 241 | +2.36 | -1.76 |
| 17:30:11 to 17:35:33 | accounting | acct Order details | 2,700 | 128 | +0.08 | +0.03 |
| 17:30:11 to 17:35:33 | accounting | acct Duplicate order | 2,401 | 398 | +0.16 | +0.03 |
| 17:30:11 to 17:35:33 | astronomy-db | db DETAIL key exists | 2,454 | 346 | +0.16 | +0.03 |
| 17:30:11 to 17:35:33 | astronomy-db | db STATEMENT INSERT | 2,444 | 356 | +0.16 | +0.03 |
| 17:30:11 to 17:35:33 | astronomy-db | db ERROR duplicate key | 2,442 | 358 | +0.16 | +0.03 |

The flood starts when the first duplicated order reaches accounting: 14:18:51 (+0.15 min), 17:22:14 (+1.68 min) and 17:30:16 (+0.08 min). In activation 20, the orders at 17:21:07, 17:21:09, 17:21:47 and 17:21:52 were not duplicated, so the flag took effect in checkout between 17:21:52 and 17:22:13. At 48,862 bytes the first hold lands within 1 s of the flood's first line in all three activations. Activation 21 was cut short by the stop at 17:35:33. Its drain at 17:35:34 to 17:35:35 is in the data, and the run ended at 17:35:42.

**The other 18 activations held nothing.** cartFailure x3, paymentFailure x2, emailMemoryLeak x5, recommendationCacheFailure x4 and loadGeneratorFloodHomepage x4 produced no hold beyond the steady class (c) and frontend moves. Their own lines stayed under the cap and passed. For example, cart's `Error_code_FailedPrecondition_detail_Can_access_cart_storage...` lines peaked at 9,920 bytes in a window and payment's `Payment_request_failed_Invalid_token_demo_user_context_loyalty_level_gold` at 11,934 bytes (table in section 3).

### 2b. Class (b): shipping, released by the Receiver in one burst

Shipping's three held patterns are its ordinary request lines: `Requesting quote`, `Sending Quote` and `Tracking ID Created`, all INFO in the text but with no `severity_level` on the record. No flag targets shipping, and none of the six scheduled flags has a path that floods shipping. The holds come from when the Receiver handled the lines, not from shipping's rate:

- Shipping wrote one ERROR line in the run, at 13:54:02 (`opentelemetry_sdk: name="BatchLogProcessor.ExportError" ... HTTP export failed: network error`). The Receiver returned it as the head of one 371-line record whose last line is from 14:38:09.
- Every shipping line after that, from 14:38:27 on, came back as a single-line record. None came back before about 17:19:15. In `pass.jsonl` the 424 burst pass records sit together between an `ad` record stamped 17:19:15 and a `recommendation` record stamped 17:19:17. In `offload.jsonl` the 1,263 burst held records sit together after the last frontend hold of the 17:13:51 window.
- The Receiver's own metric log first shows the three shipping patterns at 17:20:09 (for example `Sending_Quote` offload 430, pass 121). Their held counters stop at 420, 436 and 437 after 17:22:10, while the pass counters keep growing as live lines pass.
- No flag was active at 17:19:15. paymentFailure had reverted at 17:11:28 and kafkaQueueProblems started at 17:20:32. Neither `receiver.log` nor `fluent-bit.log` has a line that explains the release. Fluent Bit's only retry in the run was at 14:26:23, and both chunks were delivered by 14:26:33.

So the Receiver handled 3 h 25 min of shipping lines inside one window, 17:17:51 to 17:21:51:

| pattern | records the Receiver handled in that window | bytes | passed | held | `fb_ts` of the held records |
|---|---|---|---|---|---|
| Requesting quote (kAB8PMmHyKM) | 557 | 226,699 | 120 | 437 | 15:15:14 to 17:21:48 |
| Sending Quote (PX-oZ7rxgZo) | 557 | 224,568 | 121 | 436 | 15:15:37 to 17:21:48 |
| Tracking ID Created (LnOvjJt0La4) | 539 | 218,834 | 119 | 420 | 15:15:12 to 17:21:49 |

By `fb_ts`, the 1,293 held records spread over 32 windows from 15:13:51 to 17:21:51, at 3 to 21 per window per pattern. That spread is the ingest time; the Receiver decided all of them in the one window above. NOTES.md (13:07 UTC replay) records the same mechanism in the quiet run: the ERROR line opened a group, and lines without a recognised head were appended to it. As a result the quiet run returned no shipping request lines. `quiet-cells.csv` has no shipping row, and the plan never saw shipping's patterns.

### 2c. Class (c) and the plan's fourth move, per Receiver window

Held records per window. The first and last rows are partial windows (14:07:14 start, 17:35:42 end).

| window (UTC) | flag in window | otel Logs | otel Traces | otel Metrics | frontend API_request_completed |
|---|---|---|---|---|---|
| 14:07:14 to 14:09:51 | cartFailure | 136 | 138 | 84 | 102 |
| 14:09:51 to 14:13:51 | cartFailure | 145 | 142 | 83 | 108 |
| 14:13:51 to 14:17:51 | cartFailure | 142 | 137 | 82 | 112 |
| 14:17:51 to 14:21:51 | kafkaQueueProblems | 139 | 143 | 79 | 134 |
| 14:21:51 to 14:25:51 | kafkaQueueProblems | 144 | 145 | 79 | 100 |
| 14:25:51 to 14:29:51 | kafkaQueueProblems | 145 | 145 | 87 | 145 |
| 14:29:51 to 14:33:51 | paymentFailure | 145 | 143 | 87 | 97 |
| 14:33:51 to 14:37:51 | paymentFailure | 145 | 146 | 81 | 134 |
| 14:37:51 to 14:41:51 | emailMemoryLeak | 144 | 143 | 88 | 117 |
| 14:41:51 to 14:45:51 | emailMemoryLeak | 144 | 148 | 89 | 95 |
| 14:45:51 to 14:49:51 | emailMemoryLeak (two activations) | 141 | 138 | 90 | 133 |
| 14:49:51 to 14:53:51 | emailMemoryLeak | 150 | 148 | 86 | 134 |
| 14:53:51 to 14:57:51 | emailMemoryLeak | 141 | 143 | 90 | 108 |
| 14:57:51 to 15:01:51 | recommendationCacheFailure | 145 | 145 | 86 | 106 |
| 15:01:51 to 15:05:51 | recommendationCacheFailure | 140 | 143 | 88 | 119 |
| 15:05:51 to 15:09:51 | recommendationCacheFailure, loadGeneratorFloodHomepage | 145 | 152 | 90 | 99 |
| 15:09:51 to 15:13:51 | loadGeneratorFloodHomepage | 145 | 145 | 86 | 109 |
| 15:13:51 to 15:17:51 | none | 145 | 145 | 88 | 129 |
| 15:17:51 to 15:21:51 | recommendationCacheFailure | 145 | 144 | 88 | 185 |
| 15:21:51 to 15:25:51 | recommendationCacheFailure | 145 | 146 | 86 | 158 |
| 15:25:51 to 15:29:51 | emailMemoryLeak | 145 | 144 | 88 | 141 |
| 15:29:51 to 15:33:51 | emailMemoryLeak | 145 | 145 | 89 | 115 |
| 15:33:51 to 15:37:51 | emailMemoryLeak | 145 | 143 | 90 | 99 |
| 15:37:51 to 15:41:51 | loadGeneratorFloodHomepage | 144 | 147 | 90 | 136 |
| 15:41:51 to 15:45:51 | loadGeneratorFloodHomepage | 139 | 146 | 90 | 91 |
| 15:45:51 to 15:49:51 | cartFailure | 142 | 143 | 90 | 98 |
| 15:49:51 to 15:53:51 | cartFailure | 145 | 145 | 88 | 140 |
| 15:53:51 to 15:57:51 | cartFailure | 145 | 145 | 91 | 159 |
| 15:57:51 to 16:01:51 | recommendationCacheFailure | 145 | 145 | 91 | 129 |
| 16:01:51 to 16:05:51 | recommendationCacheFailure | 145 | 145 | 89 | 93 |
| 16:05:51 to 16:09:51 | loadGeneratorFloodHomepage | 145 | 148 | 91 | 94 |
| 16:09:51 to 16:13:51 | loadGeneratorFloodHomepage | 141 | 150 | 89 | 134 |
| 16:13:51 to 16:17:51 | none | 139 | 144 | 89 | 134 |
| 16:17:51 to 16:21:51 | recommendationCacheFailure | 144 | 146 | 88 | 67 |
| 16:21:51 to 16:25:51 | recommendationCacheFailure | 145 | 145 | 88 | 148 |
| 16:25:51 to 16:29:51 | cartFailure | 146 | 142 | 89 | 158 |
| 16:29:51 to 16:33:51 | cartFailure | 137 | 143 | 87 | 101 |
| 16:33:51 to 16:37:51 | cartFailure | 145 | 142 | 87 | 112 |
| 16:37:51 to 16:41:51 | emailMemoryLeak | 148 | 143 | 88 | 115 |
| 16:41:51 to 16:45:51 | emailMemoryLeak | 146 | 145 | 88 | 148 |
| 16:45:51 to 16:49:51 | loadGeneratorFloodHomepage | 142 | 147 | 90 | 109 |
| 16:49:51 to 16:53:51 | loadGeneratorFloodHomepage | 142 | 150 | 88 | 126 |
| 16:53:51 to 16:57:51 | none | 145 | 145 | 87 | 98 |
| 16:57:51 to 17:01:51 | emailMemoryLeak | 145 | 143 | 89 | 112 |
| 17:01:51 to 17:05:51 | emailMemoryLeak | 145 | 147 | 86 | 135 |
| 17:05:51 to 17:09:51 | emailMemoryLeak, paymentFailure | 143 | 139 | 91 | 146 |
| 17:09:51 to 17:13:51 | paymentFailure | 142 | 145 | 86 | 122 |
| 17:13:51 to 17:17:51 | none | 140 | 141 | 88 | 99 |
| 17:17:51 to 17:21:51 | kafkaQueueProblems | 145 | 144 | 86 | 112 |
| 17:21:51 to 17:25:51 | kafkaQueueProblems | 140 | 136 | 85 | 101 |
| 17:25:51 to 17:29:51 | none | 143 | 145 | 85 | 134 |
| 17:29:51 to 17:33:51 | kafkaQueueProblems | 142 | 144 | 84 | 149 |
| 17:33:51 to 17:35:42 | kafkaQueueProblems | 15 | 16 | 0 | 45 |

## 3. False holds: rates, load, and the cap that would have avoided them

### Rates

Quiet run: 12:54:22 to 13:16:29, five full windows, measured from the raw lines because the Receiver returned no shipping request lines in that run. Scheduled run: the 51 full Receiver windows, from raw lines by `fb_ts`.

| false hold | quiet run, per window | scheduled run, raw per window | when held (Receiver window 17:17:51 to 17:21:51) |
|---|---|---|---|
| shipping Requesting quote | 1 to 17 events, max 6,919 bytes | median 14 events, max 21; median 5,698 bytes, max 8,547 | 557 events, 226,699 bytes |
| shipping Sending Quote | 1 to 17 events, max 6,856 bytes | median 14, max 21; max 8,464 bytes | 557 events, 224,568 bytes |
| shipping Tracking ID Created | 1 to 17 events, max 6,902 bytes | median 13, max 21; max 8,526 bytes | 539 events, 218,834 bytes |
| (if counted) frontend API_request_completed | 50 to 230 events, 23,924 to 110,771 bytes (median 93,804) | 168 to 287 events, 80,979 to 138,256 bytes (median 105,083) | every window, 67 to 185 held per window |

Shipping's own rate in the scheduled run was within 1.25x of the quiet run (max 21 against 17 events per window). The Receiver saw about 26 times the scheduled run's busiest window in one window because it handled 3 h 25 min of lines at once.

### Load

- The load generator ran with the same settings in both runs: the demo's `.env` (`LOCUST_USERS=5`, `LOCUST_AUTOSTART=true`, `LOCUST_HTTP_USER_WEIGHT=9`, file unchanged since 2026-10-13) with the browser user disabled by `compose.rig.yaml` (`LOCUST_BROWSER_TRAFFIC_ENABLED=false`, `LOCUST_BROWSER_USER_WEIGHT=0`). The only overlay change between the runs (commit b0bd75c) added the Receiver's `@run/output/metric/log`.
- loadGeneratorFloodHomepage (value 100: each `flood_home` task fetches `/` 100 times) was on four times (15:08:08, 15:40:12, 16:07:59, 16:48:59). It was off when shipping was released at 17:19:15.
- The flood does not change stdout volume. In the 8 windows touched by a flood, frontend logged a median of 225 raw lines per window against 232 in the other 43, and all containers logged 1,685 against 1,708. frontend's `API_request_completed` was 101,501 bytes per window (median) in flood windows against 106,105 otherwise.

### The fleet-default number that would have avoided each false hold

- Shipping: a cap of at least **226,699 bytes**, the largest burst cell. That is 4.64x the 48,862 used and 9.28x the largest kept quiet cell (24,431). The burst is the sum of every line the Receiver held back (13:54:02 to 17:19:15), so this number reflects how long the lines were held, not shipping's load. A longer hold makes a larger burst.
- frontend `API_request_completed` (if counted): at least **138,256 bytes**, its largest window in the run.

What each cap would have done, from the replay. "First hold" is the earliest held record of any class (a) pattern, in minutes after flag on. The flood began at +0.15, +1.68 and +0.08 min in the three activations.

| cap (bytes) | otel dumps held | frontend move held | class (a) held | shipping held | ERROR held | kafka 14:18:42: held, first hold | kafka 17:20:32: held, first hold | kafka 17:30:11: held, first hold |
|---|---|---|---|---|---|---|---|---|
| 48,862 (used; replay) | 19,534 | 6,323 | 33,272 | 1,292 | 5,223 | 13,594, +0.15 | 4,581, +1.70 | 15,097, +0.08 |
| 73,293 (3x kept max) | 12,276 | 3,636 | 30,279 | 1,112 | 4,683 | 12,119, +0.17 | 4,056, +1.72 | 14,104, +0.08 |
| 122,155 (5x) | 217 | 52 | 25,663 | 751 | 3,753 | 10,170, +0.48 | 3,140, +2.03 | 12,353, +0.16 |
| 138,256 (clears the frontend move) | 0 | 0 | 24,206 | 632 | 3,456 | 9,583, +0.48 | 2,836, +2.05 | 11,787, +0.16 |
| 226,699 (clears shipping) | 0 | 0 | 16,314 | 0 | 1,829 | 6,382, +1.33 | 1,223, +2.50 | 8,709, +0.71 |
| 500,000 | 0 | 0 | 5,949 | 0 | 0 | 2,594, +1.55 | 363, +3.35 | 2,992, +1.25 |

At 226,699 all three kafka incidents are still held, but with about half the records (16,314 against 33,272). The first hold comes 1.18, 0.82 and 0.63 minutes after the flood's first line, against within 1 s at 48,862. The patterns still held at that cap are fraud-detection `Consumed record`, accounting `Order details`, and the database's ERROR, DETAIL and STATEMENT lines in all three activations, plus accounting `Duplicate order received` in activations 2 and 21. fraud-detection's `sleeping 1 second` line is no longer held. At that cap none of the plan's four moves is held, so the plan's moves would need their own rule.

### Headroom of the kept patterns

The largest window of any pattern the plan keeps, outside the class (a) kafka cells and shipping's burst, over the 53 windows the run touches and all 21 activations:

| container | pattern | largest window (bytes) | events | window start | flag in window | share of 48,862 |
|---|---|---|---|---|---|---|
| cart | GetCartAsync_called_with_userId | 29,767 | 109 | 15:17:51 | recommendationCacheFailure | 0.61 |
| cart | AddItemAsync_called_with_userId_productId_quantity | 19,287 | 61 | 15:21:51 | recommendationCacheFailure | 0.39 |
| accounting | Order_details | 18,991 | 21 | 15:53:51 | cartFailure | 0.39 |
| otel-collector | error_Error_scraping_metrics | 18,437 | 5 | 14:25:51 | kafkaQueueProblems | 0.38 |
| recommendation | Receive_ListRecommendations_for_product_ids | 17,612 | 37 | 15:01:51 | recommendationCacheFailure | 0.36 |
| payment | Transaction_complete | 13,953 | 21 | 15:53:51 | cartFailure | 0.29 |
| telemetry-docs | GET_HTTP_Wget | 11,952 | 48 | 14:21:51 | kafkaQueueProblems | 0.24 |
| payment | Payment_request_failed_Invalid_token_demo_user_context_loyalty_level_gold | 11,934 | 13 | 17:05:51 | emailMemoryLeak, paymentFailure | 0.24 |
| astronomy-db | role_root_does_not_exist | 11,233 | 47 | 15:33:51 | emailMemoryLeak | 0.23 |
| cart | Error_code_FailedPrecondition_detail_Can_access_cart_storage_System_ApplicationException_Wasn_t_able_to_connect_redis | 9,920 | 16 | 14:09:51 | cartFailure | 0.20 |

The largest window under each flag was cart's `GetCartAsync` every time: 29,767 (recommendationCacheFailure), 27,508 (cartFailure), 25,280 (loadGeneratorFloodHomepage), 24,961 (emailMemoryLeak), 24,328 (paymentFailure), 24,148 (kafkaQueueProblems) and 23,937 with no flag. The quiet run's maximum for the same pattern was 24,431.

### Recommended default rule

Keep the rule as it stands: **2 x the largest per-window cell the plan keeps** (48,862 bytes on this demo). None of the three alternatives is supported by this run:

- **A different headroom.** Over 51 full windows and 21 activations, no kept pattern rose above 0.61 of the cap except the kafkaQueueProblems flood itself. The scheduled maximum was 1.22x the quiet maximum, inside the 2x margin. Raising the headroom far enough to clear shipping (226,699, about 9.3x) halves the kafka containment, delays the first hold by 0.6 to 1.2 minutes after the flood starts, and stops the cap from holding any of the plan's four moves.
- **A longer or loaded baseline.** The homepage flood does not change stdout volume (section 3, Load), so a baseline taken under the flood would measure the same cells. A longer quiet run would still be blind to shipping: the Receiver swallowed shipping's request lines in the quiet run as well.
- **A per-container floor.** The only false hold was 1,293 shipping lines, released in a burst after up to 3 h 25 min inside the Receiver. A floor for shipping would hide that symptom and leave the burst in place.

The shipping hold comes from how the Receiver groups shipping's lines after its one ERROR line (NOTES.md, 13:07 UTC replay). That needs a fix outside the cap rule before the rerun, and the choice of fix is Tal's.

## 4. Errors

**5,223 ERROR records and 0 CRITICAL records were held.** Every one is astronomy-db's `duplicate key value violates unique constraint "order_pkey"` (KSTuhseaGEc), held during the three kafkaQueueProblems activations: 2,060 (14:18:42), 721 (17:20:32) and 2,442 (17:30:11). No other held record carries `severity_level` ERROR or CRITICAL. 11,781 held records carry no `severity_level`: astronomy-db DETAIL 5,259, STATEMENT 5,229 and shipping 1,293.

**At an ERROR and CRITICAL floor of 0.5**, each over-cap ERROR record passes with probability 0.5. In `rate-object-cap.js` the floor check (`if (TenXMath.random() < floor) return true;`) runs after the cap check. The byte and count counters are incremented before any decision, so a record passed by the floor does not change the decision for any other record. Of the 5,223 held ERROR records, the expected number passed is **2,611.5** (binomial, standard deviation 36.1, so about 2,541 to 2,682 at 95%). That leaves about 2,611 still held. Per activation the expected passes are 1,030, 360.5 and 1,221.

The floor does not reach the DETAIL and STATEMENT lines that go with each ERROR line, because they have no level. Those lines carry the order id and the failing INSERT. A level missing from the floor map takes `minRetentionThreshold`, which is 0 in this rig. So an ERROR line passed by the floor arrives without its DETAIL and STATEMENT lines, unless they are under the cap.

## 5. Delivery

Raw lines Fluent Bit received against the records the Receiver returned, scheduled run span (`fb_ts` 14:07:14 to 17:35:42). The Receiver joins continuation lines into one record, so the comparison is against the lines the returned records cover (newlines in `log` + 1).

| container | raw lines | pass | offload | pass + offload | lines covered by returned records | covered minus raw |
|---|---|---|---|---|---|---|
| accounting | 26,574 | 2,146 | 11,140 | 13,286 | 26,572 | -2 |
| ad | 1,094 | 1,025 | 0 | 1,025 | 1,094 | +0 |
| astronomy-db | 27,703 | 5,692 | 15,711 | 21,403 | 27,703 | +0 |
| cart | 13,946 | 6,844 | 0 | 6,844 | 13,946 | +0 |
| email | 1,374 | 687 | 0 | 687 | 1,372 | -2 |
| flagd | 42 | 41 | 0 | 41 | 41 | -1 |
| flagd-ui | 86 | 85 | 0 | 85 | 85 | -1 |
| fraud-detection | 8,459 | 2,035 | 6,423 | 8,458 | 8,458 | -1 |
| frontend | 12,364 | 6,010 | 6,324 | 12,334 | 12,364 | +0 |
| frontend-proxy | 1 | 1 | 0 | 1 | 1 | +0 |
| kafka | 9,466 | 9,466 | 0 | 9,466 | 9,466 | +0 |
| otel-collector | 37,442 | 14,869 | 19,535 | 34,404 | 37,442 | +0 |
| payment | 1,444 | 1,443 | 0 | 1,443 | 1,443 | -1 |
| quote | 722 | 721 | 0 | 721 | 721 | -1 |
| recommendation | 1,273 | 1,272 | 0 | 1,272 | 1,272 | -1 |
| shipping | 2,212 | 595 | 1,293 | 1,888 | 1,888 | -324 |
| telemetry-docs | 2,450 | 2,450 | 0 | 2,450 | 2,450 | +0 |
| valkey-cart | 205 | 204 | 0 | 204 | 204 | -1 |
| total | 146,857 | 55,586 | 60,426 | 116,012 | 146,522 | -335 |

- **Shipping -324.** These are shipping's raw lines from 14:07:14 to 14:38:09. They came back inside the 371-line record headed by the 13:54:02 ERROR line, whose `fb_ts` is before the span. Over the whole final run (Receiver ready 13:53:18 to `run_end` 17:35:42), shipping's raw and returned lines match one for one.
- **The other 11 lines** (accounting 2, email 2, seven containers 1 each). Over the whole final run (13:53:18 to 17:35:42), the shortfall is 10 lines: 153,999 raw against 153,989 covered, with email at 1. For flagd, quote and recommendation, the missing line is the container's last raw line, written between 17:35:33 and 17:35:41, seconds before the stop. For accounting, email, flagd-ui, fraud-detection, payment and valkey-cart, the difference is in the line count of multi-line records and is not located further.
- **Fluent Bit.** One forward retry, at 14:26:23 (`no upstream connections available`). Both chunks were delivered on retry at 14:26:30 and 14:26:33.
