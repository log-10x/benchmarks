# repro-otel-return

A controlled reproduction of the defects the ClickStack end to end run reported
on the OpenTelemetry Collector return path
(`../results/clickstack-e2e-2026-09-14.md`). Two containers, 56 crafted lines,
four variants. No ClickStack, no MinIO, no capture.

```
./repro.sh                 all four variants, then the analysis
./repro.sh resource        one variant
./probe/run.sh sweep       the parsson offset arithmetic on its own
```

`results.md` is the write up and carries every number. It is composed by
`analyze.py` from `results.head.md` and the returned records, so a rerun
regenerates it.

| File | What it is |
|---|---|
| `repro.sh` | the run: engine, collector, 56 lines, four variants |
| `make_lines.py` | writes `lines/crafted.jsonl` |
| `patch_config.py` | the asserted edits to the shipped engine config tree |
| `render_conf.py` | renders `conf/collector.yaml.tmpl` per variant |
| `analyze.py` | reads the returned records, writes `results.md` |
| `probe/` | the parsson offset arithmetic, replayed on its own |
| `patches/` | the two fixes, as unified diffs |
| `verify-patched.sh` | the same run against an engine built WITH both patches |
| `out/<variant>/wire/returned.json` | every record the receiver returned |
| `out-patched/<variant>/wire/returned.json` | the same, from the patched engine |

The engine config trees the run copies out of the image are not committed. The
returned records, the collector configs and the engine logs are.
