# clickstack-e2e

ClickStack stores log records in one ClickHouse table, `otel_logs`, which HyperDX queries. In this run, records over a byte cap on each of three services went to an S3-compatible bucket, and one Merge table answered queries over both sides. Of the 37,536 records the 10x engine returned, 13,010 went into ClickStack's table and 24,526 to the bucket, and the stored counts matched the returned ones in total and for every pattern hash.

An OpenTelemetry Collector sends each record to the 10x engine over OTLP, and a record over its service's cap comes back marked `offload`. The collector writes those to the bucket under a path naming the service and the day.

## What each query read from the table and the bucket

Count queries from the 2026-09-15 run, each on a cold cache, as ClickHouse's query log recorded them. The service filter is opentelemetry-collector.

| Query | Rows read | S3 GETs | ms |
|---|---:|---:|---:|
| ClickStack table, last hour | 12,012 | 0 | 8 |
| Merge, one service, last hour | 25,793 | 6 | 77 |
| Merge, one service, one day | 25,793 | 6 | 43 |
| Merge, last hour (HyperDX's filter) | 37,536 | 14 | 118 |
| Merge, text search | 37,536 | 14 | 99 |
| Merge, one pattern's text | 40,075 | 14 | 136 |
| Merge, hashed rows per side | 37,536 | 14 | 123 |
| Counts table, by service | 2,539 | 0 | 6 |

Each object in the bucket carries the service and the date in its name, and ClickHouse can skip a whole object on its name alone, so a service filter read only that service's 6 objects. The timestamps sit inside the objects, so the time-only filter HyperDX sends opened all 14 and took 118 ms, against 8 ms on ClickStack's table. The one-pattern query also reads the counts table.

- The counts table, one count per service and pattern per minute, got the offloaded rows' counts from one INSERT ... SELECT after the run.
- Of the 37,536 returned records, 37,486 carried a pattern hash. A record without one is stored but cannot be counted per type.

## How it was measured

The input is the first 50,000 lines of the released capture otel-sample-200mb.log, whose envelope carries no timestamp, so each record takes its ingest time. One command starts ClickStack 2.38.0 on ClickHouse 26.5.7.64, the 10x engine, a stock OpenTelemetry Collector 0.160.0 and MinIO in containers. The stock collector routes because ClickStack's own collector has no S3 exporter. The offload encoding keeps only body and attributes, so the collector first copies service, severity and record time into attributes. The harness adds a day column to ClickStack's table.

## Limits

- The run used MinIO in place of S3 and a query list written for this test, and did not measure throughput, ClickHouse Cloud cost or alerts.
- Every object carries one day in its path, because the path records the write time. Pruning across thirty days is measured in [clickstack-e2e-gaps](../clickstack-e2e-gaps/).
- The lossless check starts from the records the engine returned, not the 50,000 input lines, and a lost line and a duplicated one would cancel in it.

## Run it

```
cd clickstack-e2e
./run.sh              # everything, about fifteen minutes
LINES=20000 ./run.sh  # a smaller slice of the capture
```

A run needs Docker with about 8 GB of memory and downloads the capture on first use.

[RECORD.md](RECORD.md) has the pipeline and what a run does and does not prove, and [the results file](results/clickstack-e2e-2026-09-15.md) has every number and config.
