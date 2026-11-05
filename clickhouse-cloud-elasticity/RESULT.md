# ClickHouse Cloud: compute against rows written

A logs workload ran on one ClickHouse Cloud service under a fixed query load, in two arms that
differ only in the rows written. Arm A inserts every row. Arm B inserts only the rows the
engine's regulator kept: 65.3% of arm A's rows and 61.2% of its message bytes. The question is
how far the autoscaler's compute falls when the rows fall, above the smallest size, and how long
it takes to fall.

Every figure below names the file and field it was read from. A figure the run did not produce
is written "not measured".

## The finding

**The same cut gave a step down or no change, depending on the size the service started from.**

- **Starting at 4 units.** Arm A at 70,000 rows/s held 2 x 16 GiB (4 units), with the busiest
  replica at a median 0.455 of its CPU. Cutting to arm B's 65.3% of the rows dropped it below the
  autoscaler's 37.5% low watermark (0.340). The service stepped down to 2 x 12 GiB (3 units)
  4.20 h after the cut. Pair 3 repeated it with arm A held at 4 units by config: arm B at 0.337
  stepped down to 3 units, the new replicas booting 4.07 h after the cut. Pair 4 repeated it
  again at 0.351, booting 2.78 h after the cut.
- **Starting at 3 units.** Arm A at the same 70,000 rows/s also held 3 units for 90 min, at
  0.637. That is inside the 37.5% to 75% band, where the autoscaler takes no action. Arm B on
  3 units ran at 0.427 and 0.455, also inside the band, and did not step in its 4.5 h hold, or
  in the 10.25 h it ran in all while the run waited for SSO.
- **Why it depends on the start.** Arm A's load holds steady at both 3 and 4 units. Arm B's
  load holds steady only at 3. From a 3-unit start, the 34.7% cut in rows reads no change in
  compute.

| | Units | Ratio to arm A | Fall in compute / fall in rows (0.653) | Fall in compute / fall in bytes (0.612) |
|---|---|---|---|---|
| Pair 1, from a 4-unit start | 4.0 to 2.997 | 0.749 | 0.723 | 0.646 |
| Pair 2, from a 3-unit start | 3.0 to 3.0 | 1.0 | 0 | 0 |
| Pair 3, arm A pinned at 4 units by config | 4.0 to 3.0 | 0.750 | 0.721 | 0.644 |
| Pair 4, arm A pinned at 4 units by config | 4.0 to 3.0 | 0.750 | 0.721 | 0.644 |

Pair 1 is the only pair in which every size was the autoscaler's own choice, so it is reported
first. In pair 2, arm A's 3-unit size was where pair 1 left the service. In pairs 3 and 4, arm A's
size was set by config (`minReplicaMemoryGb` 16) and released to 8 at each arm B cut, so arm A's
size came from config and every step down was the autoscaler's own.

Dollars give the same ratio as units, read two ways:

- **usageCost computeCHC** (`results/raw/usage.jsonl`, 10-minute poll of
  `/organizations/{org}/usageCost`). It posts in 15-minute steps: 0.298 to 0.299 at 4 units, and
  0.223 to 0.224 at 3 units, in each of pairs 1, 3 and 4. That is $1.196/h against $0.896/h,
  ratio 0.749.
- **Unit-hours x $0.2993.** The rate is derived from the billing overview's Scale example
  (2 x 8 GiB at $436.95/month, 730 h); it is not a published per-unit rate. That gives $1.197/h
  against $0.898/h, ratio 0.750.

The other figures, each from a section below:

- **Scale-down lag.** The step was done 4.33, 4.21 and 2.91 h after the cut in pairs 1, 3 and 4;
  the new replicas booted 4.20, 4.07 and 2.78 h after it.
- **Write share W**, (insert + merge) / (insert + merge + select) cores, mean over replicas: 0.65
  to 0.67 in both arms. On the busiest replica 0.47 to 0.51 in arm A and 0.54 to 0.55 in arm B.
- **Memory.** About 2 GiB used per replica, of 12 to 16 GiB, in every arm.
- **Floor.** 2 units, $0.60/h at $0.2993. Both arms cost the floor below the load that lifts arm A
  off 2 units, which lies between 50,000 and 70,000 rows/s.
- **Credit.** $42.61 of the $300 credit spent, against the run's $200 cap. chce-elasticity was
  deleted at the end.

## Setup

- **Service.** `chce-elasticity`, AWS us-east-1, organization tier SCALE (usageCost
  `organizationTier`), ClickHouse 26.6, 2 replicas, vertical autoscaling configured 8 to 32 GiB
  per replica, idle after 5 minutes (`cloud/service.json`, `results/create-response.json`). One
  unit is 8 GiB and 2 vCPU. The API requires at least 2 replicas for the first service in a
  warehouse. The IP allow-list held the runner's /32, redacted to `<runner-ip>` in the committed
  files.
- **Feed.** The 215 MB OTel replay (197,430 lines, 171,807 records after multi-line folding),
  split once, locally, by engine `log10x/edge-10x:1.1.153` with `baselineMaxOverTotal` 50
  (`split/`, `results/split-count.json`, `results/rate-settings.txt`). It ran as four contiguous
  quarters on four engines side by side at 14 lines/s each. The regulator decides per node per
  4-minute window, so each node saw what one node at that pace would. Kept share by slice: 0.595,
  0.671, 0.674, 0.674. Every record came back 1.0 to 2.5 s after its line was written, with
  0 duplicate sequence numbers.
- **Staging.**
  - `bench.stage` holds all 171,807 rows with the kept flag. Kept rows are 112,205, a share of
    0.6531 (`results/stage.json`: `kept_share`). Bytes are 24,706,958 of 40,379,948 body bytes,
    0.612 (`kept_body_bytes`, `body_bytes`).
  - `bench.stage_b` holds the 112,205 kept rows only, so arm B reads only what it writes
    (`results/stage_b.json`). It matches the kept rows of `bench.stage` row for row
    (`results/stage_b-check.json`: 0 mismatched).
- **Inserts.** Native `INSERT ... SELECT` from the stage tables into the ClickStack `otel_logs`
  schema (`cloud/schema.sql`), with timestamps shifted to now. Four connections each run one
  insert every 2 s:
  - Arm A: 35,000 rows per insert, 70,000 rows/s.
  - Arm B: 22,858 rows per insert, 45,716 rows/s.
  - Every insert is logged with `written_rows` (`results/raw/load.jsonl`).
- **Query load.** Seven queries every 60 s in both arms (`cloud/queries.py`): a per-minute
  histogram, top services, a count by service and severity, a service window, a recent tail, a
  word search and a substring scan, over 15-minute and 1-hour windows ending now. From the start
  of arm A each cycle runs on its own connection on the 60 s grid, up to 3 in flight
  (`--overlap 3`), so both arms run the same number of cycles an hour. No cycle was skipped
  (`results/raw/queries.jsonl`: 0 `skipped`, 0 `error`).
- **Meters.**
  - Size: the Prometheus endpoint every 60 s, which does not wake an idle service
    (`results/raw/size.jsonl`: per replica `mem_total`, `cpu`, `cg_user`, `cg_system`, `uptime`).
  - CPU and sources: each replica's own system tables, pulled every 60 s with a 30 s lag
    (`results/raw/meter.jsonl`):
    - `asynchronous_metric_log`: CGroupUserTime, CGroupSystemTime, CGroupMaxCPU,
      CGroupMemoryTotal
    - `metric_log`: OSCPUVirtualTimeMicroseconds
    - `query_log`: CPU and `written_rows` by `log_comment`
    - `part_log`: MergeParts
  - Billing: usageCost and creditBalances every 10 minutes (`results/raw/usage.jsonl`).
- **Utilisation** is (CGroupUserTime + CGroupSystemTime) / CGroupMaxCPU per replica per minute,
  the median of a phase's settled minutes (`cloud/curve.py`). It is reported for the busiest
  replica and as the mean over replicas at every reading, because neither source says which one
  the recommender reads. The CGroup ratio reads in cores: under rising load it rose about as much
  as `metric_log` OSCPUVirtualTime (x1.4 to 1.8). The CGroup carries about 0.1 core more than the
  process counters.

## Per phase

From `cloud/arms_report.py --raw results/raw --lag-min 30`. Busiest and mean are utilisation;
cores are the busiest replica's median minute.

| Phase | Window (UTC) | Rows/s | Size | Busiest median | Busiest peak minute | Mean | Busiest cores: insert / select / merge | Unit-hours | $ at 0.2993 |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 11-02 21:40:16 to 11-03 00:55:25 | 70,000 | 2 x 16 GiB | 0.455 | 0.688 | 0.358 | 0.214 / 0.774 / 0.481 | 12.93 | 3.87 |
| B1 before the step | 00:55:25 to 05:08:35 | 45,716 | 2 x 16 GiB | 0.340 | 0.509 | 0.255 | 0.155 / 0.510 / 0.469 | 16.83 | 5.04 |
| B1 after the step | 05:15:35 to 06:15:38 | 45,716 | 2 x 12 GiB | 0.427 | 0.593 | 0.336 | | 2.89 | 0.86 |
| A2 | 06:15:38 to 07:45:42 | 70,000 | 2 x 12 GiB | 0.637 | 0.844 | 0.549 | 0.220 / 0.729 / 0.534 | 4.45 | 1.33 |
| B2 (4.5 h hold) | 07:45:42 to 12:15:51 | 45,716 | 2 x 12 GiB | 0.455 | 0.682 | 0.349 | 0.161 / 0.512 / 0.459 | 13.44 | 4.02 |
| B2 continued, waiting for SSO | 12:15:51 to 18:00:25 | 45,459 (load.jsonl) | 2 x 12 GiB | 0.457 | 0.754 | 0.354 | 0.157 / 0.506 / 0.460 | 17.20 | 5.15 |
| A3, pinned at 16 GiB from 11:18:06 | 11-04 11:25:37 to 14:33:23 | 70,000 | 2 x 16 GiB | 0.440 | 0.657 | 0.349 | 0.226 / 0.768 / 0.504 | 12.43 | 3.72 |
| B3 before the step | 14:33:23 to 18:38:35 | 45,716 | 2 x 16 GiB | 0.337 | 0.539 | 0.258 | | 16.28 | 4.87 |
| B3 after the step | 18:45:46 to 19:45:51 | 45,716 | 2 x 12 GiB | 0.505 | 0.740 | 0.447 | | 2.89 | 0.86 |
| A4, pinned at 16 GiB from 19:45:52 | 19:53:53 to 23:01:11 | 70,000 | 2 x 16 GiB | 0.486 | 0.687 | 0.392 | 0.232 / 0.803 / 0.565 | 12.37 | 3.70 |
| B4 before the step | 23:01:11 to 11-05 01:48:37 | 45,716 | 2 x 16 GiB | 0.351 | 0.541 | 0.273 | | 11.20 | 3.35 |
| B4 after the step | 01:56:03 to 02:56:09 | 45,716 | 2 x 12 GiB | 0.450 | 0.741 | 0.354 | | 2.76 | 0.83 |

- **B1 as a whole** (5.34 h): 20.38 unit-hours, $6.10. usageCost over the same window, shifted
  30 minutes, reads 6.123.
- **A1 as a whole:** usageCost reads 4.218 against $3.87. Suspicion: the window's first reading
  straddles the probe's last postings, which include the 6-unit overlap of its step up.
- **A3:** utilisation and unit-hours are the 2 x 16 GiB segment. The core split is the whole
  phase's, whose 194 meter minutes include the 2 x 16 GiB segment's 185.
- **B3 as a whole** (5.21 h): 19.83 unit-hours, $5.94; busiest cores 0.158 / 0.510 / 0.446.
  usageCost shifted 30 minutes reads 6.123, and A3's reads 3.641 against $3.92. The two sum to
  9.764 against $9.86. Suspicion: the 10-minute poll of 15-minute postings put one 4-unit
  quarter (0.298) on B3's side of the boundary.
- **B3 after the step** reads above B1 after the step (0.505 and 0.447 against 0.427 and
  0.336), as read. Suspicion, not measured: the new replicas' first hour.
- **A4** reads above A1 and A3 on the same size and load (busiest 0.486 against 0.455 and
  0.440; busiest cores 1.945 against 1.821 and 1.759), most of the difference in merge (0.565
  against 0.481 and 0.504). A4 followed B3 directly, where A3 followed a 17-hour idle. Reported
  as read; the cause is not measured. Its core split is the whole phase's, as for A3.
- **A2:** 12 of its 89 minutes had the busiest replica at 0.75 or more, the longest run 6 minutes,
  and the service did not step up (`events.jsonl`: `no_step_up`, 90 minutes).

## Where the CPU went: the write share W

Cores by source, median minute, from `query_log` tags and `part_log` MergeParts
(`cloud/curve.py`; `arms_report.py` `mean_cores`, `busiest_cores`). Insert is the tagged
`INSERT ... SELECT`, which includes reading the stage table. Merge is the background merges of
the parts the inserts wrote. Select is the seven-query load. W is (insert + merge) / (insert +
merge + select). Each source's median is taken separately, so the columns do not sum to the
cgroup.

Mean over replicas:

| Phase | Cgroup cores | Insert | Merge | Select | W | (insert + merge) / cgroup |
|---|---|---|---|---|---|---|
| A1 | 1.431 | 0.226 | 0.489 | 0.387 | 0.649 | 0.500 |
| B1 | 1.012 | 0.160 | 0.333 | 0.255 | 0.659 | 0.487 |
| A2 | 1.648 | 0.225 | 0.483 | 0.367 | 0.659 | 0.430 |
| B2 | 1.054 | 0.161 | 0.344 | 0.254 | 0.665 | 0.479 |
| A3 | 1.386 | 0.228 | 0.475 | 0.384 | 0.647 | 0.507 |
| B3 | 1.044 | 0.160 | 0.335 | 0.255 | 0.660 | 0.474 |
| A4 | 1.568 | 0.242 | 0.501 | 0.401 | 0.649 | 0.474 |
| B4 | 1.080 | 0.168 | 0.343 | 0.262 | 0.661 | 0.473 |

- **W is 0.65 to 0.67 in both arms**, on the mean over replicas. Select lands mostly on one
  replica: the busiest replica's select cores are 0.73 to 0.80 in arm A against a mean of 0.37 to
  0.40, so its W is lower, 0.47 to 0.51 in arm A and 0.54 to 0.55 in arm B.
- **Every source fell with the rows.** B over A, mean over replicas, pairs 1, 3 and 4: insert
  0.694 to 0.708, merge 0.681 to 0.705, select 0.653 to 0.664, cgroup 0.689 to 0.753, against
  rows 0.653. Select fell too because arm B's queries read a table holding fewer rows.
- **The units fell less than the cores.** The cgroup cores fell to about 0.7 of arm A's. The
  service stepped once, from 4 units to 3, which is 0.75.
- **Untagged CPU** (the cgroup less the three sources) is 0.22 to 0.35 of the cgroup in every
  phase. What it is was not measured.

The stage read inside the insert, from the `mode=read` calibration at the end of the run (15
minutes each on 2 x 12 GiB, the stage slices read into a `Null` table and nothing inserted;
`events.jsonl` phases `cal-readA`, `cal-readB`, `cal-readBfilter`, `curve.py` `read`):

| Calibration | Reads | Rows/s | Read cores, busiest | Read cores, mean | Arm insert cores, mean |
|---|---|---|---|---|---|
| `cal-readA` | `bench.stage` | 70,000 | 0.030 | 0.028 | A: 0.225 to 0.242 |
| `cal-readB` | `bench.stage_b` | 45,716 | 0.020 | 0.022 | B: 0.160 to 0.168 |
| `cal-readBfilter` | `bench.stage`, kept rows only | 70,000 read, 45,716 kept | 0.026 | 0.031 | |

The stage read is 12 to 14% of the insert cores in both arms. Taking it out of the insert lowers
W by about 0.01 in each arm (A1 0.649 to 0.640, B1 0.659 to 0.649). Reading arm B's rows from
`bench.stage` with a filter would have cost about 0.009 cores more than reading `bench.stage_b`.
The calibration's select cores are not comparable with the arms': with inserts stopped at 02:56:09Z, the queries' windows ending now held fewer rows in each
phase (busiest select 0.413, 0.277, 0.161).

## Step lags

**Step down, pair 1** (`results/raw/events.jsonl`: `step_down_started`, `step_down_done`;
`size.jsonl`: `uptime`).

| Time | What happened |
|---|---|
| 00:55:25 | Arm B1's cut. |
| 03:55:25 | The 3-hour small window first held only arm B. |
| 05:07:32 and 05:07:47 | The two 12 GiB replicas booted (sample time minus `uptime`): 4.20 h after the cut, 1.2 h after the small window held only arm B. |
| 05:14:21 sample | First 16 GiB replica gone. |
| 05:15:21 sample | Second 16 GiB replica gone, 4.33 h after the cut. |

The step was 4 GiB and 1 vCPU per replica. While both sizes served, the service carried 7 units
for about 6 minutes, then 5 units for 1 minute.

**Step up, probe step 7** (2 x 8 GiB, 70,000 rows/s).

| Time | What happened |
|---|---|
| 20:54:43 | Step 7 began. |
| 21:03 | The first minute at 0.75 or more on either replica. |
| 21:07, and 21:10 to 21:12 | Sustained 0.79 to 0.88. |
| 21:17:24 and 21:17:26 | Two 16 GiB replicas booted: 22.7 min after the step, about 14 min after the first minute over 75%, about 7 min after the sustained run. |
| between 21:24:19 and 21:25:19 | The 8 GiB pair left. |

While both pairs served, the sampler read 6 units (8 + 8 + 16 + 16 GiB). No activity entry was
logged for either step.

**Pair 2.** No step down within 4.5 h at a busiest median of 0.455 on 2 x 12 GiB
(`events.jsonl`: `no_step_down`, pair 2, 4.5 h), nor in the 5.75 h after it at 0.457 while the
run waited for SSO.

**Pairs 3 and 4.** Arm A's size was set by config: the driver PATCHed `replicaScaling` at each
arm A start and back at each arm B cut (`results/raw/scaling-patches.jsonl`, all status 200):

| Time (UTC) | Phase | Request | Response state, min, max |
|---|---|---|---|
| 11-04 11:18:05 | A3 start | `{"minReplicaMemoryGb":16,"maxReplicaMemoryGb":32}` | idle, 16, 32 |
| 11-04 14:33:23 | B3 cut | `{"minReplicaMemoryGb":8,"maxReplicaMemoryGb":32}` | running, 8, 32 |
| 11-04 19:45:51 | A4 start | `{"minReplicaMemoryGb":16,"maxReplicaMemoryGb":32}` | running, 16, 32 |
| 11-04 23:01:11 | B4 cut | `{"minReplicaMemoryGb":8,"maxReplicaMemoryGb":32}` | running, 8, 32 |

The service woke 91 s into A3 already mid-step, two 12 GiB and two 16 GiB replicas at
11:19:32Z, and held 2 x 16 GiB from 11:25:37Z (`step_up_started`, `step_up_done`, 452 s after
the phase start). A3 as a whole, including the wake and the overlap: 3.26 h, 13.10 unit-hours,
$3.92. Every step down after a cut is the autoscaler's own.

**Step down, pair 3**, from 2 x 16 GiB after the release to 8 (`events.jsonl`,
`size.jsonl` `uptime`):

| Time | What happened |
|---|---|
| 14:33:23 | Arm B3's cut, with `minReplicaMemoryGb` 8 in the same second. |
| 17:33:23 | The 3-hour small window first held only arm B. |
| 18:37:42 and 18:37:48 | The two 12 GiB replicas booted: 4.07 h after the cut. |
| 18:38:35 sample | `step_down_started`, 7 units: 4.09 h. |
| 18:45:35 sample | `step_down_done`, both 16 GiB replicas gone: 4.21 h. |

usageCost postings per 15 minutes across pair 3 (`usage.jsonl`, consecutive readings): 0.298 to
0.299 through 19:02, one 0.378 at 19:22 (the overlap), then 0.223 to 0.224. The quarters at
A3's wake read 0.03, 0.03 and 0.328.

A4 stepped up from B3's 2 x 12 GiB: the first 16 GiB replica joined at the 19:46:35Z sample
(61 s), and the service held 2 x 16 GiB from the 19:53:35Z sample (`step_up_done`, 481 s).

**Step down, pair 4**, from 2 x 16 GiB after the release to 8:

| Time | What happened |
|---|---|
| 11-04 23:01:11 | Arm B4's cut, with `minReplicaMemoryGb` 8 in the same second. |
| 11-05 01:47:46 and 01:47:54 | The two 12 GiB replicas booted: 2.78 h after the cut. |
| 01:48:37 sample | `step_down_started`, 7 units: 2.80 h. |
| 01:55:37 sample | `step_down_done`, both 16 GiB replicas gone: 2.91 h. |

This step came 1.3 h sooner than in pairs 1 and 3, while the 3-hour small window still held
A4's last 13 minutes. B4 at 4 units read 0.351 against 0.340 and 0.337 for B1 and B3. Reported as
read; why it came sooner is not measured. usageCost postings across pair 4: 0.298 to 0.299
through 02:24, one 0.363 at 02:34 (the overlap), then 0.223 to 0.224.

| Step down | Cut to new replicas booted | Cut to old replicas gone | Arm B busiest median at 4 units |
|---|---|---|---|
| Pair 1 | 4.20 h | 4.33 h | 0.340 |
| Pair 3 | 4.07 h | 4.21 h | 0.337 |
| Pair 4 | 2.78 h | 2.91 h | 0.351 |

## The floor and the load curve

On 2 x 8 GiB (2 units, the configured minimum), the probe raised arm A in 10-minute steps
(`cloud/probe.py`, `events.jsonl` phases `probe-1` to `probe-7`):

| Rows/s | Busiest median | Busiest peak minute | Mean | Busiest cores: insert / select / merge |
|---|---|---|---|---|
| 2,000 | 0.130 | 0.133 | 0.111 | 0.030 / 0.005 / 0.085 |
| 5,000 | 0.159 | 0.181 | 0.137 | 0.041 / 0.013 / 0.118 |
| 10,000 | 0.201 | 0.215 | 0.171 | 0.053 / 0.000 / 0.176 |
| 20,000 | 0.285 | 0.404 | 0.237 | 0.043 / 0.048 / 0.316 |
| 35,000 | 0.400 | 0.425 | 0.329 | 0.067 / 0.113 / 0.387 |
| 50,000 | 0.529 | 0.620 | 0.450 | 0.089 / 0.182 / 0.550 |
| 70,000, before the step | 0.698 | 0.877 | 0.581 | 0.219 / 0.308 / 0.587 |

- **Where the arms cost the same.** The service held 2 units through 50,000 rows/s and stepped
  up at 70,000. Below the load that lifts arm A off 2 units, both arms cost the floor. Read over
  10-minute steps, that load lies between 50,000 and 70,000 rows/s.
- **Floor cost.** 2 units is $0.60/h, $14.4 a day at $0.2993. An idle service bills no compute.
- **Memory** was not binding: about 2 GiB resident of 8 during the probe.

### Memory per arm

GiB per replica, the median minute (`cloud/arms_report.py`: `memory_gib`, and per segment
`used_gib_mean`, `resident_gib_mean`, `used_gib_top`). The fields are `asynchronous_metric_log`
CGroupMemoryTotal, CGroupMemoryUsed and MemoryResident. "Used, top replica" is the replica
using the most.

| Segment | Hours | Memory per replica | Used, mean | Resident, mean | Used, top replica |
|---|---|---|---|---|---|
| A1 at 4 units | 3.25 | 16 | 1.904 | 2.480 | 1.991 |
| B1 at 4 units | 4.22 | 16 | 1.900 | 2.466 | 1.994 |
| B1 at 3 units | 1.00 | 12 | 1.602 | 2.190 | 1.653 |
| A2 at 3 units | 1.50 | 12 | 2.036 | 2.630 | 2.125 |
| B2 at 3 units (4.5 h hold) | 4.50 | 12 | 1.954 | 2.562 | 2.026 |
| B2 continued | 5.74 | 12 | 2.126 | 2.731 | 2.299 |
| A3 at 4 units | 3.13 | 16 | 1.889 | 2.497 | 1.984 |
| B3 at 4 units | 4.09 | 16 | 1.949 | 2.582 | 2.065 |
| B3 at 3 units | 1.00 | 12 | 2.076 | 2.654 | 2.400 |
| A4 at 4 units | 3.12 | 16 | 2.090 | 2.700 | 2.154 |
| B4 at 4 units | 2.80 | 16 | 2.045 | 2.687 | 2.096 |
| B4 at 3 units | 1.00 | 12 | 1.786 | 2.338 | 1.840 |

At every size, each arm used about 2 GiB of 12 to 16 GiB, under a fifth. The band quoted in
`results/raw/autoscaler-doc-quotes.md` is on CPU alone, and a unit fixes memory to CPU at
8 GiB to 2 vCPU. So the memory each arm paid for was set by its CPU. Whether the recommender
reads memory as well is not measured.

## Why the service ran at 16 GiB before the run

Both replicas ran at 16 GiB and 4 vCPU from creation (11-02 14:38:37Z) through both of the
first awake stretches. At the next wake, 19:48Z, they started at 8 GiB, the configured minimum
(`results/raw/replica-history-size-minutes.jsonl`).

The configured range never changed, and `/activities` logs no scaling event. Whether that was an
autoscaler decision or a creation-time size cannot be separated from what the API and the system
tables show. The run starts from the 8 GiB wake.

## Billing, as read

- **First stretch.** usageCost 11-02 for `chce-elasticity`, before the run, read computeCHC 0.398
  for the two stretches at 4 units.
  - Against the activity log's running-to-idle span, 1.130 unit-hours, it is $0.338 at $0.2993.
    The read is 18% above.
  - Against the replicas' own first-to-last log samples, 1.428 unit-hours, it is $0.428. The
    read is 7% below.
  - Suspicion: metering covers part of the roughly 2 minutes each replica ran past
    `service_idle`. No rate is inferred from it.
- **Posting lag.** A 0.378 posting at 05:53:15 was followed by 0.224 at 06:03:18, and the
  step's overlap ran 05:07:32 to 05:15:21. If the 0.378 is the 05:00 to 05:15 quarter, postings
  land 28 to 33 minutes after the quarter closes. That attribution is a reading, not a published
  lag.

## Autoscaler rules, quoted

From the ClickHouse Cloud docs and the blog post of 2026-03-24, verbatim in
`results/raw/autoscaler-doc-quotes.md`:

- CPU target 53%, high watermark 75%, low watermark 37.5%.
- "If the CPU utilization is between 37.5%–75% of allocated capacity, no scaling action is
  taken."
- A 3-hour small window "enables faster scale-down". A 30-hour large window ensures a single-step
  scale up to the window's peak.
- In the blog's merge table, "No change | Scale-down" goes to a hunting check that trusts the
  small window unless it is trending up.

Neither source says how often the recommender runs, whether it reads the busiest replica or the
mean, or how "maximum usage" is aggregated.

## Harness notes

- **Host pacer defect.** The first split fed the collector from a pacer on the host. Docker
  Desktop's file sharing did not surface the host's appends to the collector's filelog until
  something inside the VM touched the file, so the engine got the feed in four hourly bursts.
  Its kept share read 0.0584. Proven at 18:41 to 18:42Z: with 1,616 lines in the feed, filelog
  had accepted 0; one touch from a container and it accepted 1,828. The pacer now runs in a
  container (`split/run.sh`). The invalid split is kept as evidence
  (`results/split-hostpacer.json`).
- **Connection pinning.** After the probe's step up, kept-alive HTTPS connections stayed on the
  old replicas and the new pair took no work. From 21:20:26 connections reopen every 30 s
  (`cloud/chhttp.py`, `CHC_CONN_MAX_AGE`). Real clients pool connections too, so this is a
  harness choice for clean attribution.
- **Lost system tables.** A removed replica takes its system tables with it. The old 8 GiB
  replicas' 21:18 to 21:24 records are lost, because the meter had pulled only to 21:17. From
  21:35 the meter pulls every 60 s with a 30 s lag, so a step loses at most about 1.5 minutes of
  the departing replicas. At the 05:14 step one old replica's last minute or two is missing.
- **Query overlap.** On 2 vCPU a serial query cycle reached 38.8 s, so `--overlap 3` was on from
  the start of A1, keeping both arms' cycle count equal.
- **Arm B's stage.** Arm B reads `bench.stage_b`, so it reads only what it writes. The
  calibration in the write share section measures the stage read in each arm and for arm B read
  from `bench.stage` through a filter.
- **SSO.** The AWS SSO session that holds the Cloud API key in SSM expired during B2. Running
  processes kept the key in their environment, but the driver could not PATCH `replicaScaling`
  for A3. B2's load continued past its 4.5 h hold. B2 ran 10.25 h on 3 units in all, with no step
  down. The continuation's row in the table is cut from `events.jsonl` `no_step_down`
  (12:15:51Z) to the idle phase (18:00:25Z); its rows a second are counted client side from
  `load.jsonl`, since its inserts carry B2's tag. At 18:00:25Z, with SSO still expired, the
  driver logged `forced_idle_no_sso`. It stopped load and queries and paused the meter, whose
  SQL pulls would otherwise keep the service awake. The meter paused at 18:02:55Z
  (`meter_paused`). `size.jsonl` reads `running` at 18:07:26Z and `idle`, 0 units, at 18:08:26Z.
  SSO primed at 11:18:05Z on 11-04 (`sso_primed`), after 17.3 h of idle, and pair 3 started from
  the idle service. The first PATCH reached the service while it was still idle (response
  `"state":"idle"`). The A3 phase note's "replicas at start" is the last size before the idle,
  not a reading at the restart. A live GET at 11:18:33Z read My first service's allow-list as
  the single runner /32 set on 11-02. The renewed session expired again at 11-04 19:17:35Z (the
  SSO token cache's `expiresAt`); the run was unaffected, since every running process held the
  key. For the deletion, one process read the key at 11-05 03:20:39Z, once the session was
  renewed, and held it until the end (`results/raw/teardown.jsonl`: `key_loaded`).

## Not measured

- The wire parse of real inserts. Both arms insert from a stage table, so network parse CPU is
  absent from both.
- The select share at steady state during the probe. The probe's 10-minute steps never filled
  the 1-hour query windows. The arms' select cores above are from phases of 1.5 h and more.
- Which replica the recommender reads. Busiest and mean are reported at every reading.
- The recommender's cadence.
- Why pair 4's step down came 1.3 h sooner than pairs 1 and 3, why A4 read higher merge cores
  than A1 and A3, why B3's first hour at 3 units read above B1's, and what the untagged CPU is.
  Each is reported as read where it appears.

## What this does not show

- A production query mix: this was seven queries a minute.
- The collector and engine path live: the feed was pre-split.
- More than one region, schema or service shape: us-east-1, ClickStack `otel_logs`, 2 replicas.
- Loads between the probe's steps.
- A size below 2 x 8 GiB.

## Credit

- **Spent.** $42.61 of the $300 credit, against the run's $200 cap: creditBalances `amountSpent`,
  the same in every poll from 11-05 04:25:02Z to the last at 05:35:23Z (`results/raw/usage.jsonl`).
  It read $42.15 just after the deletion, with postings still landing
  (`results/raw/teardown.jsonl`: `credit_after_delete`).
- **chce-elasticity's billing.** usageCost totalCHC 41.714, of which computeCHC 41.680: computeCHC
  4.288, 18.196, 14.878 and 4.318 on 11-02 to 11-05, each day's last reading in
  `results/raw/usage.jsonl`. Its last change landed by the 04:25:02Z poll.
- **Unit-hours.** 137.15 by the meter (from 11-02 19:48Z, when it started) and 138.56 by the
  sampler (from 14:51Z), $41.05 and $41.47 at $0.2993.
- **The rest.** amountSpent is $0.90 above the service's totalCHC. usageCost `grandTotalCHC` read
  0.17 to 0.53 CHC above the service's own rows in each poll's window; the poller kept only the
  service's rows, so which entity billed the difference is not measured.
- **Deletion.** chce-elasticity was sent the stop command at 11-05 03:44:15Z (HTTP 200), read
  stopped at 03:46:57Z and was deleted then (HTTP 200). A GET of it returned 404 and the services
  listing held only "My first service" (`results/raw/teardown.jsonl`).
- **Kept.** "My first service", created at sign-up in us-west-2, had its allow-list narrowed from
  0.0.0.0/0 to the runner's /32 at 11-02 19:51:57Z and was not deleted
  (`results/raw/first-service-ip-patch.json`).

## Files

- `split/`: the engine split.
- `cloud/`: the service, stage, feed, queries, meters, driver and reports.
- `results/`: the split and stage readings, the creation response.
- `results/raw/`: every raw log the scripts wrote. `meter`, `load`, `size`, `queries` and
  `replica-memory-all` are committed as `.jsonl.gz`; `arms_report.py` and `curve.py` read them as
  they are. `teardown.jsonl` holds the stop, the deletion and the service list after it.
