# ClickHouse Cloud elasticity

One benchmark in the [log10x benchmarks](../) repository. It asks how far a ClickHouse Cloud service's compute falls, in units and in billed dollars, when the rows written into its logs table fall, above the smallest size, and how long the autoscaler takes to lower it.

**Result: from a 4-unit start, writing 0.653 of the rows took the service from 4 units to 3, a ratio of 0.75, and billed compute to 0.749, in each of three pairs; the step down was done 2.9 to 4.3 hours after the cut. From a 3-unit start the same cut read no change in 10.25 hours.** At 3 units both arms sit inside the autoscaler's no-action band; at 4 units arm B sits below it. Every figure, with the file and field it was read from, is in [RESULT.md](RESULT.md).

ClickHouse Cloud, AWS us-east-1, Scale tier, ClickHouse 26.6, 2 replicas, vertical autoscaling 8 to 32 GiB per replica, idle after 5 minutes. The ClickStack `otel_logs` schema under seven queries a minute. Arm A writes every record of the 215 MB OTel replay at 70,000 rows/s; arm B writes the 65.3% the Receiver (`log10x/edge-10x:1.1.153`) kept, at 45,716 rows/s. 2026-11-02 19:48 to 2026-11-05 03:47 UTC. The service was deleted at the end (`results/raw/teardown.jsonl`).

| Pair | Arm A's size | Units, A to B | Ratio | usageCost computeCHC per 15 minutes, A to B | Cut to step down done |
|---|---|---|---|---|---|
| 1 | the autoscaler's | 4.0 to 2.997 | 0.749 | 0.298 to 0.224 | 4.33 h |
| 2 | the autoscaler's, where pair 1 left it | 3.0 to 3.0 | 1.0 | 0.224 to 0.224 | no step in 10.25 h |
| 3 | 16 GiB by config, released at the cut | 4.0 to 3.0 | 0.750 | 0.298 to 0.224 | 4.21 h |
| 4 | 16 GiB by config, released at the cut | 4.0 to 3.0 | 0.750 | 0.298 to 0.224 | 2.91 h |

## Rerun

Needs a ClickHouse Cloud organization and API key, Docker, Python 3.12 or later and a `clickhouse` client binary (26.8 here). `cloud_api.py` reads the key from SSM or from `CHC_KEY_ID` and `CHC_KEY_SECRET` and never prints it. The scripts keep the service password and client config under `~/git/l1x-co/.claude-tmp/chce-secrets/` by default; `CHC_SECRET_FILE`, `CLIENT` and `CONF` move them.

1. **Split.** `split/run_slices.sh` replays the `otel-sample-200mb.log` asset from `log-10x/config` tag `otel-sample-v1` (checked by sha256) through four Receivers side by side and joins what they returned into `split/build/wire/returned.json`, in about an hour.
2. **Service.** Put the runner's address in `cloud/service.json`, then run `CHC_SECRET_FILE=<file> python3 cloud_api.py create cloud/service.json`. The service password goes to that file (mode 600), not to the terminal.
3. **Tables.** Apply `cloud/schema.sql` with the client, then `cloud/stage.sh` and `cloud/stage_b.sh`.
4. **Meters**, left running, each with `--service <id>` and an `--out` under `results/raw/`: `cloud/sample.py`, `cloud/meter.py --every 60 --lag 30` and `cloud/usage_poll.py`.
5. **Feed and queries**, left running: `cloud/load.py` and `cloud/queries.py --overlap 3`. Both follow `results/raw/control.json`, which `cloud/phase.py` writes.
6. **Probe.** `cloud/probe.py` with steps of 2,000 to 70,000 rows/s, 10 minutes each.
7. **Arms.** `cloud/arms.py`. Its docstring gives both forms this run used: `--pairs` for the natural pairs, `--forced` for the pairs with arm A's size set by config, then the read calibration.
8. **Report.** `cloud/arms_report.py --raw results/raw --lag-min 30` for every phase, segment and pair; `cloud/curve.py` for the probe. Both read the committed `.jsonl.gz` files as they are.

## Files

| Path | What |
|---|---|
| `RESULT.md` | Every figure, the file and field it came from, and what was not measured |
| `split/` | The engine split |
| `cloud/` | The service request, schema, stage, feed, queries, meters, driver and reports |
| `results/` | The split and stage readings, the service creation response |
| `results/raw/` | Every log the scripts wrote: `events.jsonl` (phases and size changes), `scaling-patches.jsonl`, `usage.jsonl`, `teardown.jsonl`, and the meter, feed, sampler and query logs gzipped |
