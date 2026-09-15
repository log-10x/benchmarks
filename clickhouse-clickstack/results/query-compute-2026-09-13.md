# Does query compute follow rows

Measured 2026-09-13 by `run_query_compute.sh`. Five query shapes, 11 runs each with the first discarded, CPU as user plus system time from `system.query_log`, fastest kept. Same ClickStack schema at ZSTD(1); only the rows present differ between arms.

| Query | full | sampled_75 | sampled_50 | sampled_25 | bypattern_75 | bypattern_50 | bypattern_25 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `word` CPU ms | 5.6 | 5.2 | 5.3 | 5.3 | 5.2 | 5.3 | 5.4 |
| `service_window` CPU ms | 5.0 | 4.9 | 4.9 | 4.8 | 4.9 | 4.8 | 5.1 |
| `top_services` CPU ms | 6.7 | 6.4 | 6.1 | 5.3 | 6.6 | 6.1 | 5.4 |
| `recent_tail` CPU ms | 11.3 | 11.1 | 7.9 | 7.1 | 8.6 | 8.7 | 7.1 |
| `substring` CPU ms | 6.7 | 6.3 | 5.9 | 5.3 | 6.6 | 5.4 | 5.0 |
| rows | 197,430 | 148,147 | 99,038 | 49,499 | 143,832 | 97,367 | 47,147 |

Total CPU across the mix, fastest runs, relative to `full`:

| Arm | rows vs full | mix CPU ms | CPU vs full |
|---|---:|---:|---:|
| `full` | 100% | 35.3 | 100% |
| `sampled_75` | 75% | 33.9 | 96% |
| `sampled_50` | 50% | 30.2 | 85% |
| `sampled_25` | 25% | 27.8 | 79% |
| `bypattern_75` | 73% | 31.8 | 90% |
| `bypattern_50` | 49% | 30.2 | 86% |
| `bypattern_25` | 24% | 27.9 | 79% |

Bytes read per query, `full` arm: `word` 32, `service_window` 213,814, `top_services` 197,430, `recent_tail` 3,832,932, `substring` 41,069,495.

## What it says

**This table is too small to answer the question.** Every query in the mix costs 5 to
11 ms of CPU on a table that is 7 MB on disk. At that size the cost of a query is the
fixed cost of running any query, and the scan that would scale with rows is a rounding
error inside it. Half the rows costing 85% of the CPU is that floor, not a property of
how ClickHouse scans.

Two details confirm the reading. The `word` query read 32 bytes: the text index answered it
without touching the column at all. The `substring` query, the one shape here that must
scan the whole `Body` column, read 41 MB and is the only one that moves with row count,
6.7 ms to 5.3 ms across the arms.

**What would answer it.** The same mix on a table of tens of gigabytes, where a scan is
seconds rather than milliseconds and the fixed cost disappears into it. The insert and
merge result stands on its own; the query half of compute is not resolved by this run.
