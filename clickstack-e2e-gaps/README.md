# clickstack-e2e-gaps

Six scripts, one per gap the end to end harness next door left open, each run
against the whole 197,430 line capture rather than the 50,000 line slice, and
each against the PATCHED engine rather than the shipped image.

`../clickstack-e2e` is the route: a released capture through an OpenTelemetry
Collector into the 10x receiver, the marked slice into an object store, the rest
into ClickStack's own ClickHouse exporter, both sides read back as one table.
This folder keeps that route and asks the questions that run could not answer.

## Run it

```bash
PATCHED_JAR=<engine>/pipeline/run-cloud/build/libs/run-cloud-<v>-all.jar \
TENX_CONFIG_TREE=<checkout of log-10x/config> \
TENX_MODULES_TREE=<checkout of log-10x/modules> \
CSE_DATA_DIR=../clickstack-e2e/data \
./gap1_multiday_pruning.sh
```

Every script takes the same environment, `lib.sh` documents it, and `LINES`
shortens the feed for a smoke run. Run `../clickstack-e2e/run.sh` once first so
the capture is in `data/` with its sha256 checked; these scripts refuse to run
against a capture that does not match.

The receiver is the JVM build, the way `../clickstack-e2e/repro-otel-return/verify-patched.sh`
runs it: when these runs were made the shipped `edge-10x` image was a native
binary carrying the three OpenTelemetry return path defects, and with those
defects half the capture comes back unmarked, which would decide most of these
questions before they were asked. Build the jar with
`./gradlew :pipeline:run-cloud:shadowJar` in an engine checkout that carries both
fixes.

Both fixes are now released as 1.1.79 and published as `ghcr.io/log-10x/edge-10x`,
and `../clickstack-e2e/results/clickstack-e2e-2026-09-15.md` is that image's own
run. A rerun of this folder against the image rather than the jar is a change to
`g_engine_up` in `lib.sh` and nothing else; the runs committed here used the JVM
build of the same two fixes, and the results file says so.

A host needs about 7 GB of Docker memory and 3 GB of free disk per run, and
nothing else may be running a second ClickStack: two of them on one Docker
daemon starve each other and the first symptom is a container that dies mid-feed
with no error in the run's own log.

## What each script proves, and what it does not

| Script | Proves | Does not |
|---|---|---|
| `gap1_multiday_pruning.sh` | what a day predicate costs against what a time-only predicate costs, over thirty days of objects, counted in S3 GET and LIST | nothing about a real day's mix: every day is a replica of the run's own cold rows with the timestamps shifted, and the replicated objects are gzipped and written by ClickHouse, not by the collector |
| `gap2_vector_parquet.sh` | whether Vector's shipped build takes `encoding.codec: parquet`, what it writes when it does not, and what the same queries cost over Vector's objects and over a Parquet copy | that Parquet is reachable through Vector: the Parquet objects in the query table are written by ClickHouse from the same rows, and the file says so |
| `gap3_retriever_fetch.sh` | whether the cold layout as written is indexable by the shipped Retriever index pipeline, against the same pipeline over the same records one per line | nothing about the Retriever's deployed shape: no SQS, no S3 trigger, no Quarkus service, no fan out. The local accessor the engine ships is what runs |
| `gap4_durable_handoff.sh` | whether a line can be lost or doubled when the routing collector or the receiver is killed mid-stream and restarted, counted line by line through a sequence number inside the body | nothing about a crash that loses the collector's checkpoint file or the host, and nothing about a partial object in the store |
| `gap5_query_alert_correctness.sh` | which of three dashboard-shaped answers change when rows leave the hot table, across the hot table before, the hot table after, the Merge table and the counts table, and whether HyperDX's API accepts an alert on each | that HyperDX's own evaluation loop fired: an alert evaluates the window its interval names, and a replayed capture is older than that by the time the loop runs. The firing condition is evaluated against the counts each surface returns and is labelled as such |
| `gap6_incremental_economics.sh` | rows, bytes, insert plus merge CPU and answers for three policies on one ClickHouse: no offload, a collector-only policy by service and severity, and the per-type policy | nothing about money. There is no Cloud autoscaler here, no bill, and no compute term; the arms are comparable to each other and to nothing else |

## Files

| File | What it is |
|---|---|
| `lib.sh` | the compose pattern every script shares: images, network, MinIO, ClickStack, the patched receiver, the routing collector |
| `measure.py` | one query, timed on a cold cache, read back out of `system.query_log` with its S3 counters |
| `wire_hashes.py` | the census of what the receiver returned, from the collector's wire tap |
| `make_seq_input.py` | the capture with a sequence number inside every line, for gap 4 |
| `patch_retriever_config.py` | the asserted edits that point the shipped Retriever config at the local file system |
| `hyperdx_alert.py` | the alert attempt over the HyperDX API, every status recorded |
| `render.py` | composes `results/clickstack-e2e-gaps-<date>.md` from the per-gap JSON and the hand-written notes |
| `notes/` | the prose for each gap. The numbers are not in here |
| `results/` | `gap<N>.json` per script, and the composed results file |

## Reading the results file

`results/clickstack-e2e-gaps-<date>.md` carries one table per gap. Every number
in it comes from `results/gap<N>.json`, which comes from a run. Where a gap is
open, its section says so and says what would close it.
