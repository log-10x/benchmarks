# Rows run: 2026-10-23T17:44:50.000Z

Rows written: 27k of 29k an hour last hour (29k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 29k an hour, with 19k an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 13k pass lines an hour against 27k rows the meter puts on it, so each statement's rate is scaled by 2.03. The table holds 38k active rows.
- The Receiver's statements send 48k lines an hour; 29k an hour fits the rate, so each statement keeps up to 3077 an hour and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 3720 lines an hour whatever the limits; the rate holds down to that floor.
- Warning: The Receiver's counters read 13k pass lines an hour against 27k rows on the meter; rates are scaled by 2.03, which assumes the counters miss lines evenly across statements.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| ad | the account's bucket | 1 | 2031 | 2031 | 205 | 135 |
| cart | the account's bucket | 1 | 6094 | 5182 | 205 | 345 |
| fluentd-10x | the account's bucket | 1 | 377 | 377 | 205 | 25 |
| frontend | the account's bucket | 1 | 705 | 705 | 205 | 47 |
| grafana | the account's bucket | 1 | 292 | 292 | 205 | 19 |
| kafka | the account's bucket | 1 | 8928 | 8928 | 205 | 595 |
| opensearch | the account's bucket | 1 | 73 | 73 | 205 | 4 |
| opentelemetry-collector | the account's bucket | 1 | 28k | 10k | 205 | 694 |
| prometheus-server | the account's bucket | 1 | 36 | 36 | 205 | 2 |
| recommendation | the account's bucket | 1 | 1168 | 1168 | 205 | 77 |
| valkey-cart | the account's bucket | 1 | 182 | 182 | 205 | 12 |
| `*` (any other service) | the account's bucket | 1 | | 705 | 205 | 47 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
