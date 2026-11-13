# log10x benchmarks

This repository contains public, rerunnable measurements of what [log10x](https://www.log10x.com/?utm_source=github&utm_medium=readme&utm_campaign=benchmarks&utm_content=hero) does and does not do to log volume and cost on Splunk, Datadog, Elasticsearch, ClickHouse and CloudWatch. Most tests that ran on a platform read their figure from the platform itself, such as Splunk's license meter, Datadog's usage metric or ClickHouse's system tables. The two accounting benchmarks price the 10x engine's counts at list price and need no account.

Each directory has a short README with the result, a RECORD.md with the full method and every number, and the raw result files. For nine of the benchmarks, CI recomputes the committed figures from the kept raw counts on every pull request and every push to main, and fails if the two disagree. Several results favor a native feature or another tool, and those rows say so.

## Splunk

| Benchmark | What it measures | Result |
|---|---|---|
| [splunk-license](splunk-license/) | License meter bytes, original versus compact events | 63.91% fewer metered bytes, and every compact event read back as its original |

## Datadog

| Benchmark | What it measures | Result |
|---|---|---|
| [datadog-ceiling](datadog-ceiling/) | Standard indexing under a monthly budget as volume grows | Standard stayed at the budget as volume grew 2.9 times, and every line reached Datadog |
| [datadog-containment](datadog-containment/) | Stopping a log surge before it reaches Datadog, with or without a rule | The default limit for services without a rule sent 5,555 Postgres surge lines to S3, none outside the failure |
| [datadog-flex-accounting](datadog-flex-accounting/) | List-price cost of moving events from Standard to Flex | At demo volume, saves $3.40 to $6.04 a month against 30-day indexing and costs more against 15-day |
| [datadog-service-control](datadog-service-control/) | Per-pattern plan versus logger-name filters inside one service | Eight logger-name filters moved 24,440 of 29,043 events, the plan 23,854 |

## Elasticsearch

| Benchmark | What it measures | Result |
|---|---|---|
| [elastic-hot-tier-budget](elastic-hot-tier-budget/) | Hot-tier size under a budget during a 2.5x step | Hot stayed at 0.94 to 1.04 times the budget with moved lines on warm, and peaked at 1.43 times with them on hot |
| [elastic-hot-tier](elastic-hot-tier/) | How long moved lines stay on hot | Moved lines left hot 30 to about 110 minutes after writing, and bytes sent to hot still grew with load |
| [elastic-store-four-ways](elastic-store-four-ways/) | Index store of compact events versus native logsdb options | Logsdb with `pattern_text` was smallest, and compact on logsdb took 27.2% to 53.7% more |

## ClickHouse

| Benchmark | What it measures | Result |
|---|---|---|
| [clickhouse-clickstack](clickhouse-clickstack/) | Disk saved by compact events in the ClickStack schema | Compact events took 14.9% off, but the SQL decoder misread 78% of rows. Original text with a type column in the sort key took 13.1% off |
| [clickhouse-inflate](clickhouse-inflate/) | Query-time cost of decoding compact events | The fixed SQL decoded 137,418 rows in 548 ms, and the buggy SQL hit the memory cap |
| [clickhouse-cloud-elasticity](clickhouse-cloud-elasticity/) | ClickHouse Cloud compute bill when 65.3% of rows are written | Billed compute fell to 0.749 of the full feed's from a 4-unit start, and stayed the same from a 3-unit start |
| [clickstack-e2e](clickstack-e2e/) | Over-cap rows in an object store, queried together with hot rows | 13,010 rows hot and 24,526 in the store counted back to all 37,536 |
| [clickstack-e2e-gaps](clickstack-e2e-gaps/) | Counts, pruning and compute after moving rows to S3 | Counts matched, time-only queries opened all 180 objects, and a collector rule used less compute |
| [clickstack-rows-gate](clickstack-rows-gate/) | Which ClickHouse system table counts written rows exactly | `system.part_log` matched 22,367 rows exactly, and `system.query_log` did not |
| [clickstack-rows](clickstack-rows/) | Rows written at a set rate as load grew 2.5x | 0.91 to 1.13 of the set rate, with one window over the 1.10 bound, so the run failed as registered |

## CloudWatch

| Benchmark | What it measures | Result |
|---|---|---|
| [cloudwatch-ia-accounting](cloudwatch-ia-accounting/) | Bytes and cost of moving events to Infrequent Access | The plan for a 30% target moved 69.7% of bytes to Infrequent Access |

## Log patterns, compaction and grouping

| Benchmark | What it measures | Result |
|---|---|---|
| [pattern-identity](pattern-identity/) | Same pattern name in two places, versus Drain3 | The 10x engine named 299,997 of 300,000 probe lines the same, Drain3 0.6022 of shapes seen 2 to 10 times |
| [drain3-vs-log10x](drain3-vs-log10x/) | Pattern ID stability and byte-exact rebuild versus Drain3 | The 10x engine rebuilt 99.98% of lines and Drain3 66.48%, while Drain3 found fewer templates, closer to the hand labels |
| [intent](intent/) | How often one pattern mixes two logging statements | The 10x engine merged 0.01% to 0.21% of events, fewer than Drain3, which split fewer on two of three captures |
| [naming-stability](naming-stability/) | Pattern names across three engine releases | 0 of 582 and 0 of 2,687 patterns renamed, on two demo captures |
| [loghub-compaction](loghub-compaction/) | Compact form size on 14 full LogHub datasets | 44.7% fewer bytes over all 14, from 58.4% on Hadoop to 4.7% on HealthApp |
| [otel-denominators](otel-denominators/) | How the input's content changes a reduction figure | 64.00% as captured, 62.46% without the debug lines and added tag, 72.35% on application messages alone |
| [e103-grouping](e103-grouping/) | Multi-line events from many containers under one Fluent Bit tag | The 1.1.150 image mixed containers in 1,533 of 5,836 records, a build with the fix in none |

## How to rerun

Each directory's README gives the command that reruns the benchmark or recomputes its figures from the committed files, and links the full steps, pinned images and data sources. Most full runs need Docker and a public data download, and two need a platform account (a Datadog org with Flex Logs, a ClickHouse Cloud organization).

[RECORD.md](RECORD.md) has the principles the benchmarks follow, entry points and pinned dependencies for most of them, and what CI checks.

## License

MIT. See [LICENSE](LICENSE).
