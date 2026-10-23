# Rows run: 2026-10-23T17:24:48.000Z

Rows written: 36k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 23k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 12k pass lines an hour against 36k rows the meter puts on it, so each statement's rate is scaled by 2.98. The table holds 29k active rows.
- The Receiver's statements send 52k lines an hour; 29k an hour fits the rate, so each statement keeps up to 2654 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3785 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 12k pass lines an hour against 36k rows on the meter; rates are scaled by 2.98, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 2285 | 2285 | 176 | 152 |
| cart | the account's bucket | 1 | 6784 | 5100 | 176 | 340 |
| fluentd-10x | the account's bucket | 1 | 428 | 428 | 176 | 28 |
| frontend | the account's bucket | 1 | 696 | 696 | 176 | 46 |
| grafana | the account's bucket | 1 | 304 | 304 | 176 | 20 |
| kafka | the account's bucket | 1 | 9712 | 9712 | 176 | 647 |
| opensearch | the account's bucket | 1 | 89 | 89 | 176 | 5 |
| opentelemetry-collector | the account's bucket | 1 | 30k | 9230 | 176 | 615 |
| prometheus-server | the account's bucket | 1 | 18 | 18 | 176 | 1 |
| recommendation | the account's bucket | 1 | 1268 | 1268 | 176 | 84 |
| valkey-cart | the account's bucket | 1 | 268 | 268 | 176 | 17 |
| `*` (any other service) | the account's bucket | 1 | | 696 | 176 | 46 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
