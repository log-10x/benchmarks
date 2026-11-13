# LogHub compaction

A log platform meters ingest by the byte, and most bytes in a log line are repetitive text. 10x stores each line's repeated text once as a template, and ships each line as that template's hash plus the line's values. The 14 LogHub datasets measured here hold 52,276,250 events and 5,732,535,052 bytes of input. Weighted by input bytes, they reduce 44.7%, and the spread across them is wide.

Reduction means the bytes of the compact form, the encoded events plus the template dictionary needed to expand them, against the bytes of the original file, with no gzip or ZSTD on either side.

## What the runs measured

| Dataset | Events | Input bytes | Compact bytes | Reduction |
|---|---:|---:|---:|---:|
| Hadoop | 186,697 | 48,595,595 | 20,212,363 | 58.4% |
| Spark | 32,952,127 | 2,941,224,304 | 1,248,606,093 | 57.5% |
| Apache | 52,004 | 5,135,876 | 2,295,929 | 55.3% |
| OpenStack | 207,820 | 61,442,082 | 42,663,820 | 30.6% |
| HDFS | 11,175,629 | 1,577,982,906 | 1,118,008,927 | 29.1% |
| Android | 1,555,005 | 192,270,829 | 153,830,847 | 20% |
| HealthApp | 204,648 | 23,529,930 | 22,432,794 | 4.7% |
| All 14 | 52,276,250 | 5,732,535,052 | 3,167,463,894 | 44.7% |

The reduction tracks how much of each line is repeated text and how many lines share each template. HealthApp and Android, at 4.7% and 20%, are the floor. Both are mobile logs whose component names and tags ship as values, beside the timestamps and IDs, so little of each line is repeated text.

- HDFS and OpenStack sit at the low end of the middle because their lines are mostly values: block IDs, PIDs, and byte counts, with little fixed text between them, and the values ship on every event regardless.
- Hadoop, Spark, and Apache sit at the high end because they write more repeated message text around their values.
- All 14 rows, with template counts, are in [results/results.md](results/results.md).

## Inputs and method

Each run is one pass of the engine over one dataset: the original file goes in, and two files come out, the encoded events and the template dictionary. The LogHub datasets are the full files from the project's [Zenodo record](https://zenodo.org/records/3227177) rather than its 2,000-line benchmark excerpts. Every dataset went through the default symbol library that ships in the image. A library can be compiled from a specific codebase, and none of these runs did that.

## Limits

- A general-purpose compressor can beat these ratios on log text. A self-managed store also compresses what it holds, so the reduction does not carry to disk as-is.
- The two LogHub sets left out, Thunderbird and Windows, are the collection's largest, so the 44.7% weighted figure covers the 14 included sets and is not a LogHub-wide number.
- Query cost and a comparison with another tool's output are not measured.

## Reproducing a row

```
cd loghub-compaction
python3 report.py --check   # recompute every figure from results/ (no Docker)
./run.sh                    # all 14 datasets, then the report and its check
./run.sh Apache Linux       # some datasets
```

A full run needs Docker, Python 3 and about 5 GB of free disk at the peak (Spark). The script downloads the archives from Zenodo and pins the engine image log10x/pipeline-10x:1.1.133 by digest.

The full record is in [RECORD.md](RECORD.md): every dataset's events, bytes, ratio and template count set against the post's figures, the full method and the file list.

The same measurement, with more context: https://www.log10x.com/blog/log-compaction-measured/
