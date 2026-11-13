# ClickHouse rows gate

When the 10x engine limits how many lines a service sends into ClickStack, which ClickHouse system table counts the rows written into the logs table exactly? The NewPart rows in `system.part_log` matched the table's own count of 22,367 rows to the row, in both runs. The insert entries in `system.query_log` did not, so they serve as a cross-check at most.

ClickStack's exporter inserts asynchronously, and each insert statement lists three tables in the query log (the logs table, a counts table and a 15-minute rollup), so a filter on the logs table cannot pick out its rows. Which of the two insert entry kinds carried the extra rows also changed between runs.

## Result

The table shows the second run, on 2026-10-23. Hot means the logs table, where the lines the engine passed land.

| Count | Rows | Against the logs table |
|---|---:|---|
| `count()` on `default.otel_logs` | 22,367 | the count to match |
| Lines the engine routed to hot | 22,367 | equal |
| `system.parts`, active rows | 22,367 | equal |
| `system.part_log`, NewPart rows | 22,367 | equal |
| `system.query_log`, kind Insert | 24,315 | off by +1,948 |
| `system.query_log`, kind AsyncInsertFlush | 14,848 | off by -7,519 |

The part log matched in both runs, so it is the count to use. In the first run the Insert entries happened to equal the hot count and the AsyncInsertFlush entries ran over by the materialized view's rows.

The run also checked the limits:

- With the limit counted in lines, kafka kept 1,000 lines against a total of 1,000 and cart kept 400 against 400. The opentelemetry-collector service kept 2,050 against 2,000, and the 50 extra lines are the engine's error keep count for one storming error statement.
- Rewriting the totals file in place 4 seconds into the feed did not reset the window counts, and no limited service passed another line in that window.
- Hot plus cold equalled the records the engine returned: 22,367 + 134,720 = 157,087.

## How it was measured

The rig is the one in [clickstack-e2e](../clickstack-e2e/): ClickStack 2.38.0 on ClickHouse 26.5.7.64, the 10x engine in front of it, and an S3-compatible store for the cold side. The whole 197,430-line capture was fed in about 216 seconds. Three services had a line total for the window, and their lines over it went to S3, which a ClickHouse view reads back. The results file lists every query with its answer.

## Limits

- The feed is one limit window long, so the test says nothing about money, ClickHouse Cloud or a rate kept over hours. The hourly test that uses this count is [clickstack-rows](../clickstack-rows/).
- Both runs used one ClickStack version, and only the second run's figures are committed.
- The engine's Prometheus counters, scraped 5 seconds after the collector stopped, still lagged the lines sent (16,255 passed against 22,367). A reading of them should use the last complete hour.

## Run it

```
# from clickstack-rows-gate/, with the capture that clickstack-e2e/run.sh downloads
CSE_DATA_DIR=../clickstack-e2e/data ./run.sh
```

A run needs Docker and the capture from clickstack-e2e. The engine image is `ghcr.io/log-10x/edge-10x:1.1.147`. Results land in [results/](results/).

[RECORD.md](RECORD.md) has the full record, including the engine counters, their labels and the config patches.
