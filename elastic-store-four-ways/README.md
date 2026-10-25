# Elasticsearch store, four ways

One benchmark in the [log10x benchmarks](../) repository. It answers one question: on
Elasticsearch 9.5.5, how much index store does the engine's compact form save over a raw index,
over logsdb index mode, and over logsdb with `message` mapped as `pattern_text`, on the same
sample?

## The result

Not run yet. `results/results.md` will carry the table.

## Method

[`METHOD.md`](METHOD.md), written before the run: the sample, how the compact form is made, the
four index definitions, the measurement, and the checks.

## Reproduce

```
./run.sh             # encode, decode check, one Elasticsearch node, two repetitions, report
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
| `results/compact.json` | the compact form: counts, hashes, the two encodes compared, the decode |
| `results/licence.json` | the version, `pattern_text` on the default licence, the trial |
| `results/rep<N>.json` | each repetition: per index store, documents, settings, leases, per-field bytes |
| `results/rep<N>/` | each index's mapping and `_disk_usage` output |
| `results/results.json`, `results/results.md` | the table, the ratios and the checks |
