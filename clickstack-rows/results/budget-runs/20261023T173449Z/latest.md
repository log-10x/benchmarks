# Rows run: 2026-10-23T17:34:49.000Z

Rows written: 27k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 11k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 27k pass lines an hour against 27k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 33k active rows.
- The Receiver's statements send 41k lines an hour; 29k an hour fits the rate, so each statement keeps up to 3870 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3639 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 1950 | 1950 | 257 | 130 |
| cart | the account's bucket | 1 | 5214 | 5214 | 257 | 347 |
| fluentd-10x | the account's bucket | 1 | 330 | 330 | 257 | 22 |
| frontend | the account's bucket | 1 | 678 | 678 | 257 | 45 |
| grafana | the account's bucket | 1 | 234 | 234 | 257 | 15 |
| kafka | the account's bucket | 1 | 7428 | 7428 | 257 | 495 |
| kube-proxy | the account's bucket | 1 | 18 | 18 | 257 | 1 |
| opensearch | the account's bucket | 1 | 72 | 72 | 257 | 4 |
| opentelemetry-collector | the account's bucket | 1 | 24k | 12k | 257 | 831 |
| prometheus-server | the account's bucket | 1 | 24 | 24 | 257 | 1 |
| recommendation | the account's bucket | 1 | 822 | 822 | 257 | 54 |
| valkey-cart | the account's bucket | 1 | 150 | 150 | 257 | 10 |
| `*` (any other service) | the account's bucket | 1 | | 504 | 257 | 33 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
