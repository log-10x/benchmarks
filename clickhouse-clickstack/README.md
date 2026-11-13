# clickhouse-clickstack

On ClickHouse Cloud most of a log bill is compute, and only a little of it is the cost of keeping rows. This benchmark loaded 197,430 OpenTelemetry demo lines into ClickStack's published `otel_logs` schema, as original text and as 10x compact events. The compact table was 14.9% smaller, but the SQL that decodes it inside ClickHouse returned the wrong text for 78% of rows. Original text with a message-type column in the sort key was 13.1% smaller, with no decoder and the text index intact.

10x stores the text each log statement repeats once, as a template, and writes each message as the template's hash plus its values. The engine folds a multi-line event into one, so the lines became 159,170 compact events.

## Table size on disk at ZSTD(1)

Every compact total includes the 348,040-byte template dictionary.

| Layout | Rows | Bytes on disk | Smaller than published | Full-text index on Body |
|---|---:|---:|---:|---|
| ClickStack as published | 197,430 | 8,225,547 | reference | kept |
| Original text, one row per event | 159,170 | 7,570,122 | 8% | kept |
| Compact events in Body | 159,170 | 6,999,850 | 14.9% | values only |
| Compact, hash in sort key | 159,170 | 6,188,001 | 24.8% | values only |
| Compact, typed value arrays | 159,170 | 4,376,741 | 46.8% | none |
| Original text, type in sort key | 197,430 | 7,148,605 | 13.1% | kept |
| Original text, sorted by type | 197,430 | 6,451,087 | 21.6% | kept |

The message is a minority of a ClickStack row, and the skip indexes and attribute maps take most of the bytes. Against the same 159,170 events as original text, the compact form takes 23.55% off Body and 7.53% off the table. The larger savings come from the full-text index on Body shrinking or going away. Sorting by type first weakens the time-range primary key.

## Reading compact rows back with SQL

A one-word filter through the SQL decoder took 531 ms at its fastest, against 6 ms on the original rows. A Python decoder with the four template rules the SQL lacks returned 24,494 of the 24,501 events without a timestamp slot byte-identical, and the other 134,669 were not checked. The text is there, and the SQL misreads it. 10x does not offer the SQL decoder for ClickHouse.

## Insert and merge CPU

Row for row, compact text cost the same insert CPU as the original, 1.64 s. Half the rows, sampled uniformly, cost 39% of the insert-plus-merge CPU and a quarter cost 17%, because fewer parts merge fewer times. Removing the two largest message types left 73% of the rows and 83% of the CPU, because the remaining rows cost more each to compress.

## How the tables were built and read

The capture is otel-sample-200mb.log from the [otel-sample-v2 release](https://github.com/log-10x/config/releases/tag/otel-sample-v2), loaded into the ClickStack DDL as published minus its TTL placeholder, on ClickHouse 26.8.3.105 with 8 GiB and 8 CPUs. Bytes come from system.parts and system.parts_columns after OPTIMIZE FINAL, and CPU from system.query_log and system.part_log.

## Scope of the run

- One demo capture was measured, and its largest message type is the collector's debug exporter.
- [ClickHouse's 45x figure](https://clickhouse.com/blog/improve-compression-log-clustering) comes from one typed table per service, which this single-table test does not reproduce.
- CPU is ClickHouse's insert and merge time, without the collector.

## Run it

```
cd clickhouse-clickstack
python3 reference_decode.py --self-test   # decode rules only, no Docker or download
KEEP=1 ./run.sh                           # the storage tables, leaves ClickHouse up
./run_typed.sh                            # compact rows sorted by hash, and typed arrays
./run_labeled.sh                          # original text plus a message-type column
./run_compute.sh                          # insert and merge CPU against row count
```

The shell scripts need Docker and about 4 GB of disk. The storage run downloads the capture and takes about 20 minutes.

[RECORD.md](RECORD.md) has the decode diagnosis and the TTL, batch-size, recompression and query runs.
