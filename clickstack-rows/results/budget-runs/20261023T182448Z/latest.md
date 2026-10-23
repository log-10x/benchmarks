# Rows run: 2026-10-23T18:24:48.000Z

Rows written: 31k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 87k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 15k pass lines an hour against 31k rows the meter puts on it, so each statement's rate is scaled by 2.08. The table holds 58k active rows.
- The Receiver's statements send 116k lines an hour; 29k an hour fits the rate, so each statement keeps up to 1161 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 4950 lines an hour whatever the limits; the rate holds down to that floor.
- The meter read above the rate last hour; the limits below hold the next hour at the rate, and each node's totals bind inside every window.
- Warning: The Receiver's counters read 15k pass lines an hour against 31k rows on the meter; rates are scaled by 2.08, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 4288 | 2572 | 77 | 171 |
| cart | the account's bucket | 1 | 10k | 2322 | 77 | 154 |
| fluentd-10x | the account's bucket | 1 | 613 | 613 | 77 | 40 |
| frontend | the account's bucket | 1 | 1175 | 1161 | 77 | 77 |
| grafana | the account's bucket | 1 | 32k | 1599 | 77 | 106 |
| inventory | the account's bucket | 1 | 6425 | 1161 | 77 | 77 |
| kafka | the account's bucket | 1 | 14k | 14k | 77 | 912 |
| opensearch | the account's bucket | 1 | 113 | 113 | 77 | 7 |
| opentelemetry-collector | the account's bucket | 1 | 45k | 4644 | 77 | 309 |
| prometheus-server | the account's bucket | 1 | 50 | 50 | 77 | 3 |
| recommendation | the account's bucket | 1 | 1788 | 1161 | 77 | 77 |
| valkey-cart | the account's bucket | 1 | 313 | 313 | 77 | 20 |
| `*` (any other service) | the account's bucket | 1 | | 1161 | 77 | 77 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
