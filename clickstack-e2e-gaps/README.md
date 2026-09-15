# clickstack-e2e-gaps

Ten scripts over the questions the end to end harness next door left open, each
run against the whole 197,430 line capture rather than the 50,000 line slice.
Six are the first pass, one per gap; three more were added in a second pass after
a record check against primary sources; the tenth was added in a third pass, on
the layout the first one builds.

`../clickstack-e2e` is the route: a released capture through an OpenTelemetry
Collector into the 10x receiver, the marked slice into an object store, the rest
into ClickStack's own ClickHouse exporter, both sides read back as one table.
This folder keeps that route and asks the questions that run could not answer.

## Run it

```bash
TENX_CONFIG_TREE=<checkout of log-10x/config> \
TENX_MODULES_TREE=<checkout of log-10x/modules> \
CSE_DATA_DIR=../clickstack-e2e/data \
./gap1_multiday_pruning.sh
```

Every script takes the same environment, `lib.sh` documents it, and `LINES`
shortens the feed for a smoke run. Run `../clickstack-e2e/run.sh` once first so
the capture is in `data/` with its sha256 checked; these scripts refuse to run
against a capture that does not match.

The receiver is `ghcr.io/log-10x/edge-10x:1.1.79`, public and pinned by digest
in `lib.sh`, so nothing here needs a build and nothing here needs a private
repository. `log-10x/config` and `log-10x/modules` are public checkouts too.
Every other image is pinned by digest beside it, and the digests that ran are
recorded in the results file.

`PATCHED_JAR` remains as an optional override: set it and the receiver runs that
run-cloud shadow jar on a stock JRE image instead of the published binary, the
way `../clickstack-e2e/repro-otel-return/verify-patched.sh` does. That override
is how the runs in `results/clickstack-e2e-gaps-2026-09-15.md` were made. When
those runs were made the shipped `edge-10x` image was a native binary carrying
the three OpenTelemetry return path defects, and with those defects half the
capture comes back unmarked, which would have decided most of these questions
before they were asked. Both fixes are released as 1.1.79, and
`../clickstack-e2e/results/clickstack-e2e-2026-09-15.md` is that image's own run.

A host needs about 7 GB of Docker memory and 3 GB of free disk per run, and
nothing else may be running a second ClickStack: two of them on one Docker
daemon starve each other and the first symptom is a container that dies mid-feed
with no error in the run's own log.

## What each script proves, and what it does not

| Script | Proves | Does not |
|---|---|---|
| `gap1_multiday_pruning.sh` | what a day predicate costs against what a time-only predicate costs, over thirty days of objects, counted in S3 GET and LIST | nothing about a real day's mix: every day is a replica of the run's own cold rows with the timestamps shifted, and the replicated objects are gzipped and written by ClickHouse, not by the collector |
| `gap2_vector_parquet.sh` | that Vector carries the whole cold branch, and what the same queries cost over Vector's objects and over a Parquet copy of the same rows | anything about Parquet in Vector as it was first run: the pinned build was `0.50.0-debian` and the probe set `encoding.codec`, which is the per event serializer. Vector's Parquet option is `batch_encoding.codec` on the `aws_s3` sink, added in v0.55.0 and in official builds from v0.56.0. The Parquet objects in that query table were written by ClickHouse |
| `gap3_retriever_fetch.sh` | whether the cold layout as written is indexable by the shipped Retriever index pipeline, against the same pipeline over the same records one per line | nothing about the Retriever's deployed shape: no SQS, no S3 trigger, no Quarkus service, no fan out. The local accessor the engine ships is what runs |
| `gap4_durable_handoff.sh` | whether a line can be lost or doubled when the routing collector or the receiver is killed mid-stream and restarted, counted line by line through a sequence number inside the body | nothing about a crash that loses the collector's checkpoint file or the host, and nothing about a partial object in the store |
| `gap5_query_alert_correctness.sh` | which of three dashboard-shaped answers change when rows leave the hot table, across the hot table before, the hot table after, the Merge table and the counts table, and whether HyperDX's API accepts an alert on each | that HyperDX's own evaluation loop fired: an alert evaluates the window its interval names, and a replayed capture is older than that by the time the loop runs. The firing condition is evaluated against the counts each surface returns and is labelled as such |
| `gap6_incremental_economics.sh` | rows, bytes, insert plus merge CPU and answers for three policies on one ClickHouse: no offload, a collector-only policy by service and severity, and the per-type policy | nothing about money. There is no Cloud autoscaler here, no bill, and no compute term; the arms are comparable to each other and to nothing else |
| `gap2b_vector058_parquet.sh` | what Vector 0.58.0 takes for Parquet, and what the same rows cost as newline delimited JSON and as Parquet, both written by Vector in one run and read through two Merge tables, with the Parquet reader's row group and page counters | that the two containers hold the same shape: the JSON arm writes a free attribute map and the Parquet arm writes named columns, because a schema inferred from a free map carries one field per key seen |
| `gap7_s3_table_before_objects.sh` | ClickHouse issue 116888: what an S3 table with an explicit schema and `use_hive_partitioning` answers when created before any object exists, what the same DDL answers when created after, and whether DETACH and ATTACH recovers the first | anything about how long the empty listing is held, or which other engines cache one. One table, one prefix, one server version, named in the results |
| `gap8_ttl_to_s3.sh` | what den-crane's TTL recipe costs on the same capture: the PUTs, the parts and the merge and move CPU a forced `TTL TO VOLUME 'cold'` charges, and what a slice stamped behind the boundary charges on insert alone | nothing about a bill, and nothing about the background scheduler's own pacing: the move is forced so the whole table moves exactly once and the number does not depend on which parts the scheduler happened to pick |
| `gap9_bounded_window.sh` | what a bound inside the table costs against the same bound written into the query: a view over the cold table carrying `day >= today() - 7`, a second Merge table over hot plus that view, and the two aggregation shapes put to both | nothing about an estate's own ratio of window to retention, and nothing about the rows outside the bound, which that table cannot reach at all |

## Files

| File | What it is |
|---|---|
| `lib.sh` | the compose pattern every script shares, plus `g_cold30_layout`, gap 1's thirty day object layout, shared so gap 9 asks its question of the same one: the pinned images, the network, MinIO, ClickStack, the receiver and the routing collector, plus `g_wait_for_object`, the guard for ClickHouse 116888 |
| `measure.py` | one query, timed on a cold cache, read back out of `system.query_log` with its S3 counters |
| `wire_hashes.py` | the census of what the receiver returned, from the collector's wire tap |
| `make_seq_input.py` | the capture with a sequence number inside every line, for gap 4 |
| `patch_retriever_config.py` | the asserted edits that point the shipped Retriever config at the local file system |
| `hyperdx_alert.py` | the alert attempt over the HyperDX API, every status recorded |
| `render.py` | composes `results/clickstack-e2e-gaps-<date>.md` from the per-gap JSON and the hand-written notes |
| `notes/` | the prose for each gap. The numbers are not in here |
| `results/` | `gap<N>.json` per script, the composed first-pass file, and the second pass's own file |

## Reading the results files

`results/clickstack-e2e-gaps-2026-09-15.md` is the first pass, one table per gap.
Every number in it comes from `results/gap<N>.json`, and `render.py` composes it
from those files and the prose in `notes/`. Where a gap is open, its section says
so and says what would close it.

`results/clickstack-e2e-close-2026-09-15.md` is the second pass, written after a
record check against primary sources found one published claim false and four
questions the first pass never put. Read it for the Vector Parquet retraction,
the Parquet reader's own counters, the aggregation shapes through the Merge
table, the collector run as its code owners prescribe, ClickHouse issue 116888
and its guard, and what `TTL TO VOLUME 'cold'` costs on the same capture. That file
carries the digests every run used and the command that produced each table, and
its own JSON sits beside the first pass's: `gap1-agg.json`, `gap2b.json`,
`gap4-router-owners.json`, `gap7.json`, `gap8.json`.

The same file's last section, `Wave 3, 2026-09-15 evening`, is a third pass on the
same harness: the persistent sending queue arm of gap 4 (`gap4-router-persist.json`),
the bounded cold window (`gap9.json`), and what the public Retriever image carries,
which is why gap 3 is still not measured.

Where the two disagree, the second is the later measurement and says so.
