# Rows run: 2026-10-25T02:32:33.000Z

Rows written: 43k of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 30k an hour, with 13k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 43k pass lines an hour against 43k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 29k active rows.
- The Receiver's statements send 43k lines an hour; 30k an hour fits the rate, so each statement keeps up to 3373 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4650 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 1632 | 1632 | 224 | 108 |
| cart | the account's bucket | 1 | 5574 | 5574 | 224 | 371 |
| fluentd-10x | the account's bucket | 1 | 336 | 336 | 224 | 22 |
| frontend | the account's bucket | 1 | 1416 | 1416 | 224 | 94 |
| grafana | the account's bucket | 1 | 240 | 240 | 224 | 16 |
| kafka | the account's bucket | 1 | 7698 | 7698 | 224 | 513 |
| kube-proxy | the account's bucket | 1 | 828 | 828 | 224 | 55 |
| opensearch | the account's bucket | 1 | 78 | 78 | 224 | 5 |
| opentelemetry-collector | the account's bucket | 1 | 24k | 11k | 224 | 742 |
| prometheus-server | the account's bucket | 1 | 30 | 30 | 224 | 2 |
| recommendation | the account's bucket | 1 | 984 | 984 | 224 | 65 |
| valkey-cart | the account's bucket | 1 | 150 | 150 | 224 | 10 |
| `*` (any other service) | the account's bucket | 1 | | 906 | 224 | 60 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
