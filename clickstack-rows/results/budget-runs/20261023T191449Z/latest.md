# Rows run: 2026-10-23T19:14:49.000Z

Rows written: 40k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 112k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 6372 pass lines an hour against 40k rows the meter puts on it, so each statement's rate is scaled by 6.28. The table holds 84k active rows.
- The Receiver's statements send 141k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1001 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 6346 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 6372 pass lines an hour against 40k rows on the meter; rates are scaled by 6.28, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 3880 | 2341 | 66 | 156 |
| cart | the account's bucket | 1 | 13k | 2002 | 66 | 133 |
| fluentd-10x | the account's bucket | 1 | 4106 | 3450 | 66 | 229 |
| frontend | the account's bucket | 1 | 1431 | 1001 | 66 | 66 |
| frontend-proxy | the account's bucket | 1 | 38 | 38 | 66 | 2 |
| grafana | the account's bucket | 1 | 565 | 565 | 66 | 37 |
| inventory | the account's bucket | 1 | 16k | 1001 | 66 | 66 |
| kafka | the account's bucket | 1 | 19k | 13k | 66 | 872 |
| opensearch | the account's bucket | 1 | 188 | 188 | 66 | 12 |
| opentelemetry-collector | the account's bucket | 1 | 78k | 4005 | 66 | 266 |
| prometheus-server | the account's bucket | 1 | 38 | 38 | 66 | 2 |
| quote | the account's bucket | 1 | 38 | 38 | 66 | 2 |
| recommendation | the account's bucket | 1 | 3578 | 1001 | 66 | 66 |
| valkey-cart | the account's bucket | 1 | 640 | 640 | 66 | 42 |
| `*` (any other service) | the account's bucket | 1 | | 1001 | 66 | 66 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
