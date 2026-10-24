# Rows run: 2026-10-24T04:11:44.000Z

Rows written: 31k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 22k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 23k pass lines an hour against 31k rows the meter puts on it, so each statement's rate is scaled by 1.31. The table holds 38k active rows.
- The Receiver's statements send 51k lines an hour; 29k an hour fits the rate, so each statement keeps up to 2794 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3714 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 2264 | 2264 | 186 | 150 |
| cart | the account's bucket | 1 | 6582 | 5097 | 186 | 339 |
| fluentd-10x | the account's bucket | 1 | 415 | 415 | 186 | 27 |
| frontend | the account's bucket | 1 | 705 | 705 | 186 | 47 |
| grafana | the account's bucket | 1 | 290 | 290 | 186 | 19 |
| kafka | the account's bucket | 1 | 9575 | 9575 | 186 | 638 |
| opensearch | the account's bucket | 1 | 78 | 78 | 186 | 5 |
| opentelemetry-collector | the account's bucket | 1 | 30k | 9627 | 186 | 641 |
| prometheus-server | the account's bucket | 1 | 31 | 31 | 186 | 2 |
| recommendation | the account's bucket | 1 | 1120 | 1120 | 186 | 74 |
| valkey-cart | the account's bucket | 1 | 196 | 196 | 186 | 13 |
| `*` (any other service) | the account's bucket | 1 | | 705 | 186 | 47 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
