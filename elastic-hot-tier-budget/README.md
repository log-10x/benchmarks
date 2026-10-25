# Elastic hot-tier budget

One benchmark in the [log10x benchmarks](../) repository. It asks whether log10x-mcp's hourly hot-tier run, driving the Receiver, holds an Elasticsearch hot tier under a size S while load grows 2.5 times, as the hot node's own stats count it.

**Result: holds at steady state, not under fast growth.** Two runs. The first held the mean but not the bound; the second, with every time constant divided by 6, held hot at 0.97 to 0.98 of S under steady load and overshot to 1.23 S during a 2.5x step-up compressed into an hour. Both fail the pre-registered bound on the hot store. Results of the first run in `results/`, of the second in `results-r2/` (section at the end). A third run put a native reroute by service beside the hold under one 2.5x step (`results-two-arm/`, last section): the hold failed its bound again, peaking at 1.43 S, and the reroute tracked load, rising to 1.72 times its level before the step.

Self-managed Elasticsearch 9.5.5 (one hot node, one frozen node, filesystem snapshot repository, trial licence), engine `log10x/edge-10x:1.1.147`, log10x-mcp branch `feat/elastic-hot-tier-budget` at 6af0226, the published OpenTelemetry demo sample replayed, 2026-10-22 19:59 to 2026-10-23 09:59 UTC. `results/` holds the timeline, every hourly run's report and files, the cluster readings and slim captures (no log text).

| | Criterion | Result |
|---|---|---|
| 1 | Every applied hourly run exits 0 and commits; once the size binds, its projection is at or under S | **Pass.** 13 applied runs, all exit 0, each projecting about 45 MB against S = 44.8 MB. |
| 2 | Run hours 7 to 13: hot store at or under 1.10 S at every reading, mean at or under S | **Fail.** Mean 0.998 S over 36 readings; 6 readings above 1.10 S, peak 1.17 S at 05:19 UTC, during the step-up. |
| 3 | Every rolled tier_down index mounted on frozen at 0 bytes | **Pass.** 38 of 38. |
| 4 | Hash queries on frozen equal the local count, ten largest moved statements | **Pass.** Exact, from 170,470 down to 10,498. |
| 5 | Every line received comes back, every returned record is in Elasticsearch | **Pass.** 1,041,196 lines in and back; 162,451 kept and 672,357 moved records, each equal to the cluster's count. |
| 6 | Storm: error lines kept per 4-minute window at most limit plus 50 | **Pass.** Scored on the regulator's own windows (every 240 seconds from its first regulated line): 55 a window (the 5-line sample plus 50) in each full window; the 146 of the first minute fall in two windows either side of 05:00:01. |

## The hourly table

S = 44.8 MB, set at run hour 1 as 0.7 of where the run's own dry run said hot would settle with nothing held (64 MB). Hot store is the hot node's `indices.store.size_in_bytes`; the other two columns are `_cat/indices` store for the indices not yet mounted.

| UTC | Run hour | Load | Hot store (node stats) | of S | Kept stream on hot | Tier_down waiting on hot |
|---|---:|---|---:|---:|---:|---:|
| 19:59 | 0 | 2x | 0.0 MB | 0.00 | 0.0 MB | 0.0 MB |
| 20:59 | 1 | 2x | 11.0 MB | 0.25 | 10.9 MB | 0.0 MB |
| 21:59 | 2 | 2x | 22.4 MB | 0.50 | 14.5 MB | 7.6 MB |
| 22:59 | 3 | 2x | 24.0 MB | 0.54 | 17.2 MB | 6.4 MB |
| 23:59 | 4 | 2x | 29.0 MB | 0.65 | 23.2 MB | 5.2 MB |
| 00:59 | 5 | 2x | 37.1 MB | 0.83 | 31.2 MB | 5.1 MB |
| 01:59 | 6 | 2x | 39.6 MB | 0.88 | 34.2 MB | 4.8 MB |
| 02:59 | 7 | 2.75x | 33.8 MB | 0.76 | 28.1 MB | 4.9 MB |
| 03:59 | 8 | 3.5x | 39.7 MB | 0.89 | 31.6 MB | 7.2 MB |
| 04:59 | 9 | 4.25x | 45.4 MB | 1.01 | 29.8 MB | 14.2 MB |
| 05:59 | 10 | 5x | 50.6 MB | 1.13 | 30.9 MB | 18.4 MB |
| 06:59 | 11 | 5x | 50.1 MB | 1.12 | 26.9 MB | 22.1 MB |
| 07:59 | 12 | 5x | 47.2 MB | 1.05 | 25.1 MB | 20.7 MB |
| 08:59 | 13 | stopped | 44.8 MB | 1.00 | 22.4 MB | 20.8 MB |

## Why the bound failed

- **The always-pass floor.** The Receiver passes the first 5 lines of every statement in every window on every node, and 50 error lines over a limit. From run hour 9 the run allowed nothing more on hot, yet 1.8 to 3.2 MB an hour stayed there; 59 to 74% of those lines were the sample, across about 2,300 statements.
- **Moved lines waiting to mount.** A tier_down index rolls every 15 minutes here and mounts about 40 minutes later, so up to 22 MB of moved lines sat on hot during the growth, about half of S. Hot here keeps a kept line 6 hours; with retention of days the same hour of moved lines is about 1% of hot.

## The rig

`rig/`: two Elasticsearch nodes and Fluent Bit (`compose.yaml`), the Receiver rendered by log10x-mcp with `elasticHotTier` and a policy branch (`gen-receiver-values.mjs`), the MCP's frozen-tier recipe then the time-scaled policies (`es-setup.mjs`: kept lines 6 hours on hot, tier_down rollover 15 minutes), `policy.yaml` from `emitPolicyYaml` (`gen-policy.mjs`), `tenx-recur` every hour (`budget-run.sh`), the replay (`make-replay.py`, `forward_send.py`), the phases (`phases.sh`) and the meter (`meter.py`). The Receiver pulled its files from `log-10x/config` branch `test/elastic-hot-tier-policy`.

## Not shown

A bill; Cloud Hosted; production retention lengths; a hot tier held under growth.

## The rerun (`results-r2/`), 2026-10-23 11:25 to 15:55 UTC

log10x-mcp `feat/elastic-hot-tier-budget` at 0b45d4a. Every time constant divided by 6: a run every 10 minutes, kept lines 2 hours on hot (10-minute rollover, frozen 110 minutes later), tier_down rollover 3 minutes, ILM poll 100 seconds (changed only because everything else was scaled), meter every 100 seconds, growth in four 20-minute steps from 56 to 140 lines a second. No raw capture: lines in are Fluent Bit's input counter, and the local copies of returned records keep only container, times, hash, route, `utf8Size`, level, name and line count (`results-r2/captures/`). S = 56.7 MB, 0.7 of where the dry run said hot would settle with nothing held (81 MB).

| | Criterion | Result |
|---|---|---|
| 1 | Runs exit 0 and commit; projection at or under S, or the floor reported | **Pass.** 26 of 26 applied runs; projections 51 to 57 MB; the always-pass floor 79 to 268 MB a day, inside what fit at every run. |
| 2 | Run minutes 130 to 250: hot at or under 1.10 S every reading, mean at or under S | **Fail.** Mean 1.095 S, peak 1.23 S, 30 of 72 readings over 1.10 S. Before growth (minutes 111 to 131) 0.97 to 0.98 S. |
| 3 | Rolled tier_down indices mounted at 0 bytes | **Pass.** 73 of 73. |
| 4 | Hash queries on frozen equal local, ten largest moved statements | **Pass.** 10 of 10. |
| 5 | Delivery | **Every returned record is in Elasticsearch. Lines in against lines back: 1,301,174 in, 1,300,992 back; 171 of the 182 not returned are the sample's blank lines, 11 are unaccounted for.** |
| 6 | Storm kept per window at most limit + 50 | **Pass.** On the regulator's own windows (rolling at 14:12:14 and 14:16:14): 121 and 165 kept, each within its limit plus 50 and the 5-line sample; the rest of the second window kept none, as its allowance was spent, and the storm ended before the next one. |

**Why growth overshoots.** The run steers what new lines do; it cannot move lines already on hot. When load rose 2.5 times within an hour, the moved lines waiting to mount grew from 3 MB to 10 to 19 MB at once (the run's own estimate of that slice was right), while the kept lines already on hot leave only as their indices age out, over 2 hours here. The run tightened its allowance to 86 to 90% and projected 51 to 55 MB, but hot stayed above 1.1 S until the window closed. Relative to the time a line stays on hot, this step-up was about 50 times faster than a year of 2.5x growth against days of retention, but the run does not show what a slower ramp does.

## Two-arm run, 2026-10-24

The question, from the method written before the run (`TWO_ARM_METHOD.md`, 2026-10-24): under a 2.5x step-up in load, does the Receiver's hourly hold keep the hot store at S where a native reroute by service does not? Run 2026-10-24 21:12 to 2026-10-25 01:26 UTC, results in `results-two-arm/`.

**Result: the hold fails its bound and the reroute tracks load; delivery is exact in both arms.** Arm A peaked at 1.43 S in the scored window. Arm B rose to 1.72 times its level before the step. Within the hour of the hold, arm B's peak hot store (1.36 S) stayed below arm A's (1.43 S). At the end of the hold arm A was back at 1.02 S, while arm B was at 1.30 S and still rising.

**Arm A, the hold**, is the `results-r2` rig with every time constant divided by 6. `tenx-recur` from log10x-mcp main at d6fa2b1 (1.30.84, where the `results-r2` branch merged) ran every 10 minutes against the engine `ghcr.io/log-10x/edge-10x:1.1.150` (sha256:3e755bbc14780a27e643e09b76dfd7ec9616cab67833f70daf9420eff646d350). Kept lines stay 2 hours on hot (10-minute rollover, frozen 110 minutes later). The tier_down index rolls every 10 minutes (the recipe's hour divided by 6) and goes frozen 1 minute after rollover. The ILM poll is 100 seconds. S = 63 MB, 0.7 of the 90 MB where the dry run at 0:10 said hot would settle with nothing held.

**Arm B, the native reroute**, is a second Elasticsearch 9.5.5 cluster with the same image and node sizes (one hot node with a 1 GB heap, one frozen node) and its own snapshot repository. Fluent Bit copies every line before it reaches the Receiver and routes the copy with a rule fixed before the run. The services that made the top half of bytes in the feed's first 20 minutes, at the run's pace, go to `native-overflow`, which carries arm A's tier_down ILM policy copied from cluster A. Every other service goes to `native-app`, which carries arm A's kept policy. One service made the top half: `opentelemetry-collector`, with 68.9% of the bytes (`arm-b-rule.json`). Arm B has no Receiver. Its index templates are arm A's, with the stream names changed.

Each arm has its own hot node because the hot-tier run counts every index on the hot nodes and subtracts whatever is not the Receiver's from S. On arm A's node, arm B's streams would have taken arm A's allowance. The method's "one Elasticsearch 9.5.5 node" is therefore read as one hot node per arm.

**Load.** The feed is the `results-r2` feed (`replay/source.jsonl`, sha256 24e02233a797…), sent by one sender for the whole run that numbers every line (`seq`). The start is 56 lines a second. S binds at the first meter reading at or above 0.95 S after the first applied run, or at 2:10 (R after that run), whichever comes first. Here it bound at 2:10, 23:22:19 UTC, with arm A at 0.93 S. Load stayed steady for 40 minutes, then took one step to 140 lines a second at 00:02:22, held for 60 minutes. The feed stopped at 01:02:28 after 1,070,359 lines, followed by a 20-minute drain. The run had no new service and no storm, since the method's load names neither.

**Meter.** Every 100 seconds the meter read both clusters: the hot node's index store, each stream's store on hot and its frozen mounts (`_cat/indices`), and ILM explain. Each reading first refreshes both arms' indices on hot. Arm B's indices take no searches, and a search-idle shard writes nothing to its store until a refresh. In the smoke, before the refresh was added, arm B showed 6,223 of 9,236 indexed documents. Each frozen node's cache is 128 MB (512 MB in `results-r2`), to stay inside the disk budget; the cache serves searches on frozen and nothing else.

| | Criterion | Result |
|---|---|---|
| 1 | Arm A's hot store at or under 1.10 S at every reading from 20 minutes after the step to the end of the hold | **Fail.** 13 of 24 readings (00:23:55 to 01:02:15) over 1.10 S. Peak 1.43 S (90.0 MB at 00:57), mean 1.15 S. |
| 2 | Arm B's hot store above 1.5 times its pre-step level during the hold (pre-step level: the mean of its readings in the 20 minutes before the step); "no differentiator" if every reading from 20 minutes after the step stays within 1.10 times | **Pass.** Pre-step 50.0 MB. Above 1.5 times from 00:45:35, peak 85.9 MB (1.72 times) at 01:00. Above 1.10 times through the scored window, so the run shows a differentiator. |
| 3 | Every line in each arm on hot or frozen, by sequence number | **Pass.** Arm B: 1,070,359 documents, seq 1 to 1,070,359, none missing or repeated, each in the stream its service names. Arm A: all 1,070,203 non-blank lines are in the 848,190 returned records. Each record carries its first line's seq and holds exactly the non-blank lines from that seq to the next record's (`_lines`). The other 156 lines are blank. |

The hot store per stream around the step, from the meter (`score.json`, `meter.jsonl.gz`):

| UTC | Minutes from step | Arm A hot node | A kept (`tenx-app`) | A tier_down waiting | Arm B hot node | B normal (`native-app`) | B overflow (`native-overflow`) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 20 minutes before, mean | | 59.9 MB (0.95 S) | 55.4 MB | 3.7 MB | 50.0 MB | 46.2 MB | 2.9 MB |
| 00:02 | 0 | 60.0 MB (0.95 S) | 57.1 MB | 2.0 MB | 51.0 MB | 46.7 MB | 3.4 MB |
| 00:23 | +22 | 78.9 MB (1.25 S) | 55.3 MB | 22.5 MB | 69.3 MB | 60.3 MB | 7.9 MB |
| 00:43 | +42 | 75.0 MB (1.19 S) | 50.5 MB | 23.4 MB | 73.5 MB | 66.0 MB | 6.3 MB |
| 00:57, arm A's peak | +55 | 90.0 MB (1.43 S) | 48.3 MB | 40.3 MB | 82.1 MB | 73.4 MB | 7.4 MB |
| 01:00, arm B's peak | +58 | 62.1 MB (0.99 S) | 49.3 MB | 11.5 MB | 85.9 MB | 76.3 MB | 8.4 MB |
| 01:02, end of hold | +60 | 64.2 MB (1.02 S) | 48.7 MB | 14.2 MB | 81.8 MB | 77.3 MB | 3.3 MB |

**Why arm A overshoots.** The kept stream was held: 55.4 MB before the step and 46.0 to 57.7 MB during the hold. The overshoot comes from moved lines waiting to mount, which rose from 3.7 MB before the step to as much as 40.3 MB. Each tier_down index takes 10 minutes of moved lines and then waits about 7 minutes more for its mount (the run's own measure, 0.3 hours). At 2.5 times the load that is 20 to 25 MB. The 1.43 S peak is a single index, `tenx-tierdown-000019`. It read 15.3 MB at its last reading before rollover and 34.4 MB for the next three readings, until the searchable_snapshot action's force-merge step; after that it read 16.4 MB.

**Why arm B rises.** Arm B's normal stream keeps every line of the services outside the top half for 2 hours, so it grows as lines at the new rate replace those at the old: 46.2 MB before the step and 77.3 MB at the end of the hold. The hold ended before those 2 hours had turned over. The overflow stream holds one 10-minute index plus its mount wait: 2.9 MB before the step and 2.1 to 9.7 MB during the hold.

**Frozen.** Every rolled index in both arms mounted on frozen at 0 bytes local. Arm A mounted 20 tier_down indices and 11 kept indices; arm B mounted 20 overflow and 11 normal. The snapshot repositories hold 181 MB for arm A and 108 MB for arm B; arm A's documents carry the Receiver's fields.

**Grouping across containers.** The Receiver groups multi-line events in the order lines arrive, so 71 of the 848,190 returned records hold lines from more than one container. For example, kafka's four startup lines at seq 2751 to 2754 joined the jaeger record at seq 2750, which is filed under jaeger. Every such line is still delivered.

**Projection (Elastic's published arithmetic applied to the measured hot store per arm, not a measured bill).** Hot cost per TB of hot store per month = 1,000 GB / (disk-to-RAM ratio x 0.85 usable) GB of RAM x $ per GB RAM-hour x 730 hours x 2 zones. The rates come from Elastic's Cloud Hosted price table for AWS us-east-1 at Enterprise (https://cloud.elastic.co/deployment-pricing-table). The ratios come from Elastic's AWS default instance page (https://www.elastic.co/docs/reference/cloud/cloud-hosted/aws-default), which marks them as estimations. `aws.es.datahot.i8g` at $0.0793 and 27:1 gives $5,045 per TB-month; `aws.es.datahot.i3en` at $0.0590 and 74:1 gives $1,369. With S set at 1 TB of hot store, the measured ratios price as follows:

| | Hot store | i8g, per month | i3en, per month |
|---|---:|---:|---:|
| Arm A, 20 minutes before the step | 0.95 S | $4,799 | $1,303 |
| Arm A, peak in the hold | 1.43 S | $7,207 | $1,956 |
| Arm A, end of the hold | 1.02 S | $5,144 | $1,396 |
| Arm B, 20 minutes before the step | 0.79 S | $4,008 | $1,088 |
| Arm B, peak in the hold | 1.36 S | $6,875 | $1,866 |
| Arm B, end of the hold | 1.30 S | $6,552 | $1,779 |

What moves to frozen sits in the snapshot repository at $0.033 per GB-month. Elastic's node sizes step, so a difference in hot store saves money only when it crosses a node step. At full-size nodes a step is one node, about 1.5 TB of hot store on a 27:1 instance. A hot tier is sized for its peak, and in this hour arm A's peak was the higher of the two.

**Smoke**, 2026-10-24 20:43 to 21:09 UTC, every phase at a tenth of its length (`results-two-arm-smoke/`). Both arms received every line: 101,241 fed. Arm B held 101,241 documents; arm A held 101,215 non-blank lines in 78,852 records, exact by the same check. Both meters read, and each arm mounted a frozen index. The smoke ran the rig before it was committed; the meter's refresh and the arrival-order delivery check were added from what it showed.

**Rig additions.** `compose.arm-b.yaml` (arm B's cluster), `es-setup-b.mjs` (arm A's ILM policies, poll and templates copied to arm B), `top-half.py` and `render-fb-two-arm.py` with `fluent-bit-two-arm/` (the fixed rule), `forward_send.py paced` and `run.sh feed` (one numbered sender, speed changed in place), `meter.py` with `ES_URL_B` (both clusters, per stream, refresh first), `dump-seq.py` and `score-two-arm.py` (delivery and the three criteria), `phases-two-arm.sh` (the schedule), and `record-build.py` (`build.json`: every image digest and the commits).

Not shown: a measured Elastic Cloud bill, 300 nodes, compact, autoscaling, or a hold longer than the hot retention.
