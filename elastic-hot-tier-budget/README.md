# Elastic hot-tier budget

One benchmark in the [log10x benchmarks](../) repository. It asks whether log10x-mcp's hourly hot-tier run, driving the Receiver, holds an Elasticsearch hot tier under a size S while load grows 2.5 times, as the hot node's own stats count it.

**Result: not yet.** The run held the kept stream and the mean, but not the bound. Two defects in the run's arithmetic were found and are fixed on the log10x-mcp branch; this folder records the run that found them.

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
