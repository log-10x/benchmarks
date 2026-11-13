# LogHub compaction

How much smaller than the original logs is the 10x engine's compact form, on the 14 full public LogHub datasets? Across all 14 the compact form came to 44.7% fewer bytes, weighted by size. Per dataset the reduction ran from 58.4% on Hadoop down to 4.7% on HealthApp.

The compact form is the encoded events plus the template dictionary needed to expand them back. Both are counted before any codec, so the figure stacks with whatever codec the storage layer applies after, such as gzip or ZSTD.

## Result

The table shows the four datasets over 100 MB, the highest and lowest of the other ten, and the total.

| Dataset | Events | Input bytes | Compact bytes | Reduction |
|---|---:|---:|---:|---:|
| Hadoop | 186,697 | 48,595,595 | 20,212,363 | 58.4% |
| Spark | 32,952,127 | 2,941,224,304 | 1,248,606,093 | 57.5% |
| BGL | 4,728,216 | 743,185,031 | 482,351,424 | 35.1% |
| HDFS | 11,175,629 | 1,577,982,906 | 1,118,008,927 | 29.1% |
| Android | 1,555,005 | 192,270,829 | 153,830,847 | 20% |
| HealthApp | 204,648 | 23,529,930 | 22,432,794 | 4.7% |
| All 14 | 52,276,250 | 5,732,535,052 | 3,167,463,894 | 44.7% |

The four over 100 MB together came to 44.9%. The spread is wide, and HealthApp saves little. All 14 rows, with template counts, are in [results/results.md](results/results.md).

- Ten of the 14 match, byte for byte, the figures in the log10x post [Log compaction, measured](https://www.log10x.com/blog/log-compaction-measured/), and every reduction matches to the decimal place.
- Hadoop, Spark and OpenStack differ slightly. Each is many files read in directory order, and that order differs between the macOS file system of the post's run and the Linux container here.
- Linux differs because its template count changes from run to run. A two-digit day matches both the MMM d and the MMM dd date formats, and the format is chosen per event. Its reduction stays the same.

## How it was measured

The inputs are the full LogHub datasets from Zenodo record 3227177, not the 2,000-line excerpts, each checked against the md5 Zenodo publishes. The released engine image ran in a Linux container with its default symbol library, one encode config and no per-dataset compile. Each dataset started with an empty template cache, so its whole dictionary is charged to it. The reduction is one minus the size of the two output files (`encoded.log` for the events, `templates.json` for the dictionary) over the input bytes the engine read. Both outputs are hashed so a rerun can be compared byte for byte.

## Limits

- Storage on disk after gzip or ZSTD is not measured. A codec compresses both the original and the compact form.
- Query cost and a comparison with another tool's output are not measured.
- The figures are for these 14 datasets. HDFS is the HDFS_1 set, and the Thunderbird and Windows datasets were not measured.

## Run it

```
cd loghub-compaction
python3 report.py --check   # recompute every figure from results/ (no Docker)
./run.sh                    # all 14 datasets, then the report and its check
./run.sh Apache Linux       # some datasets
```

A full run needs Docker, Python 3 and about 5 GB of free disk at the peak (Spark). The script downloads the archives from Zenodo and pins the engine image log10x/pipeline-10x:1.1.133 by digest.

The full record is in [RECORD.md](RECORD.md): every dataset's events, bytes, ratio and template count set against the post's figures, the full method and the file list.
