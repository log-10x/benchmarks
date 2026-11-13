# clickhouse-inflate

A ClickHouse view runs its SQL each time a query reads it. Here a view decodes compact log events, each a template hash plus the line's values, with SQL functions from the log-10x/clickhouse-app repository. Decoding all 137,418 rows took 548 ms and peaked at 41.1 MiB when the decode lambda took its arrays as arrayMap arguments. With a lambda that reads the same arrays by subscript, the query hit the server's memory cap at ClickHouse defaults and aborted.

A lambda that indexes into its arrays captures them, and ClickHouse copies a captured array once per mapped element, so a row with N literals materializes N copies of its N-element arrays. Arrays passed to arrayMap as arguments are walked element by element.

A `SELECT count()` over the view measures none of this, because ClickHouse answers it from a built-in count projection and its plan has no function nodes.

## What ClickHouse's query log recorded

Times average the second and third of three runs. Every figure is from [results.json](results.json).

| Query | Decode lambda | Outcome | Time | Peak memory |
|---|---|---|---:|---:|
| `SELECT count()` | not in the plan | 1 row, 24 bytes read | 16 ms | not recorded |
| `sum(length(decoded_log))` | by subscript | aborts, code 241 | n/a | 7.2 GiB |
| same, bounded settings | by subscript | completes | 4,290 ms | 2.86 GiB |
| `sum(length(decoded_log))` | as arguments | completes | 548 ms | 41.1 MiB |
| `SELECT decoded_log`, `FORMAT Null` | by subscript | aborts, code 241 | n/a | 7.2 GiB |
| `SELECT decoded_log`, `FORMAT Null` | as arguments | completes | 535 ms | 40.9 MiB |
| `sum(length(decoded_log))`, format-preserving view | as arguments | completes | 600 ms | 78 MiB |

The 7.2 GiB is above this host's 6.89 GiB cap because ClickHouse records the usage a refused 4 GiB allocation would have reached. The bounded run, with a block size of 64, 4 threads and a per-query limit of 6000000000 bytes, completed in 3 of 3 runs.

- Both lambdas return byte-identical output over all 137,418 rows, 29,065,810 bytes.
- The decode needs 800,397 array elements and the subscript lambda materializes 189,949,597, 96.9% of them from one template with 818 literals on 275 rows.
- Replacing the functions alone leaves the views on the old body, because ClickHouse copies a function body into each view at creation. [install-fixed.sql](install-fixed.sql) recreates them.

## How the queries were run

ClickHouse 25.8.28.1 ran in Docker at default query settings, pinned to 8 GiB and 8 CPUs. The data is 500 compact events the 10x engine wrote from the OpenTelemetry demo's Kubernetes logs, repeated to 137,418 rows. The queries ran on the subscript version in [install-buggy.sql](install-buggy.sql), then on [install-fixed.sql](install-fixed.sql). For the byte comparison, the subscript version decodes at a block size of 64 so that it completes.

## Limits

- One host and one ClickHouse version were tested. Times move with hardware, and the abort point moves with the memory cap, which ClickHouse sets by default at 0.9 times the RAM it can see.
- The byte comparison checks the two lambdas against each other, never against the original log text. [clickhouse-clickstack](../clickhouse-clickstack/) makes that check, and there this SQL returns the wrong text for most rows.

## Run it

```
cd clickhouse-inflate
./run.sh          # pulls the pinned ClickHouse image and writes results.json
KEEP=1 ./run.sh   # the same run, leaving the container up afterwards
```

A run needs Docker, and the two aborting queries take between 2 seconds and 10 minutes, depending on the host's memory pressure.

[RECORD.md](RECORD.md) has the abort message, how ClickHouse sets its memory cap, the plan node counts and the SQL of both lambdas.
