# Elastic hot tier

The size of an Elasticsearch cluster follows how much data sits in its hot tier, because hot nodes carry the local SSD and the memory that keep that data searchable. Elasticsearch tiers by index, so lines over a log statement's byte budget, marked by the 10x engine, go to an index that ILM rolls over hourly and moves to frozen. On a self-managed 9.5.5 cluster, one fixed budget moved 59% of the message bytes to that index, and 65% to 73% at 2.5 times the load. Each moved line left hot 30 to about 110 minutes after it was written.

## What the budget moved, hour by hour

The budget was 22,148 bytes per statement per 4-minute window on each node. Message bytes an hour on 2026-10-22 (UTC), from Fluent Bit's copy of the engine's output:

| Hour | Phase | Bytes sent to hot | Bytes moved | Share moved |
|---|---|---:|---:|---:|
| 00:15 | baseline | 5,254,073 | 12,768 | 0% |
| 01:15 | budget on | 2,120,292 | 3,107,510 | 59% |
| 02:15 | budget on | 2,166,152 | 3,079,135 | 59% |
| 03:15 | budget on | 2,167,937 | 3,066,345 | 59% |
| 04:15 | budget on | 2,197,761 | 3,107,231 | 59% |
| 05:15 | budget on, 2.5x load | 4,589,240 | 8,626,759 | 65% |
| 06:15 | budget on, 2.5x load | 4,174,512 | 11,471,373 | 73% |
| 07:15 | budget on, 2.5x load | 4,050,664 | 9,484,012 | 70% |

No statement kept more than the budget on hot in any window, beyond a 5-line sample and up to 50 extra error lines. The budget is per statement, so growth in statements under it still reached hot.

## How long moved lines stayed on hot

At ILM's default 10-minute poll, indices 2 to 7 each rolled over 70 minutes after creation and entered the frozen phase 10 minutes later. The searchable snapshot action then took three more polls, so each index left hot 30 to 40 minutes after rollover, mounted at 0 bytes of local store. Index 1 sat empty until the budget took effect, and index 8 received no line.

For the ten largest moved patterns, a term query on `tenx_hash`, the engine's pattern hash, returned the local count from frozen. All 372,783 non-blank lines sent reached Elasticsearch, and all 159,536 moved records ended on frozen.

## How the cluster was read

The cluster had one hot node and one frozen node, and its APIs were read every 10 minutes. The published [OpenTelemetry demo sample](https://github.com/log-10x/config/releases/tag/otel-sample-v1) was replayed into Fluent Bit at 7 lines a second for 6 hours, then 17.5 a second for 3 hours with an injected service and an error storm.

## What this run does not show

- With the budget fixed, the run does not show a hot tier kept at a set size as load grows.
- The budget was set so half of the second baseline hour's message bytes exceeded it, and 59% moved. The storm line's kept count fits the engine sizing the whole forwarded record rather than the message, which the run leaves open.
- The run shows nothing about a bill, since Elastic Cloud Hosted bills the configured size.
- Elastic's own tools and logsdb were not measured.

## Rerunning the benchmark

```
cd elastic-hot-tier/rig
python3 make-replay.py <path to otel-sample-200mb.log>
MCP=<log10x-mcp checkout> python3 detach.py ../results/phases.log ./phases.sh
# after the run: bring the two nodes back on the same volumes and score
RIG_DIR=$PWD RIG_DATA=$PWD/../results/data docker compose -p elastic-rig -f compose.yaml up -d es-hot es-frozen
python3 analyze.py
```

A rerun takes 11 hours and needs Docker with about 5 GB of memory free, Node 20, Python 3 and a built log10x-mcp checkout (1.30.77, engine 1.1.147).

[RECORD.md](RECORD.md) has every check, each index's ILM timeline, the hourly readings and the rig.
