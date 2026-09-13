# OTel sample on three denominators

One benchmark in the [log10x benchmarks](../) repository. It answers one question:
when a reduction figure is quoted for a Kubernetes log stream, what was in the denominator,
and how much does the answer move when you change it.

## The question

The published figure for this capture is **63.7%**. The capture is a Fluentd envelope around
each container's stdout line, so most of its bytes are Kubernetes and Docker metadata rather
than the application's message. Two objections follow, and they point in opposite directions.

- *You are measuring your own metadata.* The capture carries a `tenx_tag` field this project
  injects, and about half its bytes are the demo collector's debug exporter printing every
  telemetry batch it handles.
- *You are measuring an envelope, not logs.* An OpenTelemetry practitioner compares this
  against OTLP, which carries no per-record Fluentd envelope, and expects the figure to
  collapse once the envelope is removed.

Rather than argue either one, this benchmark builds all three denominators from the same
public file and measures them with the same engine, the same configs and the same round-trip
check.

## The result

| Case | Input bytes | Lines | Encoded | Templates bytes | Compact | Reduction | Templates | Round trip |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| (a) as captured | 215,039,161 | 197,430 | 74,841,891 | 3,226,416 | 78,068,307 | **63.70%** | 2,933 | byte-identical |
| (b) SIEM-billed | 88,975,911 | 111,691 | 30,496,832 | 2,903,267 | 33,400,099 | **62.46%** | 2,869 | byte-identical |
| (c) message only | 40,551,755 | 197,430 | 10,644,634 | 600,758 | 11,245,392 | **72.27%** | 2,631 | byte-identical |

Reduction is the compact form, the encoded events plus the template dictionary needed to
expand them, against the input, with no gzip or ZSTD on either side. Each row decodes back to
its own input and is compared with `cmp`, so no row borrows another row's round trip.

**The second objection does not survive the measurement.** On the message text alone, with the
whole envelope gone, the reduction is 8.57 points **higher** than the published figure, not
lower. Repeated text is a larger share of an application message than of the Kubernetes
metadata around it, so removing the envelope removes the harder part of the file.

**The first objection moves the figure by 1.24 points.** Removing the injected field and
dropping 85,739 collector debug lines, which together take 126,063,250 bytes off the input,
58.6% of it, moves 63.70% to 62.46%.

An OTLP log record carries more than a bare message, since it has a timestamp, severity, body,
attributes and trace ids, and much less than this Fluentd envelope. Rows (b) and (c) therefore
bracket it at **62.46% to 72.27%**. No figure for an OTLP wire is measured here, and none is
claimed. Measuring one needs a capture of OTLP records, which this is not.

## What each denominator is

- **(a) as captured** is the release asset, untouched: one JSON record per line with `log`,
  `stream`, `docker` and `kubernetes` keys, plus the `tenx_tag` field the forwarder adds.
- **(b) SIEM-billed** removes `tenx_tag` and drops the collector's debug-exporter lines,
  keeping the Kubernetes and Docker envelope, because a log platform bills that envelope. A
  line is dropped only when its container is `opentelemetry-collector` **and** its message
  matches zap's tab-separated debug prefix `<ts>\tinfo\t(Traces|Logs|Metrics)\t`. Ordinary
  collector error logs are kept, including the 3,745 lines reading `failed to upload metrics`:
  those are a misconfiguration in the captured cluster, and a platform bills them.
- **(c) message only** is the `log` value alone, one message per line, envelope discarded. No
  record's `log` value contains a newline, 0 of 197,430, so the line count is unambiguous.

(b) and (c) differ in line count on purpose. (c) keeps every message including the collector's;
only (b) drops them.

## What is not claimed

- **No figure for the OpenTelemetry wire.** Both this capture and the numbers above are Fluentd
  envelopes. The bracket in the result section is arithmetic on two measured points, not a
  measurement.
- **No claim about what a particular platform bills.** Metering rules differ per product and
  per contract. (b) is named for the shape a platform receives, not for anyone's invoice.
- **One capture, one cluster, about ten hours.** 36 containers from one small demo cluster at
  roughly 5 lines per second. A shape that occurs once at 5 lines per second is a different
  population from a shape that occurs once at 100,000.
- **(b) is a sensitivity check, not a production configuration.** It removes two unrelated
  things at once. The forwarder that produced this capture adds `tenx_tag`; the demo enables
  the debug exporter. Neither is a property of the engine being measured.

## Reproduce

```sh
./run.sh
```

Needs Docker and about 1.2 GB of free disk. The script fetches the public capture once (8.4 MB
gzipped), checks its sha256 against the one this table was measured on, builds the two derived
inputs and checks their byte and line counts against the committed run, then encodes and
decodes all three cases. It writes `results/results.csv` and `results/results.md`, and deletes
the bulky per-case output unless `OTD_KEEP=1`.

`./run.sh c_msg` runs one case. `OTD_DATA_DIR`, `OTD_IMAGE` and `OTD_KEEP` override the cache
location, the engine image and the output retention.

| File | What it is |
|---|---|
| `run.sh` | fetch, build, encode, decode, compare, report |
| `build_inputs.py` | derives (b) and (c) from (a), and fails if the counts move |
| `report.py` | renders `results/results.md` from the CSV, recomputing the percentage from the byte counts |
| `results/results.csv` | the committed run, one row per case |
| `results/results.md` | the same run as a table, with the image digest and the input sha256 |

Pinned: engine image `log10x/pipeline-10x@sha256:aeb3784c8895bf990e9a88f49c68d59f5729f6738c44c6e8fd87a489f725d316`
(`log10x/pipeline-10x:1.1.5`), and the two round-trip configs in
[`../drain3-vs-log10x/`](../drain3-vs-log10x/), which are the configs the compaction post
publishes.

## Data

`otel-sample-200mb.log` from [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1),
215,039,161 bytes, 197,430 lines, sha256
`aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`. Kubernetes container output
captured through Fluentd from a cluster running the OpenTelemetry demo 2.1.3, about ten hours
between the 1st and 99th percentile timestamp, 36 containers. The same asset the
[`pattern-identity/`](../pattern-identity/) benchmark runs on.

### One line differs from the copy the blog post measured

The post's manifest reports 215,039,166 input bytes for this dataset; the published asset is
215,039,161. The difference is a single line, 9731, whose message names an engine config path.
The copy behind the manifest, published February 2026, reads `@apps/edge/optimizer`, an earlier
name for the same app. The released asset, published July 2026, reads `@apps/regulator`, the
current name, so the released asset carries one token changed after the capture was taken. One
token, five bytes, in one line of 197,430.

It moves the compact form by two bytes, 78,068,307 here against 78,068,309 in the manifest, and
moves neither the reduction to two decimals nor the template count. Every figure in this
benchmark is measured on the published asset, so a reader who downloads it reproduces this
table rather than the manifest's byte counts.
