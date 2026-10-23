# Rows run: 2026-10-23T19:04:47.000Z

Rows written: 30k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 68k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 14k pass lines an hour against 30k rows the meter puts on it, so each statement's rate is scaled by 2.10. The table holds 79k active rows.
- The Receiver's statements send 97k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1150 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4215 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 14k pass lines an hour against 30k rows on the meter; rates are scaled by 2.10, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 4477 | 2565 | 76 | 170 |
| cart | the account's bucket | 1 | 12k | 2300 | 76 | 153 |
| fluentd-10x | the account's bucket | 1 | 706 | 706 | 76 | 47 |
| frontend | the account's bucket | 1 | 1425 | 1150 | 76 | 76 |
| grafana | the account's bucket | 1 | 492 | 492 | 76 | 32 |
| inventory | the account's bucket | 1 | 6407 | 1150 | 76 | 76 |
| kafka | the account's bucket | 1 | 17k | 15k | 76 | 982 |
| kube-proxy | the account's bucket | 1 | 38 | 38 | 76 | 2 |
| opensearch | the account's bucket | 1 | 126 | 126 | 76 | 8 |
| opentelemetry-collector | the account's bucket | 1 | 52k | 4600 | 76 | 306 |
| prometheus-server | the account's bucket | 1 | 25 | 25 | 76 | 1 |
| recommendation | the account's bucket | 1 | 2081 | 1150 | 76 | 76 |
| valkey-cart | the account's bucket | 1 | 366 | 366 | 76 | 24 |
| `*` (any other service) | the account's bucket | 1 | | 1150 | 76 | 76 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
