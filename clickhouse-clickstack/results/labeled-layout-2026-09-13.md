# Ship the label, keep the text: native rows plus a message-type column

Measured 2026-09-13 by `run_labeled.sh`. Same 197,430 rows, same ClickStack schema at ZSTD(1), same text index on Body. The only additions are one LowCardinality column and, in two arms, its place in the sort key.

| Arm | What | Body | attributes | text index | all skip idx | total | vs native | ingest CPU s, fastest | every run |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `native` | ClickStack as published | 1,888,235 | 2,575,656 | 3,641,204 | 3,724,080 | 8,225,547 | 0.0% | 2.03 | 2.03, 2.08, 2.15 |
| `labeled` | plus templateHash, ClickStack sort key | 1,888,235 | 2,575,656 | 3,641,204 | 3,724,080 | 8,322,336 | -1.2% | 1.95 | 1.95, 2.07, 2.17 |
| `labeled_sorted` | templateHash inside the ClickStack sort key | 1,666,928 | 2,609,474 | 2,705,972 | 2,789,395 | 7,148,605 | 13.1% | 2.05 | 2.05, 2.27, 2.59 |
| `labeled_bytype` | sorted (ServiceName, templateHash, Timestamp) | 1,525,870 | 2,286,436 | 2,538,663 | 2,564,535 | 6,451,087 | 21.6% | 1.94 | 1.94, 2.10, 2.30 |

The templateHash column itself: `labeled` 90,934 bytes, `labeled_sorted` 39,108 bytes, `labeled_bytype` 30,669 bytes.

## What it says

Adding the column alone costs 90,934 bytes and changes nothing else. Putting it inside ClickStack's own sort key takes the original text from 1,888,235 to 1,666,928 bytes (11.7%) and the whole table from 8,225,547 to 7,148,605 (13.1%), with the text index intact and no decoder anywhere. Sorting by type first takes the text to 1,525,870 (19.2%) and the table to 6,451,087 (21.6%), at the cost of a weaker time-range primary key.

Ingest CPU, fastest of three table-to-table copies, is in the table; read the every-run column before believing a difference.
