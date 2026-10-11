# Splunk licence-metered volume, with and without 10x in front

One benchmark in the [log10x benchmarks](../) repository. It answers one
question: Splunk bills on what its licence meter counts, so what does putting
the 10x Receiver in front of Splunk do to that number, rather than to a file
size on disk.

## The question

A file shrinking on disk and Splunk's licence meter are different
measurements. The meter counts what the indexer ingests, which is neither the
file size on disk nor what the forwarder sent. This run reads the meter.

The same capture, two arms, one difference. Arm one ships the raw file.
Arm two ships the same file after the 10x Receiver has compacted it, with the
three settings the Splunk app requires: `varMaxRecurIndexes: 0`,
`timestampZone: UTC` and `maxPerObject: 1`. Same forwarder, same
index settings, same instance, same licence day.

## The result

Two runs on the same capture, the same Splunk 10.4.3, the same forwarder path and the same
licence meter. The full table for each, with the Monitoring Console's own output and the raw
rollup line, is in [`results-2026-10-10/results.md`](results-2026-10-10/results.md) and
[`results/results.md`](results/results.md).

| Run | Engine | Splunk app | Baseline, metered bytes | Compact, metered bytes | Licence-metered reduction |
|---|---|---|---:|---:|---:|
| 2026-10-10 | 1.1.139 | 1.1.5 | 214,841,731 | 77,532,468 | **63.91%** |
| 2026-09-18 | 1.1.79 | commit `9a203c6` | 214,841,731 | 80,653,626 | 62.46% |

**63.91%** on the current engine and app, measured by Splunk's licence meter on Splunk
10.4.3, through a Universal Forwarder, on the Enterprise download trial. The compact arm is
the compact events, 74,338,244 metered bytes, and the template dictionary, 3,194,224. The
same two files measured on disk give 63.87%; the next section explains the gap.

The 2026-09-18 run's compact arm also carried the app's searchable copy of each template,
2,441,744 metered bytes, which the app now writes unmetered. The rest of the difference is
the engine: 74,338,244 metered bytes of compact events against 75,017,247.

Splunk's own dated figure for its own tool is "customers using Edge Processor can routinely
reduce ingest volumes by 30-50% without losing analytical value" (2026-04-20). Both runs are
above that range on this capture.

**Every compact event expands back to its original text.** In both runs all 157,228 come back
byte-identical, in UTC and in any other timezone, read through the app's own macro and
compared against the text that went in.

## The three things the licence meter sees that a file ratio does not

**Line terminators are not billed.** The meter counts the bytes of each event's
raw text, and Splunk has already stripped the line break by then. The capture is
215,039,161 bytes on disk and 214,841,731 metered, exactly its 197,430 newlines
short. The compact arm loses its own newlines the same way, and as a
share of itself it loses more of them, 0.21% against the baseline's 0.09%,
because its bytes are fewer while its records are of the same order. So the
metered ratio comes out slightly better than the file ratio on the same two
files: 63.91% against 63.87% in the 2026-10-10 run, where nothing else is counted.

**The template dictionary is billed.** The compact events are unreadable without
it, so a deployment sends it, and Splunk meters it like anything else. It is
inside the compact arm here for that reason.

**The app's searchable copy of each template.** When the app's Consume KV alert
fills the KV store, it also writes each template into Splunk as a searchable
`tenx_dml_pure` event, sent here to the compact arm's own index so the arm is
charged for whatever the meter counts. In the 2026-09-18 run the app wrote that
copy through `/services/receivers/simple` and the meter counted 2,441,744 bytes.
The app writes it with `collect` as sourcetype `stash`, which Splunk does not
meter: 0 bytes in the 2026-10-10 run.

**The event time is free.** App 1.1.5 sets a compact event's `_time` from the
timestamp in its original line while the event is parsed. The compact events
metered exactly their raw text, 74,338,244 bytes, with that setting on.

## The daily rollup has no per-arm figure in it

The obvious place to read GB/day is `index=_internal source=*license_usage.log
type=RolloverSummary`. On Splunk 10.4.3 that rollup is a single line per licence
pool, carrying the day's total `b=` and no `idx`, `st`, `s` or `h`. Split it by
index and nothing comes back. The per-arm split has to come from `type=Usage`,
the per-minute records, binned to the same day.

Splunk's own console does the same: the Monitoring
Console's Historic License Usage view reads RolloverSummary while it is unsplit
and switches to Usage the moment it is split by index, source, host or
sourcetype. The run reports both, keeps the empty output of the by-index rollup
query so the next reader does not think the run failed, and checks the one
identity that ties them together: the per-index Usage bytes sum to the rollup's
own daily total to the byte, 292,374,199 in the 2026-10-10 run and 295,495,357 in
the 2026-09-18 run.

## Expansion

Every one of the 157,228 compact events was read back through the app's own
`tenx-inflate` macro and compared, byte for byte, against the text that went in.
**All 157,228 come back byte-identical** in both runs, with the search head in UTC
and with it in the instance's own timezone. `expansion.json` and
`expansion_local_tz.json` in each results directory carry the two checks.

The three Receiver settings are what the app's expansion relies on:

- `varMaxRecurIndexes: 0`: the app does not expand back-referenced templates,
  so the compact form carries none. The engine's own round trip on the same
  compact form is byte-identical.
- `timestampZone: UTC`: the app renders timestamps in UTC, so the compact form
  stores them in UTC.
- `maxPerObject: 1`: the app stores one timestamp format per template. At `1`
  the first timestamp in an event keeps its slot and any later one round-trips
  as ordinary text. `template_stats.py` fails the run if any template carries
  two slots.

Each run installed the app commit named in its results file. The 2026-09-18
commit's changes are in the app's `main`: Java quoted literals in timestamp
formats (`log-10x/splunk-app` #11), UTC rendering with exact sub-second digits
(#14), and a KV store keyed on the trimmed template hash (#13). The 2026-10-10
run installed app 1.1.5 (`log-10x/splunk-app` #41), which dates each compact
event by its original line, so the harness counts and reads compact events over
all time rather than over the last hours.

## What is claimed and what is not

- **The volume figures are what this Splunk instance metered**, on one capture,
  on one licence day, through the forwarder path named in the results file. They
  are not a claim about a customer's estate, whose data, sourcetypes and
  forwarder topology are all different.
- **Every compact event expands to its original text on both runs**, byte for
  byte, in both timezones, with the three Receiver settings above.
- **One capture.** 36 Kubernetes containers from one small demo cluster, a
  Fluentd envelope around each container's stdout line.
- **Nothing about indexed storage, search speed or retention.** The meter is
  about ingest.
- **Nothing about Splunk Cloud**, whose metering and ingest path are not this.

## Reproduce

```sh
./run.sh                  # everything, then tear the containers down
KEEP=1 ./run.sh           # leave them up
./run.sh encode licence   # some stages only, in the order given
```

The defaults reproduce the 2026-10-10 run: engine `log10x/pipeline-10x:1.1.139` pinned by
digest, Splunk and the Universal Forwarder at 10.4.3, results in `results-2026-10-10/`. The
2026-09-18 run is `E21_ENGINE=ghcr.io/log-10x/edge-10x:1.1.79 E21_RESULTS=$PWD/results` with
the app at commit `9a203c6` in `E21_APP_DIR`.

Stages are `data encode groundtruth splunk ingest kv expand licence report`.
Needs Docker with about 10 GB of free disk, since the Splunk image alone is
6.5 GB, and roughly two hours, most of it waiting for a licence day to end.
It stands up a throwaway Splunk container on the Enterprise download trial and
destroys it; it touches no existing Splunk.

### The licence day, and why the container gets a timezone

`RolloverSummary` is written when the licence day ends, at midnight in the
licence manager's own local time, and a partial day is not a result. A run
started at nine in the morning would otherwise wait fifteen hours for a number.
So `run.sh` gives the container a whole-hour timezone chosen to put its next
local midnight at least 75 minutes ahead of container start, which is long
enough for the whole ingest to sit inside one licence day with room to spare.
The rollover is an ordinary one and the day it summarises holds the entire run;
only its wall-clock position is chosen. `E21_MIN_LEAD` sets the margin.

### Sizing to the ceiling rather than around it

The download trial meters 500 MB a day. Both arms together are about 296 MB, so
the whole capture fits inside one licence day on one instance, and the two arms
go into separate indexes on that same day. Nothing here raises, resets or works
around the quota.

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `tenx-encode-splunk.config.yaml` | the published OUTER round-trip encode config |
| `tenx-decode.config.yaml` | the published decode config, for the engine round trip |
| `conf/indexer/`, `conf/uf/` | every Splunk and forwarder setting, as it ran |
| `conf/tenx_config.conf` | the one app setting changed, and why |
| `conf/searches/` | the licence searches, including the Monitoring Console's own |
| `build_groundtruth.py` | what each compact event's original text was, with its invariants |
| `template_stats.py` | fails the run if any template carries more timestamp slots than the app can reconstruct |
| `worst_slice.py` | the reduction per Kubernetes container, so the worst slice is named |
| `verify_expansion.py` | every compact event read back through the app, against that |
| `report.py` | renders `results/results.md` from the kept RolloverSummary lines |
| `results-2026-10-10/` | the 2026-10-10 run, engine 1.1.139 and app 1.1.5 |
| `results/` | the 2026-09-18 run, engine 1.1.79 |

`report.py` recomputes the licence figures from
`results/license_usage_rollover.log`, the rollup lines kept verbatim, rather
than from a search result, so the table and the primary log agree by
construction.

## Data

`otel-sample-200mb.log` from
[otel-sample-v2](https://github.com/log-10x/config/releases/tag/otel-sample-v2),
215,039,161 bytes, 197,430 lines, sha256
`aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`.
[otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1)
carries the same file (gzip sha256 `c118e55f…` in both releases). The same
asset the [`otel-denominators/`](../otel-denominators/) and
[`clickhouse-clickstack/`](../clickhouse-clickstack/) benchmarks run on, which
is what lets the licence-metered figure here be set beside the file ratios
there.
