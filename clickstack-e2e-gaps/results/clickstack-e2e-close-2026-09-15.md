# ClickStack end to end: closing the gaps, 2026-09-15

A second pass over `clickstack-e2e-gaps`, written after a record check found one
published claim false and four questions the first pass never put. Every number
here comes from a run on this host on 2026-09-15, and every run is named with the
command that produced it.

`clickstack-e2e-gaps-2026-09-15.md` holds the first pass and is unchanged in its
numbers. Where this file contradicts it, this file is the later measurement and
says so in its own section.

## The images that ran

Every image is pinned by tag and digest in `lib.sh`. These are the digests these
runs used.

| Image | Digest |
|---|---|
| `ghcr.io/log-10x/edge-10x:1.1.79` | `sha256:14357d8d570cb36ba6ca254802a1b8eedb11d8acf6916a936893f8e3babb41f4` |
| `clickhouse/clickstack-all-in-one:2.38.0` | `sha256:7b3bd9eec4e61aded56f705af7ddb2e8e49c54098d21aaaa7de6fde4d7c1f267` |
| `otel/opentelemetry-collector-contrib:0.160.0` | `sha256:799dc6cf12c96192af37b5bdba804da8c10b3bc563b43cb90c3f3c58d9572ad6` |
| `timberio/vector:0.58.0-debian` | `sha256:1c1ea358c617ea0b23003d5af87f7a678b30f8f7096437e680380c47fc13d2d9` |
| `quay.io/minio/minio:latest` | `sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` |
| `quay.io/minio/mc:latest` | `sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727` |
| `eclipse-temurin:23-jre` | `sha256:4972459272d4050ab14700677ac7a7511194f1d9ed333b95e886c3c8c80dedae` |

ClickHouse inside the ClickStack image reports `26.5.7.64`.

## Step 1: the runs no longer need a private build

**Closed.** The first pass ran the receiver as a run-cloud shadow jar on a JRE
image, because the shipped `edge-10x` image was then a native binary carrying
three OpenTelemetry return path defects. Both fixes shipped in 1.1.79, so
`g_engine_up` now runs the published image by default and `PATCHED_JAR` survives
as an optional override for anyone reproducing the first pass or testing an
unpublished build. Five of the six gap scripts need no jar, no engine checkout
and no private repository. Gap 3 still does, because it drives the Retriever
index and query pipelines rather than the receiver, and its own guard says so.

The smoke run below is gap 1 over a short feed on three days rather than thirty,
which is enough to prove the route end to end on the image: the receiver starts,
the harness's asserted config edits apply to the image's own config tree, records
come back marked, the collector writes objects, and the queries answer with their
object-store counters intact.

```
LINES=20000 DAYS=3 CSE_DATA_DIR=<repo>/clickstack-e2e/data ./gap1_multiday_pruning.sh
```

| Measure | Smoke on the image |
|---|---:|
| lines fed | 20,000 |
| records the receiver returned | 13,161 |
| rows in the hot table | 7,251 |
| rows in the objects | 5,910 |
| objects the run wrote | 9 |
| objects after replication across 3 days | 18 |
| bytes after replication | 762KiB |

| Query | Answer | Rows read | S3 GET | S3 LIST | ms |
|---|---|---:|---:|---:|---:|
| hot only, last hour, count | 7,251 | 6,253 | 0 | 0 | 50 |
| merge, service and one day, both in the path | 4,568 | 10,812 | 2 | 1 | 79 |
| merge, service, no day predicate | 15,039 | 19,948 | 6 | 1 | 204 |
| merge, time only, the shape HyperDX sends | 13,161 | 24,981 | 18 | 1 | 303 |
| merge, time plus `day >= today() - 1` | 13,161 | 19,071 | 12 | 1 | 127 |
| merge, text search for 'snapshot', no other filter | 1,338 | 24,981 | 18 | 1 | 423 |
| merge, text search for 'snapshot', one day | 203 | 13,161 | 6 | 1 | 276 |
| merge, one pattern hash, no time filter | 6,196 | 24,981 | 18 | 1 | 1,797 |
| merge, one pattern hash and one day | 1,953 | 13,161 | 6 | 1 | 243 |
| cold only, one day, count | 5,910 | 5,910 | 6 | 1 | 130 |

Read this table as a proof that the image path runs, not as a pruning
measurement: the committed pruning figures are gap 1's own, over the whole
capture and thirty days, in `clickstack-e2e-gaps-2026-09-15.md`. The shape holds
at this size too, at one GET per object and one LIST for the whole matched key
set.

The smoke's own `gap1.json` is not committed. `results/gap1.json` remains the
full-capture run.

## Step 2: Vector 0.58.0, and Parquet written by Vector

**Closed, and the first pass's answer is withdrawn.** Vector writes Parquet. The
first pass pinned `timberio/vector:0.50.0-debian`, published 2025-09-23, and
probed `encoding.codec`, which names the per event serializer and has never
taken a columnar codec. Vector's Parquet option is `batch_encoding.codec` on the
`aws_s3` sink, added in v0.55.0 on 2026-04-22 and carried by the official release
binaries from v0.56.0 on 2026-06-03; upstream issue 1374 closed on 2026-04-28,
by pull requests 25156 and 25321.

```
CSE_DATA_DIR=<repo>/clickstack-e2e/data ./gap2b_vector058_parquet.sh
```

Build that ran: `vector 0.58.0 (x86_64-unknown-linux-gnu 2bcad9b 2026-08-26
13:37:07.557544670)`. Three configurations were put to its own validator.

| Configuration | `vector validate` | What the binary says |
|---|---|---|
| `encoding.codec: parquet` | exit 78 | ``sinks.out: unknown variant `parquet`, expected one of `avro`, `cef`, `csv`, `gelf`, `json`, `logfmt`, `native`, `native_json`, `otlp`, `protobuf`, `raw_message`, `text`, `syslog` `` |
| `batch_encoding.codec: parquet`, no `encoding` | exit 78 | ``sinks.out: missing field `encoding` `` |
| `batch_encoding.codec: parquet` with `encoding.codec: json` | exit 0 | Validated |

So `encoding` stays required alongside `batch_encoding`, and the key the first
pass probed is still refused on the current build for the same reason it was
refused on the old one. The published claim that Vector's shipped build writes no
Parquet is false, and this run is the retraction.

The route then ran once, with Vector writing both containers off the same
transform: newline delimited JSON into one bucket, Parquet into another, from
157,151 records returned by the receiver, of which 116,507 carried the offload
mark and 40,644 went to the hot table.

| Measure | Vector JSON | Vector Parquet |
|---|---:|---:|
| objects | 68 | 68 |
| bytes | 169MiB | 3.2MiB |
| rows readable through the S3 table | 116,507 | 116,507 |

Sink settings on the Parquet arm: `compression: none` at the sink because
Parquet compresses per column page, `encoding.codec: json` because the field is
required and ignored for the batch, `batch_encoding.schema_mode: auto_infer`, and
snappy inside the file.

One shape difference, stated rather than buried. The JSON arm writes
`{"body": ..., "logAttributes": {...}}` and ClickHouse reads the attributes as a
`Map(String, String)`. The Parquet arm writes the fields the queries name as
columns of their own, because a schema inferred from a free map carries one field
per attribute key the batch happened to see. The rows are the same rows, and
every query answers the same number through both.

| Query | Answer | Rows read | Bytes read | S3 GET | S3 reads | S3 LIST | ms | ms warm |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| hot only, last 4 hours, count | 40,644 | 40,644 | 325,152 | 0 | 0 | 0 | 138 | 67 |
| merge, service and one day: Vector json | 89,743 | 106,917 | 123,437,448 | 24 | 25 | 1 | 628 | 302 |
| merge, time only, the shape HyperDX sends: Vector json | 157,151 | 157,151 | 177,418,092 | 68 | 69 | 1 | 951 | 968 |
| merge, text search, no other filter: Vector json | 14,580 | 157,151 | 186,570,062 | 68 | 69 | 1 | 375 | 324 |
| merge, one pattern hash: Vector json | 36,395 | 157,151 | 177,701,349 | 68 | 69 | 1 | 354 | 383 |
| merge, service and one day: Vector parquet | 89,743 | 106,917 | 90,835 | 24 | 25 | 1 | 75 | 37 |
| merge, time only, the shape HyperDX sends: Vector parquet | 157,151 | 157,151 | 3,594,401 | 68 | 69 | 1 | 137 | 115 |
| merge, text search, no other filter: Vector parquet | 14,580 | 140,386 | 9,219,738 | 68 | 69 | 1 | 87 | 71 |
| merge, one pattern hash: Vector parquet | 36,395 | 157,151 | 3,877,658 | 68 | 69 | 1 | 82 | 78 |

### The Parquet reader's own counters

`system.query_log` was read per query for the four counters the record check
named. The three queries that read every Parquet object report
`ParquetReadRowGroups` 68, one row group per object, all of them read. The
service and day query reports zero on that counter while reading 24 objects, and
this run does not say why.

| Query | ParquetPrunedRowGroups | ParquetReadRowGroups | ParquetPrunedPages | ParquetReadPages |
|---|---:|---:|---:|---:|
| merge, service and one day: Vector parquet | 0 | 0 | 0 | 0 |
| merge, time only: Vector parquet | 0 | 68 | 0 | 0 |
| merge, text search: Vector parquet | 0 | 68 | 0 | 0 |
| merge, one pattern hash: Vector parquet | 0 | 68 | 0 | 0 |

The Parquet counters this server moved at all, from `system.events`:
`ParquetMetadataCacheHits`, `ParquetMetadataCacheMisses`,
`ParquetFetchWaitTimeMicroseconds`, `ParquetReadRowGroups`,
`ParquetDecodingTasks`, `ParquetDecodingTaskBatches`,
`ParquetPrefetcherReadRandomRead`. `ParquetPrunedRowGroups`,
`ParquetPrunedPages` and `ParquetReadPages` are not among them and read zero on
every query.

**Nothing was pruned.** The first pass said the Parquet copy "reads fewer rows on
the text search because Parquet row groups are skipped on statistics that JSON
has no equivalent of". The counter that would show that is zero. The text search
does read 140,386 rows through Parquet against 157,151 through JSON, and what
accounts for the difference is not settled by this run; row group pruning is
ruled out by direct measurement rather than by argument. The gain that is settled
is bytes: 3,594,401 against 177,418,092 on the time only query, because only the
columns the query names are read.

### One GET per object, and what the recipe's batch size does

The recipe advises `batch.max_bytes: 33554432` for Vector, and the arithmetic in
the post says one GET per object a path predicate does not exclude. Both arms
report `S3GetObject` exactly equal to the number of objects the query did not
exclude, 68 and 24, with `S3ReadRequestsCount` one higher in each case. So no
object here took more than one GET, Parquet included.

The reason is that the batch never reached `max_bytes`. `timeout_secs: 5` flushed
first, so the JSON objects average about 2.5 MiB and the Parquet objects about
48 KiB, and every one of them is under the 4 MiB
`remote_read_min_bytes_for_seek` default at which ClickHouse starts seeking
rather than reading an object end to end. A run whose batches did fill 32 MiB
would be on the other side of that threshold, and the one-GET line would need
measuring again rather than assuming.

## Step 3: the two shapes Altinity says a Merge table does not push down

**Closed, and the objection is half right in a way the table makes exact.**
Alexander Zaitsev of Altinity published this on 2025-11-07, after trying a Merge
table over MergeTree plus object storage for hot and cold logs: "The main problem
is bad performance... the Merge engine does not push query execution steps down,
such as aggregations or limits." Gap 1 measured filters and counts, which is a
different claim, so this run puts the two shapes he names.

```
QUERY_SET=agg CSE_DATA_DIR=<repo>/clickstack-e2e/data ./gap1_multiday_pruning.sh
```

The layout is gap 1's, regenerated: 197,430 lines fed, 157,100 records returned
by the receiver, 40,466 into the hot table, 116,634 into 78 objects, those
objects replicated across 30 day partitions into 180 objects, 151MiB, 3,499,020
rows. One day holds 6 objects.

Each shape runs four ways. Three are the same Merge table with a different
predicate; the fourth is the hot table on its own, as the baseline.

| Query | Rows read | Bytes read | S3 GET | S3 LIST | ms | ms warm | CPU us |
|---|---:|---:|---:|---:|---:|---:|---:|
| GROUP BY ServiceName: time only | 3,539,486 | 152,716,146 | 180 | 1 | 4,978 | 6,233 | 13,468,784 |
| GROUP BY ServiceName: time plus `day >= today() - 1` | 273,734 | 10,602,869 | 12 | 1 | 428 | 430 | 955,261 |
| GROUP BY ServiceName: time plus `_table = 'otel_logs'` | 40,466 | 365,431 | 0 | 0 | 12 | 9 | 15,887 |
| GROUP BY ServiceName: hot table alone, the baseline | 40,466 | 365,431 | 0 | 0 | 9 | 9 | 10,837 |
| ORDER BY Timestamp DESC LIMIT 100: time only | 3,539,486 | 162,215,654 | 180 | 1 | 5,090 | 5,239 | 14,218,383 |
| ORDER BY Timestamp DESC LIMIT 100: time plus `day >= today() - 1` | 273,734 | 20,102,377 | 12 | 1 | 416 | 405 | 925,232 |
| ORDER BY Timestamp DESC LIMIT 100: time plus `_table = 'otel_logs'` | 40,466 | 9,864,939 | 0 | 0 | 18 | 19 | 21,792 |
| ORDER BY Timestamp DESC LIMIT 100: hot table alone, the baseline | 41,344 | 550,672 | 0 | 0 | 7 | 8 | 9,327 |

**On the limit, Zaitsev is right, and the number says how right.** All four ways
of the second shape return the same hundred rows: the digest over their bodies is
`13114138106639873076` in every row of the table, hot baseline included, because
the hundred most recent records are hot records. Getting to that identical answer
through the Merge table with a time predicate alone reads 3,539,486 rows and
opens all 180 objects, 5,090 ms against the hot table's 7 ms. Nothing about the
`LIMIT 100` reaches the S3 table before its objects are opened. That is the
pushdown failure, measured on our own layout rather than argued about.

**On the aggregation, the answer is different and worth separating.** The
`GROUP BY` through the Merge table with a time predicate alone returns
opentelemetry-collector 89,739 and kafka 28,789, the same totals the hot table
gave before the offload. Reaching them costs 180 GETs and 13.47 CPU seconds.
The hot table alone answers in 10,837 microseconds and returns 13,054 for
opentelemetry-collector, which is the wrong answer rather than a cheap one: the
rows are in the bucket. So the cost here buys a correct answer, and the question
is what it costs to get the correct answer cheaply.

**Two predicates do that, and both prune.** A day predicate takes the
aggregation from 180 GETs and 4,978 ms to 12 GETs and 428 ms, with the same
answer, because the day is a path segment. And `_table = 'otel_logs'` takes it to
zero GETs and 12 ms against the hot table's own 9 ms, which settles a narrower
question: the Merge engine does push `_table` down, opens no object for it, and
charges 3 ms for naming the hot side through the Merge table rather than querying
it directly.

**What this does not say.** Nothing about Distributed tables, where Zaitsev's
complaint is sharper, and nothing about projections, which the children here do
not carry. And the day mix is gap 1's: every one of the 30 days is a replica of
this run's own cold rows with the timestamps shifted, so the day predicate's
saving is exact in requests and synthetic in content.

## Step 5: ClickHouse issue 116888, and what actually triggers it

**Closed, and the trigger is not what the issue's summary suggests.** The defect
is real, it is worse than a simple error because the table looks healthy, and it
is not the `CREATE TABLE` that arms it.

ClickHouse issue 116888 is open, filed 2026-08-28 by `zlareb1`, a ClickHouse
member: an S3 table with an explicit schema and `use_hive_partitioning = 1`
created before any object exists under its prefix resolves its partition columns
against an empty listing and keeps that, after which every predicate on a path
column matches nothing. The offload recipe renders exactly that DDL as a setup
step.

```
./gap7_s3_table_before_objects.sh
```

One MinIO, one ClickHouse at `26.5.7.64`, objects written by ClickHouse itself:
two objects at `service=cart/day=2026-09-15/` and `service=kafka/day=2026-09-15/`,
20,000 rows each. Four tables, the same DDL every time, differing only in when
each was created and whether each was read while the prefix was still empty.

| The table | `count()` | `count() WHERE service = 'cart'` | `count() WHERE day = '2026-09-15'` |
|---|---:|---:|---:|
| created before any object exists, not read until after | 40,000 | 20,000 | 40,000 |
| created AND read once while the prefix is empty | 40,000 | **0** | **0** |
| created after the first object exists | 40,000 | 20,000 | 40,000 |
| the read-while-empty table, after DETACH and ATTACH | 40,000 | 20,000 | 40,000 |

Read the second row against the first. Creating the table over an empty prefix
does nothing on its own, because the S3 engine resolves its listing during
`SELECT` rather than at `CREATE`. Reading it once while the prefix is still empty
is what arms the defect, and a reader who follows the recipe does exactly that:
runs the `CREATE TABLE` setup step, then runs a count to check the step worked.

The failure is silent in the way that matters most. `count()` with no predicate
returns 40,000 on the broken table, so the one query a reader runs next says the
table is fine. Only the path predicates are dead, and those are the predicates
the whole request-count argument rests on.

Two ways out, both measured. Create the table after the first object exists,
which is what `g_wait_for_object` in `lib.sh` now enforces before every
`CREATE TABLE` over an S3 prefix in this folder. Or `DETACH TABLE` then
`ATTACH TABLE`, which restores a table that is already broken without dropping
it.
