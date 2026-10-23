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
hour (0.7 of that). There were 13 applied runs.

| | Criterion | Result |
|---|---|---|
| 1 | Every applied run exits 0 and commits, projecting at or under R | **Pass.** 14 runs, all exit 0, each projecting about 29k rows an hour once the rate bound. |
| 2 | Each 4-minute window at or under R/15 plus the floor's share; each 10-minute meter window at or under R/6 | **Fail.** 23 of 25 four-minute windows were under their bound. 19:04 read 1.52 and 19:08 read 1.06. Every complete 10-minute window read 0.99 to 1.04 of R/6, except 19:00 at 1.36. |
| 3 | Hot plus cold equals the returned records, for the ten largest moved statements | **Fail.** 3 of 10 were exact. 7 were 1 to 11 rows over: 33 rows inserted twice into the hot table across the run (0.04%). The bucket was exact. |
| 4 | A count through the Merge table equals the local count | **Fail against the wire, exact against storage.** For all ten statements the Merge table equalled hot plus cold. The differences are the duplicates in criterion 3. |
| 5 | Every line written comes back; every returned record is in the table or the bucket | **Every returned record is stored:** 194,864 rows held 194,831 returned records, none missing, 33 duplicated. Lines in against records back is not settled here: the Receiver folds multi-line events, 242,741 lines into 194,831 records. |
| 6 | Storm: error lines of the storming statement per window at most its limit plus 50 | **Pass, read by hand.** The largest increase in a 4-minute window was about 117, against a limit of about 73 plus 50. |
| 7 | The injected service is held from its first window by the `*` row | **Fail in its first window:** 96 rows against a `*` total of 49. From its second window it held to its own row. |

**What held.** Load grew 2.5 times, with a 20-minute error storm and a new service.
Through all of it, the rows written into the table stayed at 0.99 to 1.04 of R in every
complete 10-minute window from the first growth step to the end of the 5x hold. Before the
first applied run they read 1.40 to 1.43 of R. Every line over a total went to the bucket
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
  at the starting load (scale 1.00). At 4.25x and 5x they read 2.1 to 6.3 times fewer pass
  lines than the meter counted, with a healthy scrape. The rows run takes totals from the
  meter and only the share each statement contributes from the counters, so the hold did
  not depend on them. The report prints the scale factor every run.
- **ClickStack's insert path wrote 33 rows twice** over 84,439 inserted, with no restart.
  An earlier run found the same on a retry of an insert that had already committed
  (`clickstack-e2e-gaps`, gap 5).

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
