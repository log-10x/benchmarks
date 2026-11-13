# Elastic hot tier

When lines over a per-statement budget go to an Elasticsearch index that rolls over hourly and moves to frozen, how long do they stay on hot? Each moved line left hot 30 to about 110 minutes after it was written, and all 159,536 moved records reached frozen. A fixed budget moved 59% to 73% of message bytes off hot, but the bytes sent to hot still grew with the load.

The 10x engine gives each log statement a byte budget per 4-minute window. Fluent Bit sends lines over it to the `tenx-tierdown` alias, whose hourly indices are mounted on frozen as searchable snapshots at 0 bytes of local store.

## Result

Message bytes per hour, 2026-10-22 UTC, with a budget of 22,148 bytes per statement per 4-minute window.

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

With the budget on, no statement kept more than its budget on hot in any window, beyond a 5-line sample and 50 extra error lines for the storming statement. At 2.5 times the load hot still took about 4.3 MB an hour, because the statements under budget grew too.

- Six of the eight hourly indices of moved lines spent 100 to 110 minutes on hot.
- All 372,783 non-blank lines sent reached Elasticsearch. Term queries on `tenx_hash` for the ten largest moved patterns matched the local counts on frozen.
- Of the moved bytes, 86% came from three OpenTelemetry Collector statements that no rule named.

## How it was measured

Elasticsearch 9.5.5 ran self-managed with one hot node, one frozen node and a trial license. The load was the published OpenTelemetry demo sample at 7 lines a second, then 2.5 times that for 3 hours plus a new service and a 20-minute error storm. The budget was set from the second baseline hour so that half of its message bytes were over it. The table counts bytes in Fluent Bit's local copy of what the engine returned. Index sizes and ILM state came from the cluster's own APIs every 10 minutes.

## Limits

- Hot-node bytes say nothing about a bill, since Elastic Cloud Hosted bills the configured size.
- The budget stayed fixed, so the run does not show hot kept at a set size under growth.
- No comparison was made with Elastic's own tools or logsdb.
- The budget aimed at 50% of the baseline message bytes and moved 59%. The storm statement's kept count fits the engine sizing the whole forwarded record, which the run leaves open.

## Run it

```
cd elastic-hot-tier/rig
python3 make-replay.py <path to otel-sample-200mb.log>
MCP=<log10x-mcp checkout> python3 detach.py ../results/phases.log ./phases.sh
# after the run: bring the two nodes back on the same volumes and score
RIG_DIR=$PWD RIG_DATA=$PWD/../results/data docker compose -p elastic-rig -f compose.yaml up -d es-hot es-frozen
python3 analyze.py
```

A rerun takes about 11 hours and needs Docker with about 5 GB free memory, Node 20, Python 3, a built log10x-mcp checkout and otel-sample-200mb.log from release otel-sample-v1. This run used engine 1.1.147 and log10x-mcp 1.30.77.

[RECORD.md](RECORD.md) has every check, the cluster's hourly readings and the rig.
