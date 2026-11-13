# Elastic hot-tier budget

The size of an Elasticsearch cluster follows how much data sits in its hot tier, because hot nodes carry the local SSD and the memory that keep that data searchable. Here a run every 10 minutes read the hot node's store and set the 10x engine's byte limit per log statement to fit a budget, and lines over a limit moved to an index that ILM sends to frozen. With that index on a warm node, through an hour at 2.5 times the log volume, the hot tier stayed between 0.94 and 1.04 times the budget from 20 minutes after the step.

A fixed reroute by service in Fluent Bit, on a second cluster, rose to 1.66 times its level before the step. With the moved lines' index on hot, the engine's hot tier peaked at 1.43 times the budget, above the reroute's peak.

## What the hot node's index store read

The feed stepped from 56 to 140 lines a second, and the budget was 63 MB.

| Setup | Moved lines written to | Mean, 20 minutes before | Peak in the hour | End of the hour |
|---|---|---:|---:|---:|
| 10x engine | warm node | 61.6 MB | 65.7 MB | 65.2 MB |
| Reroute by service | warm node | 47.4 MB | 78.7 MB | 78.7 MB |
| 10x engine | hot node | 59.9 MB | 90.0 MB | 64.2 MB |
| Reroute by service | hot node | 50.0 MB | 85.9 MB | 81.8 MB |

The bound was 1.10 times the budget at every reading from 20 minutes after the step. With moved lines on warm, none of 25 readings went over it. With moved lines on hot, 13 of 24 did, because each moved-lines index stays on hot for its 10 minutes of writes and about 7 more until it mounts. The reroute rose because the other services' lines stay on hot for 2 hours. With either placement, each cluster received every non-blank line.

## How the two clusters were set up and read

Two self-managed Elasticsearch 9.5.5 clusters shared one Docker host, each with a hot node and a frozen node that also took the warm role in the warm run. Fluent Bit sent a replay of the published OpenTelemetry demo sample through the 10x engine to the first cluster and a copy of every line to the second. For the second cluster it routed `opentelemetry-collector`, 68.9% of the bytes in the first 20 minutes, to an index with the moved lines' lifecycle. Every 100 seconds a meter read each hot node's `indices.store.size_in_bytes`. Both methods were fixed in advance: [TWO_ARM_METHOD.md](TWO_ARM_METHOD.md) and [TWO_ARM_METHOD_WARM.md](TWO_ARM_METHOD_WARM.md).

## Time scale and scope

- Every time constant was divided by 6, so the hourly run came every 10 minutes and kept lines stayed 2 hours on hot. A slow ramp against days of retention is not shown.
- Each comparison ran once, on one machine. Elastic Cloud Hosted was not tested.
- No bill was measured, and neither was the cost of warm, where moved lines peaked at 20.7 MB.

## Rerunning the warm-placement run

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

[RECORD.md](RECORD.md) has every run, its criteria, the per-stream tables, the cost projection and the rig.
