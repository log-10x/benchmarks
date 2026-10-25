# Rows run: 2026-10-25T03:02:34.000Z

Rows written: 31k of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 30k an hour, with 23k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 32k pass lines an hour against 31k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 44k active rows.
- The Receiver's statements send 53k lines an hour; 30k an hour fits the rate, so each statement keeps up to 2524 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4695 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 2124 | 2124 | 168 | 141 |
| cart | the account's bucket | 1 | 7026 | 5458 | 168 | 363 |
| fluentd-10x | the account's bucket | 1 | 420 | 420 | 168 | 28 |
| frontend | the account's bucket | 1 | 1830 | 1830 | 168 | 122 |
| grafana | the account's bucket | 1 | 306 | 306 | 168 | 20 |
| kafka | the account's bucket | 1 | 9612 | 9612 | 168 | 640 |
| opensearch | the account's bucket | 1 | 66 | 66 | 168 | 4 |
| opentelemetry-collector | the account's bucket | 1 | 30k | 8825 | 168 | 588 |
| prometheus-server | the account's bucket | 1 | 36 | 36 | 168 | 2 |
| recommendation | the account's bucket | 1 | 1212 | 1212 | 168 | 80 |
| valkey-cart | the account's bucket | 1 | 210 | 210 | 168 | 14 |
| `*` (any other service) | the account's bucket | 1 | | 1212 | 168 | 80 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
