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
