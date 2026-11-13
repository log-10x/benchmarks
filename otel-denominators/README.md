# OTel sample on three denominators

How much does a log reduction figure depend on what was in the input? On one public capture from a Kubernetes cluster running the OpenTelemetry demo, the 10x engine's figure is 64.00% on the file as captured, 62.46% with the debug output and an added field removed, and 72.35% on the application messages alone. Taking away the Kubernetes metadata around each message raised the figure.

The capture wraps each container's stdout line in a Fluentd envelope of Kubernetes and Docker metadata. Two objections follow from that. One says the file is padded by a `tenx_tag` field the log10x forwarder adds and by the demo collector's debug exporter. The other says OTLP has no such envelope, so the figure should collapse without it.

## Result

| Input | Input bytes | Lines | Compact bytes | Reduction |
|---|---:|---:|---:|---:|
| (a) as captured | 215,039,161 | 197,430 | 77,421,244 | 64.00% |
| (b) tag and debug lines removed | 88,975,911 | 111,691 | 33,401,403 | 62.46% |
| (c) message only | 40,551,755 | 197,430 | 11,212,254 | 72.35% |

On the message text alone the reduction is 8.35 points higher than on the file as captured, because repeated text is a larger share of an application message than of the metadata around it. Removing the added field and 85,739 collector debug lines took 58.6% of the bytes off the input and moved the figure down by 1.54 points.

- Every case decoded back to its own input byte for byte.
- An OTLP record carries more than a bare message and much less than this envelope, so (b) and (c) bracket it at 62.46% to 72.35%.

## How it was measured

The input is `otel-sample-200mb.log` from the public [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1) release, captured through Fluentd from 36 containers over about ten hours. Input (b) removes the added field and the collector's debug exporter lines, and keeps the envelope because a log platform bills it. Input (c) is the message value of each record, one per line. All three ran through the same engine and configs, and each decode was compared with its own input. Compact bytes are the encoded events plus the template dictionary, with no gzip or ZSTD on either side.

## Limits

- One capture from one small demo cluster at roughly 5 lines per second.
- No OTLP capture was measured. The OTLP range above is inferred from two measured points.
- Nothing here says what a particular platform bills.
- Input (b) removes two unrelated things at once and serves as a sensitivity check. Neither removal is a property of the engine.

## Run it

```
cd otel-denominators
python3 report.py --csv results/results.csv --out /tmp/results.md   # recompute the table from the committed counts
./run.sh                                                            # full rerun of all three cases
```

The recompute needs only Python. The full rerun needs Docker and about 1.2 GB of free disk, and runs engine image `log10x/pipeline-10x:1.1.136`, pinned by digest in the script.

The complete record is in [RECORD.md](RECORD.md): how each input is built, the full table with template counts, the image digest and the data's sha256.
