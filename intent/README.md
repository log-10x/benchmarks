# Intent: does each pattern hold one logging statement?

A log pattern is useful when it stands for one thing the code does. A cap, a
sample rate or a route set on a pattern then acts on that one statement. This
benchmark measures that against ground truth. Every labelled event of two
captures of the OpenTelemetry demo (99.58% of otel215's events, 99.42% of rec1155's) carries
the source statement that wrote it, found in the program's own source at the
version that ran. Each tool's patterns are then scored against those labels. [METHOD.md](METHOD.md)
describes how a label is made.

Three outcomes, per event:

- **merged**: the event shares its pattern with a different statement that holds most of the pattern's events. This is the defect: two statements under one pattern share one cap, one sample rate, one route.
- **split**: the event sits outside its statement's most frequent pattern. One statement under several patterns can still be capped one pattern at a time, so a split costs rule count, not correctness.
- **exact grouping**: the event's statement has exactly one pattern, and that pattern holds only that statement.

Two tools are scored on the same events:
- the 10x engine (versions 1.1.132 and 1.1.133);
- [Drain3](https://github.com/logpai/Drain3) 0.9.11, with the settings of [`../pattern-identity`](../pattern-identity).

## Results

`otel215`: 215 MB, 157,228 events, 156,563 labelled.

| tool | merged events | split events | exact grouping | statements with one pattern of their own | patterns |
|---|---:|---:|---:|---:|---:|
| 10x engine 1.1.133 | 0.01% (13) | 4.59% | 91.38% | 77.59% of 299 | 2,277 |
| 10x engine 1.1.132 | 4.44% (6,944) | 4.59% | 78.83% | 75.92% of 299 | 2,274 |
| Drain3, strong arm | 0.05% (83) | 3.47% | 80.95% | 76.25% of 299 | 865 |
| Drain3, baseline arm | 0.06% (99) | 3.41% | 80.92% | 74.25% of 299 | 812 |
| Drain3, strong arm, per record | 4.48% (7,013) | 3.47% | 76.57% | 76.25% of 299 | 851 |

`rec1155`: 41,573 events, 41,333 labelled.

| tool | merged events | split events | exact grouping | statements with one pattern of their own | patterns |
|---|---:|---:|---:|---:|---:|
| 10x engine 1.1.133 | 0.15% (63) | 9.95% | 85.94% | 78.4% of 213 | 406 |
| 10x engine 1.1.132 | 1.1% (454) | 9.95% | 84.05% | 77.0% of 213 | 404 |
| Drain3, strong arm | 1.78% (734) | 10.37% | 28.42% | 63.38% of 213 | 386 |
| Drain3, baseline arm | 1.81% (749) | 10.49% | 28.26% | 62.91% of 213 | 420 |
| Drain3, strong arm, per record | 1.78% (734) | 10.35% | 79.79% | 65.26% of 213 | 377 |

Without the opentelemetry-collector container (57% of otel215's events, 46% of rec1155's):

| tool | otel215 merged | otel215 exact grouping | rec1155 merged | rec1155 exact grouping |
|---|---:|---:|---:|---:|
| 10x engine 1.1.133 | 0.02% (13) | 79.8% | 0.28% (63) | 73.91% |
| 10x engine 1.1.132 | 10.39% (6,944) | 50.41% | 2.04% (454) | 70.4% |
| Drain3, strong arm | 0.12% (79) | 55.61% | 3.3% (734) | 52.71% |
| Drain3, baseline arm | 0.14% (94) | 55.54% | 3.36% (749) | 52.42% |

[`results/results.md`](results/results.md) has every table:
- split shares without the collector;
- scores by whether the statement's source is in the engine's default library;
- the engine's origin and name scores;
- the Drain3 run statistics.

The `results/*.json` files list every merged pattern with its statements, and every split statement with its top patterns.

## Reading the numbers

**Merges.** 1.1.133 merges the fewest events on both captures.
- On otel215 the gap to Drain3 is small when Drain3 is given the engine's events: 13 events against 83. Drain3's merges there pair statements that differ in one word, such as Grafana's `starting to provision dashboards` and `finished to provision dashboards`, or OpenSearch's `Starting housekeeping task for auto refresh streaming jobs.` and its `Finished` twin.
- Fed one record at a time, as Drain3 normally runs, it also merges the cart service's three statements (6,930 events). The .NET console logger prints the same header line before each message, so every cart event starts with the same line. 1.1.132 made the same merge; 1.1.133 names such an event from its first record that holds a message.
- On rec1155, Drain3 merges 734 events against 63. The largest are payment's two OpenTelemetry log dumps (390 events each) and two product-reviews statements (225 each).

**Where Drain3 does better.**
- It splits fewer events on otel215: 3.47% against 4.59%, and 8.0% against 10.76% without the collector.
- Without the collector, more of otel215's statements get a pattern of their own: 77.36% against 74.72%.
- It produces about a third as many patterns.
- On otel215 statements whose source the engine's library does not list, its exact grouping is higher: 65.49% against 62.89%.

Two Grafana statements account for 1,331 of 1.1.133's 2,277 otel215 patterns. The migrator's `Executing migration` (`migrator.go:369`) yields 666 patterns, one per migration id, because the ids are made of words the library knows, and its `Migration successfully executed` twin yields 665.

**Exact grouping is all or nothing per statement.** One stray event makes every event of its statement count as not exact. Drain3 on rec1155 keeps 7,060 of the 7,063 events of the collector's `Traces` statement in one pattern. The other three sit in single-event patterns built from early lines, before the template generalized. Across the three debug-exporter statements, six such events decide whether 19,054 events count as exact. Fed per record, Drain3 builds none of them, and its exact grouping on rec1155 moves from 28.42% to 79.79% on an input that differs by 140 continuation records. Merged events is the stable comparison.

## Caveats

- **One application.** Both captures are the OpenTelemetry demo: two versions (2.2.0 and 2.1.3), two forwarders (Fluent Bit and Fluentd), two clusters. LogHub, the usual alternative, has template labels, not source statements.
- **The collector's debug exporter is half of otel215.** Its three statements are 85,739 of otel215's 157,228 events. The tables without the opentelemetry-collector container show the rest.
- **Unlabelled events are excluded.** 0.58% of rec1155's events and 0.42% of otel215's carry no label and are excluded from every score; [METHOD.md](METHOD.md) lists them by container.
- **The default library lists much of what runs.** The engine names a line from the library compiled into it: the 1.1.89 library, inside both engine images.
  - Its manifest lists the repository or image behind 144 of otel215's 289 code statements (145,612 of its 156,563 labelled events) and 199 of rec1155's 207 (39,902 of 41,333). These include the OpenTelemetry demo itself, Kafka and the collector.
  - That cuts both ways: where the source is listed, the engine can find the statement; where it is not (Grafana, fluentd, OpenSearch, Kubernetes), the engine names the line from the words in it that the library knows.
  - `results/results.md` splits every score this way. On otel215 statements outside the library, 1.1.133 merges 0.13% of events against Drain3's 0.86%, and Drain3's exact grouping is higher.
- **Event boundaries are the engine's.** An event is one record or a run of records the engine groups (a stack trace, a .NET header and its message). Drain3 is scored on those events, either given each event's text (the default rows) or fed one record at a time (the "per record" rows).
- **Who wrote the labels.** Log10x wrote them, from source code alone, and froze them on 2026-10-05 before any tool's output was read (`labels/FROZEN.json`). Every label names a repository, ref, path and line in `labels/statements.tsv`, so any one can be checked against its source.
- **The 1.1.133 column is in-sample.** Engine 1.1.133's group-lead rule (a multi-line event is named from its first record that holds a message) was developed after the freeze, with these two captures in view. Its column shows the rule on the data it was built against; a capture held out from that work is the out-of-sample test. Drain3 ran at its published settings, untuned.

## Drain3 settings

All taken from `../pattern-identity/bench/identity.py`, imported rather than copied:
- depth 6, `sim_th` 0.6, `max_children` 20, `max_clusters` 2,000;
- numeric tokens parametrized;
- the first 1,024 characters of each message;
- baseline arm: typed-token masking; strong arm: the masking block of Drain3's `examples/drain3.ini`.

Each run is the harness's reference pass: one instance learns the whole capture in memory, then every message is matched back read-only (`full_search_strategy="fallback"`) and named by the template it matches. No message went unmatched.

Fed one record at a time, the run reproduces the harness's own reference pass on otel215: 1,481 clusters under the strong arm and 1,465 under the baseline. drain3 0.9.11 on Python 3.13.11.

## Engines

| engine | image | library inside |
|---|---|---|
| 1.1.133 | `log10x/pipeline-10x:1.1.133@sha256:fe3dcdefdc2f42fa7117c4f63fe97b28508fbf1356725422703f0dfab55f2360` | the 1.1.89 library |
| 1.1.132 | `log10x/pipeline-10x:1.1.132@sha256:3e21cd41cde6d8263b5fa1b121ff15587a6bfe33ca4b3338b08bbb8c0e7a0c5f` | the 1.1.89 library |

The library files inside both images are byte-identical: manifest `4ad0993d5e32b9b6`, symbols `1c539d9496761c8d` (JSON) and `e5544b5f274b876d` (protobuf), first 16 hex digits of SHA-256.

Both engines run with their shipped configuration through the dev app (`@apps/dev`), which writes each event's pattern name, typed origin and text. `bench/engine.sh` mounts an empty directory over the sample input the image ships, so the engine reads the capture alone.

## Reproduce

```
./run.sh
```

This needs Docker, curl and Python 3. `run.sh` does the following:
- downloads otel215 from the `otel-sample-v1` release of log-10x/config and rec1155 from this repository's `intent-data-v1` release, checking both hashes;
- runs both engine images and the four Drain3 combinations;
- scores every run and writes `results/`.

On an Intel laptop with Docker Desktop it takes about 45 minutes.

To score another engine image:

```
bench/engine.sh log10x/pipeline-10x:<tag> cache/otel215.log out/
python3 bench/score.py otel215 out/events.jsonl
```

`bench/score.py` refuses a run whose events are not the labelled events one for one.

## Files

- `METHOD.md`: how the labels were made, coverage, exclusions, versions.
- `labels/`: per-event labels, the statement registry, text hashes for the alignment check, file names per repository for the origin score, and the freeze record.
- `bench/engine.sh`, `bench/events.config.yaml`: run an engine image over a capture.
- `bench/drain_arm.py`: the Drain3 arm.
- `bench/score.py`: the scorer.
- `bench/summarize.py`: writes `results/results.md`.
- `results/`: the committed output of `run.sh`.
