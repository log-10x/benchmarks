# clickstack-e2e

Can the rows a capped service sends over its cap go to an object store and still be queried with the rows ClickStack kept, as one ClickHouse table, with none lost? In this run they could. Of the 37,536 records the 10x engine returned, 13,010 went into ClickStack's table and 24,526 went to S3-compatible storage, and counting both sides back gave 37,536 with a gap of 0.

Three services had a byte cap, and the engine marked every record it returned with a route, and the records over a cap were marked offload. A stock OpenTelemetry Collector writes the offload records to the object store under a service and day path and sends the rest to ClickStack. ClickHouse reads the objects in place, and a Merge table reads both sides under one name.

## Result

Count queries from the 2026-09-15 run, each on a cold cache. The service filter is opentelemetry-collector.

| Query | Rows read | S3 GETs | ms |
|---|---:|---:|---:|
| Hot table only, last hour | 12,012 | 0 | 8 |
| Merge, one service, last hour | 25,793 | 6 | 77 |
| Merge, one service, one day | 25,793 | 6 | 43 |
| Merge, time only (HyperDX's shape) | 37,536 | 14 | 118 |
| Merge, text search | 37,536 | 14 | 99 |
| Merge, one pattern hash | 37,536 | 14 | 123 |
| Counts table, by service | 2,539 | 0 | 6 |

The time-only filter that HyperDX sends read every row and made one GET per offloaded object. A service filter cut that to the 6 objects under that service. The hot table and the counts table made no object-store request.

- Only the capped services had offloaded rows: 16,856 from opentelemetry-collector, 4,522 from kafka and 3,148 from cart.
- The same 2,495 distinct pattern hashes were on the wire and in storage. Only 37,486 of the 37,536 returned records carried a hash, and a record without one is stored but not counted per type.
- ClickStack's own collector has no S3 exporter, so a second, stock collector does the routing. The harness also adds a day column to ClickStack's `otel_logs` table.

## How it was measured

The input is the first 50,000 lines of the released capture otel-sample-200mb.log. One host runs ClickStack 2.38.0 on ClickHouse 26.5.7.64, the 10x engine, a stock OpenTelemetry Collector 0.160.0 and MinIO. The lossless check counts every record the engine returned against the stored rows, in total and per pattern hash. Query figures come from ClickHouse's own query log, with caches dropped first.

## Limits

- One run, with MinIO in place of S3. The times say nothing about real S3, throughput or ClickHouse Cloud cost.
- No alert is defined or fired, and the queries were written for this test.
- Every object carries one day in its path, because the path records the write time. Pruning across thirty days is measured in [clickstack-e2e-gaps](../clickstack-e2e-gaps/).
- The lossless check is a total, so a lost line and a duplicated one would cancel. The gaps benchmark counts per line.

## Run it

```
cd clickstack-e2e
./run.sh              # everything, about fifteen minutes
LINES=20000 ./run.sh  # a smaller slice of the capture
```

A run needs Docker with about 8 GB of memory and downloads the capture on first use.

[RECORD.md](RECORD.md) describes the pipeline and what a run does and does not prove, and [the results file](results/clickstack-e2e-2026-09-15.md) has every number and config from this run.
