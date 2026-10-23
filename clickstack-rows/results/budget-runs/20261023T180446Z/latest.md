# Rows run: 2026-10-23T18:04:46.000Z

Rows written: 29k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 43k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 13k pass lines an hour against 29k rows the meter puts on it, so each statement's rate is scaled by 2.18. The table holds 48k active rows.
- The Receiver's statements send 72k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1515 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3930 lines an hour whatever the limits; the rate holds down to that floor.
- Warning: The Receiver's counters read 13k pass lines an hour against 29k rows on the meter; rates are scaled by 2.18, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 3124 | 3083 | 101 | 205 |
| cart | the account's bucket | 1 | 8234 | 3030 | 101 | 202 |
| fluentd-10x | the account's bucket | 1 | 523 | 523 | 101 | 34 |
| frontend | the account's bucket | 1 | 993 | 993 | 101 | 66 |
| grafana | the account's bucket | 1 | 327 | 327 | 101 | 21 |
| inventory | the account's bucket | 1 | 6744 | 1515 | 101 | 101 |
| kafka | the account's bucket | 1 | 12k | 12k | 101 | 821 |
| kube-proxy | the account's bucket | 1 | 39 | 39 | 101 | 2 |
| opensearch | the account's bucket | 1 | 52 | 52 | 101 | 3 |
| opentelemetry-collector | the account's bucket | 1 | 39k | 6061 | 101 | 404 |
| recommendation | the account's bucket | 1 | 1189 | 1189 | 101 | 79 |
| valkey-cart | the account's bucket | 1 | 261 | 261 | 101 | 17 |
| `*` (any other service) | the account's bucket | 1 | | 1091 | 101 | 72 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
