# ClickStack end to end: the six gaps, 2026-09-15

Every number below comes from a run of the script named in its section, over the
whole 197,430 line capture, against the PATCHED engine. A gap that could not be
closed says so in its own section and says why.

## Gap 1: multi-day pruning

**Closed.** A day predicate prunes to that day's objects and a time-only
predicate opens every object in the bucket, at one S3 GET per object either way.

The run wrote its own cold objects, and those objects were then replicated
across thirty day partitions with their timestamps shifted by whole days, the
way `../../clickhouse-clickstack/run_scale.sh` replicates rows. Two things about
the replicated objects are not what the collector wrote, and both are here
rather than in a footnote: they are gzipped, because thirty uncompressed copies
of the cold side of the full capture does not fit on the host this ran on, and
ClickHouse wrote them, because shifting the day is what the replication is for.
The object count, the request count and which objects a predicate opens are
unaffected by either.

Read the GET column against the object counts. One day holds six objects and
two of them belong to the service asked for. The service and day query opens
exactly those two. The service alone opens sixty, which is that service's two
objects on each of thirty days. Every query that names only a time opens all
one hundred and eighty, because the day in the path is the only thing that can
exclude an object before it is opened, and `Timestamp` lives inside the file.
Adding `day >= today() - 1` to the same time-only query takes it from one
hundred and eighty GETs and 7,449 ms to twelve and 468 ms.

The pattern hash behaves the same way: named alone it opens every object,
because the hash is a column inside the file and not a path segment. A query
that names a type and a day pays six.

What this does not say: nothing about a real estate's day mix, because every day
here is a replica of one day's cold rows; and nothing about Parquet row-group
skipping, because these objects are JSON.

One run of the route over 197,430 lines: 157,101 records returned by the receiver, 44,788 into the hot table, 113,849 into 54 objects. Those objects were then replicated across 30 day partitions, 2 objects per service and day: 180 objects, 144MiB, 3,415,470 rows. One day holds 6 objects; all days hold 180. The day probed is 2026-09-10, the service opentelemetry-collector.

| Query | Answer | Rows read | Bytes read | S3 GET | S3 LIST | ms | ms warm |
|---|---|---:|---:|---:|---:|---:|---:|
| hot only, last hour, count | 44788 | 44,788 | 358,304 | 0 | 0 | 12 | 8 |
| merge, service opentelemetry-collector and one day, both in the path | 76915 | 82,277 | 3,319,724 | 2 | 1 | 115 | 159 |
| merge, service opentelemetry-collector, no day predicate | 2320676 | 2,335,854 | 99,319,940 | 60 | 1 | 2,156 | 2,095 |
| merge, time only, the shape HyperDX sends | 158637 | 3,460,258 | 145,413,762 | 180 | 1 | 7,449 | 7,097 |
| merge, time plus day >= today() - 1 | 158637 | 272,486 | 10,116,817 | 12 | 1 | 468 | 539 |
| merge, text search for 'snapshot', no other filter | 372829 | 3,460,258 | 155,744,958 | 180 | 1 | 4,453 | 3,612 |
| merge, text search for 'snapshot', one day | 12351 | 119,211 | 4,845,257 | 6 | 1 | 169 | 640 |
| merge, one pattern hash, no time filter | 983326 | 3,460,258 | 145,725,389 | 180 | 1 | 7,494 | 7,822 |
| merge, one pattern hash and one day | 32649 | 119,211 | 4,850,619 | 6 | 1 | 408 | 263 |
| cold only, one day, count | 113849 | 113,849 | 4,834,533 | 6 | 1 | 150 | 142 |

## Gap 2: the cold branch in Vector

**Closed, and the answer to the first question is no.** Vector's shipped build
does not carry a parquet codec. Its own binary lists what it will take, and
parquet is not in the list. The research note that said Vector "writes Parquet
natively" is wrong, and any surface that rests on it needs correcting.

What Vector does do is the rest of it, and it does it without complaint: an
OpenTelemetry source takes the returned stream from the routing collector, a
`route` transform makes the offload decision on `routeState`, a `remap`
transform shapes each record into the body and attribute map the cold table
reads, and `aws_s3` writes objects with the service and the day in `key_prefix`.
The objects are read by the same S3 table and the same Merge table the harness
uses, with no change to either, and the same queries answer the same numbers.

Two things about the run are worth reading off the table rather than the prose.
The object count is what a large batch buys: fifty objects for the whole cold
side, against one S3 GET each on a query that names only a time. And the
Parquet copy of exactly the same rows, written by ClickHouse because Vector
cannot write it, is three objects and 1.3 MiB against fifty objects and 165 MiB
of JSON, answers every query identically, and reads fewer rows on the text
search because Parquet row groups are skipped on statistics that JSON has no
equivalent of. That is the shape of what a parquet codec at the collector would
be worth; it is not a measurement of Vector.

Two footnotes on the run itself. Vector 0.50 has no `ndjson` codec either: the
newline delimited JSON the S3 table reads is the `json` codec with newline
framing. And end to end acknowledgements on the OpenTelemetry source hold the
gRPC response until the S3 batch flushes, which pushes back through the
collector and stalls the entire route, hot side included; the first run of this
script moved 1,425 records of 157,083 for that reason, and the config turns them
off.

| Question | Answer |
|---|---|
| Vector build | `vector 0.50.0 (x86_64-unknown-linux-gnu 9053198 2025-09-23 14:18:50.944442940)` |
| `encoding.codec: parquet` accepted | NO |
| codec the run used | `json` |
| objects Vector wrote | 50 |
| bytes Vector wrote | 165MiB |
| rows readable through the S3 table | 113,732 |
| rows on the wire | 157,083 |
| rows in the hot table | 43,351 |
| Parquet copy, written by ClickHouse | 3 objects, 1.3MiB, 113,732 rows |

What Vector's own binary says about the parquet codec:

```
Failed to load ["/etc/vector/probe.yaml"]
-----------------------------------------
x unknown variant `parquet`, expected one of `avro`, `cef`, `csv`, `gelf`, `json`, `logfmt`, `native`, `native_json`, `protobuf`, `raw_message`, `text`

in `sinks.out`
```

| Query | Answer | Rows read | Bytes read | S3 GET | S3 LIST | ms | ms warm |
|---|---|---:|---:|---:|---:|---:|---:|
| hot only, last 4 hours, count | 43351 | 43,351 | 346,808 | 0 | 0 | 8 | 9 |
| merge, service opentelemetry-collector and one day: Vector objects, json | 89739 | 93,218 | 123,228,832 | 19 | 1 | 109 | 106 |
| merge, time only, the shape HyperDX sends: Vector objects, json | 157083 | 157,083 | 172,958,539 | 50 | 1 | 207 | 210 |
| merge, text search, no other filter: Vector objects, json | 14581 | 157,083 | 183,063,710 | 50 | 1 | 157 | 157 |
| merge, one pattern hash: Vector objects, json | 36395 | 157,083 | 173,259,848 | 50 | 1 | 253 | 200 |
| merge, service opentelemetry-collector and one day: Parquet copy | 89739 | 93,218 | 50,433 | 1 | 1 | 14 | 14 |
| merge, time only, the shape HyperDX sends: Parquet copy | 157083 | 157,083 | 1,535,058 | 3 | 1 | 82 | 85 |
| merge, text search, no other filter: Parquet copy | 14581 | 139,354 | 7,506,302 | 3 | 1 | 46 | 55 |
| merge, one pattern hash: Parquet copy | 36395 | 157,083 | 1,836,367 | 3 | 1 | 86 | 72 |

## Gap 3: the Retriever over this layout

**Half closed, and the half that is open is named.** The layout is indexable as
written. A value-level fetch from it was not completed here, and the reason is
the Retriever's topology rather than the objects.

The objects the collector wrote, one JSON array per object with the body and a
flat attribute map per record, went through the shipped index pipeline with the
`Local` accessor and came out with a byte-range index, a reverse index, a
template file and bloom filter objects under `tenx/app/{b,r,t}/` and
`app/<bucket>/<byte range>/`. The same records written one per line indexed the
same way. Neither shape needed a change to the objects, so the container shape
is not a barrier: the indexer reads the array and it reads the lines.

The query is where it stops. Two things had to be changed in the shipped query
config before it would even start, both asserted in `patch_retriever_config.py`
and both reported here rather than worked around:

- `search` may not be blank. A query by type alone, with the hash in `filters`
  and nothing in `search`, is refused at construction with "search cannot be
  blank", so the run passes a word from the type's own pattern text.
- The scan slice, `scanFunction.parallel.timeslice`, is one minute in the
  shipped file, and the coordinator reads it to decide between running each
  slice itself and posting it to a worker. With a window wider than a slice
  every slice is posted to `http://localhost:8080/pipeline`, and a single
  container has nothing listening there. Set to zero, the scan runs in the
  coordinator's own thread pool and the query completes.

With the scan local and a type that is in the indexed objects, the query runs to
completion in the time the table records, the scan matches byte ranges, and then
the fetch of those byte ranges is posted to the stream worker endpoint, which is
the same address. Three connection failures, no results object, no rows returned.
The Retriever's read path is a coordinator plus scan workers plus stream workers;
what a single container can do is index and scan, not fetch.

**What it would take to close the other half.** The deployed shape, or the
Lambda flavour: a query handler and a stream worker reachable at the scan and
stream URLs, which is what `terraform-aws-tenx-retriever-lambda` stands up. That
is a deployment, not a change to the layout, and nothing in this run suggests
the layout is what would fail.

Two smaller facts from the run, both of which a deployment would have to size
for: indexing is per object and the objects here are megabytes, and the first
run of this script indexed one 9 MB object in about six minutes with the
progress gauge on. This run sets `quiet` and indexes two objects per shape
rather than all forty three, because what is being answered is whether the
layout is indexable, not what a bucket's worth costs.

| Shape indexed | Objects attempted | Exit code | Index artifacts written |
|---|---:|---:|---:|
| as the collector wrote it, one JSON array per object | 2 | 0 | 8 |
| the same records, one JSON object per line | 2 | 0 | 7 |

Objects indexed: 2 of 43 in the export, written by gap5. The query asked for pattern hash `irw7La5zUmA` over a one day window against the jsonl index: exit 0 in 15,924 ms.

The indexer's last words on the objects as written:

```
026-09-15 14:40:09.745 [main] ExecutionPipeline - terminate of unit: templateLoader took 1ms
[INFO ] 2026-09-15 14:40:09.746 [main] ExecutionPipeline - terminate of unit: group took 1ms
[INFO ] 2026-09-15 14:40:09.752 [main] ExecutionPipeline - terminate of unit: output took 6ms
[INFO ] 2026-09-15 14:40:09.790 [main] IndexFilterStats - index complete. Bytes: 477, filters.size: 1, probability historgram: [1=>1], key sizes: [150=>1], element counts: [50=>1], epochs: 1
[INFO ] 2026-09-15 14:40:09.791 [main] IndexFilterWriter - index written: object=service=cart/day=2026-09-15/logs_279753243.json, byteRanges=1, filters=1, values=62, minTimestamp=1789480979793 (2026-09-15T14:02:59.793+0000), maxTimestamp=1789480979793 (2026-09-15T14:02:59.793+0000)
[INFO ] 2026-09-15 14:40:09.791 [main] ExecutionPipeline - terminate of unit: output took 39ms
[INFO ] 2026-09-15 14:40:09.792 [main] ExecutionPipeline - terminate of unit: publishEnvMetrics took 1ms
[INFO ] 2026-09-15 14:40:09.792 [main] ExecutionPipeline - terminate phase took 49ms
[INFO ] 2026-09-15 14:40:09.793 [main] ExecutionPipeline - execution of: /opt/tenx/modules/pipelines/run/pipeline.yaml (myObjectStorageIndex) completed in: 12sec
```

## Gap 4: durable handoff under failure

**Closed, and the answer is no.** The handoff is not durable. A container killed
mid-stream and restarted twenty seconds later costs a third to a half of the
capture, and the collector arm doubles some of what survives.

Every input line carries its own number inside its body, so the reconciliation
is per line and not per batch: `extractAll(Body, 'tenxseq…')` over the Merge
table counts what was stored, whatever the receiver grouped or the collector
batched. Read the missing and duplicate rows of the table first; everything else
is context for them.

**The routing collector, killed and restarted.** The collector checkpoints its
file position in a `file_storage` extension, which is what a deployment would
configure, and the checkpoint is why this arm does not simply re-read the file
from the top. What it does instead is lose everything that was in flight and
deliver part of the rest twice. The file receiver reads far ahead of the route,
so by the time the container dies its checkpoint has already passed the lines
the engine and the exporters were still holding, and those lines come back from
nowhere.

**The receiver, killed and restarted.** Nothing is duplicated and more is lost.
The collector's OTLP exporter cannot deliver while the receiver is down, its
queue fills, and the records in it are gone; the receiver's own in-memory state
goes with the container.

Two things this arm pair does NOT say. It does not say what a crash costs when
the collector's checkpoint is also lost, which is the harsher case. And it does
not say anything about a half-written object: the object store here is MinIO on
the same host, and every object the run wrote was complete.

**One reading artifact, stated so the table is not misread.** The collector's
file exporter, which taps every record the receiver returned, is truncated when
the collector container restarts. In the collector arm the tap therefore holds
only what came back after the restart, which is why `records over, counted by
hash` is large there and means nothing: the wire is not a reference in that arm.
In the receiver arm the collector never restarts, the tap is intact, and hot
plus cold equals the tap exactly.

**What would close the gap the other way.** A persistent queue on both hops: the
collector's `file_storage` extension behind the exporter queues rather than the
file position alone, and a receiver that either acknowledges nothing until the
record is written or keeps its own spool. Neither is configured in the shipped
recipe today, and until one is, "every line kept" is a claim about the policy
and not about the route.

| Measure | router | engine |
|---|---:|---:|
| input lines | 197,430 | 197,430 |
| hot rows at the kill | 27,119 | 24,156 |
| seconds down | 20 | 20 |
| records the receiver returned | 23,899 | 89,768 |
| rows in the hot table | 48,696 | 27,501 |
| rows in the objects | 70,676 | 62,267 |
| sequence numbers found | 148,989 | 112,668 |
| distinct sequence numbers | 132,161 | 112,668 |
| sequence numbers seen more than once | 8,414 | 0 |
| duplicate deliveries | 16,828 | 0 |
| input lines never stored | 65,269 | 84,762 |
| pattern hashes on the wire | 97 | 2,586 |
| pattern hashes stored | 2,598 | 2,586 |
| records short, counted by hash | 0 | 0 |
| records over, counted by hash | 95,473 | 0 |

## Gap 5: query and alert correctness

**Closed on the queries and on the alert's creation, open on the alert's own
evaluation.** Two of the three questions change their answer when rows leave the
hot table. The Merge table and the counts table both give the answer the hot
table gave before the offload, to the row. HyperDX's API accepts an alert over
each of the three surfaces, the Merge table included, which is the surface an
alert has to point at if it is to keep firing.

Read the question table by column. The hot table before the offload and the
Merge table after it agree exactly: the type that was counted 36,395 times
before is counted 36,395 times after, through hot plus cold. The hot table after
the offload answers 3,688 for the same question, and it does not fail or warn
while doing it, which is the whole problem. The counts table answers the
count-shaped questions at a fraction of the rows read and with no object-store
request at all.

**Q3 is weaker than intended, and here is why.** The word for the text search was
supposed to be one that lives only in offloaded rows. No word of the twenty
biggest offloaded types is absent from the hot table, because the cap keeps the
first occurrences of every type and offloads the overflow: a capped type is on
both sides by construction. The run reports that in `word_only_cold`, and the
word it fell back to lives on both sides, so Q3 measures the drift rather than a
clean disappearance. A type that first appears after its window's cap is already
spent would give the clean case; finding one is a search over the census, not a
property of the policy.

**Nothing was lost and nothing was stored twice in this run, and that is not a
property of the route.** Hot plus cold equals what the receiver returned, on both
feeds, and every stored row is a distinct `(Timestamp, Body)` pair. An earlier
run of this same script on this same host stored 207,384 rows for 157,126
distinct pairs: fifty thousand copies, with no restart and no policy change, from
a retry on an insert that had already committed. The duplicates table is in the
results because the check is cheap and the failure is invisible to the lossless
check the end to end harness performs. One caveat on its cold column: a cold
row's timestamp is reconstructed from `TimestampSec`, so two identical messages
inside one second are indistinguishable there and the cold repeats are an
artifact of second resolution, not evidence of duplication.

**The alert.** A webhook, three sources, three saved searches and three alerts,
all created over the API, all 200. Two API facts worth keeping: an alert is
refused without `channel.webhookId`, and a webhook is refused if its URL resolves
to a private or reserved address. Whether each alert would fire is computed from
the count its surface returns against a threshold of half the before count, and
the table says which: the hot table stops firing after the offload, the Merge
table and the counts table do not. That computation is not HyperDX's own
evaluation loop. An alert evaluates the window its interval names, and by the
time a five minute loop runs, a replayed capture's rows are older than the
window. That is the open half of this gap and it needs a live feed, not a replay.

Before: 157,090 rows in the hot table, 0 objects. After: 43,367 hot, 113,756 in 65 objects. The type asked for is `z1LKaIvhNlY`; the word is `Traces`, NOT only on the cold side.

| Side | Rows stored | Distinct (Timestamp, Body) | Stored more than once |
|---|---:|---:|---:|
| before, hot table | 157,090 | 157,090 | 0 |
| after, hot table | 43,367 | 43,367 | 0 |
| after, the objects | 113,756 | 107,403 | 6,353 |

| Question | before, hot table | after, hot table | after, merge table | before, counts table | after, counts table |
|---|---|---|---|---|---|
| Q1 count all by service, last 4 hours | opentelemetry-collector = 89739 / kafka = 28789 / cart = 196 | opentelemetry-collector = 12972 / kafka = 7975 / ad = 7115 / | opentelemetry-collector = 89740 / kafka = 28789 / cart = 196 | opentelemetry-collector = 89739 / kafka = 28789 / cart = 196 | opentelemetry-collector = 89740 / kafka = 28789 / cart = 196 |
| Q2 count of one offloaded type | 36395 | 3688 | 36395 | 36395 | 36395 |
| Q3 text search, word only in offloaded rows | 36422 | 3715 | 36422 | 36396 | 36396 |

The alert, over the HyperDX API. The rule is "fires when the count of the type is above half what it was before the offload", threshold 18,197.

| Surface | Count the surface returns | Would fire | Saved search | Alert |
|---|---:|---|---|---|
| before, hot table | 36,395 | yes | 200 | 200 |
| after, hot table | 3,688 | no | 200 | 200 |
| after, merge table | 36,395 | yes | 200 | 200 |
| after, counts table | 36,395 | yes | not attempted | not attempted |

## Gap 6: incremental economics against a collector-only policy

**Closed, and the answer on this capture is no.** The per-type policy does not
beat a competent collector-only policy on hot compute. It beats it on what a
query can ask, and that is a different claim.

Three arms, the whole capture each time, on a ClickHouse whose `query_log` and
`part_log` were truncated before each: no offload, a collector-only policy by
service and severity, and the per-type cap with the overflow offloaded. The
collector-only policy is the one a competent engineer writes after reading a
census once: parse a severity out of the line, send the two chattiest services'
INFO and DEBUG to the object store, leave everything else alone. The two
chattiest services were read off the first arm's own hot table.

Insert plus merge CPU: the collector-only arm is the cheapest of the three. It
keeps more rows than the per-type arm and still costs less to insert and merge,
and the reason is in the bytes column rather than the rows column. The receiver
groups a multi-line event into one record, so the per-type arm's rows are fewer
and bigger, and ClickStack's text index is built over `Body`. Fewer, larger rows
is not automatically less work on a table whose cost is dominated by indexing
the text.

That grouping is also why the arms do not hold the same number of records at
all: the collector-only arm stores one record per input line, 197,430 of them,
and the two arms with the receiver in the path store about 157,000. Any
comparison of row counts across those arms is a comparison of two different
units, and the table says so.

What the per-type arm buys is the question the collector-only arm cannot answer.
`Q2`, the count of one message type, is asked by hash. In the collector-only arm
there is no hash on any row, hot or cold, so the question is not answered
wrongly, it cannot be put. `Q1` and `Q3` are answered by all three arms, and the
hot table's answers differ from the Merge table's in both offload arms, in the
direction the offload moved the rows.

**What this does not say.** Nothing about money: there is no Cloud autoscaler
here, no bill and no compute term, and the CPU seconds are ClickHouse's own
accounting on one container on one host. Merge CPU in particular is noisy: it
depends on which parts the scheduler happened to merge inside the arm's window,
and the per-type arm's merge figure is larger than the no-offload arm's despite
a quarter of the rows. A claim about compute on a customer estate needs that
estate's own `system.query_log`, not this.

**One thing to fix before this is rerun.** The three arms ran as three separate
invocations, on three fresh stacks, because an unrelated process on the host
removed the containers twice mid-run. Each arm's numbers are internally
consistent and come from its own truncated logs; a single uninterrupted run of
all three on one stack would be better and is what the script does by default.

The two chattiest services, read off the first arm's hot table: opentelemetry-collector, kafka. The type asked for is `z1LKaIvhNlY`, the word is `snapshot`.

| Measure | a_none | b_collector | c_10x |
|---|---:|---:|---:|
| rows in the hot table | 157,092 | 72,759 | 43,128 |
| bytes in the hot table | 11,277,704 | 3,522,512 | 4,664,841 |
| active parts | 3 | 4 | 6 |
| insert CPU, seconds | 4.3 | 1.3 | 1.8 |
| insert statements | 29 | 10 | 27 |
| merge CPU, seconds | 5.8 | 1.4 | 6.3 |
| merges | 5 | 1 | 4 |
| insert plus merge CPU, seconds | 10.1 | 2.7 | 8.1 |
| counts table merge CPU, seconds | 0.1 | 0.0 | 0.2 |
| objects written | 0 | 50 | 60 |
| rows in the objects | 0 | 124,671 | 113,947 |

The three questions, per arm:

| Question | a_none | b_collector | c_10x |
|---|---|---|---|
| Q1 count all by service, last 4 hours: hot table | opentelemetry-collector = 89740 / kafka = 28789 / cart = 196 | cart = 39292 / frontend = 16204 / ad = 7118 / recommendation | opentelemetry-collector = 13026 / kafka = 7858 / ad = 7115 / |
| Q3 text search for 'snapshot': hot table | 14580 | 43 | 2261 |
| Q2 count of one type by hash: hot table | 36395 | not asked | 3780 |
| Q1 count all by service, last 4 hours: counts table | opentelemetry-collector = 89740 / kafka = 28789 / cart = 196 | opentelemetry-collector = 93875 / cart = 39292 / kafka = 310 | opentelemetry-collector = 89740 / kafka = 28789 / cart = 196 |
| Q1 count all by service, last 4 hours: merge table | not asked | opentelemetry-collector = 93875 / cart = 39292 / kafka = 310 | opentelemetry-collector = 89740 / kafka = 28789 / cart = 196 |
| Q3 text search for 'snapshot': merge table | not asked | 14581 | 14580 |
| Q2 count of one type by hash: merge table | not asked | not asked | 36395 |

## What stayed open

| Gap | What is open | Why, and what would close it |
|---|---|---|
| 3 | the fetch | The Retriever's read path is a coordinator plus scan workers plus stream workers. A single container indexes and scans; the fetch of the matched byte ranges is posted to a stream worker endpoint, and there is none here. Closing it needs the deployed shape or the Lambda flavour, not a change to the layout |
| 5 | the alert's own evaluation | An alert evaluates the window its interval names, and a replayed capture is older than any interval short enough to wait for. The API's acceptance of each alert is measured; the firing is computed from the counts. Closing it needs a live feed |
| 5 | the clean text case | No word of the twenty biggest offloaded types is absent from the hot table, because the cap keeps the first occurrences of every type. The text search therefore measures drift, not disappearance. Closing it needs a type that first appears after its window's cap is spent |
| 6 | money | No Cloud autoscaler, no bill, no compute term. CPU seconds are ClickHouse's own accounting on one container. Closing it needs an estate's own `system.query_log` and its invoice |
| 6 | merge CPU as a stable number | Merge cost depends on which parts the scheduler happened to merge inside an arm's window, and the per-type arm's merge figure is larger than the no-offload arm's on a quarter of the rows. Closing it needs repeats per arm, the way `../../clickhouse-clickstack/run_compute.sh` keeps the fastest of three |
| 1 | a real day mix | Every one of the thirty days is a replica of the run's own cold rows with the timestamps shifted, gzipped, and written by ClickHouse rather than the collector. The request counts are exact; the content is not an estate's |

## Two findings that are about the harness rather than a gap

**The route drops records, and the drop is silent.** The collector's file
receiver reads far faster than the receiver can take. With the shipped exporter
queue, the batches that do not fit are rejected and logged as "sending queue is
full", and nothing downstream counts them: a hundred thousand lines were read in
twenty seconds with nothing listening at all. Every run in this folder adds
`sending_queue.block_on_overflow: true` on the exporter into the receiver, which
turns the drop into backpressure, and adds the collector's own telemetry on an
address the run can read so a run knows how many lines the file receiver has
accepted. Without both, a run settles early and calls a partial feed a finished
one. The first run of gap 1 in this folder did exactly that, and its numbers were
thrown away.

**Hot plus cold is not the same as every line, and it is not even the same as
every row once.** The lossless check the end to end harness performs counts
records the receiver returned against rows stored. Gap 4 counts input lines
through a number inside each body, and under a restart finds both loss and
duplication. Gap 5 counts distinct `(Timestamp, Body)` pairs against rows stored,
with no restart at all; in the committed run it finds none, and in an earlier run
of the same script on the same host it found fifty thousand copies of rows
inserted twice. Three different questions, three different answers, and only the
first one is the one the harness next door asks.

## The host these ran on

Every number above is one run on one laptop with 8 GB of Docker memory, and
three of the runs were repeated because an unrelated process on the same host
removed the containers mid-feed. Nothing here is a throughput measurement, and
the timings are comparable to each other and to nothing else.

