# Naming stability across releases

One benchmark in the [log10x benchmarks](../) repository. It answers one question: when the
engine moves to its next release, how many events change their pattern name, pattern hash or
template hash, with the configuration and symbol library each release ships?

This is a folder of its own rather than a section of [`../intent`](../intent). The intent
benchmark scores grouping against source-statement labels, and a rename that keeps every
statement in one pattern leaves its scores unchanged. A rename rate is a property of two
releases and needs no labels, so it is measured here, and each new release adds two rows.

## The result

Engine releases 1.1.140, 1.1.141 and 1.1.142 on the two OpenTelemetry demo captures of
`../intent`, each release with its own image's configuration and library:

| capture | releases | events | pattern name changed | pattern hash changed | template hash changed | patterns renamed |
|---|---|---:|---:|---:|---:|---:|
| rec1155 | 1.1.140 to 1.1.141 | 41,573 | 0 | 0 | 0 | 0 of 582 |
| rec1155 | 1.1.141 to 1.1.142 | 41,573 | 0 | 0 | 0 | 0 of 582 |
| otel215 | 1.1.140 to 1.1.141 | 157,228 | 0 | 0 | 0 | 0 of 2,687 |
| otel215 | 1.1.141 to 1.1.142 | 157,228 | 0 | 0 | 0 | 0 of 2,687 |

Each pair cut each capture into the same events, so events are compared one for one. No event
changed its pattern name, its pattern hash (`tenx_hash`, the hash of the name) or its template
hash, so no pattern is listed as changed ([`results/results.md`](results/results.md)).

These pattern counts take every event: 2,687 on otel215 and 582 on rec1155 for 1.1.142.
[`../intent`](../intent) counts the patterns of labelled events only and reports 2,277 on
otel215 and 406 on rec1155 for the same 1.1.142 image. The counts differ by 410 on otel215 and
176 on rec1155. The difference is the patterns that only unlabelled events take. The two runs
cut each capture into the same events and give every event the same pattern name. On otel215
the 665 unlabelled events take 411 patterns, and one of them, `Starting`, also names a labelled
event, so they add 410. On rec1155 the 240 unlabelled events take 176 patterns that no labelled
event shares, so they add 176. In frontend-proxy, which has no labelled events, each unlabelled
event takes a pattern of its own: 114 on otel215 and 115 on rec1155, most of them lines of
Envoy's startup listing. The next largest are opensearch with 83 patterns, jaeger 58 and
prometheus-server 38 on otel215, and postgresql 23 and flagd 13 on rec1155.
[`../intent/bench/pattern_counts.py`](../intent/bench/pattern_counts.py) computes these numbers
from the two runs' events ([otel215](../intent/results/pattern-counts-1.1.142_otel215.json),
[rec1155](../intent/results/pattern-counts-1.1.142_rec1155.json)).

## What changed in each release, and what these captures exercise

The three images carry the same symbol library files, the 1.1.89 library
([`results/library.tsv`](results/library.tsv)). The changes are in the engine and in the
shipped configuration.

- **1.1.141.** Its [release notes](https://github.com/log-10x/pipeline-releases/releases/tag/1.1.141)
  say the engine is unchanged from 1.1.140 and the configuration and modules change. 18 files
  of the shipped configuration differ, among them the group, template and rate modules
  ([`results/config-diff.txt`](results/config-diff.txt)). The one change in those notes that
  touches how events are cut or named is that a line opening with the ANSI dim code, as Rust `tracing` prints a coloured timestamp,
  now starts its own event. Neither capture holds such a line (0 records in each), so that
  change had nothing to act on here. The same notes report the intent benchmark's merged and
  split counts unchanged on these two captures.
- **1.1.142.** Its [release notes](https://github.com/log-10x/pipeline-releases/releases/tag/1.1.142)
  list two engine changes; no file of the shipped configuration differs from 1.1.141. The
  group flush timer now counts per source, which the notes describe on the forwarder input,
  where batches arrive over time; these runs read each capture as a file. A timestamp
  fraction that starts with `1000` now keeps its second, which the notes report on 3 of
  67,070 events of other public logs; no event here changed.

So on these captures, read as files, neither release changed a name, and neither capture
exercises the ANSI case or a forwarder connection's timing.

## Limits

- **Two captures of one application.** Both are the OpenTelemetry demo (versions 2.2.0 and
  2.1.3). Another application, or the ANSI-coloured lines 1.1.141 regroups, can rename where
  these do not.
- **File input only.** The 1.1.142 flush change is described for the forwarder input; a run
  through a forwarder is not measured here.
- **Three releases.** Releases before 1.1.140 are not compared. In `../intent`, 1.1.132 and
  1.1.133 group otel215 differently (6,944 merged events against 13), so names changed
  between those two. Adding an image to `RELEASES` in `run.sh` adds its pair.
- **A library change is not measured.** All three images carry the same library files. A
  new library is where names built from library words would move, and none shipped between
  these releases.
- **No compatibility policy is stated here.** This folder measures what happened between
  releases; it does not promise what future releases will do.

## Method

- **Captures.** `otel215` (the `otel-sample-200mb.log` asset of `log-10x/config` release
  `otel-sample-v1`) and `rec1155` (this repository's `intent-data-v1` release), checked by
  sha256 as `../intent` checks them.
- **Engines.** Each release's `log10x/pipeline-10x` image by digest (in `run.sh`), the dev app
  (`@apps/dev`) with the image's shipped configuration, and an output module
  (`bench/events.config.yaml`) that writes each event's `message_pattern`, `tenx_hash`,
  `templateHash` and text. `bench/engine.sh` mounts an empty directory over the sample input
  the image ships, so the engine reads the capture alone.
- **What each image ships.** `run.sh` copies the symbol library and the configuration tree
  out of each image and records their SHA-256 (`results/library.tsv`,
  `results/config-<version>.sha256`, `results/config-diff.txt`).
- **Comparison.** `bench/compare.py` compares consecutive releases event by event when both
  cut the capture into the same events, and record by record otherwise. A pattern of the
  earlier release counts as renamed when any of its events carries another name in the later
  one.

The runs were made on 2026-10-15 with no other container running on the host.

## Reproduce

```
NS_PRUNE=1 ./run.sh
```

Needs Docker, curl and Python 3. `run.sh` downloads the two captures (or reuses them from
`NS_CACHE`), pulls each image, records what it ships, runs it on both captures, and writes
`results/`. `NS_PRUNE=1` removes each image the script pulled once its runs are done, so one
release image is on disk at a time. On an Intel macOS laptop with an idle host each release's
runs took one to three minutes for both captures, plus the image pull. `python3 bench/compare.py --render` rebuilds
`results/results.md` from the committed `results/compare.json`; CI checks that the two agree.

## Files

- `run.sh`, `bench/engine.sh`, `bench/events.config.yaml`: run each release over each capture.
- `bench/compare.py`: the comparison and `results/results.md`.
- `results/`: `compare.json`, `results.md`, `library.tsv`, `config-<version>.sha256`,
  `config-diff.txt`.
