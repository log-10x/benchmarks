# clickhouse-clickstack

How much disk do 10x compact events save in ClickHouse's ClickStack `otel_logs` schema? On 197,430 lines from the OpenTelemetry demo, the whole table came out 14.9% smaller, but the SQL functions that decode compact rows in ClickHouse returned the wrong text for 78% of them. Keeping the original text and adding the message type as a column inside the sort key took 13.1% off the table with no decoder and the text index intact.

The 10x engine writes each message as a template hash plus its values and folds a multi-line event into one, so the lines became 159,170 compact events.

## Result

Whole table on disk at ZSTD(1), with the 348,040-byte template dictionary in every compact total.

| Layout | Rows | Bytes on disk | Smaller than published | Full-text index on Body |
|---|---:|---:|---:|---|
| ClickStack as published | 197,430 | 8,225,547 | 0.0% | kept |
| Compact events in Body | 159,170 | 6,999,850 | 14.9% | kept |
| Compact, hash in sort key | 159,170 | 6,188,001 | 24.8% | kept |
| Compact, typed value arrays | 159,170 | 4,376,741 | 46.8% | none |
| Original text, type in sort key | 197,430 | 7,148,605 | 13.1% | kept |
| Original text, sorted by type | 197,430 | 6,451,087 | 21.6% | kept |

Against the original text of the same events, the compact form takes 23.55% off the `Body` column. The larger savings come mostly from ClickStack's full-text index on Body shrinking or going away, and sorting by type first weakens the time-range primary key.

- Through the SQL decoder, 78.0% of compact rows matched no captured line, and a text filter took 531 ms against 6 ms on the original rows. A Python decoder with the four rules the SQL lacks returned 24,494 of the 24,501 events without a timestamp slot byte-identical, so the text is intact and the SQL misreads it. log10x does not offer the SQL decoder for ClickHouse.
- Row for row, the compact text cost the same insert CPU as the original (1.64 s). Removing rows cut CPU more than proportionally: half the rows cost 39% of insert-plus-merge CPU and a quarter cost 17%.
- TTL RECOMPRESS does nothing on ClickStack, which declares CODEC(ZSTD(1)) on every column. Without that codec, the original-text table at ZSTD(12) was 29.9% smaller than at ZSTD(1), more than any layout above that keeps the text index.

## How it was measured

The data is `otel-sample-200mb.log` from the otel-sample-v2 release, loaded into the published ClickStack DDL with all eight skip indexes and its sort key, minus the TTL placeholder. ClickHouse 26.8.3.105 ran in one container with 8 GiB and 8 CPUs. Every byte count is read from system.parts and system.parts_columns after OPTIMIZE FINAL.

## Limits

- The data is one demo capture in one container.
- ClickHouse's own 45x figure comes from one typed table per service, which this single-table test does not reproduce.
- CPU covers ClickHouse's insert and merge time, not the collector and not the write cost of ZSTD(12).
- No price is attached.

## Run it

```
cd clickhouse-clickstack
python3 reference_decode.py --self-test   # decode rules only, no Docker or download
KEEP=1 ./run.sh                           # the storage tables, leaves ClickHouse up
./run_typed.sh                            # compact rows sorted by hash, and typed arrays
./run_labeled.sh                          # original text plus a message-type column
```

The scripts need Docker and about 4 GB of disk. The storage run downloads the capture and takes roughly 20 minutes, and the other two reuse its container.

The full record, with the decode diagnosis and the compute, TTL, batch-size and query-at-scale runs, is in [RECORD.md](RECORD.md).
