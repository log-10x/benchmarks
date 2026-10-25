# Elastic hot tier

One benchmark in the [log10x benchmarks](../) repository. It answers one question: with the
Receiver's per-statement byte budget in place and log10x-mcp's Elasticsearch frozen-tier recipe
(hourly rollover, and a frozen phase set to start one minute after it, which ILM acts on at its
next poll, every 10 minutes by default), how long do the lines it moves stay on the hot tier,
can they still be found by pattern hash once they are on frozen, and how much of the volume does
a fixed budget keep off hot as load grows, as the cluster's own APIs count it?

Every count of what Elasticsearch holds comes from the cluster, read every 10 minutes
(`_cat/indices`, `_cat/allocation`, `_ilm/explain`, and `_stats/store` hourly) into
[`results/meter.jsonl.gz`](results/meter.jsonl.gz). Counts of what the Receiver returned come
from Fluent Bit's local copies, slimmed to [`results/captures/`](results/captures/) (no log text).

## The result

Self-managed Elasticsearch 9.5.5 (one hot node, one frozen node, a filesystem snapshot
repository, trial licence), engine `log10x/edge-10x:1.1.147`, log10x-mcp 1.30.77, the published
OpenTelemetry demo sample replayed at 7 lines a second, 2026-10-21 23:14 to 2026-10-22 10:14 UTC.

| | Criterion | Result |
|---|---|---|
| 1 | Each tier-down index enters the frozen phase within rollover (1 hour) plus two poll intervals of its creation, at 0 bytes of local store | **Pass.** Indices 2 to 7: frozen phase 80.0 minutes after creation every time (rollover at 70.0, frozen phase 10.0 later), each mounted at 0 bytes. Index 1 sat empty from setup until the budget took hold and rolled over at the first poll after its first line. Index 8 received no line before the load stopped and was never rolled over, as ILM leaves an empty index. |
| 2 | From the capped phase on, the tier-down lines on hot never exceed the index being written plus the one mounting; the lines kept on hot follow the budget | **Pass.** At most 8.6 MB of tier-down data on hot at any reading, in at most two indices. In 4-minute windows counted from the capped start, no statement with lines moved kept more message bytes on hot than the budget, beyond the 5-line sample and the error keep count. |
| 3 | A term query on `tenx_hash` against the frozen indices returns what the local copy holds | **Pass.** The ten largest moved patterns: 49,785, 47,996, 17,700, 16,915, 11,172, 9,932, 3,285, 1,304, 631 and 516 documents on frozen, each equal to the local count. |
| 4 | Every line received is in a returned record, and every returned record is in Elasticsearch | **Pass.** 372,783 non-blank lines in and 372,783 back, in 301,980 records (the Receiver folds a multi-line event into one record): 142,444 kept and 142,444 documents in `tenx-app`; 159,536 moved and 159,536 documents across the tier-down indices. |
| 5 | Storm: error lines of the storming statement kept on hot per window at most its budget plus 50 | **Pass.** 109 to 113 a window against an allowance of 186, with 1,649 to 2,260 a window moved. |

**How long a moved line stays on hot.** ILM acts at its 10-minute poll, so it entered the frozen
phase 10 minutes after each rollover, but the `searchable_snapshot` action then waited one poll
each for shard history leases, the time-series end check and the force merge, so the original
index left hot and the mounted copy appeared 30 to 40 minutes after rollover (the meter reads
every 10 minutes). Each index lived 100 to 110 minutes on hot. A line written early in an
index's hour stayed up to about 110 minutes; one written just before rollover, 30 to 40. All of
it at ILM's default 10-minute poll (`indices.lifecycle.poll_interval`), which this run did not
change.

| Index | Created | Rolled over | Frozen phase | Last seen on hot | First seen mounted |
|---|---|---|---|---|---|
| 000002 | 01:25 | 02:35 | 02:45 | 03:05 | 03:15 |
| 000003 | 02:35 | 03:45 | 03:55 | 04:15 | 04:25 |
| 000004 | 03:45 | 04:55 | 05:05 | 05:25 | 05:35 |
| 000005 | 04:55 | 06:05 | 06:15 | 06:35 | 06:45 |
| 000006 | 06:05 | 07:15 | 07:25 | 07:45 | 07:55 |
| 000007 | 07:15 | 08:25 | 08:35 | 08:55 | 09:05 |

**How much a fixed budget keeps off hot.** One budget for every statement, set before the
capped phase where half of the second baseline hour's message bytes were over it, moved 59% of
the message bytes at the starting load and 65% to 73% an hour at 2.5 times it. The budget is per
statement, so growth spread across statements under it still reaches hot: the message bytes kept
on hot went from 5.25 MB in the last baseline hour to about 2.17 MB an hour capped and about
4.3 MB an hour at 2.5 times the load. Holding the hot tier at a size as load grows needs the budget
kept current against the tier; this run held it fixed.

## Whose statements moved

The budget moved 159,536 records, 42 MB of message text, from 15 statements. 86% of those bytes came from three statements of the OpenTelemetry Collector, the debug exporter's `Traces`, `Logs` and `Metrics` lines, and 5% from one Grafana statement (the storm line): code the account runs but does not write. No regular expression, fingerprint rule or per-service list was written for any of them; each line carried the engine's pattern hash from the Receiver, the same on every node running the same engine, library and configuration, and the hash queries in criterion 3 find them on frozen by that hash. The injected service's one new statement (`inventory`, 4%) was held from its first window with no entry of its own.

| Container | Records moved | Message MB | Share of bytes | Statements |
|---|---:|---:|---:|---:|
| opentelemetry-collector | 114,736 | 36.23 | 86.3% | 5 |
| grafana | 11,172 | 1.96 | 4.7% | 1 |
| inventory (injected) | 17,700 | 1.69 | 4.0% | 1 |
| cart | 13,848 | 1.55 | 3.7% | 3 |
| recommendation | 1,304 | 0.40 | 1.0% | 1 |
| ad | 768 | 0.12 | 0.3% | 2 |
| kafka | 8 | 0.00 | 0.0% | 2 |

From [`results/captures/tier_down.tsv.gz`](results/captures/tier_down.tsv.gz), by container, `tenx_hash` and `message_pattern`.

## The hourly table

Hours from the capped start. Message bytes are the UTF-8 size of each line's text in the
records the Receiver returned (local). `tenx-app` growth and the tier-down columns are the
cluster's `store.size` (cluster), which also moves with segment merges, so an hour's growth is
not exactly its documents' size.

| Hour (UTC) | Phase | Message bytes to hot | Message bytes moved | Moved | tenx-app growth on hot | Tier-down on hot at hour end | Tier-down docs on frozen at hour end |
|---|---|---:|---:|---:|---:|---:|---:|
| 00:15 | baseline | 5,254,073 | 12,768 | 0% | 4,791,108 | 249 | 0 |
| 01:15 | capped | 2,120,292 | 3,107,510 | 59% | 3,053,345 | 1,806,542 | 1,731 |
| 02:15 | capped | 2,166,152 | 3,079,135 | 59% | 2,916,215 | 2,971,517 | 1,731 |
| 03:15 | capped | 2,167,937 | 3,066,345 | 59% | 3,099,663 | 4,072,216 | 13,584 |
| 04:15 | capped | 2,197,761 | 3,107,231 | 59% | 4,282,683 | 2,934,268 | 25,238 |
| 05:15 | growth | 4,589,240 | 8,626,759 | 65% | 6,695,066 | 6,379,264 | 37,082 |
| 06:15 | growth | 4,174,512 | 11,471,373 | 73% | 6,574,067 | 8,612,903 | 68,850 |
| 07:15 | growth | 4,050,664 | 9,484,012 | 70% | 6,279,659 | 6,850,134 | 122,388 |
| 08:15 | drain | 0 | 0 | 0% | 1,349,761 | 249 | 159,536 |
| 09:15 | drain | 0 | 0 | 0% | 0 | 249 | 159,536 |

## How the budget was set

Written before the run in the method and not changed during it. `rig/cap.py` read the records the
Receiver returned between 00:14 and 01:14 (the second baseline hour), grouped them by container,
pattern and 4-minute window, and found the byte limit at which half of those bytes were over it:
**22,148 bytes per pattern per window per node** ([`results/cap.out`](results/cap.out)). The
Receiver was then relaunched with the values log10x-mcp renders for that fleet default:
`rateReceiverAbsoluteCap 22148`, `rateReceiverDefaultAction tier_down`, `outputOffload=true`
([`results/values/launch.json`](results/values/launch.json); the baseline's, with no budget, in [`results/values-baseline/`](results/values-baseline/)).

The budget held more than half: 59% of message bytes moved. The regulator sizes a line as the
UTF-8 size of the event's text, and the storm statement's kept count (about 112 a window, a
162-byte message) fits that text being the whole forwarded record rather than the message alone.
`cap.py` counted the message. This is noted, not resolved, here.

## The rig

Everything under [`rig/`](rig/). `compose.yaml` (two Elasticsearch nodes and Fluent Bit) plus the
Receiver service that `gen-receiver-values.mjs` writes from log10x-mcp's own renderers;
`es-setup.mjs` starts the trial licence, registers the snapshot repository and sends every request
in `elasticFrozenTierRecipe` verbatim; `fluent-bit/fluent-bit.conf` routes `routeState: tier_down`
to the `tenx-tierdown` alias and everything else to `tenx-app`, as the recipe tells the operator to;
`forward_send.py` replays the sample; `phases.sh` is the run; `meter.py` reads the cluster;
`analyze.py` scores it.

Where the rig differs from an install, and why:

- **No Kubernetes.** The rendered values read the policy files from a ConfigMap. The rig mounts
  header-only cap, action and total files instead, so the fleet budget and default action decide
  every line, and leaves out the opt-in config-generation file.
- **Measurement fields.** The rig adds `symbolMessageHashField tenx_hash` (log10x-mcp writes it
  for Datadog only; the Elastic recipe maps the field) and an `outputEncodeField` that keeps
  `routeState`, `message_pattern` and `severity_level` on the returned record.
- **The split.** log10x-mcp renders one Elasticsearch output; the recipe's note tells the operator
  to send tier_down lines to `tenx-tierdown`. The rig does that with `rewrite_tag`.
- **Load.** The published OpenTelemetry demo sample (`otel-sample-200mb.log`, release
  `otel-sample-v1`), not a live demo: 7 lines a second for 6 hours, then 17.5 lines a second for
  3 hours, plus one injected service (2 lines a second) and a 20-minute storm of one real Grafana
  `level=error` line at 10 lines a second.

## What this run does not show

- Anything about a bill. Elastic Cloud Hosted bills the configured size; this run shows bytes on
  a self-managed cluster's hot node.
- A hot tier held at a size under growth. The budget was fixed for the run.
- A comparison with a build on Elastic's own tools, or with logsdb.

## Reproduce

Docker with about 5 GB of memory free, Node 20, Python 3, and a log10x-mcp checkout built with
`npm run build`.

    cd elastic-hot-tier/rig
    # the replay feed and the storm line, from the published sample
    python3 make-replay.py <path to otel-sample-200mb.log>
    MCP=<log10x-mcp checkout> python3 detach.py ../results/phases.log ./phases.sh
    # after the run: bring the two nodes back on the same volumes and score
    RIG_DIR=$PWD RIG_DATA=$PWD/../results/data docker compose -p elastic-rig -f compose.yaml up -d es-hot es-frozen
    python3 analyze.py
