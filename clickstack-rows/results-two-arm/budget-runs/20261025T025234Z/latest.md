# Rows run: 2026-10-25T02:52:34.000Z

Rows written: 30k of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 30k an hour, with 13k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 30k pass lines an hour against 30k rows the meter puts on it, so each statement's rate is scaled by 1.01. The table holds 38k active rows.
- The Receiver's statements send 43k lines an hour; 30k an hour fits the rate, so each statement keeps up to 3524 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4511 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 1930 | 1930 | 234 | 128 |
| cart | the account's bucket | 1 | 5589 | 5589 | 234 | 372 |
| fluentd-10x | the account's bucket | 1 | 340 | 340 | 234 | 22 |
| frontend | the account's bucket | 1 | 1626 | 1626 | 234 | 108 |
| grafana | the account's bucket | 1 | 231 | 231 | 234 | 15 |
| kafka | the account's bucket | 1 | 7701 | 7701 | 234 | 513 |
| kube-proxy | the account's bucket | 1 | 36 | 36 | 234 | 2 |
| opensearch | the account's bucket | 1 | 73 | 73 | 234 | 4 |
| opentelemetry-collector | the account's bucket | 1 | 24k | 12k | 234 | 772 |
| prometheus-server | the account's bucket | 1 | 24 | 24 | 234 | 1 |
| recommendation | the account's bucket | 1 | 783 | 783 | 234 | 52 |
| valkey-cart | the account's bucket | 1 | 182 | 182 | 234 | 12 |
| `*` (any other service) | the account's bucket | 1 | | 561 | 234 | 37 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
