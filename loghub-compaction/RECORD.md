# LogHub compaction

One benchmark in the [log10x benchmarks](../) repository. It answers one question: how much
smaller is the engine's compact form than the original logs, on the 14 full public LogHub
datasets, with the engine and library as they ship.

The compact form is the encoded events plus the template dictionary needed to expand them
back. The reduction is measured before any codec (gzip, ZSTD), so it stacks with whatever
the storage layer applies after.

## The result

Engine `log10x/pipeline-10x:1.1.133` by digest, the 1.1.89 symbol library it ships, each
corpus cold:

<!-- generated:table -->
| Corpus | Events | Input | Compact (encoded + dictionary) | Reduction | Ratio | Templates | Against the ledger |
|---|---:|---:|---:|---:|---:|---:|---|
| Hadoop | 186,697 | 48,595,595 B | 20,212,363 B | 58.4% | 2.4x | 931 | events 186,697 against 186,695; compact bytes 20,212,363 against 20,198,860; templates 931 against 888 |
| Spark | 32,952,127 | 2,941,224,304 B | 1,248,606,093 B | 57.5% | 2.36x | 3,370 | events 32,952,127 against 32,952,122; compact bytes 1,248,606,093 against 1,248,618,288; templates 3,370 against 3,377 |
| Apache | 52,004 | 5,135,876 B | 2,295,929 B | 55.3% | 2.24x | 371 | equal |
| OpenSSH | 655,147 | 73,417,506 B | 36,854,297 B | 49.8% | 1.99x | 3,032 | equal |
| Proxifier | 21,329 | 2,541,814 B | 1,353,818 B | 46.7% | 1.88x | 1,854 | equal |
| Zookeeper | 74,380 | 10,426,438 B | 5,673,286 B | 45.6% | 1.84x | 157 | equal |
| Linux | 25,567 | 2,349,686 B | 1,303,867 B | 44.5% | 1.8x | 1,262 | compact bytes 1,303,867 against 1,304,303; templates 1,262 against 1,266 |
| HPC | 330,461 | 33,553,503 B | 20,485,336 B | 38.9% | 1.64x | 2,045 | equal |
| BGL | 4,728,216 | 743,185,031 B | 482,351,424 B | 35.1% | 1.54x | 136,461 | equal |
| Mac | 107,220 | 16,879,552 B | 11,391,093 B | 32.5% | 1.48x | 2,466 | equal |
| OpenStack | 207,820 | 61,442,082 B | 42,663,820 B | 30.6% | 1.44x | 8,134 | compact bytes 42,663,820 against 42,663,612; templates 8,134 against 8,133 |
| HDFS | 11,175,629 | 1,577,982,906 B | 1,118,008,927 B | 29.1% | 1.41x | 279 | equal |
| Android | 1,555,005 | 192,270,829 B | 153,830,847 B | 20% | 1.25x | 29,400 | equal |
| HealthApp | 204,648 | 23,529,930 B | 22,432,794 B | 4.7% | 1.05x | 1,341 | equal |

**All 14:** 52,276,250 events, 5,732,535,052 B in, 3,167,463,894 B compact, byte-weighted reduction 44.7%. The 4 over 100 MB (Spark, BGL, HDFS, Android): 44.9%.
<!-- /generated:table -->

The last column sets each corpus against the measurement the compaction post's figures come
from (the ledger, `ledger.json`). That run used a local build of the same engine version on
macOS; this one uses the released image in a Linux container. Ten of the fourteen reproduce
it byte for byte, and every reduction holds to the decimal place. Where a corpus is many files (Hadoop, Spark, OpenStack) the engine reads
them in directory order, which differs between the two file systems, so multi-line grouping
and the order templates are first seen move slightly. Linux's template count varies from run to run on any setup, because two-digit days
match both `MMM d` and `MMM dd` and the format is chosen per event; its reduction does not.

## Method

- **Inputs.** The full datasets of [LogHub](https://github.com/logpai/loghub) from
  [Zenodo record 3227177](https://zenodo.org/records/3227177), not the 2,000-line excerpts.
  `corpora.tsv` names each file, its md5 as Zenodo publishes it, and the files of the archive
  the engine reads (Hadoop's 978 container logs, Spark's 3,852, OpenStack's three). HDFS is
  `HDFS_1`. Thunderbird (2.0 GB compressed) and Windows (1.7 GB) are not measured.
- **Engine.** `log10x/pipeline-10x:1.1.133@sha256:fe3dcdefdc2f42fa7117c4f63fe97b28508fbf1356725422703f0dfab55f2360`,
  with its default symbol library and no per-corpus compile.
- **Config.** `tenx-encode.config.yaml`, copied unchanged from
  [`drain3-vs-log10x/`](../drain3-vs-log10x/) at commit `0fb1d10`, the config the post's
  reproduce section names. It writes `encoded.log` (one encoded event per line) and
  `templates.json` (one template per line).
- **Cold.** Each corpus starts with an empty template cache, so its whole dictionary is
  charged to it.
- **Counts.** Input bytes and lines are summed over the files the engine read; events are the
  lines of `encoded.log`, templates the lines of `templates.json`. Reduction is
  1 - (`encoded.log` + `templates.json`) / input. The container runs in UTC; timestamps inside
  `encoded.log` follow the time zone, byte counts do not.

`results/<corpus>.json` keeps each corpus's counts and the sha256 of both output files;
`results/results.md` lists them. The outputs themselves are not kept here (Spark's alone is
1.2 GB); a rerun on the same image compares against the hashes.

## Reproduce

```
./run.sh                   # all 14, then the report and its check
./run.sh Apache Linux      # some corpora
./run.sh report            # re-render from results/
```

Needs Docker, Python 3 and about 5 GB free at the peak (Spark). Each archive is downloaded
once into `data/tar/` and checked against Zenodo's md5; each corpus's extracted input and
outputs are deleted once hashed (`LC_KEEP=1` keeps them). `report.py --check` recomputes
`results/results.json` and the table above from `results/<corpus>.json` and fails on any
difference; CI runs it.

## What is claimed and what is not

- The reduction of the compact form against the original bytes, per corpus and in total, on
  these files, with this engine and library.
- Not storage after a codec, which compresses both sides; not query cost; not a comparison
  with another tool's output.

## Files

| File | What it is |
|---|---|
| `run.sh` | the whole run, per corpus |
| `corpora.tsv` | each corpus's Zenodo file, md5 and the files the engine reads |
| `tenx-encode.config.yaml` | the encode config, unchanged from `drain3-vs-log10x/` at `0fb1d10` |
| `measure.py` | counts one corpus's input and outputs and hashes the outputs |
| `report.py` | renders `results/results.json`, `results/results.md` and the table above; `--check` fails on drift |
| `ledger.json` | the figures the compaction post carries, from the 2026-10-05 measurement |
| `results/<corpus>.json` | each corpus's counts and output hashes |
