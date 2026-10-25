# Elasticsearch store, four ways

One benchmark in the [log10x benchmarks](../) repository. It answers one question: on
Elasticsearch 9.5.5, how much index store does the engine's compact form save over a raw index,
over logsdb index mode, and over logsdb with `message` mapped as `pattern_text`, on the same
sample? The compact form is indexed in standard mode and in logsdb mode, so there are five
variants; the comparison that decides is compact on logsdb against logsdb with `pattern_text`.

Two things to know before reading the table. The raw index holds the parsed record (one field per
key of the shipped JSON, the message in `message`), not each whole line as one field the way the
8.17.0 measurement did. And document counts differ by design: the three native indexes hold one
document per line, while the engine folds a multi-line event into one, so the compact indexes hold
one per event plus one per template. Each index is checked against its own input.

## The result

Not run yet. `results/results.md` will carry the table.

## Method

[`METHOD.md`](METHOD.md), written before the run: the sample, how the compact form is made, the
five index definitions, the measurement, and the checks.

## Reproduce

```
./run.sh             # encode twice, decode check, one Elasticsearch node, five variants twice, report
./run.sh report      # re-render results/results.md from results/
```

Needs Docker, Python 3 and `curl`; about 2 GB of memory for Elasticsearch and 3 GB of free disk.
The sample is fetched from the `otel-sample-v1` release of `log-10x/config` into `data/` unless
`ES4_SAMPLE` names a local copy; either way its sha256 is checked. The engine and Elasticsearch
images are pinned by digest. Every container is started detached under a fixed name and removed
with `docker rm -f -v`, on exit too.

## What is claimed and what is not

- Primary store size after a force merge to one segment, per variant, on this sample, with these
  images and a trial licence.
- Not query or ingest cost, not search-time decoding, not Elastic Cloud pricing. `METHOD.md`
  lists the rest.

## Files

| File | What it is |
|---|---|
| `METHOD.md` | the plan, written before the run |
| `run.sh` | the whole run |
| `bench.py` | the Elasticsearch side: licence, index definitions, loading, measurement, report |
| `results/compact.json` | the compact form: counts and sha256 of both encodes, whether they match, the decoded output's sha256 and the byte comparison with the sample |
| `results/licence.json` | the version, the response to creating a `pattern_text` index on the default licence, the trial |
| `results/rep<N>.json` | each repetition: per index store, documents, settings, leases, per-field bytes |
| `results/rep<N>/` | each index's mapping and `_disk_usage` output |
| `results/results.json`, `results/results.md` | the table, the ratios and the checks |
