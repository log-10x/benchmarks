# Rows run: 2026-10-24T05:51:48.000Z

Rows written: 5070 of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 21k an hour, with 0 an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 5112 pass lines an hour against 5070 rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 83k active rows.
- The Receiver's statements send 21k lines an hour, under the 29k an hour that fits the rate; every statement keeps its lines, with room to grow 1.4 times.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 2784 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 774 | 1105 | 36 | 73 |
| cart | the account's bucket | 1 | 2364 | 3375 | 146 | 225 |
| fluentd-10x | the account's bucket | 1 | 162 | 231 | 15 | 15 |
| frontend | the account's bucket | 1 | 288 | 411 | 27 | 27 |
| grafana | the account's bucket | 1 | 108 | 154 | 7 | 10 |
| inventory | the account's bucket | 1 | 1350 | 1927 | 128 | 128 |
| kafka | the account's bucket | 1 | 3570 | 5097 | 30 | 339 |
| opensearch | the account's bucket | 1 | 24 | 34 | 1 | 2 |
| opentelemetry-collector | the account's bucket | 1 | 11k | 16k | 440 | 1084 |
| prometheus-server | the account's bucket | 1 | 12 | 17 | 1 | 1 |
| recommendation | the account's bucket | 1 | 456 | 651 | 43 | 43 |
| valkey-cart | the account's bucket | 1 | 90 | 128 | 1 | 8 |
| `*` (any other service) | the account's bucket | 1 | | 8807 | 587 | 587 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
