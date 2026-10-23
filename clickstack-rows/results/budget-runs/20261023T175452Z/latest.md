# Rows run: 2026-10-23T17:54:52.000Z

Rows written: 31k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 31k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 12k pass lines an hour against 31k rows the meter puts on it, so each statement's rate is scaled by 2.57. The table holds 43k active rows.
- The Receiver's statements send 60k lines an hour; 29k an hour fits the rate, so each statement keeps up to 2168 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4004 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 12k pass lines an hour against 31k rows on the meter; rates are scaled by 2.57, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 2832 | 2832 | 144 | 188 |
| cart | the account's bucket | 1 | 8357 | 4335 | 144 | 289 |
| fluentd-10x | the account's bucket | 1 | 462 | 462 | 144 | 30 |
| frontend | the account's bucket | 1 | 1016 | 1016 | 144 | 67 |
| grafana | the account's bucket | 1 | 339 | 339 | 144 | 22 |
| kafka | the account's bucket | 1 | 11k | 11k | 144 | 734 |
| kube-proxy | the account's bucket | 1 | 46 | 46 | 144 | 3 |
| opensearch | the account's bucket | 1 | 46 | 46 | 144 | 3 |
| opentelemetry-collector | the account's bucket | 1 | 35k | 7934 | 144 | 528 |
| prometheus-server | the account's bucket | 1 | 62 | 62 | 144 | 4 |
| recommendation | the account's bucket | 1 | 1016 | 1016 | 144 | 67 |
| valkey-cart | the account's bucket | 1 | 292 | 292 | 144 | 19 |
| `*` (any other service) | the account's bucket | 1 | | 739 | 144 | 49 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
