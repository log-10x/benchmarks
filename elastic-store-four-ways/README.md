# Elasticsearch store, four ways

One benchmark in the [log10x benchmarks](../) repository. It answers one question: on
Elasticsearch 9.5.5, how much index store does the engine's compact form save over a raw index,
over logsdb index mode, and over logsdb with `message` mapped as `pattern_text`, on the same
sample? The compact form is indexed in standard mode, in logsdb mode, and in logsdb mode sorted
on its template id; the comparison that decides is compact on logsdb against logsdb with
`pattern_text`.

Two things to know before reading the table. The raw index holds the parsed record: one field per
key of the shipped JSON, the message in `message`. And document counts differ by design: the three native indexes hold one
document per line (197,430), while the engine folds a multi-line event into one, so the compact
indexes hold one per event (157,228) plus one per template (3,030). Each index is checked
against its own input.

## The result

Elasticsearch 9.5.5 (Lucene 10.5.1) on a trial licence, engine
`ghcr.io/log-10x/edge-10x:1.1.150`, the published OpenTelemetry demo sample (215,039,161 B,
197,430 lines). Primary store after a force merge to one segment, `best_compression` on every
index, two repetitions:

| Variant | Index mode | `message` | Store, rep 1 | Store, rep 2 | Mean | Of (a) | Of (b) |
|---|---|---|---:|---:|---:|---:|---:|
| (a) raw | standard | `text` | 20,108,998 B | 20,106,803 B | 20,107,900 B | 100.0% | 167.6% |
| (b) logsdb | logsdb | `text` | 12,003,158 B | 11,997,590 B | 12,000,374 B | 59.7% | 100.0% |
| (c) logsdb + `pattern_text` | logsdb, sorted on `message.template_id` | `pattern_text` | 6,977,160 B | 6,972,360 B | 6,974,760 B | 34.7% | 58.1% |
| (d) compact | standard | encoded event | 14,909,550 B | 14,901,237 B | 14,905,394 B | 74.1% | 124.2% |
| (e) compact on logsdb | logsdb | encoded event | 10,721,205 B | 10,718,972 B | 10,720,088 B | 53.3% | 89.3% |
| (f) compact on logsdb, sorted | logsdb, sorted on `l1x_tid` | encoded event | 8,875,307 B | 8,872,791 B | 8,874,049 B | 44.1% | 73.9% |

The compact variants' store includes the template dictionary index (537,262 B).

**Logsdb with `pattern_text`, sorted on its template id, takes less store than the compact form
in every mode.** Compact on logsdb (e) is 153.7% of (c), 53.7% larger; sorted the same
way on its own template id (f), 127.2% of (c), 27.2% larger. The native pair alone holds
this sample in 34.7% of the raw index's store, 65.3% less. Over (a) and (b) the compact form still saves: (e) is 53.3% of (a) and
89.3% of (b).

Where the difference sits, from `_disk_usage` (repetition 1): the stored compact text in (f),
`message._original`, is about the size of what `pattern_text` stores for (c),
`message.args` plus `message.template`. What the compact form adds is the inverted index over the
encoded `message`, which indexes every variable value as a term, the container, pod and image
ids folded into each event included. In (c) those values sit in `keyword` doc values instead.

### Amendment, 2026-10-25

The sort setting alone did not reach Lucene: with `index.logsdb.default_sort_on_message_template:
true` and documents that carry no `host.name`, the segments of (c) carried a sort on `@timestamp`
only, and (c) measured 10,649,904 B, 52.9% of (a). That run is in
[`results-setting-only/`](results-setting-only/), where the sort check fails. (c) sets
`index.sort.field` explicitly, as Elastic's `pattern_text` page shows in its "Custom sorting"
example, and (f) gives the compact form the same sort on its own template id. `METHOD.md` records
the amendment at its end.

### The licence

`pattern_text` is an Enterprise feature, and the basic licence accepts it with templating off.
On the default basic licence, before the trial, creating a logsdb index with `message` as
`pattern_text` returned 200 and a document indexed (201), and the mapping came back as `{"type": "pattern_text", "disable_templating": true}` and the source mode as
`STORED`: templating off and no synthetic source. On the trial, (c)'s mapping is plain
`{"type": "pattern_text"}`. Both are in `results/licence.json`.

### The compact form

The two encodes of the sample are byte-identical: 157,228 events and
3,030 templates, 74,140,583 B encoded plus 3,281,830 B dictionary,
64.0% under the sample before any codec. The dictionary followed by the events decodes to the
sample byte for byte (decoded output sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`). Hashes of both
encodes are in `results/compact.json`.

## Method

[`METHOD.md`](METHOD.md), written before the run, with its amendment: the sample, how the compact
form is made, the index definitions, the measurement, and the checks. All 66 checks pass in
`results/results.md`.

## Reproduce

```
./run.sh             # encode twice, decode check, one Elasticsearch node, six variants twice, report
./run.sh report      # re-render results/results.md from results/
```

Needs Docker, Python 3 and `curl`; about 2 GB of memory for Elasticsearch and 3 GB of free disk.
The sample is fetched from the `otel-sample-v1` release of `log-10x/config` into `data/` unless
`ES4_SAMPLE` names a local copy; either way its sha256 is checked. The engine and Elasticsearch
images are pinned by digest. Every container is started detached under a fixed name and removed
with `docker rm -f -v`, on exit too. The whole run takes about 10 minutes.

## What is claimed and what is not

- Primary store size after a force merge to one segment, per variant, on this sample, with these
  images and a trial licence.
- Not query or ingest cost, not search-time decoding with the l1es plugin, not
  Elastic Cloud pricing, not a compact form of the message text alone with the metadata kept as
  fields. `METHOD.md` lists the rest.

## Files

| File | What it is |
|---|---|
| `METHOD.md` | the plan, written before the run, and its amendment |
| `run.sh` | the whole run |
| `bench.py` | the Elasticsearch side: licence, index definitions, loading, measurement, report |
| `results/compact.json` | the compact form: counts and sha256 of both encodes, whether they match, the decoded output's sha256 and the byte comparison with the sample |
| `results/licence.json` | the version, the response to creating a `pattern_text` index on the default licence, the trial |
| `results/rep<N>.json` | each repetition: per index store, documents, segments and their sort, settings, leases, per-field bytes |
| `results/rep<N>/` | each index's mapping and `_disk_usage` output |
| `results/results.json`, `results/results.md` | the table, the ratios and the checks |
| `results-setting-only/` | the run before the amendment, (c) with `default_sort_on_message_template` alone |
