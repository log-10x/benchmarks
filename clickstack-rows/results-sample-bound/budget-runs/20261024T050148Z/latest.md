# Rows run: 2026-10-24T05:01:49.000Z

Rows written: 31k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 106k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 21k pass lines an hour against 31k rows the meter puts on it, so each statement's rate is scaled by 1.47. The table holds 63k active rows.
- The Receiver's statements send 135k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1090 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 5087 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 3720 | 2464 | 72 | 164 |
| cart | the account's bucket | 1 | 12k | 2181 | 72 | 145 |
| fluentd-10x | the account's bucket | 1 | 742 | 742 | 72 | 49 |
| frontend | the account's bucket | 1 | 1361 | 1090 | 72 | 72 |
| grafana | the account's bucket | 1 | 38k | 1612 | 72 | 107 |
| inventory | the account's bucket | 1 | 7414 | 1090 | 72 | 72 |
| kafka | the account's bucket | 1 | 17k | 14k | 72 | 945 |
| opensearch | the account's bucket | 1 | 124 | 124 | 72 | 8 |
| opentelemetry-collector | the account's bucket | 1 | 53k | 4362 | 72 | 290 |
| prometheus-server | the account's bucket | 1 | 71 | 71 | 72 | 4 |
| recommendation | the account's bucket | 1 | 2289 | 1090 | 72 | 72 |
| valkey-cart | the account's bucket | 1 | 398 | 398 | 72 | 26 |
| `*` (any other service) | the account's bucket | 1 | | 1090 | 72 | 72 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
