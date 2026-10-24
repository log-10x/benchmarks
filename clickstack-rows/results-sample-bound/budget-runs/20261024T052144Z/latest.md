# Rows run: 2026-10-24T05:21:44.000Z

Rows written: 31k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 83k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 24k pass lines an hour against 31k rows the meter puts on it, so each statement's rate is scaled by 1.28. The table holds 73k active rows.
- The Receiver's statements send 112k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1117 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4458 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 5085 | 2572 | 74 | 171 |
| cart | the account's bucket | 1 | 13k | 2235 | 74 | 148 |
| fluentd-10x | the account's bucket | 1 | 836 | 836 | 74 | 55 |
| frontend | the account's bucket | 1 | 1580 | 1117 | 74 | 74 |
| grafana | the account's bucket | 1 | 598 | 598 | 74 | 39 |
| inventory | the account's bucket | 1 | 7370 | 1117 | 74 | 74 |
| kafka | the account's bucket | 1 | 19k | 15k | 74 | 968 |
| kube-proxy | the account's bucket | 1 | 46 | 46 | 74 | 3 |
| opensearch | the account's bucket | 1 | 169 | 169 | 74 | 11 |
| opentelemetry-collector | the account's bucket | 1 | 61k | 4469 | 74 | 297 |
| prometheus-server | the account's bucket | 1 | 176 | 176 | 74 | 11 |
| recommendation | the account's bucket | 1 | 2439 | 1117 | 74 | 74 |
| valkey-cart | the account's bucket | 1 | 422 | 422 | 74 | 28 |
| `*` (any other service) | the account's bucket | 1 | | 1117 | 74 | 74 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
