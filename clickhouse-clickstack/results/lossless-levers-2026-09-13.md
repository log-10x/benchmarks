# Two lossless levers on the real capture: batch shape and recompression

Measured 2026-09-13 by `run_lossless.sh`. Same 197,430 rows, same ClickStack schema, every row present in every arm. CPU is ClickHouse's own user plus system time.

## A. Insert batch shape

Fewer, larger inserts make fewer parts, and fewer parts merge fewer times. The engine already batches upstream, so this is a knob it owns. Three passes after a discarded warm-up, fastest kept, every pass shown.

| Rows per batch | Batches | Insert CPU s | Merge CPU s | Total CPU s | vs 5,000 | Every pass total |
|---:|---:|---:|---:|---:|---:|---|
| 1,000 | 198 | 14.42 | 14.61 | 29.03 | 303% | 29.03, 30.80, 33.20 |
| 5,000 | 40 | 4.86 | 4.71 | 9.58 | 100% | 9.58, 9.77, 11.11 |
| 20,000 | 10 | 3.51 | 1.60 | 5.11 | 53% | 5.11, 6.64, 6.90 |
| 100,000 | 2 | 4.23 | 0.00 | 4.23 | 44% | 4.23, 4.96, 9.60 |

## B. Recompression ceiling on real log text

`run_policy.sh` showed `TTL RECOMPRESS` is a no-op against ClickStack's explicit column codecs and measured 2.1% on synthetic digits where it does fire. This is the real `Body` at four levels with nothing in the way, which is the most a recompress policy could ever return on this text.

| Codec | Body bytes | vs ZSTD(1) | Whole table | vs ZSTD(1) |
|---|---:|---:|---:|---:|
| ZSTD(1) | 1,888,245 | 0.0% | 8,225,912 | 0.0% |
| ZSTD(3) | 1,860,990 | 1.4% | 7,375,649 | 10.3% |
| ZSTD(9) | 1,549,663 | 17.9% | 5,796,994 | 29.5% |
| ZSTD(12) | 1,523,871 | 19.3% | 5,763,077 | 29.9% |

## What it says

Batch shape moves insert-plus-merge CPU from 29.03 s at a thousand rows per insert to 4.23 s at a hundred thousand, 85% less for the same rows with nothing removed. This is a compute lever a collector or the engine controls upstream of ClickHouse, and it costs nothing but latency between a line being logged and being queryable.

**Two caveats that bound this.** The inserts here are `INSERT ... SELECT` from a staging table, which ClickHouse does not route through `async_insert`; a client sending small HTTP inserts to 26.3 or later gets server-side coalescing by default, so the thousand-row baseline is pessimistic for such a client and the lever is the part count that reaches merges, not the statement count. And the CPU a collector spends holding and shipping larger batches is not in these numbers; only ClickHouse's side is.

Recompressing the real text from ZSTD(1) to ZSTD(12) takes 19.3% off the Body column and 29.9% off the table. Disk is about a tenth of a thirty-day bill, so the most a recompress policy can return on that bill is roughly a tenth of that figure, and only after the ClickStack column codecs are removed so the TTL can act.

The write cost of the higher level is not measured here. ZSTD(12) spends more CPU compressing on insert and on every merge than ZSTD(1) does, so a recompress policy that applies it only to parts past their hot window, which is what `TTL RECOMPRESS` is for, is the shape that keeps that cost off the ingest path.
