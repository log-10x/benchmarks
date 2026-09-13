# The second rung: compact events stored the way ClickHouse wants them

Measured 2026-09-13 by `run_typed.sh`, on the container `run.sh` left up. Same capture, same ClickHouse, same ZSTD(1). Everything is `system.parts`, `system.parts_columns`, `system.data_skipping_indices` and `system.query_log` after `OPTIMIZE FINAL`.

## Why this exists

`clickstack-storage` stored the compact event as one text string in `Body`, which is what the ClickHouse app does today and the worst shape ClickHouse allows for it. ClickHouse's own log-clustering post measured that rung at 22x against 19x raw, then 45x once the template sat in a low-cardinality column and the values in typed columns. This file climbs the same ladder with the same compact events: first add the template hash to the sort key, then replace the text with typed arrays.

## The layouts

| Layout | Rows | What it is |
|---|---:|---|
| `native` | 197,430 | one row per captured line, Body is the message |
| `native_folded` | 159,170 | one row per event, Body is the original text |
| `compact_text` | 159,170 | Body is the compact event as one string, ClickStack sort key |
| `compact_sorted` | 159,170 | same, template hash materialised and added to the sort key |
| `compact_typed` | 159,170 | Body replaced by hash + typed value arrays, hash in the sort key |
| `compact_typed_bytemplate` | 159,170 | typed, sorted by (service, template, time) |

The typed layout carries 1,303,199 value slots: 141,827 timestamps, 453,440 integers, 707,932 text. Every row was reversed to its compact event byte for byte before it was written, and `run_typed.sh` rebuilds it again inside ClickHouse and compares hash sums with the text layout.

## On disk

`payload` is the column or columns that hold the message: `Body`, or the five typed columns. `total` is `bytes_on_disk`, plus the template dictionary for every compact layout. Skip indexes are shown because the typed layouts have no `Body` and so no `idx_lower_body`; that is a real saving and a real loss of the text index, both.

| Layout | payload | payload vs native_folded | other columns | text index on Body | all skip indexes | total + dict | total vs native | total vs native_folded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `native` | 1,888,235 | -1.2% | 2,575,656 | 3,641,204 | 3,724,080 | 8,225,547 | 0.0% | -8.7% |
| `native_folded` | 1,865,254 | 0.0% | 2,201,125 | 3,385,853 | 3,466,940 | 7,570,122 | 8.0% | 0.0% |
| `compact_text` | 1,426,009 | 23.5% | 2,201,086 | 2,906,658 | 2,987,745 | 6,999,853 | 14.9% | 7.5% |
| `compact_sorted` | 1,335,571 | 28.4% | 2,234,000 | 2,145,698 | 2,227,356 | 6,188,001 | 24.8% | 18.3% |
| `compact_typed` | 1,674,663 | 10.2% | 2,234,000 | 0 | 81,658 | 4,376,741 | 46.8% | 42.2% |
| `compact_typed_bytemplate` | 1,493,245 | 19.9% | 1,918,529 | 0 | 24,031 | 3,822,133 | 53.5% | 49.5% |

Template dictionary on disk: 348,040 bytes, included in every compact total.

## The typed columns, one by one

| Column | compact_typed compressed | uncompressed | bytemplate compressed |
|---|---:|---:|---:|
| `templateHash` | 38,680 | 242,460 | 30,485 |
| `slot_kinds` | 110,031 | 2,576,559 | 71,280 |
| `ts_vals` | 342,000 | 2,407,976 | 293,288 |
| `num_vals` | 377,270 | 4,900,880 | 354,577 |
| `str_vals` | 806,682 | 12,124,946 | 743,615 |
| `Body`, in compact_text, for scale | 1,426,009 | 12,408,451 | |
| `Body`, in native_folded, for scale | 1,865,254 | 41,665,945 | |

## Ingest cost, measured cleanly

Each layout copied table-to-table with `INSERT ... SELECT` into a fresh table of the same shape, then `OPTIMIZE FINAL`. No JSON is parsed on any side, so the CPU is what ClickHouse spends turning rows into compressed columns for that layout, and then merging them. `clickstack-storage` could not separate this from JSON parsing; this can.

Three copies per layout, fastest kept, every run shown. The first copy of `native` on a loaded host read 10 s in one run and 4.7 s the next, so a single run is not a number.

| Layout | insert CPU s, fastest | every run | merge CPU s | rows |
|---|---:|---|---:|---:|
| `native` | 2.46 | 2.46, 2.78, 4.14, 10.15 | 0.68 | 197,430 |
| `native_folded` | 1.64 | 1.64, 1.74, 1.74, 3.72 | 0.64 | 159,170 |
| `compact_text` | 1.64 | 1.64, 1.93, 2.00, 2.29 | 0.56 | 159,170 |
| `compact_sorted` | 1.54 | 1.54, 1.55, 1.66, 2.83 | 0.52 | 159,170 |
| `compact_typed` | 1.38 | 1.38, 1.46, 1.48, 2.17 | 0.59 | 159,170 |
| `compact_typed_bytemplate` | 1.55 | 1.55, 1.93, 1.95, 2.77 | 0.62 | 159,170 |

## What this says

**The generic typed layout loses on the payload.** Five typed arrays compress to 1,674,663 bytes against 1,426,009 for the same events as one text string, and 1,493,245 even sorted by template. Each array carries its own offsets stream and the values lose the neighbouring context ZSTD was using inside the string. ClickHouse's 45x rung came from one typed column per variable in a hand-built per-service table. A layout with no schema per template does not reach it, and this run is the evidence.

**The sort key alone is worth having.** Adding the template hash to ClickStack's own sort key, and changing nothing else, takes the payload from 1,426,009 to 1,335,571 bytes, 6.3% on top of the text form, and the other columns from 2,201,086 to 1,918,529 when the template leads the key, because rows of one template share their attributes. It is the one change here that a ClickHouse engineer would make unprompted, and it needs nothing but a materialised column.

**The text index is the elephant.** `idx_lower_body`, ClickStack's full-text index on `Body`, is 3,385,853 of the 7,570,122 bytes the folded native table occupies, 45%. Every large total saving in the table above is that index shrinking or disappearing, not the data compressing better. On a compact `Body` it still indexes the values, so value search works without expansion, but it cannot index the template's words because they are not in the row. A deployment that searches by pattern instead of by word can drop it and take the saving. One that needs word search keeps it and keeps most of the cost.

**Ingest, row for row, is not cheaper for the compact text.** 1.64 s against 1.64 s to build and compress the same 159,170 rows. The deployment-level gap, 2.46 s for the 197,430 native rows against 1.64 s, is the row count: it is the folding, not the compaction. The sort key takes 6.3% off and the typed layout 15.6%, because there is less text to tokenise for the index and fewer bytes to compress. The app README claims 25 to 30 percent less ingest CPU; on ClickHouse's own insert path, with parsing taken out, that claim does not hold for the text form. What a smaller payload does save is the parsing upstream of ClickHouse, in the collector and on the wire, which this run deliberately does not measure.

