# Elastic hot-tier budget

One benchmark in the [log10x benchmarks](../) repository. It asks whether log10x-mcp's hourly hot-tier run, driving the Receiver, holds an Elasticsearch hot tier under a size S while load grows 2.5 times, as the hot node's own stats count it.

**Result: holds at steady state, not under fast growth.** Two runs. The first held the mean but not the bound and found two defects in the run's arithmetic; the second, with both fixed and every time constant divided by 6, held hot at 0.97 to 0.98 of S under steady load and overshot to 1.23 S during a 2.5x step-up compressed into an hour. Both fail the pre-registered bound. Results of the first run in `results/`, of the second in `results-r2/` (section at the end).

Self-managed Elasticsearch 9.5.5 (one hot node, one frozen node, filesystem snapshot repository, trial licence), engine `log10x/edge-10x:1.1.147`, log10x-mcp branch `feat/elastic-hot-tier-budget` (1.30.79, unreleased) at the build of 2026-10-22 20:01 UTC, the published OpenTelemetry demo sample replayed, 2026-10-22 19:59 to 2026-10-23 09:59 UTC. Method, written before the run: `results/` holds the timeline, every hourly run's report and files, the cluster readings and slim captures (no log text).

| | Criterion | Result |
|---|---|---|
| 1 | Every applied hourly run exits 0 and commits; once the size binds, its projection is at or under S | **Pass.** 13 applied runs, all exit 0, each projecting about 45 MB against S = 44.8 MB. |
| 2 | Run hours 7 to 13: hot store at or under 1.10 S at every reading, mean at or under S | **Fail.** Mean 0.998 S over 36 readings; 6 readings above 1.10 S, peak 1.17 S at 05:19 UTC, during the step-up. |
| 3 | Every rolled tier_down index mounted on frozen at 0 bytes | **Pass.** 38 of 38. |
| 4 | Hash queries on frozen equal the local count, ten largest moved statements | **Pass.** Exact, from 170,470 down to 10,498. |
| 5 | Every line received comes back, every returned record is in Elasticsearch | **Pass.** 1,041,196 lines in and back; 162,451 kept and 672,357 moved records, each equal to the cluster's count. |
| 6 | Storm: error lines kept per 4-minute window at most limit plus 50 | **Fail in one window.** 55 in four windows (the 5-line sample plus 50); 146 in the window that spans the 05:01 policy reload. |

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

## What went wrong

- **The always-pass floor was not in the arithmetic.** The Receiver passes the first 5 lines of every statement in every window on every node, and 50 error lines over a limit. From run hour 9 the run allowed nothing more on hot, yet 1.8 to 3.2 MB an hour stayed there; 59 to 74% of those lines were the sample, across about 2,300 statements. The plan now counts each statement's floor in the kept total, and when the floor alone exceeds what fits it says so and projects above S.
- **Moved lines waiting to mount.** A tier_down index rolls every 15 minutes here and mounts about 40 minutes later, so up to 22 MB of moved lines sat on hot during the growth, about half of S. Hot here keeps a kept line 6 hours; with retention of days the same hour of moved lines is about 1% of hot.
- **The tier_down lifetime was never measured.** Every report used the 2-hour default: on a mounted index `index_creation_date_millis` is the original index's creation, so every delay came out negative. The mount completes at `step_time_millis` once the frozen phase's step reads complete. Fixed; it would have made the run hold less, not more.
- **A policy reload during the storm.** Each applied run rewrites the policy files; the window that spans the 05:01 reload kept about two windows' worth of the storming error line.

## The rig

`rig/`: two Elasticsearch nodes and Fluent Bit (`compose.yaml`), the Receiver rendered by log10x-mcp with `elasticHotTier` and a policy branch (`gen-receiver-values.mjs`), the MCP's frozen-tier recipe then the time-scaled policies (`es-setup.mjs`: kept lines 6 hours on hot, tier_down rollover 15 minutes), `policy.yaml` from `emitPolicyYaml` (`gen-policy.mjs`), `tenx-recur` every hour (`budget-run.sh`), the replay (`make-replay.py`, `forward_send.py`), the phases (`phases.sh`) and the meter (`meter.py`). The Receiver pulled its files from `log-10x/config` branch `test/elastic-hot-tier-policy`.

## Not shown

A bill; Cloud Hosted; production retention lengths; a hot tier held under growth.

## The rerun (`results-r2/`), 2026-10-23 11:25 to 15:55 UTC

log10x-mcp `feat/elastic-hot-tier-budget` at 0b45d4a (the floor in the plan and the report, the tier_down lifetime from `step_time_millis`). Every time constant divided by 6: a run every 10 minutes, kept lines 2 hours on hot (10-minute rollover, frozen 110 minutes later), tier_down rollover 3 minutes, ILM poll 100 seconds (changed only because everything else was scaled), meter every 100 seconds, growth in four 20-minute steps from 56 to 140 lines a second. No raw capture: lines in are Fluent Bit's input counter, and the local copies of returned records keep only container, times, hash, route, `utf8Size`, level, name and line count (`results-r2/captures/`). S = 56.7 MB, 0.7 of where the dry run said hot would settle with nothing held (81 MB).

| | Criterion | Result |
|---|---|---|
| 1 | Runs exit 0 and commit; projection at or under S, or the floor reported | **Pass.** 26 of 26 applied runs; projections 51 to 57 MB; the always-pass floor 79 to 268 MB a day, inside what fit at every run. |
| 2 | Run minutes 130 to 250: hot at or under 1.10 S every reading, mean at or under S | **Fail.** Mean 1.095 S, peak 1.23 S, 30 of 72 readings over 1.10 S. Before growth (minutes 111 to 131) 0.97 to 0.98 S. |
| 3 | Rolled tier_down indices mounted at 0 bytes | **Pass.** 73 of 73. |
| 4 | Hash queries on frozen equal local, ten largest moved statements | **Pass.** 10 of 10. |
| 5 | Delivery | **Pass.** 1,301,174 lines in, 1,300,992 non-blank lines back (the difference is the sample's blank lines, 171 expected); every returned record in Elasticsearch. |
| 6 | Storm kept per window at most limit + 50 | **Fail.** 286 in the window spanning the 14:15 policy reload, against a limit of about 117 lines + 50. From 14:17 to 14:20 the Receiver kept none of the storm's error lines. |

**Why growth overshoots.** The run steers what new lines do; it cannot move lines already on hot. When load rose 2.5 times within an hour, the moved lines waiting to mount grew from 3 MB to 10 to 19 MB at once (the run's own estimate of that slice was right), while the kept lines already on hot leave only as their indices age out, over 2 hours here. The run tightened its allowance to 86 to 90% and projected 51 to 55 MB, but hot stayed above 1.1 S until the window closed. Relative to the time a line stays on hot, this step-up was about 50 times faster than a year of 2.5x growth against days of retention, but the run does not show what a slower ramp does.

**For the engine.** Two observations the regulator page does not predict: the window that spans a policy reload kept about twice its allowance of the storming line in both runs, and in this run the error keep count passed nothing for three minutes once grafana's limits were in force (a 42,102-byte limit and a 117,054-byte total), where the first run's 1-byte limit passed 55 a window.
