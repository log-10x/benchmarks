# Splunk licence-metered volume, with and without 10x in front

One benchmark in the [log10x benchmarks](../) repository. It answers one
question: Splunk bills on what its licence meter counts, so what does putting
the 10x Receiver in front of Splunk do to that number, rather than to a file
size on disk.

## The question

Every Splunk-facing figure log10x has published was measured as a file
shrinking outside Splunk. The compaction post gives 63.7% on this capture; the
docs tell the reader to "validate with Splunk license usage reports". Until a
licence-metered run exists, a file ratio is standing in for a Splunk number, and
the two are not the same measurement: the meter counts what the indexer ingests,
which is neither the file size on disk nor what the forwarder sent.

So: the same capture, two arms, one difference. Arm one ships the raw file.
Arm two ships the same file after the 10x Receiver has compacted it, with the
three settings the Splunk app requires: `varMaxRecurIndexes: 0`,
`timestampZone: UTC` and `maxPerObject: 1`. Same forwarder, same
index settings, same instance, same licence day.

## The result

The full table, the Monitoring Console's own output and the raw rollup line are
in [`results/results.md`](results/results.md). The headline:

| Arm | What it carries | Licence-metered bytes | GB/day |
|---|---|---:|---:|
| baseline | the capture as it is | 214,841,731 | 0.200087 |
| compact | compact events, the template dictionary, and the app's own re-index | 80,653,626 | 0.075115 |

**62.46%**, measured by Splunk's licence meter on Splunk 10.4.3, through a
Universal Forwarder, on the Enterprise download trial. The same two files
measured on disk give 63.55%, and the gap between those two numbers is explained
below rather than averaged away.

Against Splunk's own dated figure for its own tool, "customers using Edge
Processor can routinely reduce ingest volumes by 30-50% without losing
analytical value" (2026-04-20), this run is higher on this capture. That
comparison is one dataset against a general claim, and it is worth exactly that.

**The expansion check passes, and that is part of the result.** All 157,228
compact events come back byte-identical, in UTC and in any other timezone, read
through the app's own macro and compared against the text that went in. It took
four defects closed to get there, three of them in pull requests against the
Splunk app that have not merged. Neither number should travel without the other.

## The three things the licence meter sees that a file ratio does not

**Line terminators are not billed.** The meter counts the bytes of each event's
raw text, and Splunk has already stripped the line break by then. The capture is
215,039,161 bytes on disk and 214,841,731 metered, exactly its 197,430 newlines
short. The compact arm loses its own newlines the same way, and as a
share of itself it loses more of them, 0.20% against the baseline's 0.09%,
because its bytes are fewer while its records are of the same order. So the
metered ratio comes out slightly better than the file ratio on the same two
files, 63.6% against 63.55%, before anything else is counted.

**The template dictionary is billed.** The compact events are unreadable without
it, so a deployment sends it, and Splunk meters it like anything else. It is
inside the compact arm here for that reason.

**The app re-indexes every template a second time.** This is the one a file
measurement cannot see at all. When the app's Consume KV alert fills the KV
store, it writes each template back into Splunk again as a searchable
`tenx_dml_pure` event, through `/services/receivers/simple`. That is metered
volume the compact arm causes. The app's default sends it to `main`, where it is
charged to whatever else lives there; this run points it at the compact arm's own
index so the arm is charged for it. The results file reports the compact arm both
ways.

## The daily rollup has no per-arm figure in it

The ask for this run named `index=_internal source=*license_usage.log
type=RolloverSummary` as the place to read GB/day. On Splunk 10.4.3 that rollup
is a single line per licence pool, carrying the day's total `b=` and no `idx`,
`st`, `s` or `h`. Split it by index and nothing comes back. The per-arm split has
to come from `type=Usage`, the per-minute records, binned to the same day.

That is not a workaround, it is what Splunk's own console does: the Monitoring
Console's Historic License Usage view reads RolloverSummary while it is unsplit
and switches to Usage the moment it is split by index, source, host or
sourcetype. The run reports both, keeps the empty output of the by-index rollup
query so the next reader does not think the run failed, and checks the one
identity that ties them together: the per-index Usage bytes sum to the rollup's
own daily total, 295,495,357, to the byte.

## The expansion check passes, and four defects had to be closed first

A volume win with wrong text is not a win. So every one of the 157,228 compact
events was read back through the app's own `tenx-inflate` macro and compared,
byte for byte, against the text that went in. Not a sample: all of them.

**All 157,228 come back byte-identical**, with the search head in UTC and with
it in the instance's own timezone. `results/expansion.json` and
`results/expansion_local_tz.json` carry the two runs.

That result holds only with the three Receiver settings this run pins and the
three app fixes named below. The first pass of this benchmark failed the same
check: 61,982 of 157,228 matched with the search head in UTC and 22,550 with it
anywhere else. Four separate defects came out of that pass, each with an exact
blast radius, because the events partition cleanly. They are recorded here
because the settings and the fixes are only legible next to what they repair,
and because a reader repeating the run on the app as it currently ships in
`main` will get the failing numbers, not these.

**Timestamps came back quoted, and marked with the wrong zone.** 2,466 of the
then 2,986 templates carried a timestamp slot, covering 134,669 events. The
cause was one function, `convert_java_to_strftime` in `tenx_dml_builder.py`,
which converts the engine's Java `SimpleDateFormat` pattern into a Splunk
`strftime` format and had no handling for Java's single-quoted literal sections.
In `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` the `'T'` and `'Z'` are literals; the converter
passed the quotes through and converted the letters inside them, so `Z`, which
marks UTC, became `%z`, a numeric offset. `2025-10-02T06:35:34.470Z` came back as
`2025-10-02'T'06:35:34.470'+0000'`. Fixed in `log-10x/splunk-app` #11.

**And they came back differently for different people.** The offset rendered was
the search head's, not the timestamp's, because the macro calls `strftime` and
Splunk renders in the viewer's timezone. The same stored event therefore read
one way in UTC and another way in Sydney. That is why the check is run twice,
once in each zone, and why the two rows being equal is itself part of the
result. Fixed in #12, which also keeps sub-second digits exact.

**A template carrying two timestamps kept only the last.** 23 templates held
more than one `$(...)` slot and the app stores a single `timestamp_format` per
template, taken from the last slot rather than the first. A template reading
`[$(yyyy-MM-dd HH:mm:ss,SSS)] INFO Kafka startTimeMs: $(+%s)` stored `+%%%S` and
rendered `[+%04]` where the date belonged. Those 23 templates accounted for all
5,892 events still wrong once #11 and #12 were in.

This one is closed on the Receiver side rather than in the app. The engine's
`maxPerObject` setting, unlimited by default, caps how many timestamps an event
gets a slot for. At `1` the first timestamp keeps its slot and any later one
becomes an ordinary variable whose literal text round-trips as it is, which was
checked on a two-timestamp fixture before it went into the run. `run.sh` sets it
and `template_stats.py` fails the run if any template still carries two slots.
The setting changes the compact form, which is why it moves the metered bytes
and why the whole run was repeated rather than patched.

**A template hash ending in a space never expanded.** 43 template hashes carried
a trailing space and all 45 of their events came back with the compact record
itself as the event text: the KV store lookup found nothing. Splunk's
search-time extraction trims the space while the KV store keeps it in both
`_key` and `pattern_hash`, so the lookup missed. Trimming all hashes produces no
collisions. Fixed in #13, which keys the store on the trimmed hash.

`results/expansion_after_app_fixes.json` holds the intermediate measurement, the
same check with #11 and #12 applied and neither of the other two closed: 151,336
of 157,228, 96.25%, equal in both timezones. It is kept because it is what
isolates the last two causes from the first two.

These are all separate from the back-reference defect the app's README carries.
`varMaxRecurIndexes: 0` is set throughout, so no back-referenced template is
produced, and the engine's own round trip on the same compact form is
byte-identical. What the first pass established is that the compact form held
the original text and the app did not give it back; what this one establishes is
that, with the four causes closed, it does.

**The app this was measured against is not the app in `main`.** The three fixes
are open pull requests, `log-10x/splunk-app` #11, #12 and #13, stacked in that
order, and the run installs their head. `results/results.md` names the commit.
Until they merge, the expansion figure belongs to that stack and not to a
released app.

## What is claimed and what is not

- **The volume figures are what this Splunk instance metered**, on one capture,
  on one licence day, through the forwarder path named in the results file. They
  are not a claim about a customer's estate, whose data, sourcetypes and
  forwarder topology are all different.
- **The compact arm gives the original text back on this run, under stated
  conditions.** Every event, byte for byte, in both timezones. The conditions
  are the three Receiver settings and the three app pull requests named above,
  none of them merged at the time of the run. On the app as it ships in `main`
  today, the same check fails. The volume number and the expansion result belong
  together, and quoting the first without the second would misdescribe what
  shipped.
- **One capture.** 36 Kubernetes containers from one small demo cluster, a
  Fluentd envelope around each container's stdout line. A Splunk estate is
  rarely shaped like this, and a second run on something syslog-shaped would say
  more to a Splunk buyer.
- **Nothing about indexed storage, search speed or retention.** The meter is
  about ingest.
- **Nothing about Splunk Cloud**, whose metering and ingest path are not this.

## Reproduce

```sh
./run.sh                  # everything, then tear the containers down
KEEP=1 ./run.sh           # leave them up
./run.sh encode licence   # some stages only, in the order given
```

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
| `results/` | the committed run |

`report.py` recomputes the licence figures from
`results/license_usage_rollover.log`, the rollup lines kept verbatim, rather
than from a search result, so the table and the primary log agree by
construction.

## Data

`otel-sample-200mb.log` from
[otel-sample-v2](https://github.com/log-10x/config/releases/tag/otel-sample-v2),
215,039,161 bytes, 197,430 lines, sha256
`aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`. The same
asset the [`otel-denominators/`](../otel-denominators/) and
[`clickhouse-clickstack/`](../clickhouse-clickstack/) benchmarks run on, which
is what lets the licence-metered figure here be set beside the 63.7% file ratio
there.
