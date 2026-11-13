# ClickHouse rows run

Can the rows written into a ClickStack logs table be kept at a set rate an hour while log volume grows 2.5 times? On one node, the rows ClickHouse wrote stayed between 0.91 and 1.13 of the set rate in every 10-minute window as load grew, one over the 1.10 the test allowed. A static collector rule on the same feed let its table grow to 2.95 to 3.42 times its starting level at full load. CPU did not separate the two.

Every 10 minutes a scheduled run reads ClickHouse's own `system.part_log` and sets a limit per log statement in the 10x engine. Lines over the limits, apart from a small sample, go to the account's own bucket instead of ClickHouse.

## Result

Rows written in eight 10-minute windows on 2026-10-25, against a set rate R of 30,099 rows an hour (5,016 a window).

| Minutes | Lines a second | 10x engine rows | Of R/6 | Collector rule rows |
|---|---:|---:|---:|---:|
| 50 to 60 | 14 | 4,697 | 0.94 | 2,686 |
| 60 to 70 | 19 | 5,492 | 1.09 | 3,572 |
| 80 to 90 | 24 | 5,471 | 1.09 | 5,858 |
| 100 to 110 | 30 | 5,671 | 1.13 | 12,877 |
| 120 to 130 | 35 | 5,377 | 1.07 | 7,963 |
| 130 to 140 | 35 | 4,581 | 0.91 | 7,932 |
| 140 to 150 | 35 | 5,443 | 1.09 | 9,179 |
| 150 to 160 | 35 | 5,052 | 1.01 | 8,142 |

The registered test required every window from minute 60 to 160 at or under 1.10 of R/6, and nine of ten were. Minutes 100 to 110, the first window of a 20-minute error storm, read 1.13, so the run fails as registered.

- Against each setup's level in minutes 50 to 60, insert plus merge CPU read 0.87 to 1.24 for the 10x engine and 0.40 to 1.61 for the rule at full load, as merge CPU swung with which merges ran.
- Of the 50,378 records the rule would have kept in minutes 100 to 160, the 10x engine sent 27,155 (53.9%) to the bucket. After the storm, in minutes 120 to 160, the share was 43.2%.

## How it was measured

Both setups shared one ClickStack 2.38.0 node and a replay of the OpenTelemetry demo capture. Load stepped from 14 to 35 lines a second every 20 minutes, adding a new service at minute 80 and the storm at 100. Every clock is divided by 6, so limits were reset every 10 minutes instead of hourly. R is 0.7 of a dry run's rate with nothing limited. The rule sends the two chattiest services' INFO and DEBUG lines to a second bucket and the rest to a copy of the logs table. CPU is insert time from `system.query_log` plus merge time from the part log.

## Limits

- One node and one replayed capture, with nothing on money, ClickHouse Cloud or durability across a restart.
- The setups insert through different collectors, so CPU compares only within a setup.
- Delivery was not exact: the 10x engine's table had 933 rows more than the engine returned, and the two tables logged 20 and 18 failed inserts, all but one before any scored window.

## Run it

```
# from clickstack-rows/: recompute the comparison from the committed files
python3 rig/score.py results-two-arm --arms two

# full rerun of both setups
ARMS=two MCP=<log10x-mcp checkout with build/> GH_TOKEN=$(gh auth token) \
  CAPTURE=<path to otel-sample-200mb.log> rig/phases.sh
```

The recompute needs only Python 3, and a full rerun takes 180 minutes, Docker and the capture `clickstack-e2e/run.sh` downloads.

[RECORD.md](RECORD.md) has all three runs with their registered criteria, scores and rig notes.
