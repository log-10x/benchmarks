# Drain3 stability: reordering vs four-way splits

Driver behind the Log10x blog post ["Drain pattern IDs: stable under reordering, not
under splits"](https://www.log10x.com/blog/the-drain-pattern-id-you-cant-trust/).

The script that produced the post's numbers was never committed; this directory is a
reconstruction (2026-07-17) from the post's method section, validated against the
post's published figures (table below). It is a different experiment from
[`../drain3-vs-log10x/`](../drain3-vs-log10x/), which measures A+B vs B+A order
stability on the LogHub 2k excerpts with default Drain3 config. Nothing here touches
that harness.

## Input

`otel-sample-200mb.log`, the release asset at
[log-10x/config `otel-sample-v1`](https://github.com/log-10x/config/releases/tag/otel-sample-v1):
215,039,161 bytes, 197,430 lines of OpenTelemetry-demo Kubernetes output.
sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`.

The copy at `https://log10x-public-assets.s3.amazonaws.com/samples/otel-k8s/large/input/otel-sample.log`
is 215,039,166 bytes and differs from the release asset in exactly one line
(line 9,731; 5 bytes). The release asset, which the post cites, is the input used here.

## Method

Each input line is a fluentd JSON wrapper; the `log` field is extracted and fed to
Drain3 (see reconstruction notes). A typed-token preprocessor runs first, in this
order: UUIDs to `<UUID>`, ISO-8601 timestamps to `<TS>`, IPv4 with optional port to
`<IP>`, `0x` literals and hex runs of 6+ chars containing a digit to `<HEX>`, bare
numbers to `<NUM>`; every line is truncated to 1,024 chars before masking.

Drain3 0.9.11 (pinned in `requirements.txt`), configured as the post states:
depth=6, similarity threshold 0.6, max 20 children per node, max 2,000 clusters,
parameter token `<*>`; `parametrize_numeric_tokens` left at its default (true); no
Drain3-level masking. A cluster's identity for every comparison is its template
string, never the internal cluster number.

- **Shuffle:** the full 197,430 lines in 30 seeded random orders; pairwise
  template-set Jaccard over all 435 run pairs.
- **Split:** 30 seeded trials; each partitions the lines into 4 disjoint quarters
  and runs a fresh Drain3 on each; 6 pairwise Jaccards per trial, reported as the
  mean of trial means with std across trials.
- **Per-event identity:** a seeded 10,000-line sample; the fraction of lines whose
  matched template string is identical across all 30 shuffle runs.

Seed: **42** (per-run seeds derive as `42*1000+run` and `42*2000+trial`). The
original run's seed was not recorded, so `results.json` reproduces exactly under
this seed, not the original one.

## Results vs the post

| quantity | post | this driver |
|---|---|---|
| templates, full corpus unshuffled | 1,450 | 1,463 |
| templates per shuffle run | 1,464 ± 2.7 | 1,471 to 1,481 |
| shuffle pairwise Jaccard (30 runs) | 0.9295 ± 0.0067, min 0.91 | 0.9300 ± 0.0078, min 0.9065 |
| four-way-split pairwise Jaccard (30 trials) | 0.1807 ± 0.0027, range 0.176 to 0.188 | 0.1840 ± 0.0023, range 0.180 to 0.191 |
| clusters per quarter | 601 ± 16 | 610 ± 16 |
| per-event identity, 10K sample, 30 reorders | 99.6% | 99.5% |

Arithmetic check on the split figure: mean shared templates per quarter pair 190,
mean union 1,030, 190 / 1,030 = 0.184, the same structure as the post's
184 / 1,018 = 0.1807.

## Reconstruction notes

The post's prose leaves two choices open. The ones that reproduce its numbers:

1. Drain3 clusters the **extracted `log` field**, not the raw wrapped JSON line.
   Raw lines also give a plausible unshuffled baseline (1,418 templates) but were
   not run to completion; the extracted field reproduces all figures above.
2. The shuffle Jaccard is **pairwise between all 30 runs**, not each run against a
   reference order.

Residual deltas against the post (+13 baseline templates, +0.003 split Jaccard) are
consistent with the unrecorded original seed and small preprocessor-regex
differences the prose does not pin down.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
curl -LO https://github.com/log-10x/config/releases/download/otel-sample-v1/otel-sample-200mb.log.gz
gunzip otel-sample-200mb.log.gz
.venv/bin/python3 stability_measured.py full otel-sample-200mb.log logfield
```

`results.json` committed here carries the per-run raw Jaccards for both experiments
and the summary statistics.
