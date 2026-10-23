# Rows run: 2026-10-23T17:14:47.000Z

Rows written: 41k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 13k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 42k pass lines an hour against 41k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 24k active rows.
- The Receiver's statements send 42k lines an hour; 29k an hour fits the rate, so each statement keeps up to 3542 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3792 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 1680 | 1680 | 236 | 112 |
| cart | the account's bucket | 1 | 5256 | 5256 | 236 | 350 |
| fluentd-10x | the account's bucket | 1 | 336 | 336 | 236 | 22 |
| frontend | the account's bucket | 1 | 576 | 576 | 236 | 38 |
| grafana | the account's bucket | 1 | 240 | 240 | 236 | 16 |
| kafka | the account's bucket | 1 | 7644 | 7644 | 236 | 509 |
| kube-proxy | the account's bucket | 1 | 828 | 828 | 236 | 55 |
| opensearch | the account's bucket | 1 | 78 | 78 | 236 | 5 |
| opentelemetry-collector | the account's bucket | 1 | 24k | 12k | 236 | 775 |
| prometheus-server | the account's bucket | 1 | 30 | 30 | 236 | 2 |
| recommendation | the account's bucket | 1 | 942 | 942 | 236 | 62 |
| valkey-cart | the account's bucket | 1 | 150 | 150 | 236 | 10 |
| `*` (any other service) | the account's bucket | 1 | | 702 | 236 | 46 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
