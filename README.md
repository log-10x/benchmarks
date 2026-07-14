# Log10x Benchmarks

Reproducible benchmarks behind the [Log10x](https://www.log10x.com/?utm_source=github&utm_medium=readme&utm_campaign=benchmarks&utm_content=hero)
engineering blog. Each folder is a self-contained benchmark: the exact commands, the tool
versions, the configs, and the committed reference numbers, so anyone — or any AI assistant —
can rerun it and check every figure a post cites.

## Principles

- **Public data.** Every corpus is a public dataset or release asset, fetched by the
  benchmark's own setup steps. Nothing depends on private data.
- **Exact, not approximate.** Tool versions are pinned; configs are committed; the driver is
  the source of truth. If a number is in a post, the code here produces it.
- **Committed reference results.** Each benchmark commits its `facts.json` / results so a
  rerun can be diffed against what the post reported.
- **Independently verifiable.** Where practical, a benchmark ships a second script that
  recomputes its headline numbers from primary files, not from the summary JSON.

## Benchmarks

| Benchmark | Question | Post |
|---|---|---|
| [`drain3-vs-log10x/`](drain3-vs-log10x/) | Can a log parser reduce a file *losslessly*, and does it assign stable pattern IDs? log10x vs [Drain3](https://github.com/logpai/Drain3) on the [loghub](https://github.com/logpai/loghub) 2k datasets. | *Templates you can't reverse* (draft) |
| [`clickhouse-inflate/`](clickhouse-inflate/) | What does it cost to expand compacted logs at query time in ClickHouse, and what did our own published benchmark actually measure? | [*We published a ClickHouse benchmark that measured nothing*](https://www.log10x.com/blog/) |

## Layout

```
<benchmark>/
  README.md            setup + exact run steps
  requirements.txt     pinned Python deps
  bench/               the driver scripts + committed reference results
  *.config.yaml        any pipeline configs the benchmark uses
```

Each benchmark resolves paths relative to its own folder, so you can run it from anywhere
(or set `BENCH_DIR` to point at data elsewhere). See the benchmark's own README to run it.

## License

Apache-2.0. See [LICENSE](LICENSE).
