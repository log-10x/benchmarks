# Datadog service control

Inside one Datadog service, can the index filters a user writes move as many events out of Standard as a per-pattern plan? On the OpenTelemetry demo's Kafka logs they can. At the 70% target, eight logger-name filters moved 24,440 of 29,043 events and the plan moved 23,854, and neither moved an error or warning. On this data the control can be built in house, with eight rules against the plan's one.

The plan is one cap row, a byte limit per log pattern on the kafka container, and events the 10x engine marks over it go to Flex through an index filter. Datadog's Kafka pipeline parses each logger into `logger.name`, so the native rule is `service:kafka @logger.name:<class>`.

## Result

Events moved out of Standard at the 70% target. B got A's rules unchanged, beside a plan written on B.

| Capture | Rule set | Rules | Events moved | Lifecycle events moved, of 317 |
|---|---|---:|---:|---:|
| A, 29,043 events | per-pattern plan | 1 cap row | 23,854 | n/a |
| A | logger-name filters | 8 | 24,440 | n/a |
| B, 6,226 events | plan rewritten on B | 1 cap row | 3,321 | 0 |
| B | A's cap, unchanged | 1 cap row | 3,493 | 95 |
| B | A's logger-name filters | 8 | 4,658 | 0 |

On A the filters leave in Standard 3,046 events the plan moves, from two logger classes they do not name. On B, A's filters moved none of the 317 lifecycle events (patterns B has and A lacks), while A's cap moved 95.

Across all services of both captures, after a buyer's usual filters (`-status:(error OR warn)` service filters on three services, DEBUG and TRACE dropped):

- The plan moved 5,539 events beyond those filters on A (3.5% of the capture) and 4,882 on B (11.7%).
- On B, six more service filters cut that to 48 events but also move 4,085 events the plan keeps.
- A phrase of each pattern's own words selects it, which takes 13 index filters on A and 22 on B. One phrase on A also catches 2 kept events.

## How it was measured

The data is the kafka records of two public OpenTelemetry demo captures on Kafka 3.9.1. A covers ten hours through Fluentd and B two hours through Fluent Bit. The plan was written on A at targets from 30 to 90% and moved 23,836 to 23,905 events at each. The filters follow a rule fixed before the run: the fewest logger classes, largest first, whose events reach the plan's. Each count is read from the emitted records and the engine's own counters, and the run fails if they differ.

## Limits

- Only two demo captures were tested. A production stream can have more events that only the pattern ID selects.
- Nothing was sent to Datadog, so no Datadog meter was read.
- The rule counts leave out the work of finding each pattern first.

## Run it

```
python3 report.py --check   # recompute every table from the committed files
./run.sh                    # the full run
```

The check needs only Python. The full run needs Docker, Node 18 or later, about 2 GB of disk and under twenty minutes, and no Datadog account.

[RECORD.md](RECORD.md) has every target and variant, the all-services analysis and the predictions written before the run.
