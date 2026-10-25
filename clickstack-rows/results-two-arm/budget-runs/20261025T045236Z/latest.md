# Rows run: 2026-10-25T04:52:36.000Z

Rows written: 0 of 30k an hour last hour (30k rows an hour set in the policy; part_log on default.otel_logs); at these limits the table takes about 0 an hour, with 0 an hour of lines to the account's bucket.

- Outside the Receiver: 0 rows an hour (outside_rows_per_hour). The Receiver's counters read 0 pass lines an hour against 0 rows the meter puts on it, so each statement's rate is scaled by 1.00. The table holds 89k active rows.
- The Receiver's statements send 0 lines an hour, under the 30k an hour that fits the rate; every statement keeps its lines, with room to grow 2.0 times.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 0 lines an hour whatever the limits; the rate holds down to that floor.

| Service | Destination | Nodes | Sent an hour | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| `*` (any other service) | the account's bucket | 1 | | 30k | 2006 | 2006 |

Limits and totals are lines per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window. The meter is `system.part_log` NewPart rows on default.otel_logs, read by the event's own time.
