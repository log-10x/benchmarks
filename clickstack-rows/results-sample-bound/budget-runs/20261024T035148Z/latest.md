# Rows run: 2026-10-24T03:51:48.000Z

Rows written: 32k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 16k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 20k pass lines an hour against 32k rows the meter puts on it, so each statement's rate is scaled by 1.60. The table holds 28k active rows.
- The Receiver's statements send 45k lines an hour; 29k an hour fits the rate, so each statement keeps up to 3262 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3645 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 20k pass lines an hour against 32k rows on the meter; rates are scaled by 1.60, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 2060 | 2060 | 217 | 137 |
| cart | the account's bucket | 1 | 6160 | 5524 | 217 | 368 |
| fluentd-10x | the account's bucket | 1 | 366 | 366 | 217 | 24 |
| frontend | the account's bucket | 1 | 722 | 722 | 217 | 48 |
| grafana | the account's bucket | 1 | 250 | 250 | 217 | 16 |
| kafka | the account's bucket | 1 | 8296 | 8296 | 217 | 553 |
| opensearch | the account's bucket | 1 | 38 | 38 | 217 | 2 |
| opentelemetry-collector | the account's bucket | 1 | 26k | 11k | 217 | 725 |
| recommendation | the account's bucket | 1 | 1068 | 1068 | 217 | 71 |
| valkey-cart | the account's bucket | 1 | 192 | 192 | 217 | 12 |
| `*` (any other service) | the account's bucket | 1 | | 895 | 217 | 59 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
