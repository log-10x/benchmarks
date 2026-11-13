# clickstack-e2e-gaps

What changes in ClickStack when part of the logs moves to S3 and a Merge table reads both sides? Counts through the Merge table matched the counts from before the move, while the hot table alone gave a wrong count with no error. Queries that name only a time opened all 180 objects over 30 days. On ClickHouse compute, a plain collector rule by service and severity was cheaper than the 10x per-type policy.

The 10x engine keeps the first lines of each message type in a window hot and marks the rest, which the collector writes to S3 under a service and day path. ClickHouse can skip an object unopened only on those path segments, since the timestamp and the message type live inside the file.

## Result

From several runs over one 197,430-line capture.

| Measurement | Result |
|---|---|
| Time-only query over 30 days | 180 GETs, 7,449 ms |
| Same query plus a day predicate | 12 GETs, 468 ms |
| LIMIT 100 through the Merge table | 180 GETs, 5,090 ms |
| Same LIMIT 100, hot table alone | 0 GETs, 7 ms |
| One type's count, hot table alone | 3,688 (36,395 before offload) |
| Same count through the Merge table | 36,395 |
| Insert plus merge CPU, seconds | none 10.1, collector 2.7, per-type 8.1 |
| Lines lost, engine acks after writing | 0 of 197,430 |

Both LIMIT 100 queries returned the same hundred rows, all of them hot. The collector rule used the least CPU, but its rows carry no message type to count by.

- With the engine acknowledging only after its lines are written, killing the collector, the engine or both lost no line in two runs and stored at most 997 lines twice. Acknowledging on receipt lost 24,900 to 32,203 lines under the same kills.
- An S3 table with hive partitioning that is read once while its prefix is empty matches nothing on a path predicate, while `count()` looks right (ClickHouse issue 116888). Creating it after the first object exists avoids this.

## How it was measured

The route is the one in [clickstack-e2e](../clickstack-e2e/), with a local S3-compatible store, on one laptop with 8 GB of Docker memory. For the 30-day queries, one run's cold objects were copied into 30 day partitions, six objects a day. GETs and CPU come from ClickHouse's query and part logs, and lost lines are counted by a sequence number inside every line. The collector rule sends the two busiest services' INFO and DEBUG lines to S3.

## Limits

- Each setup ran once or a few times. Timings compare only with each other. Merge CPU and doubled lines vary by run.
- The 30 days are copies of one day's cold rows, so request counts are real but the content is not a real month.
- Nothing here measures money, HyperDX's own alert evaluation, or fetching cold objects back through 10x.

## Run it

```
cd clickstack-e2e-gaps
../clickstack-e2e/run.sh        # once: the base run; fetches the capture, checks its sha256
./gap1_multiday_pruning.sh      # or any gap*.sh; LINES=20000 for a short run
```

Each script needs Docker with about 7 GB of memory and 3 GB of disk. The acknowledge-after-write runs used engine 1.1.150 through `PATCHED_JAR` (see `lib.sh`).

[RECORD.md](RECORD.md) has the full record: what each script measures and leaves out, the build each run used, and a guide to [results/](results/).
