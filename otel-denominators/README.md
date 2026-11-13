# OTel sample on three denominators

The same stream was measured three ways, each decoded byte-identical. The stream is Kubernetes container output, captured through Fluentd from a cluster running the OpenTelemetry demo. As captured, metadata included, the reduction is 64.00%. On the log message text alone, metadata stripped, the reduction is 72.35%.

About half the bytes are the demo collector's debug exporter, which the demo enables by default. Reduction means the bytes of the compact form, the encoded events plus the template dictionary needed to expand them, against the bytes of the original file, with no gzip or ZSTD on either side.

## Result

| Input | Input bytes | Lines | Compact bytes | Reduction |
|---|---:|---:|---:|---:|
| (a) as captured | 215,039,161 | 197,430 | 77,421,244 | 64.00% |
| (b) tag and debug lines removed | 88,975,911 | 111,691 | 33,401,403 | 62.46% |
| (c) message only | 40,551,755 | 197,430 | 11,212,254 | 72.35% |

The first is the file as Fluentd shipped it. With the tag field our forwarder adds and the collector's debug output removed, metadata kept, the reduction is 62.46%. The second removes two things at once and is a sensitivity check.

- An OTLP record carries more than a bare message and much less than this envelope, so (b) and (c) bracket it at 62.46% to 72.35%.

## How it was measured

The stream covers 36 Kubernetes containers over about ten hours, the demo's own services (demo version 2.1.3) together with the cluster's infrastructure and system pods, every line carrying its Kubernetes metadata as Fluentd ships it. Input (b) removes the added field and the collector's debug exporter lines, and keeps the envelope because a log platform bills it. Input (c) is the message value of each record, one per line. All three ran through the same engine and configs, and each decode was compared with its own input.

## Limits

- One capture from one small demo cluster at roughly 5 lines per second.
- No OTLP capture was measured. The OTLP range above is inferred from two measured points.
- Nothing here says what a particular platform bills.

## Run it

```
cd otel-denominators
python3 report.py --csv results/results.csv --out /tmp/results.md   # recompute the table from the committed counts
./run.sh                                                            # full rerun of all three cases
```

The recompute needs only Python. The full rerun needs Docker and about 1.2 GB of free disk, and runs engine image `log10x/pipeline-10x:1.1.136`, pinned by digest in the script.

The complete record is in [RECORD.md](RECORD.md): how each input is built, the full table with template counts, the image digest and the data's sha256.

The same measurement, with more context: https://www.log10x.com/blog/log-compaction-measured/
