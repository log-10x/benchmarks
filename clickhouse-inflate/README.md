# clickhouse-inflate

What does it cost ClickHouse to turn compact log events back into text at query time? Here the events sit in a table, and a view decodes them with SQL functions from the log10x ClickHouse app. With the SQL in `install-fixed.sql`, decoding all 137,418 rows took 548 ms and peaked at 41.1 MiB. The SQL in `install-buggy.sql` could not finish the same query at ClickHouse defaults and aborted at the server's memory cap.

A `SELECT count()` over the view measures none of this, because ClickHouse answers it from a projection and prunes the decode out of the plan. The two SQL files differ by one line per function. The buggy lambda reaches its arrays by subscript, so ClickHouse copies each array once per mapped element. The fixed one passes them to arrayMap as arguments, which ClickHouse walks element by element.

## Result

Figures are from results.json, with times averaged over 3 runs after discarding the first.

| Query | SQL file | Outcome | Time | Peak memory |
|---|---|---|---:|---:|
| `SELECT count()` | buggy | 1 row, 24 bytes read | 16 ms | not recorded |
| `sum(length(decoded_log))` | buggy | aborts, code 241 | n/a | 7.20 GiB |
| `sum(length(decoded_log))`, bounded settings | buggy | completes | 4,290 ms | 2.86 GiB |
| `sum(length(decoded_log))` | fixed | completes | 548 ms | 41.1 MiB |
| `SELECT decoded_log`, `FORMAT Null` | buggy | aborts, code 241 | n/a | 7.20 GiB |
| `SELECT decoded_log`, `FORMAT Null` | fixed | completes | 535 ms | 40.9 MiB |

The 7.20 GiB is above this host's 6.89 GiB cap because ClickHouse records the usage a refused 4 GiB allocation would have reached. The buggy decode completed in 3 of 3 runs with a block size of 64, 4 threads and a per-query limit of 6000000000 bytes.

- Both files give byte-identical output over all 137,418 rows, 29,065,810 bytes.
- The decode needs 800,397 array elements and the buggy SQL materializes 189,949,597. One template with 818 literals, on 275 rows, accounts for 96.9% of the materialized elements.
- Replacing the functions alone leaves the views on the old body, because ClickHouse copies a function body into a view when it creates the view. The fixed install file recreates the views.

## How it was measured

ClickHouse 25.8.28.1 ran in Docker, pinned to 8 GiB and 8 CPUs. The data is 500 compact events the 10x engine wrote from the OpenTelemetry demo's Kubernetes logs, cycled to 137,418 rows. The script runs every query on the buggy SQL, then the decodes on the fixed SQL, and compares the outputs byte for byte. Times and peak memory come from ClickHouse's query log.

## Limits

- The test ran on one host with one ClickHouse version. Times move with hardware, and the abort point moves with the memory cap, which ClickHouse sets at 0.9 times the RAM it can see.
- The data set is small, 500 events cycled to fill the table.
- The byte-identity check compares the two files' output against each other, not against the original log text.

## Run it

```
cd clickhouse-inflate
./run.sh                # pulls the pinned ClickHouse image and writes results.json
SKIP_PREFIX=1 ./run.sh  # skips the two buggy-SQL queries that abort
```

A run needs Docker. The two aborting queries take 2 seconds to 10 minutes, depending on host memory pressure.

The full record is in [RECORD.md](RECORD.md): the abort message, the memory cap, plan node counts, the SQL change and the figures this harness does not reproduce.
