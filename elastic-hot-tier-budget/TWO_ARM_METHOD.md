# Elastic two-arm run, method (written before the run, 2026-10-24 20:30 UTC)

Question: under a 2.5x step-up in load, does the Receiver's hourly hold keep the hot store at S where a native reroute by service does not? Every published run had one arm; the testers compared the two at one load.

## Arms, one Elasticsearch 9.5.5 node, same capture, same pace
- **A, the hold:** the elastic-hot-tier-budget rig as run on 10-23 (results-r2), time constants divided by 6: `reduction.hot_tier_gb` S, the hourly run every 10 minutes rewriting per-statement byte limits, tier_down index rolling hourly with the frozen phase one minute after rollover.
- **B, the native reroute:** the same lines into a second pair of data streams through a collector/forwarder rule fixed at the start: the services that make up the top half of bytes in the first 20 minutes go to an overflow stream with the same ILM as A's tier-down index (rollover 1h, frozen 1m after); the rest to a stream with the capture's normal retention. The list does not change during the run. No Receiver in this arm.

## Load
The replay as in results-r2: steady for 40 minutes after S binds, then a 2.5x step-up held for 60 minutes, then drain. Both arms receive every line.

## Meter
Hot store bytes per data stream (`_cat/indices` on hot, `_nodes/stats/fs` for the node), every 100 seconds; frozen mounts per stream; delivery by sequence number per arm.

## Criteria
1. Arm A's hot store stays at or under 1.10 S in every reading from 20 minutes after the step to the end of the hold.
2. Arm B's hot store rises above 1.5x its pre-step level during the hold (it tracks load). If B also holds within 1.10 of its pre-step level, the run reports "no differentiator" and no Cloud deployment is bought.
3. Delivery: every line in each arm is on hot or frozen.

## Projection, reported, not scored
Peak hot bytes per arm -> hot tier RAM via Elastic's storage-to-RAM ratio for the instance type -> hourly rate at Enterprise, from Elastic's calculator (three figures from Elastic's price table). Node sizes step at 1, 2, 4, 8, 16, 32, 64 GB; S sits on a step. Stated as Elastic's published arithmetic, not a measured bill.

## Not claimed
A measured Elastic Cloud bill; 300 nodes; compact (no 9.x plugin); autoscaling behaviour.
