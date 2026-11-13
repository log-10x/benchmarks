# Elastic hot-tier budget

Can a size budget on an Elasticsearch hot tier stay where it was set when log volume steps up 2.5 times within an hour? In this test the budget stayed when the lines over the limits went to a warm node. From 20 minutes after the step to the hour's end, hot sat between 0.94 and 1.04 times the budget, while a fixed reroute by service rose to 1.66 times its level. With those lines on the hot node, hot peaked at 1.43 times.

The 10x engine limits bytes per log statement, and a run every 10 minutes rewrites them against the hot node's store. Lines over a limit (moved lines below) go to an index that rolls over every 10 minutes and then mounts on frozen.

## Result

Hot node index store from node stats, around one step from 56 to 140 lines a second, against a 63 MB budget. "Before" is the 20-minute mean before the step.

| Setup | Moved lines written to | Before | Peak in the hour | End of the hour |
|---|---|---:|---:|---:|
| 10x engine | warm node | 61.6 MB | 65.7 MB | 65.2 MB |
| Reroute by service | warm node | 47.4 MB | 78.7 MB | 78.7 MB |
| 10x engine | hot node | 59.9 MB | 90.0 MB | 64.2 MB |
| Reroute by service | hot node | 50.0 MB | 85.9 MB | 81.8 MB |

The bound was 1.10 times the budget at every reading from 20 minutes after the step. With moved lines on warm, none of 25 readings crossed it. With moved lines on hot, 13 of 24 did, because each moved-lines index stays on hot for its 10 minutes of writes and about 7 more until it mounts.

- The reroute grew because the other services' lines stay on hot for 2 hours.
- In the warm run every non-blank line arrived: 1,025,014 in the 10x cluster, 1,025,170 documents in the reroute cluster.

## How it was measured

Two self-managed Elasticsearch 9.5.5 clusters shared one Docker host, each with a hot node and a warm and frozen node. Fluent Bit replayed the OpenTelemetry demo sample to both, through the 10x engine to the first. The second routed `opentelemetry-collector`, the service with the top half of the bytes, to a stream with the moved lines' lifecycle. The budget was 0.7 of where a dry run without limits said hot would settle. Every 100 seconds a meter read each hot node's `indices.store.size_in_bytes`. The methods were fixed in advance: [TWO_ARM_METHOD.md](TWO_ARM_METHOD.md) and [TWO_ARM_METHOD_WARM.md](TWO_ARM_METHOD_WARM.md).

## Limits

- Every time constant was divided by 6, so kept lines stayed 2 hours on hot and a slow ramp against days of retention is not shown.
- Each placement ran once, about four hours, at megabyte scale on one machine.
- The cost of warm, where moved lines peaked at 20.7 MB, was not measured.
- No bill was measured. RECORD.md prices hot at Elastic's published rates.

## Run it

```
# from elastic-hot-tier-budget/, with Docker running
# set POLICY_REPO=<owner/repo> to use your own copy of log-10x/config with branch test/elastic-hot-tier-policy
export RESULTS=$PWD/results-rerun MCP=/path/to/log10x-mcp GH_TOKEN=$(gh auth token) \
  ENGINE_IMAGE=ghcr.io/log-10x/edge-10x:1.1.150
python3 rig/make-replay.py otel-sample-200mb.log   # release otel-sample-v1 of log-10x/config
rig/phases-two-arm-warm.sh                         # about four hours
python3 rig/score-two-arm.py "$RESULTS"
```

A rerun needs Docker with room for 7.1 GiB of container limits, a built log10x-mcp checkout at c1b456a and a GitHub token that can push the policy branch.

[RECORD.md](RECORD.md) has every run, its criteria, per-stream tables, the cost projection and the rig.
