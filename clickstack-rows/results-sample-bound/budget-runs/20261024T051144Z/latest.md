# Rows run: 2026-10-24T05:11:44.000Z

Rows written: 28k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 68k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 22k pass lines an hour against 28k rows the meter puts on it, so each statement's rate is scaled by 1.28. The table holds 68k active rows.
- The Receiver's statements send 98k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1143 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4208 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 4196 | 2540 | 76 | 169 |
| cart | the account's bucket | 1 | 12k | 2286 | 76 | 152 |
| fluentd-10x | the account's bucket | 1 | 736 | 736 | 76 | 49 |
| frontend | the account's bucket | 1 | 1419 | 1143 | 76 | 76 |
| grafana | the account's bucket | 1 | 514 | 514 | 76 | 34 |
| inventory | the account's bucket | 1 | 6444 | 1143 | 76 | 76 |
| kafka | the account's bucket | 1 | 17k | 15k | 76 | 985 |
| kube-proxy | the account's bucket | 1 | 23 | 23 | 76 | 1 |
| opensearch | the account's bucket | 1 | 115 | 115 | 76 | 7 |
| opentelemetry-collector | the account's bucket | 1 | 53k | 4573 | 76 | 304 |
| prometheus-server | the account's bucket | 1 | 54 | 54 | 76 | 3 |
| recommendation | the account's bucket | 1 | 2232 | 1143 | 76 | 76 |
| valkey-cart | the account's bucket | 1 | 345 | 345 | 76 | 23 |
| `*` (any other service) | the account's bucket | 1 | | 1143 | 76 | 76 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
