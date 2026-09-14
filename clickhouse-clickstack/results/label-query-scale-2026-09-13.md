# The label as a query lever, at a size where queries cost something

Measured 2026-09-13 by `run_scale.sh`. The labeled sample replicated 100x with timestamps shifted by whole days, 19,743,000 rows, the same 2,627 message types across 100 days. CPU is ClickHouse's own user plus system time from `system.query_log`, 7 runs with the first discarded, fastest and median kept. Replicated data compresses better than real data would, so the storage figures are optimistic; the query comparison is two ways of reading one table and is not affected.

## Storage at this size

| Table | Rows | On disk | Body | vs ClickStack order |
|---|---:|---:|---:|---:|
| `big_labeled`, ClickStack order plus the label column | 19,743,000 | 827,547,676 | 190,572,929 | |
| `big_labeled_sorted`, label inside the order | 19,743,000 | 714,724,590 | 168,116,420 | 13.6% |

## The same question three ways

Two message types share the wording `GetCartAsync called with userId=`, one carrying an id and one not. The question is "how many of the one with the id". Text cannot tell them apart; the label can. `type_label_both` asks for both, which is the question the text queries actually answer, so their cost can be compared on equal terms.

| Query | How | CPU ms, fastest | median | Bytes read | Rows read | Answer |
|---|---|---:|---:|---:|---:|---:|
| `type_text_scan` | `position(Body, wording)`, plain scan | 297 | 347 | 4,094,783,489 | 19,743,000 | 1,270,900 |
| `type_text_index` | `hasToken`, ClickStack text index | 21 | 30 | 1,616 | 101 | 1,270,900 |
| `type_label` | `templateHash = x`, the label | 87 | 93 | 25,636,362 | 16,156,306 | 1,848,000 |
| `type_label_both` | label, both types | 88 | 110 | 24,928,198 | 17,699,269 | 2,541,600 |
| `type_rows_scan` | scan, and read the rows | 241 | 257 | 141,245,316 | 2,577,068 |  |
| `type_rows_label` | label, and read the rows | 240 | 243 | 130,697,691 | 7,938,684 |  |
| `word_text_scan` | word `checkout`, plain scan | 189 | 197 | 4,094,783,489 | 19,743,000 | 231,600 |
| `word_text_index` | word `checkout`, text index | 21 | 24 | 1,616 | 101 | 231,800 |
| `census_count` | top 10 types by count, label only | 449 | 462 | 29,015,660 | 19,743,000 |  |
| `census_bytes` | top 10 types by bytes, label only | 3252 | 3412 | 4,121,205,697 | 19,743,000 |  |
| `service_day` | one service, one day, control | 15 | 16 | 228,729 | 151,170 | 16,204 |
| `anyword_error` | word `error`, text index, no label equivalent | 22 | 24 | 1,616 | 101 | 279,300 |

## What it says

**One message type.** The plain scan costs 297 ms and reads 4,094,783,489 bytes; the text index costs 21 ms and reads 1,616; the label costs 87 ms and reads 25,636,362. Against the plain scan the label is 3x less CPU; against the text index 0.2x. And the answers differ for a reason that is not an error on either side: this type is a two-line event, a header line and a `GetCartAsync` line, and the label tags both lines of every event, 9,240 of each, 1,848,000 after replication. The wording sits on one line per event and belongs to two types, 9,240 plus 3,468 plus one, 1,270,900 after replication. The label's unit is the event; the text's unit is the line that happens to carry the words. Asked for both types by label the answer is 2,541,600 lines, and the cost is unchanged.

**Two counts that should match and do not.** `word_text_scan` returns 231,600 and `word_text_index` 231,800, two lines per replicated day apart. They are not the same predicate: `position(Body, 'checkout')` is a case-sensitive substring test and `hasToken(lower(Body), 'checkout')` is a case-insensitive whole-token test, so a line carrying `Checkout` counts in one and not the other. Inferred from the predicates, not re-queried; the table was torn down before this was noticed. The CPU comparison between them stands as a comparison of two ways users write the question, not of two identical questions.

**A word, not a type.** `checkout` by plain scan is 189 ms; by text index 21 ms. The label has no equivalent for a word, and does not pretend to. `error` across everything is the text index's question alone.

**The census.** Top ten types by count costs 449 ms reading 29,015,660 bytes. By bytes it costs 3252 ms reading 4,121,205,697, because summing `length(Body)` reads the text; a materialised length column would make it as cheap as the count. Text has no version of either query.

**What this does and does not establish.** At this size the fixed cost is gone and the differences are real. Whether they are money depends on what a cluster's query load is made of: type-shaped questions and censuses move to the label and get cheaper; word-shaped questions stay on the text index and do not. Neither the mix nor the Cloud autoscaler's response to lower CPU is measured here.

## The label's best case: service, then type, in the sort key

`big_labeled_bytype`, `ORDER BY (ServiceName, templateHash, Timestamp)`, 19,743,000 rows, 636,855,786 bytes on disk, Body 155,580,760. Same replicated data, same queries, same method.

| Query | How | CPU ms, fastest | median | Bytes read | Rows read |
|---|---|---:|---:|---:|---:|
| `bt_type_label` | one type by label, service-then-type key | 71 | 75 | 9,718,849 | 4,868,824 |
| `bt_type_text_index` | one type's wording by text index | 21 | 23 | 1,616 | 101 |
| `bt_type_rows_label` | one type, read the rows, label | 262 | 289 | 161,512,729 | 6,384,782 |
| `bt_census_count` | top 10 types by count | 390 | 401 | 39,401,651 | 19,743,000 |
| `bt_service_day` | one service, one day (was the control) | 15 | 15 | 90,925 | 10,102 |
| `bt_day_all` | one day, all services: the time query this key hurts | 10 | 10 | 16 | 1 |

With the type second in the key, after service, the label filter reads 4,868,824 rows and costs 71 ms, against the text index's 21 ms: still three to four times the CPU, because the inverted index answers a token count from its postings without touching a column, and the label has to walk its granules in each of the 101 daily partitions. The time penalty I expected from moving time out of the leading key did not appear in these two queries: a whole day is answered from partition metadata, 1 row read, because the table is partitioned by day, and one service in one day is pruned by the service-first key. A sub-day window across all services is where this order would pay, and that was not measured.
