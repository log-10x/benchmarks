# Rows run: 2026-10-23T18:54:47.000Z

Rows written: 30k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 81k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 13k pass lines an hour against 30k rows the meter puts on it, so each statement's rate is scaled by 2.37. The table holds 73k active rows.
- The Receiver's statements send 110k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1121 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4473 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 13k pass lines an hour against 30k rows on the meter; rates are scaled by 2.37, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 5138 | 2512 | 74 | 167 |
| cart | the account's bucket | 1 | 13k | 2241 | 74 | 149 |
| fluentd-10x | the account's bucket | 1 | 811 | 811 | 74 | 54 |
| frontend | the account's bucket | 1 | 1537 | 1121 | 74 | 74 |
| grafana | the account's bucket | 1 | 584 | 584 | 74 | 38 |
| inventory | the account's bucket | 1 | 7202 | 1121 | 74 | 74 |
| kafka | the account's bucket | 1 | 19k | 15k | 74 | 971 |
| opensearch | the account's bucket | 1 | 142 | 142 | 74 | 9 |
| opentelemetry-collector | the account's bucket | 1 | 59k | 4482 | 74 | 298 |
| prometheus-server | the account's bucket | 1 | 270 | 270 | 74 | 18 |
| recommendation | the account's bucket | 1 | 2434 | 1121 | 74 | 74 |
| valkey-cart | the account's bucket | 1 | 427 | 427 | 74 | 28 |
| `*` (any other service) | the account's bucket | 1 | | 1121 | 74 | 74 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
