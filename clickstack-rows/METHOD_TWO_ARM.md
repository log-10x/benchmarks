# ClickHouse two-arm run, method (written before the run, 2026-10-24 20:30 UTC)

Question: under a 2.5x step-up, does the rows run hold rows written at R where a collector rule by service and severity does not? The gaps run compared the two at one load (2.7 s against 8.1 s of insert plus merge CPU); no run compared them under growth.

## Arms, one ClickStack 2.38.0 node, same capture, same pace, the regulator bound in force (1.1.150 image)
- **A, the rows run:** clickstack-rows rig as rerun on 10-24 (results-sample-bound), on the ghcr.io/log-10x/edge-10x:1.1.150 image (no overlay), rows_per_hour R from the dry run, a run every 10 minutes.
- **B, the collector rule:** the same lines through the routing collector alone: the two chattiest services' INFO and DEBUG lines to the bucket (the gap6 policy), the rest to otel_logs. Fixed at the start. No Receiver.
Both arms write to their own table (`otel_logs` and `otel_logs_rule`) on the same node, so `system.part_log` meters each.

## Load
As in the rows run: 14 lines a second, stepped to 35 (2.5x) over the growth phase, held, then drained. Both arms receive every line.

## Meter
`system.part_log` NewPart rows per table per 10-minute window; insert plus merge CPU seconds per table per window from `system.query_log` and `system.part_log` ProfileEvents (whole-node figures labelled noisy); rows in the bucket per arm.

## Criteria
1. Arm A's rows per 10-minute window stay at or under 1.10 R/6 from the first growth step to the end of the hold (the 4-minute test of the rows run also reported).
2. Arm B's rows per 10-minute window rise above 1.5x its pre-step level during the hold.
3. CPU: arm A's insert plus merge CPU seconds per window after the step at or under 1.10 of its pre-step level; arm B's above 1.5x. Reported with the noise caveat the gaps run states.
If B also holds, the run reports "no differentiator".

## Projection, reported, not scored
ClickHouse Cloud compute: $0.2985 per 8 GiB unit-hour (Scale), units set by the autoscaler on utilisation (scale-down under 37.5% CPU). Saving = W x R where W is the buyer's write share of CPU from its own query_log; stated as an inequality, not a bill.

## Not claimed
A measured ClickHouse Cloud bill; the autoscaler's step; 300 nodes.
