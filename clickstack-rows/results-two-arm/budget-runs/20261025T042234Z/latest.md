# Rows run: 2026-10-25T04:22:35.000Z

Rows written: 29k of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 30k an hour, with 80k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 29k pass lines an hour against 29k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 84k active rows.
- The Receiver's statements send 111k lines an hour; 30k an hour fits the rate, so each statement keeps up to 1098 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 5091 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 4836 | 2502 | 73 | 166 |
| cart | the account's bucket | 1 | 14k | 2760 | 73 | 183 |
| fluentd-10x | the account's bucket | 1 | 834 | 834 | 73 | 55 |
| frontend | the account's bucket | 1 | 2268 | 1860 | 73 | 123 |
| grafana | the account's bucket | 1 | 594 | 594 | 73 | 39 |
| inventory | the account's bucket | 1 | 7200 | 1098 | 73 | 73 |
| kafka | the account's bucket | 1 | 19k | 14k | 73 | 955 |
| kube-proxy | the account's bucket | 1 | 54 | 54 | 73 | 3 |
| opensearch | the account's bucket | 1 | 150 | 150 | 73 | 10 |
| opentelemetry-collector | the account's bucket | 1 | 59k | 4392 | 73 | 292 |
| prometheus-server | the account's bucket | 1 | 42 | 42 | 73 | 2 |
| recommendation | the account's bucket | 1 | 2304 | 1098 | 73 | 73 |
| valkey-cart | the account's bucket | 1 | 390 | 390 | 73 | 26 |
| `*` (any other service) | the account's bucket | 1 | | 1098 | 73 | 73 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
