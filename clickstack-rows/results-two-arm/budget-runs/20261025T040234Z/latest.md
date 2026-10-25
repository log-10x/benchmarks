# Rows run: 2026-10-25T04:02:34.000Z

Rows written: 30k of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 30k an hour, with 87k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 30k pass lines an hour against 30k rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 74k active rows.
- The Receiver's statements send 117k lines an hour; 30k an hour fits the rate, so each statement keeps up to 1036 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 6048 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 4236 | 2385 | 69 | 158 |
| cart | the account's bucket | 1 | 13k | 2937 | 69 | 195 |
| fluentd-10x | the account's bucket | 1 | 792 | 792 | 69 | 52 |
| frontend | the account's bucket | 1 | 2508 | 1984 | 69 | 132 |
| grafana | the account's bucket | 1 | 11k | 1606 | 69 | 107 |
| inventory | the account's bucket | 1 | 7206 | 1036 | 69 | 69 |
| kafka | the account's bucket | 1 | 18k | 14k | 69 | 901 |
| kube-proxy | the account's bucket | 1 | 36 | 36 | 69 | 2 |
| opensearch | the account's bucket | 1 | 144 | 144 | 69 | 9 |
| opentelemetry-collector | the account's bucket | 1 | 57k | 4146 | 69 | 276 |
| prometheus-server | the account's bucket | 1 | 84 | 84 | 69 | 5 |
| recommendation | the account's bucket | 1 | 2430 | 1036 | 69 | 69 |
| valkey-cart | the account's bucket | 1 | 390 | 390 | 69 | 26 |
| `*` (any other service) | the account's bucket | 1 | | 1036 | 69 | 69 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
