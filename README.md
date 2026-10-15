# Log10x Benchmarks

Reproducible benchmarks behind the [Log10x](https://www.log10x.com/?utm_source=github&utm_medium=readme&utm_campaign=benchmarks&utm_content=hero)
engineering blog. Each folder is a self-contained benchmark: the exact commands, the tool
versions, the configs, and the committed reference results, so a reader or an assistant can
rerun it and check every figure a post cites.

## Principles

- **Public data.** Every log set is a public dataset or a public release asset, fetched by the
  benchmark's own setup steps. Nothing depends on private data, and no benchmark vendors a
  large file into git.
- **Exact, not approximate.** Tool versions are pinned, configs are committed, and the driver
  is the source of truth. If a number is in a post, the code here produces it.
- **Committed reference results.** Each benchmark commits the artifacts its own scripts wrote,
  so a rerun can be diffed against what the post reported.
- **Independently verifiable.** Where practical a benchmark ships a second script that
  recomputes its headline numbers from primary files rather than from a summary JSON.
- **Falsifiers are named before the run.** Where a benchmark states a threshold that would
  refute a Log10x claim, the script checks it on every run and prints the verdict, including
  the runs where the claim lost.

## Benchmarks

| Folder | Question it answers | Status |
|---|---|---|
| [`pattern-identity/`](pattern-identity/) | Does a log line keep the same name over time, and does it get the same name in two places? A four-line replay inside one Drain3 process, two Drain3 instances fed disjoint halves of one stream and two engine 1.1.142 instances fed the same halves, the template string separated from the integer Drain returns beside it, and engine-side coverage probed with invented vocabulary and two LogHub log sets. | Current. Behind *A log pattern name learned from traffic changes as more lines arrive* (draft). |
| [`otel-denominators/`](otel-denominators/) | A reduction figure is quoted against a denominator. What happens to it when the denominator changes? One Kubernetes capture measured three ways: as captured, with our own injected field and the collector's debug output removed, and on the log message text alone with the envelope discarded. | Current. Behind the OTel figures in [*Log compaction, measured*](https://www.log10x.com/blog/log-compaction-measured/). |
| [`clickhouse-inflate/`](clickhouse-inflate/) | What does it cost to expand compacted logs at query time in ClickHouse, and what did an earlier Log10x benchmark actually measure? | Current. Behind [*We published a ClickHouse benchmark that measured nothing*](https://www.log10x.com/blog/). |
| [`clickhouse-clickstack/`](clickhouse-clickstack/) | What does the compact form cost or save on disk in ClickHouse's own recommended log schema, the ClickStack `otel_logs` table, rather than in a single `String` column? Three arms so the row-count change from multi-line folding never hides inside a ratio, three codecs, and a check on whether the compact rows read back as the text they came from. | Current. Not behind a post. |
| [`clickstack-e2e/`](clickstack-e2e/) | Does the whole ClickHouse route work end to end, in containers? The released capture through a collector into the 10x receiver, the rows the receiver marked `offload` written to an object store and the rest inserted by ClickStack's own exporter, both sides read back as one table, the query shapes timed with their object-store requests, and a reconciliation of what left the receiver against what is stored. | Current. Behind [*Reading ClickHouse logs from the table and the bucket in one query*](https://www.log10x.com/blog/clickhouse-offload-merge-table/). |
| [`clickstack-e2e-gaps/`](clickstack-e2e-gaps/) | The six questions the end to end run left open, each over the whole capture: what a day predicate prunes across thirty days of objects, whether Vector can write the cold branch, whether the Retriever indexes and queries that layout, what a container killed mid-stream costs line by line, which dashboard answers change when rows leave the hot table, and how the per-type policy compares with a collector-only policy on insert and merge CPU. Plus a second pass on four of them: Vector 0.58.0 writing Parquet beside JSON with the Parquet reader's own counters, a `GROUP BY` and an `ORDER BY ... LIMIT` through the Merge table, the collector configured as its code owners prescribe, the `TTL TO VOLUME 'cold'` alternative costed on the same capture, and ClickHouse issue 116888 demonstrated with its guard. | Current. Not behind a post. |
| [`splunk-license/`](splunk-license/) | Splunk bills on what its licence meter counts, not on a file size. What does the 10x Receiver in front of Splunk do to that number? The same capture through the same Universal Forwarder into the same instance, twice, raw and compact, measured from `license_usage.log` and from the Monitoring Console's own searches, with every compact event read back through the 10x Splunk app and compared to the text that went in. | Current. Not behind a post. |
| [`datadog-flex-accounting/`](datadog-flex-accounting/) | Datadog bills Standard indexing per million events. When the 10x Receiver moves events from Standard to Flex Logs under the plan the 10x MCP writes, how many events and GB move, and what do they cost at Datadog's list prices? The released engine and MCP on one capture at three targets, counted two independent ways, priced per million events moved, with the custom metrics the Datadog metric output creates. Computed from the engine's counts at list price; no Datadog account needed. | Current. Not behind a post. |
| [`datadog-service-control/`](datadog-service-control/) | Inside one service a Datadog service filter cannot split the volume, so the rules a person writes are filters on the service's logger names. On the kafka container of two public captures of the same code, what does the per-pattern plan the 10x MCP writes move against the fewest `@logger.name` filters that move as many events, and what does each do on the second capture with nothing re-tuned? Computed from the engine's counts; no Datadog account needed. | Current. Not behind a post. |
| [`datadog-containment/`](datadog-containment/) | When a service floods its logs, does the released Receiver, installed with the values the MCP writes for Datadog, hold the flood before Datadog, including in a service with no rule, and what does it hold that it should not? The OpenTelemetry demo's own seeded failures on engine 1.1.142. | Current |
| [`cloudwatch-ia-accounting/`](cloudwatch-ia-accounting/) | CloudWatch bills ingestion per GB, and an Infrequent Access log group ingests at half the Standard rate. When the 10x Receiver moves events to Infrequent Access or offloads them to S3 under the plan the 10x MCP writes, how many GB move, and what do they cost at AWS's list prices for us-east-1? Computed from the engine's counts at list price; no AWS account needed. | Current. Not behind a post. |
| [`intent/`](intent/) | Does each pattern hold one logging statement? Every event of two OpenTelemetry-demo captures and a LogHub ZooKeeper capture is labelled with the source statement that wrote it, from the programs' own source, and the 10x engine (1.1.142, the current release, on all three; 1.1.132 and 1.1.133 on the demo captures; 1.1.136 on ZooKeeper) and Drain3 are scored against those labels: events merged with another statement, events split from their statement's main pattern, and exact grouping. | Current. Linked from [*How a Drain pattern group changes as more lines arrive*](https://www.log10x.com/blog/drain-pattern-groups-change/). |
| [`loghub-compaction/`](loghub-compaction/) | How much smaller is the engine's compact form than the original logs, on the 14 full public LogHub datasets, with the engine and library as they ship? The compact form is the encoded events plus the template dictionary, measured before any codec. | Current |
| [`drain3-vs-log10x/`](drain3-vs-log10x/) | Log10x against [Drain3](https://github.com/logpai/Drain3) on the [LogHub](https://github.com/logpai/loghub) 2k sets: does a line get the same pattern ID regardless of file and order, and does the reduced form reverse to the original bytes? | Retired as a benchmark. The post it was written for never shipped. Its `tenx-encode.config.yaml` and `tenx-decode.config.yaml` are still cited elsewhere as the published round-trip configs, so the folder stays. |

For anything about pattern identity, read `pattern-identity/`, not `drain3-vs-log10x/`. The two
ask overlapping questions and only the first is maintained.

## Layout

There is no single template. Each folder carries its own README with the exact run steps, and
each resolves its paths relative to itself, so a benchmark can be run from anywhere.

| Folder | Entry point | Pinned deps | Where results land | External data |
|---|---|---|---|---|
| `pattern-identity/` | `./run.sh` | `requirements.txt` (drain3 0.9.11, Python 3.13) and a pinned engine image digest | `results/` | Release assets from `log-10x/config` tag `otel-sample-v1`, plus two LogHub sets from Zenodo record 3227177, fetched into `data/` on first run |
| `otel-denominators/` | `./run.sh` | pinned engine image digest, plus the round-trip configs in `drain3-vs-log10x/` | `results/` | the `otel-sample-200mb.log` asset from `log-10x/config` tag `otel-sample-v1`, fetched into `data/` on first run |
| `clickhouse-inflate/` | `./run.sh` | pinned ClickHouse Docker image | `results.json` | none, the sample is committed |
| `clickhouse-clickstack/` | `./run.sh` | pinned engine image digest and a ClickHouse Docker image | `results/` | the `otel-sample-v2` release asset from `log-10x/config`, fetched into `data/` on first run |
| `clickstack-e2e/` | `./run.sh` | pinned ClickStack, engine, collector and MinIO images | `results/` | the `otel-sample-v2` release asset from `log-10x/config`, fetched into `data/` on first run |
| `clickstack-e2e-gaps/` | `./gap<N>_*.sh` | the same images by digest, plus Vector by digest; the receiver is the published `edge-10x` image | `results/` | the same `otel-sample-v2` asset, read from `../clickstack-e2e/data` |
| `splunk-license/` | `./run.sh` | pinned engine, Splunk and forwarder images, and the 10x Splunk app | `results/` | the `otel-sample-v2` release asset from `log-10x/config`, fetched into `data/` on first run |
| `datadog-flex-accounting/` | `./run.sh` | pinned engine image digest, log10x-mcp from npm at a pinned version, and the shared scripts in `accounting-lib/` | `results/` | the `otel-sample-200mb.log` asset from `log-10x/config` tag `otel-sample-v1`, checked by sha256 |
| `datadog-service-control/` | `./run.sh` | the same as `datadog-flex-accounting/` | `results/` | the same asset, and `rec1155.log.gz` from `log-10x/benchmarks` tag `intent-data-v1`, both checked by sha256 |
| `datadog-containment/` | `rig/go.sh` | engine and Fluent Bit images by digest, log10x-mcp from npm at a pinned version, OpenTelemetry demo 3.1.0 | `results/` | the demo's images, pulled by tag |
| `cloudwatch-ia-accounting/` | `./run.sh` | the same as `datadog-flex-accounting/` | `results/` | the same asset |
| `intent/` | `./run.sh` | engine image digests (1.1.132, 1.1.133, 1.1.136, 1.1.142) and drain3 0.9.11 from `pattern-identity/requirements.txt` | `results/` | the `otel-sample-200mb.log` asset from `log-10x/config` tag `otel-sample-v1` and `rec1155.log.gz` from this repository's `intent-data-v1` release, fetched into `cache/` on first run |
| `drain3-vs-log10x/` | see its README | `requirements.txt` | `bench/facts.json`, `bench/results.json` | LogHub 2k sets, fetched into `loghub/` |

Large inputs are never committed. Each folder's `.gitignore` excludes whatever that benchmark
downloads or generates at run time.

## Continuous integration

`.github/workflows/ci.yml` syntax-checks every driver and runs the two mechanism checks that
need no download: `drain3-vs-log10x/smoke_test.py` and `pattern-identity/bench/replay.py`. The
full runs need Docker and several hundred megabytes of public data, so they are run by hand and
their artifacts are committed. `otel-denominators/report.py` is checked the same way: CI
re-renders the committed CSV and fails if the rendered table does not match the committed
`results.md`, so an edited number in the table without a rerun is caught. `splunk-license`
carries the same guard against its own primary file: CI recomputes the licence figures from
the `RolloverSummary` lines the run kept verbatim and fails if `results.json` disagrees. `intent` re-renders `results/results.md` from the committed score files and fails if the tables disagree.

## License

MIT. See [LICENSE](LICENSE).
