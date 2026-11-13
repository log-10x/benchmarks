# ClickHouse rows run

Every row that arrives in ClickHouse has to be parsed, indexed, written to disk, and merged again each time parts combine, and `system.part_log` records each new part with its row count. A scheduled run read that log and set limits per log statement and service in the 10x engine, which sent lines over them, apart from a sample, to the account's bucket. As load grew 2.5 times, rows written into ClickStack stayed between 0.91 and 1.13 of the set rate in every 10-minute window, while a collector rule by service and severity let its table grow 2.95 to 3.42 times its starting level. One window went over the 1.10 the registered test allowed, and CPU did not separate the two setups.

The set rate R is 30,099 rows an hour, 0.7 of a dry run's unlimited rate. Every clock in the rig is divided by 6, so the scheduled run comes every 10 minutes and each window is scored against R/6.

## Rows written per 10-minute window

| Minutes | Lines a second | Rows, 10x engine | Of R/6 | Rows, collector rule |
|---|---:|---:|---:|---:|
| 50 to 60 | 14 | 4,697 | 0.94 | 2,686 |
| 60 to 70 | 19 | 5,492 | 1.09 | 3,572 |
| 80 to 90 | 24 | 5,471 | 1.09 | 5,858 |
| 100 to 110 | 30 | 5,671 | 1.13 | 12,877 |
| 120 to 130 | 35 | 5,377 | 1.07 | 7,963 |
| 130 to 140 | 35 | 4,581 | 0.91 | 7,932 |
| 140 to 150 | 35 | 5,443 | 1.09 | 9,179 |
| 150 to 160 | 35 | 5,052 | 1.01 | 8,142 |

The second window of each growth step, left out here, read 0.92, 0.91 and 0.95 of R/6. The window over 1.10 is minutes 100 to 110, the first of a 20-minute error storm, so the run fails as [registered](METHOD_TWO_ARM.md).

- Of the 50,378 records the rule keeps in minutes 100 to 160, the engine sent 27,155 (53.9%) to the bucket, and 43.2% in minutes 120 to 160, after the storm.
- The engine's table had 933 more rows than the engine returned, and the tables logged 20 and 18 failed inserts, all but one before any scored window.

## Insert and merge CPU per window

The setups insert through different collectors, so each is read against its own level in minutes 50 to 60. After the first growth step the engine's table read 0.87 to 1.24 of it, three of ten windows over 1.10, and at full load the rule's read 0.40 to 1.61. Insert CPU followed the rows, and merge CPU swung with the merges run in each window.

## How the part log was read

Both setups shared one ClickStack 2.38.0 node (ClickHouse 26.5.7.64) and one replay of the OpenTelemetry demo capture. Load rose from 14 to 35 lines a second over minutes 60 to 120 and stayed at 35 to minute 160. The rule sends the two chattiest services' INFO and DEBUG lines to a second bucket. CPU is insert time from `system.query_log` plus merge time from the part log.

## Scope of the run

The run covers one node and one replayed capture, and measures nothing about money, ClickHouse Cloud or durability across a restart.

## Run it

```
# from clickstack-rows/: recompute the comparison from the committed files
python3 rig/score.py results-two-arm --arms two

# full rerun of both setups
ARMS=two MCP=<log10x-mcp checkout with build/> GH_TOKEN=$(gh auth token) \
  CAPTURE=<path to otel-sample-200mb.log> rig/phases.sh
```

The recompute needs only Python 3 and prints [every window](results-two-arm/score.md). A full rerun takes 180 minutes, Docker, Node.js and the capture `clickstack-e2e/run.sh` downloads.

[RECORD.md](RECORD.md) has all three runs on this rig, their criteria, scores and rig notes.
