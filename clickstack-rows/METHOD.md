# ClickHouse rows run, compressed, method (written before the run, 10-23)

The metered gate for the claim ruled at STOP 1 (`RECOMMENDATION_STEP1.md`, amended in `RECOMMENDATION_STEP3.md` section 8): the Receiver, driven by log10x-mcp's rows run, holds the rows written into a ClickStack logs table at a rate R an hour while load grows 2.5x, as ClickHouse's own `system.part_log` counts them. Rig: `benchmarks` branch `bench/clickhouse-rows-run`, folder `clickstack-rows/`. Time-scaled the way the Elastic rerun is (every clock divided by 6), with the factors stated here and in the README.

## Build

- log10x-mcp branch `feat/clickhouse-rows-budget` (off `feat/elastic-hot-tier-budget` 0b45d4a, unreleased): `clickhouse-rows-tick.ts`, policy `rows_per_hour` with `clickhouse_table`, `container_label`, `meter_minutes`, `keep_count`, `default_action: offload`, `nodes_by_container`; `receiverFleetValues({ clickhouseRows: true })` writes `rateReceiverUnit events` and `symbolMessageHashField tenx_hash`.
- Engine `ghcr.io/log-10x/edge-10x:1.1.147`; ClickStack 2.38.0 (ClickHouse 26.5.7.64); the `clickstack-e2e` routing collector (contrib 0.160.0) unchanged but for the feed path; RustFS as the S3 store; Prometheus 3.9.1 scraping the Receiver.
- The meter picked by the gate (`clickstack-rows-gate`): `system.part_log` NewPart rows on `default.otel_logs`, by `event_time`. `system.parts` active rows as the cross-check. `system.query_log` is not the meter.

## Time scale: every clock divided by 6

| Production | Rig |
|---|---|
| tick every hour | tick every 10 minutes (the harness invokes `tenx-recur`; no cron) |
| meter window one hour (`meter_minutes: 60`) | `meter_minutes: 10`, read as a rate an hour |
| growth stepped hourly | stepped every 20 minutes |
| a day of lookback | the run's own span |

Not scaled: the regulator's 4-minute window and the always-pass sample of 5 (engine constants), the collector's 5-second batch, the hour the rate R is stated in.

## Load

The published OpenTelemetry demo capture (197,430 lines) replayed into the collector's file at a set pace by a pacer that loops the capture and rewrites its timestamps to now. Starting pace 2x the capture's own rate (about 14 lines a second); stepped every 20 minutes from 1:00 to 2.75x, 3.5x, 4.25x and 5x (2.5 times the starting load), held 40 minutes, then stopped. A new service (`inventory`, a line shape not in the capture) injected at 1:20 at 2 lines a second. An error storm (a real `level=error` line of one Grafana statement) at 1:40 for 20 minutes at 10 lines a second. Drain 20 minutes.

## Rate

At 0:30, a dry run with `rows_per_hour: auto` reports the meter's last complete window scaled to an hour with nothing held (P). R = 0.7 x P, written to `policy.yaml` as `rows_per_hour`, and not changed. The first applied run follows at 0:40; applied runs every 10 minutes until the drain ends.

## Meter

`system.part_log` NewPart rows per 4-minute window by `event_time`, every 100 seconds, plus `count()` on the hot table, rows in the cold view, and the object count. The Receiver's returned records are tapped on the wire as in `clickstack-e2e`. Prometheus holds the Receiver's counters for the run and the report.

## Criteria

1. Every applied run exits 0 and commits its files to the policy branch; once the rate binds, each run's projection is at or under R, or the run reports that the floor alone exceeds what fits.
2. From 1:00 (two applied runs after the rate binds) to the end of the 5x hold: rows written into the table per 4-minute window, on the meter, at or under R / 15 plus the floor's share of a window at every window, and the sum over each 10-minute meter window at or under R / 6. The step-up windows decide.
3. Hot rows plus rows in the objects equal the records the Receiver returned, per hash for the ten largest moved statements (the lossless reconciliation of totals, with the restart caveat stated).
4. A count of each of the ten largest moved statements through the Merge table equals the local count.
5. Delivery: every non-blank line the pacer wrote comes back from the Receiver, and every returned record is in the table or the bucket.
6. Storm: error lines of the storming statement in the table per node per window at most its limit plus 50; the window that spans a policy reload is reported separately.
7. The injected service is held from its first window by the `*` row.

## Reports, pre-registered, not scored

- The floor F each run computes, beside R.
- The meter in the window spanning each policy reload.
- Rows outside the Receiver (O) each run.
- Insert plus merge CPU seconds per 10 minutes from `system.query_log` and `system.part_log` ProfileEvents, whole table, labelled noisy, against a control feed with no cap (if time allows a second pass).
- Objects and GETs for criterion 4.

## Not claimed

A bill figure; ClickHouse Cloud behaviour or the autoscaler; 300 nodes; a comparison with the native loop; durability across a restart (E89); a write-CPU figure against a collector rule (D12).
