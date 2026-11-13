# Datadog service control

Datadog bills Standard indexing per million events. Inside one service a service filter cannot split that volume, so the control there is an index filter on the logger name Datadog's Kafka pipeline parses, `service:kafka @logger.name:<class>`. In a replay of kafka's records from a public OpenTelemetry demo capture, eight such filters moved 24,440 of 29,043 events out of Standard and a per-pattern plan moved 23,854. Neither moved an error or warning, and on this data the control can be built in house.

The plan is one cap row, a byte limit per pattern per 240-second window, and the 10x engine marks events over it for a Flex index.

## Events moved out of Standard in the kafka service

The plan was asked to move 70% of the volume, and capture B, a later demo version, got A's rules unchanged.

| Capture | Rule set | Rules | Events moved | Lifecycle events moved, of 317 |
|---|---|---:|---:|---:|
| A, 29,043 events | per-pattern plan | 1 cap row | 23,854 | n/a |
| A | logger-name filters | 8 | 24,440 | n/a |
| B, 6,226 events | plan written on B | 1 cap row | 3,321 | 0 |
| B | A's cap, unchanged | 1 cap row | 3,493 | 95 |
| B | A's logger-name filters | 8 | 4,658 | 0 |

On A the filters leave in Standard 3,046 events the plan moves, from two classes they do not name. All of A's filters still matched on B. Of B's 317 lifecycle events, from patterns A lacks, A's cap moved 95 and the filters none.

## What the plan moves after service and level filters

Of the events left in Standard on both whole captures after `-status:(error OR warn)` filters on three services and DEBUG and TRACE dropped, the plan at 70% moved 5,539 on A, 3.5% of the capture, and 4,882 on B, 11.7%. An index filter on a quoted phrase of each pattern's constant words selects it, 13 filters on A and 22 on B, and one also selects 2 events the plan keeps. A condition fixed before the run called for a trial of the plan only if most of those events needed the pattern ID, and none do.

On B, six more service filters leave 48 of those events and also move 4,085 the plan keeps, nearly all of them statements split into one pattern per value or short statements the byte cap keeps.

## How the events were counted

Capture A is ten hours through Fluentd and B two hours through Fluent Bit, on Kafka 3.9.1. On A the plan moved 23,836 to 23,905 events at targets from 30 to 90%. The filters follow a rule fixed before the run, the fewest logger classes, largest first, whose events reach the plan's, so the totals on A are close by construction. Each count is read twice from the 10x engine's replay, and the run fails if the two differ.

## Limits

- Only two demo captures were tested.
- Nothing was sent to Datadog, so no usage metric was read.
- The rule counts leave out the work of finding each pattern first.

## Run it

```
cd datadog-service-control
python3 report.py --check   # recompute every table from the committed files
./run.sh                    # the full run
```

The full run needs Docker, Node 18 or later, about 2 GB of disk and under twenty minutes.

[RECORD.md](RECORD.md) has every target, the all-services analysis and the predictions written before the run.
