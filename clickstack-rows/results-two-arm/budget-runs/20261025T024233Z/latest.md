# Rows run: 2026-10-25T02:42:34.000Z

Rows written: 33k of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 30k an hour, with 13k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 34k pass lines an hour against 33k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 34k active rows.
- The Receiver's statements send 43k lines an hour; 30k an hour fits the rate, so each statement keeps up to 3461 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4494 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 1980 | 1980 | 230 | 132 |
| cart | the account's bucket | 1 | 5358 | 5358 | 230 | 357 |
| fluentd-10x | the account's bucket | 1 | 336 | 336 | 230 | 22 |
| frontend | the account's bucket | 1 | 1806 | 1806 | 230 | 120 |
| grafana | the account's bucket | 1 | 246 | 246 | 230 | 16 |
| kafka | the account's bucket | 1 | 7782 | 7782 | 230 | 518 |
| opensearch | the account's bucket | 1 | 60 | 60 | 230 | 4 |
| opentelemetry-collector | the account's bucket | 1 | 24k | 11k | 230 | 759 |
| prometheus-server | the account's bucket | 1 | 12 | 12 | 230 | 1 |
| recommendation | the account's bucket | 1 | 978 | 978 | 230 | 65 |
| valkey-cart | the account's bucket | 1 | 150 | 150 | 230 | 10 |
| `*` (any other service) | the account's bucket | 1 | | 978 | 230 | 65 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
