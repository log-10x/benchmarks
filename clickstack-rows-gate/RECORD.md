# ClickHouse rows gate: which meter equals the hot count

One question, answered on the `clickstack-e2e` rig file for file: when the Receiver
regulates in lines with a service total and the shipped always-pass sample of 5,
which ClickHouse system table counts the rows written into the logs table to the
row? The answer is the meter the rows run reads every hour.

## Result

Two runs on 2026-10-23, engine `ghcr.io/log-10x/edge-10x:1.1.147`, ClickStack
2.38.0 on ClickHouse 26.5.7.64, the whole 197,430-line capture fed in about 216 s.
Results in [`results/`](results/), one file per run date.

| Count | Run 2 (events unit) | Against hot |
|---|---:|---|
| Hot rows, `SELECT count() FROM default.otel_logs` | 22,367 | the count to match |
| Wire records marked `pass` | 22,367 | equal |
| `system.parts` active rows | 22,367 | equal |
| `system.part_log` NewPart rows, `otel_logs` | 22,367 | **equal** |
| `system.query_log` `written_rows`, kind `Insert`, `tables` has `otel_logs` | 24,315 | off by +1,948 |
| `system.query_log` `written_rows`, kind `AsyncInsertFlush` | 14,848 | off by -7,519 |

In run 1 the `Insert` entries happened to equal the hot count and the
`AsyncInsertFlush` entries ran over by the materialized view's rows. ClickStack's
exporter inserts asynchronously, and which of the two entry kinds carries the
downstream rows differs from run to run, so `system.query_log` is a cross-check at
most. `system.part_log` NewPart rows equalled the hot count in both runs and is the
meter. Every insert statement names three tables (`otel_logs`, the counts table and
`otel_logs_kv_rollup_15m`) in `query_log`'s `tables`, which is why a filter on the
logs table alone cannot separate its rows there.

Hot plus cold equalled the wire: 22,367 + 134,720 = 157,087 records returned by the
Receiver, with every record carrying a route.

## What else the run measured

- **The service totals held to the row.** With the regulator counting events,
  kafka kept 1,000 of a total of 1,000, cart 400 of 400, and opentelemetry-collector
  2,050 of 2,000: the extra 50 is the error keep count for one storming error
  statement, which the rate doc states.
- **A policy-file rewrite mid-window did not reset the window counts.** The totals
  file was rewritten in place 4 seconds into the feed; the engine logged the reload
  with all four policy files, and no capped service passed another line in the
  window. The limits bind inside the window across a reload on this engine.
- **The events unit does not take effect from the environment.** Run 1 passed
  `rateReceiverUnit=events` in the container's environment and the caps still counted
  bytes (each capped service kept only its 5-line samples). The unit has to be in the
  config file or an engine option, which is how `receiverFleetValues` writes it.
- **The e2e harness's config patches on 1.1.147:** its rate edits no longer apply
  (1.1.147 ships `warmupMs: 0`), and its splice patch failed on indentation only. This
  gate's [`patch_engine_config.py`](patch_engine_config.py) matches the expression
  text, writes `unit: events`, and leaves `baselineCount` at the shipped 5.
- **The Receiver's Prometheus counters** carry `k8s_container`, `tenx_user_service`,
  `tenx_hash`, `message_pattern`, `severity_level`, `routeState` and `tenx_env`. At the
  moment of a scrape they lag the wire (`pass` 16,255 against 22,367), so a run reads
  the last complete hour rather than the current one.

## Run it

```
CSE_DATA_DIR=../clickstack-e2e/data ./run.sh    # the capture clickstack-e2e/run.sh downloads
RELOAD_AFTER=40 ./run.sh                         # seconds into the feed to rewrite totals.csv
```

MinIO's public images were withdrawn from quay.io and Docker Hub (401 and access
denied on 2026-10-23), so the object store is RustFS on the same port and endpoint
name with the same static credentials, and bucket operations run through the AWS CLI
image. The collector and ClickHouse read it as S3 unchanged.

## What a run does not prove

Nothing about money, ClickHouse Cloud, or a rate held over hours: the feed is one
regulator window long. The rows run's metered run is the separate harness that holds
a rate through growth; this gate only picks its meter.
