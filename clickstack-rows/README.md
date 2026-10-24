# ClickHouse rows run: rows written into ClickStack held at a rate an hour

One benchmark in the [log10x benchmarks](../) repository. It is the metered gate for the
rows run in log10x-mcp (`log10x_setup_recurring` with `rows_per_hour`). Each run reads the
rows ClickHouse wrote into the logs table from its own `system.part_log`, and rewrites the
Receiver's per-statement limits and service totals in lines. Lines over a service's total
go to the account's own bucket before ClickHouse receives them.

The method was written before the run: [`METHOD.md`](METHOD.md). It is time-scaled, with
every clock divided by 6 (a run every 10 minutes, a 10-minute meter window, growth stepped
every 20 minutes). The regulator's 4-minute window and the always-pass sample of 5 are
engine constants and were not scaled.

## Result, 2026-10-23: FAIL as registered; the rate held flat through the growth

The engine was `ghcr.io/log-10x/edge-10x:1.1.147`, on ClickStack 2.38.0 (ClickHouse
26.5.7.64). The released OpenTelemetry demo capture was replayed from 14 to 35 lines a
second. The dry run measured 42,000 rows an hour with nothing held, so R = 29,399 rows an
hour (0.7 of that). There were 15 applied runs, the last after the feed stopped.

| | Criterion | Result |
|---|---|---|
| 1 | Every applied run exits 0 and commits, projecting at or under R | **Pass.** 15 runs, all exit 0, each projecting about 29k rows an hour once the rate bound. |
| 2 | Each 4-minute window at or under R/15 plus the floor's share; each 10-minute meter window at or under R/6 | **Fail.** 23 of 25 four-minute windows were under their bound. 19:04 read 1.52 and 19:08 read 1.06. Every complete 10-minute window read 0.99 to 1.04 of R/6, except 19:00 at 1.36. |
| 3 | Hot plus cold equals the returned records, for the ten largest moved statements | **Fail.** 3 of 10 were exact. 7 were 1 to 11 rows over: 33 rows inserted twice into the hot table across the run (0.04%). The bucket was exact. |
| 4 | A count through the Merge table equals the local count | **Fail against the wire, exact against storage.** For all ten statements the Merge table equalled hot plus cold. The differences are the duplicates in criterion 3. |
| 5 | Every line written comes back; every returned record is in the table or the bucket | **Every returned record is stored:** 194,864 rows held 194,831 returned records, none missing, 33 duplicated. Lines in against records back is not settled here: the Receiver folds multi-line events, 242,741 lines into 194,831 records. |
| 6 | Storm: error lines of the storming statement per window at most its limit plus 50 | **Pass, read by hand.** The largest increase in a 4-minute window was about 117, against a limit of about 73 plus 50. |
| 7 | The injected service is held from its first window by the `*` row | **Pass on the regulator's windows.** Read by clock window, the first reads 96 rows against a `*` total of 49. The regulator's windows start at its first regulated line, and that clock window spans two of them, 47 and 49, each at or under the total. From its second window it held to its own row. |

**What held.** Load grew 2.5 times, with a 20-minute error storm and a new service.
Through all of it, the rows written into the table stayed at 0.99 to 1.04 of R in every
complete 10-minute window but one, from the first growth step to the end of the hold at
35 lines a second (2.5 times the starting 14). The one, 19:00, read 1.36, and cause 2 below
is why. Before the first applied run they read 1.40 to 1.43 of R. Every line over a total went to the bucket
before ClickHouse received it: 110,392 rows there against 84,472 in the table.

**Why criterion 2 failed: two causes.**

1. **The always-pass floor.** Each statement passes 5 lines per window on every node,
   whatever its limit. The run subtracts that floor from the allowance, but the floor
   changes from window to window with the statements that print. The method allows the
   floor's share in the 4-minute bound and not in the 10-minute sum, which is why most
   10-minute windows read 1 to 4% over R/6.
2. **One service printing 1,422 new statements in four minutes.** When the replay looped
   the capture, Grafana's migrator ran again. The engine names that statement once per
   migration id, so it arrived as 1,422 distinct patterns in one window, each passing its
   always-pass sample, and no service total bounds that sample. Grafana passed 1,481 lines
   in the window against a usual 140, which is the 1.52. The next applied run, ten minutes
   later, sized the window after it. The rate holds against growth in known traffic. A
   burst of new statements from one service overshoots by its pattern count times the
   sample, until the next run.

**Two more findings.**
- **The Receiver's Prometheus counters undercount under load.** They agreed with the meter
  at the starting load (scale 1.00). At 30 and 35 lines a second they read 2.1 to 6.3 times fewer pass
  lines than the meter counted, with a healthy scrape. The rows run takes totals from the
  meter and only the share each statement contributes from the counters, so the hold did
  not depend on them. The report prints the scale factor every run.
- **ClickStack's insert path wrote 33 rows twice** over 84,439 inserted, with no restart.
  An earlier run found the same on a retry of an insert that had already committed
  (`clickstack-e2e-gaps`, gap 5).

## Rerun, 2026-10-24, with the regulator's sample bound: every 4-minute window under its bound; FAIL as registered on the 10-minute sum alone

Same rig, image, capture, pace steps, storm and injected service as the run above, with one
change in the Receiver's configuration: the always-pass sample counts toward its service's
total, and a service passes at most 50 more sample lines per window once its total is spent
(`baselineMaxOverTotal`, log-10x/config `4253528`, declared in log-10x/modules `cbbc8c32`, both
mounted over the 1.1.147 image's own files for this run; the 1.1.150 image ships them in its configuration; `results-sample-bound/build/` records the
commits and the patches). The dry run measured the same 42,000 rows an hour, so R = 29,399
again. There were 15 applied runs. Results in `results-sample-bound/`.

| | Criterion | Result |
|---|---|---|
| 1 | Every applied run exits 0 and commits, projecting at or under R | **Pass.** 15 runs, all exit 0, each projecting about 29k rows an hour once the rate bound. |
| 2 | Each 4-minute window at or under R/15 plus the floor's share; each 10-minute meter window at or under R/6 | **Fail on the 10-minute sum alone.** All 25 four-minute windows were under their bound. The complete 10-minute windows read 0.97 to 1.07 of R/6; 5 of 9 were over by 3 to 7%, the floor's share the bound makes no allowance for. |
| 3 | Hot plus cold equals the returned records, for the ten largest moved statements | **Pass.** All ten exact. No row was inserted twice: 194,524 returned, 83,018 in the table and 111,506 in the bucket. |
| 4 | A count through the Merge table equals the local count | **Pass.** All ten exact. |
| 5 | Every line written comes back; every returned record is in the table or the bucket | **Every returned record is stored, none twice.** 242,357 lines became 194,524 records (the Receiver folds multi-line events). |
| 6 | Storm: error lines of the storming statement per window at most its limit plus 50 | **Pass, read by hand.** The largest increase in a 4-minute window was about 124, against the service's total of 76 to 88 plus 50. |
| 7 | The injected service is held from its first window by the `*` row | **Pass.** 86 rows in its first clock window against a `*` total of 186 in force; from the next applied run it held to its own row of 92, with 43 to 92 a window. |

**What changed.** The capture loop inside the hold at 35 lines a second, where the first run
passed 1,481 Grafana lines in one window (1,422 new statements, each passing its sample), passed
under 200 in every window here: the rows written in that 10-minute window read 1.03 of R/6,
against 1.36 before. The only window with more than 200 Grafana passes in the whole run is the
startup window, before any total was set (1,588 lines, 1,433 statements). The 10-minute sums
sit 3 to 7% over R/6 for the reason the first run found: the floor is inside R and the
10-minute test has no allowance for it, while the 4-minute test does and holds everywhere.

**The regulator bound, measured by the gate first.** `tests/regulator/run.sh b1-sample-bound
b2-sample-bound-off b3-sample-bound-mute` in log-10x/config: on the image's own configuration
a 200-statement burst under a 50-line total passes 400 of 400 lines; with the bound it passes
100 (the total plus 50), and `baselineMaxOverTotal: 0` restores 400.

## Two-arm run: the rows run against a collector rule, under the same growth

The method was written before the run: [`METHOD_TWO_ARM.md`](METHOD_TWO_ARM.md).
`ARMS=two rig/phases.sh` runs the rows run as above (arm A, `default.otel_logs`, on the
1.1.150 image with its own configuration) and, on the same node and the same feed, a second
routing collector with the collector-only rule from `clickstack-e2e-gaps` gap 6 (arm B,
[`rig/router-rule.yaml`](rig/router-rule.yaml)): the two chattiest services' INFO and DEBUG
lines go to a second bucket and the rest into `default.otel_logs_rule`, a copy of the logs
table with the same counts view. Arm B has no Receiver. The meter reads, per table and per
window of ten rig minutes counted from the start, NewPart rows from `system.part_log`, merge
CPU from its MergeParts ProfileEvents and insert CPU from `system.query_log`.
`rig/score.py <results> --arms two` scores the three criteria and writes the comparison
table. Results go to `results-two-arm/`.

```bash
ARMS=two MCP=<log10x-mcp checkout with build/> GH_TOKEN=$(gh auth token) rig/phases.sh
```

## Files

| Path | What |
|---|---|
| `METHOD.md` | the method, written before the run |
| `rig/` | the harness (`phases.sh` runs it: `MCP=<log10x-mcp checkout> GH_TOKEN=... rig/phases.sh`) |
| `results/score.md`, `results/final.md` | criteria 1, 2, 6 and the reports; criteria 3, 4, 5, 7 |
| `results/timeline.jsonl`, `results/meter.log` | every phase and every meter reading |
| `results/budget-runs/*/` | each run's report, files and commit |
| `results/policy.yaml`, `results/images.txt`, `results/cse-engine.log`, `results/engine-metrics.txt` | the policy, image digests, the Receiver's log and its last scrape |

The wire tap (428 MB) and the replay feed (251 MB) are not committed. The run writes them
again.

## Rig notes

- **ClickStack's collector** opens 4317 only after HyperDX hands it a config, which needs a
  registered team. The rig registers inside its start loop, then waits for the port.
- **The meter user.** ClickStack's `default` user refuses HTTP from outside the container.
  The rig reads through a `rows_meter` user, defined in `rig/rows_meter.xml`, with SELECT on
  `system.part_log` and `system.parts` and SHOW TABLES on `otel_logs`. It has no SELECT on
  the logs table.
- **The object store is RustFS.** MinIO's public images were withdrawn from quay.io and
  Docker Hub (401, access denied), so the rig runs RustFS with the AWS CLI image.

## What a run does not prove

Nothing about money, ClickHouse Cloud or its autoscaler, 300 nodes, durability across a
restart, or write CPU against a collector rule. It holds rows on one node, from one
replayed capture.
