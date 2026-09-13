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
| [`pattern-identity/`](pattern-identity/) | Does a log line keep the same name over time, and does it get the same name in two places? A four-line replay inside one Drain3 process, two Drain3 instances fed disjoint halves of one stream, the template string separated from the integer Drain returns beside it, and engine-side coverage probed with invented vocabulary and two LogHub log sets. | Current. Behind *A log pattern name learned from traffic changes as more lines arrive* (draft). |
| [`clickhouse-inflate/`](clickhouse-inflate/) | What does it cost to expand compacted logs at query time in ClickHouse, and what did an earlier Log10x benchmark actually measure? | Current. Behind [*We published a ClickHouse benchmark that measured nothing*](https://www.log10x.com/blog/). |
| [`clickhouse-clickstack/`](clickhouse-clickstack/) | What does the compact form cost or save on disk in ClickHouse's own recommended log schema, the ClickStack `otel_logs` table, rather than in a single `String` column? Three arms so the row-count change from multi-line folding never hides inside a ratio, three codecs, and a check on whether the compact rows read back as the text they came from. | Current. Not behind a post. |
| [`drain3-vs-log10x/`](drain3-vs-log10x/) | Log10x against [Drain3](https://github.com/logpai/Drain3) on the [LogHub](https://github.com/logpai/loghub) 2k sets: does a line get the same pattern ID regardless of file and order, and does the reduced form reverse to the original bytes? | Retired as a benchmark. The post it was written for never shipped. Its `tenx-encode.config.yaml` and `tenx-decode.config.yaml` are still cited elsewhere as the published round-trip configs, so the folder stays. |

For anything about pattern identity, read `pattern-identity/`, not `drain3-vs-log10x/`. The two
ask overlapping questions and only the first is maintained.

## Layout

There is no single template. Each folder carries its own README with the exact run steps, and
each resolves its paths relative to itself, so a benchmark can be run from anywhere.

| Folder | Entry point | Pinned deps | Where results land | External data |
|---|---|---|---|---|
| `pattern-identity/` | `./run.sh` | `requirements.txt` (drain3 0.9.11, Python 3.13) and a pinned engine image digest | `results/` | Release assets from `log-10x/config` tag `otel-sample-v1`, plus two LogHub sets from Zenodo record 3227177, fetched into `data/` on first run |
| `clickhouse-inflate/` | `./run.sh` | pinned ClickHouse Docker image | `results.json` | none, the sample is committed |
| `clickhouse-clickstack/` | `./run.sh` | pinned engine image digest and a ClickHouse Docker image | `results/` | the `otel-sample-v2` release asset from `log-10x/config`, fetched into `data/` on first run |
| `drain3-vs-log10x/` | see its README | `requirements.txt` | `bench/facts.json`, `bench/results.json` | LogHub 2k sets, fetched into `loghub/` |

Large inputs are never committed. Each folder's `.gitignore` excludes whatever that benchmark
downloads or generates at run time.

## Continuous integration

`.github/workflows/ci.yml` syntax-checks every driver and runs the two mechanism checks that
need no download: `drain3-vs-log10x/smoke_test.py` and `pattern-identity/bench/replay.py`. The
full runs need Docker and several hundred megabytes of public data, so they are run by hand and
their artifacts are committed.

## License

MIT. See [LICENSE](LICENSE).
