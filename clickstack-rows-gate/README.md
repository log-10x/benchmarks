# ClickHouse rows gate

Two ClickHouse system tables record inserts: `system.query_log` has an entry per insert with the rows it wrote, and `system.part_log` has a NewPart entry per new data part with its row count. Both were read against the row count of ClickStack's logs table while the 10x engine limited three services to a set total per window. The NewPart rows equaled the table's count in both runs. In the second run the query log's insert entries were 1,948 rows over or 7,519 under, depending on the entry kind.

ClickStack's exporter inserts asynchronously, and each insert statement lists three tables in the query log (the logs table, a counts table and a 15-minute rollup), so a filter on the logs table cannot pick out its rows.

## What the system tables counted

| Count, second run, 2026-10-23 | Rows | Against the logs table |
|---|---:|---|
| `count()` on `default.otel_logs` | 22,367 | the count to match |
| Events the engine passed | 22,367 | equal |
| `system.parts`, active rows | 22,367 | equal |
| `system.part_log`, NewPart rows | 22,367 | equal |
| `system.query_log`, kind Insert | 24,315 | off by +1,948 |
| `system.query_log`, kind AsyncInsertFlush | 14,848 | off by -7,519 |

The part log also matched in the first run, where the Insert entries happened to equal the table's count and the AsyncInsertFlush entries ran over by a materialized view's rows. Which entry kind carries the other tables' rows changes between runs, so the query log is a cross-check at most. Rows in the table and the store add up to the 157,087 records the engine returned (22,367 + 134,720).

- In the second run, kafka put 1,000 rows in the table against its total of 1,000, cart 400 against 400 and opentelemetry-collector 2,050 against 2,000. The extra 50 are the error lines the engine keeps for one storming error statement.
- Rewriting the totals file in place 4 seconds into the feed did not reset the window counts, and no limited service added another row.
- Scraped 5 seconds after the collector stopped, the engine's Prometheus counters still lagged, at 16,255 passed events against 22,367, so a scheduled run reads the last complete hour.

## The ClickStack rig and the feed

The rig is the one in [clickstack-e2e](../clickstack-e2e/): ClickStack 2.38.0 on ClickHouse 26.5.7.64, the 10x engine and an S3-compatible store. An OpenTelemetry collector reads the 197,430-line capture and sends its events to the engine, which returns them marked pass or offload. Passed events go into the logs table and offloaded ones to the store, which a ClickHouse view reads back. Every count was read after flushing the system logs, and the [results file](results/clickstack-rows-gate-2026-10-23.md) lists each query and its answer.

## What the run does not cover

- The feed is one limit window long, so the run says nothing about money, ClickHouse Cloud or a rate kept over hours, which [clickstack-rows](../clickstack-rows/) measures from the part log.
- Both runs used one ClickStack version and its exporter's asynchronous inserts, and only the second run's figures are committed.

## Run it

```
# from clickstack-rows-gate/, with the capture that clickstack-e2e/run.sh downloads
CSE_DATA_DIR=../clickstack-e2e/data ./run.sh
```

A run needs Docker and the capture from clickstack-e2e, uses the engine image `ghcr.io/log-10x/edge-10x:1.1.147` and writes to [results/](results/).

[RECORD.md](RECORD.md) has the full record, with the engine's counters, config patches and store setup.
