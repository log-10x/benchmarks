# clickstack-e2e-gaps

On ClickHouse, every row that arrives has to be parsed, indexed, written to disk, and merged again each time parts combine. These runs fed a 197,430-line capture to ClickStack, kept each message type's first lines per time window in ClickStack's hot table, sent the rest to a local S3-compatible bucket, and read both through one Merge table. A count of one message type returned 36,395 through the Merge table, as before the move, and 3,688 from the hot table alone, with no error. A collector rule moving the two busiest services' INFO and DEBUG lines cost less insert and merge CPU than the per-type budget, 2.7 seconds against 8.1, but its rows carry no message type to count by.

The 10x engine marks lines over budget, and a stock OpenTelemetry Collector writes them under a service and day path. ClickHouse can skip an object only by its path, so a query bounded only by time opens every object in the bucket.

## What ClickHouse counted

| Measurement | Result |
|---|---|
| Time-only query over 30 days | 180 GETs, 7,449 ms |
| Same query plus a day predicate | 12 GETs, 468 ms |
| Newest 100 rows, Merge table | 180 GETs, 5,090 ms |
| Newest 100 rows, hot table alone | 0 GETs, 7 ms |
| One type's count, hot table alone | 3,688 (36,395 before the move) |
| Same count through the Merge table | 36,395 |
| Insert plus merge CPU, seconds | none 10.1, collector 2.7, per-type 8.1 |
| Lines lost, engine acks after writing | 0 of 197,430 |

Both queries for the newest 100 rows returned the same rows, all hot. The collector rule kept more hot rows than the per-type budget, 72,759 against 43,128, but fewer bytes, 3,522,512 against 4,664,841, and most of the work on ClickStack's table is indexing the body text.

- With the shipped 10x collector recipe and the engine answering after writing, killing the collector, the engine or both lost no line in two runs, stored at most 997 lines twice, and left 2,040 to 2,538 objects. Answering on receipt lost 24,900 to 32,203 lines and left 24 or 25 objects.
- An S3 table with hive partitioning read once while its prefix is empty matches nothing on a path predicate, while `count()` looks right (ClickHouse issue 116888). Creating it after the first object exists avoids this.

## How the capture went through ClickStack

The table draws on several runs of the [clickstack-e2e](../clickstack-e2e/) route, on one laptop with 8 GB of Docker memory. The 30 day partitions are copies of one run's cold objects, so request counts are real and the content is not a real month. GETs and CPU come from ClickHouse's query and part logs, and lost lines from a sequence number inside every line.

## Limits

- Each setup ran once or a few times. Timings compare only with each other, and merge CPU and doubled lines vary by run.
- Money, HyperDX's own alert evaluation and fetching cold objects back through 10x are not measured.

## Run it

```
cd clickstack-e2e-gaps
../clickstack-e2e/run.sh        # once: the base run; fetches the capture, checks its sha256
./gap1_multiday_pruning.sh      # or any gap*.sh; LINES=20000 for a short run
```

Each script needs about 7 GB of Docker memory and 3 GB of disk. Gap 3 and the answer-after-write runs need an engine jar in `PATCHED_JAR` (see `lib.sh`), and those runs used 1.1.150.

[RECORD.md](RECORD.md) has what each script measures and leaves out, each run's build, and a guide to [results/](results/).
