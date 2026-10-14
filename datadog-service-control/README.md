# Datadog service control

One benchmark in the [log10x benchmarks](../) repository. It asks what a per-pattern plan
moves inside a single service that the rules a Datadog user writes for that service would
not, and how many rules each takes. [`datadog-flex-accounting/`](../datadog-flex-accounting/)
sets the plan against an index filter per service across a whole cluster. Inside one service
a service filter cannot split the volume, so the control here is the filter a person writes
on the service's own logger names.

Everything is computed from the engine's own counts. Nothing was sent to Datadog, and no
Datadog account is needed to rerun it.

## The data

<!-- generated:run -->
The kafka container's records from two public captures of the OpenTelemetry demo. Capture A: 31,029 records, 31,230,658 bytes, 29,043 events after grouping in 424 patterns and 54 logger classes, ten hours. Capture B: 6,230 records, 6,569,531 bytes, 6,226 events in 256 patterns and 64 logger classes, two hours. Engine `log10x/pipeline-10x:1.1.140`, log10x-mcp 1.30.49.
<!-- /generated:run -->

Both captures run the same Kafka code (3.9.1): A is demo 2.1.3 shipped by Fluentd, B is demo
2.2.0 shipped by Fluent Bit. On both, the logger classes of segment and snapshot churn on
`__cluster_metadata` carry almost all of kafka's events, every one INFO; `results/results.md`
lists the classes by events. The rest are start-up, partition loading, coordinator election
and config dumps.

## The arms

**Per-pattern plan.** The MCP's plan on A's kafka slice at 30, 50, 70 and 90% of the slice,
its `caps.csv` and `actions.csv` applied as written through the released engine. One
container, so one cap row. The engine marks the events over the cap `tier_down`; in Datadog,
an index filter on `@routeState:tier_down` in front of the Standard index sends them to a
Flex index.

**Logger-class filters.** Every Kafka line ends with its log4j logger in parentheses, for
example `(org.apache.kafka.storage.internals.log.LogSegment)`. Datadog's Kafka log pipeline
parses it into the standard attribute `logger.name`
([Kafka integration](https://docs.datadoghq.com/integrations/kafka/),
[standard attributes](https://docs.datadoghq.com/standard-attributes/), both read
2026-10-12), so the filter a Datadog user writes is `service:kafka @logger.name:<class>`,
one per class. Each event's class is read from its own text in the replay's output. A Scala
object logs under its own name: `kafka.log.LocalLog$` is a different logger from
`kafka.log.LocalLog`, and a filter names one or the other.

**Selection rule, fixed before the run.** Datadog bills Standard indexing per million
events, so the arms are matched on events. Per target, the control takes the fewest classes,
largest by events first, whose events reach at least the events the engine marked
`tier_down` under the plan, and reports the overshoot without trimming it. A second variant
adds `-status:(error OR warn)` to each filter. Events with no logger class (the image's shell
start-up output) cannot be named by such a filter and are never chosen.

**On B, nothing re-tuned.** A's chosen classes applied to B's slice; A's cap carried to B's
span and applied through the engine; and, for reference, the plan rewritten on B.

## Prediction, written before the run

The control matches the plan at every target with at most 9 classes. It wrongly moves the
rare lines that share those classes, about a hundred events (`UnifiedLog`'s producer-state
loading, 52, is the largest). On B the same classes still match, because the code is the
same, and the lifecycle lines B has and A does not (coordinator resignation, offsets
unloading, shutdown, event queue closed) sit in classes the control never named, so both
arms keep them. On the same code, Kafka's logger hierarchy is a good native key and the
comparison is close to a draw on events; what it measures is the rule count, about nine
against one cap row, and the rare-line count. The tables are published as they come out.

## Capture A

<!-- generated:capture-a -->
| Target | Arm | Rules | Events moved | Over the plan | GB moved | Errors and warnings moved | Events of patterns the plan keeps under the cap | Events the plan moves that stay in Standard |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 30% | per-pattern plan | 1 cap row | 23,905 | 0 | 0.026 | 0 | 0 | 0 |
| 30% | logger-class filters | 8 | 24,440 | +535 | 0.026 | 0 | 0 | 3,056 |
| 30% | logger-class filters, `-status:(error OR warn)` | 8 | 24,440 | +535 | 0.026 | 0 | 0 | 3,056 |
| 50% | per-pattern plan | 1 cap row | 23,836 | 0 | 0.026 | 0 | 0 | 0 |
| 50% | logger-class filters | 8 | 24,440 | +604 | 0.026 | 0 | 0 | 3,077 |
| 50% | logger-class filters, `-status:(error OR warn)` | 8 | 24,440 | +604 | 0.026 | 0 | 0 | 3,077 |
| 70% | per-pattern plan | 1 cap row | 23,854 | 0 | 0.026 | 0 | 0 | 0 |
| 70% | logger-class filters | 8 | 24,440 | +586 | 0.026 | 0 | 0 | 3,046 |
| 70% | logger-class filters, `-status:(error OR warn)` | 8 | 24,440 | +586 | 0.026 | 0 | 0 | 3,046 |
| 90% | per-pattern plan | 1 cap row | 23,901 | 0 | 0.026 | 0 | 0 | 0 |
| 90% | logger-class filters | 8 | 24,440 | +539 | 0.026 | 0 | 0 | 3,059 |
| 90% | logger-class filters, `-status:(error OR warn)` | 8 | 24,440 | +539 | 0.026 | 0 | 0 | 3,059 |
<!-- /generated:capture-a -->

<!-- generated:capture-a-classes -->
The filters at 30%, 50%, 70%, 90%, largest first: `@logger.name:org.apache.kafka.storage.internals.log.LogSegment`, `@logger.name:kafka.log.UnifiedLog`, `@logger.name:kafka.log.LocalLog`, `@logger.name:org.apache.kafka.storage.internals.log.ProducerStateManager`, `@logger.name:org.apache.kafka.storage.internals.log.SnapshotFile`, `@logger.name:org.apache.kafka.image.publisher.SnapshotEmitter`, `@logger.name:org.apache.kafka.image.publisher.SnapshotGenerator`, `@logger.name:kafka.raft.KafkaMetadataLog`.
<!-- /generated:capture-a-classes -->

<!-- generated:capture-a-verdict -->
- **30%**: the plan, one cap row on `kafka` of 4,593 bytes per window, states 85.5% of the volume and moves 23,905 of 29,043 events. 8 logger-class filters reach that with 24,440, 535 more. Neither moves an error or warning; the filters move 0 events of patterns the plan keeps under the cap and leave in Standard 3,056 events the plan moves (`LocalLog$`, `Snapshots`).
- **50%**: the plan, one cap row on `kafka` of 4,593 bytes per window, states 85.5% of the volume and moves 23,836 of 29,043 events. 8 logger-class filters reach that with 24,440, 604 more. Neither moves an error or warning; the filters move 0 events of patterns the plan keeps under the cap and leave in Standard 3,077 events the plan moves (`LocalLog$`, `Snapshots`).
- **70%**: the plan, one cap row on `kafka` of 4,593 bytes per window, states 85.5% of the volume and moves 23,854 of 29,043 events. 8 logger-class filters reach that with 24,440, 586 more. Neither moves an error or warning; the filters move 0 events of patterns the plan keeps under the cap and leave in Standard 3,046 events the plan moves (`LocalLog$`, `Snapshots`).
- **90%**: the plan, one cap row on `kafka` of 4,593 bytes per window, states 88.5% of the volume, its ceiling, short of the target and moves 23,901 of 29,043 events. 8 logger-class filters reach that with 24,440, 539 more. Neither moves an error or warning; the filters move 0 events of patterns the plan keeps under the cap and leave in Standard 3,059 events the plan moves (`LocalLog$`, `Snapshots`).
<!-- /generated:capture-a-verdict -->

## Capture B, nothing re-tuned

<!-- generated:capture-b -->
| Target | Arm | Rules | Events moved | Over B's plan | Errors and warnings moved | Lifecycle events moved, of 317 | Events of patterns B's plan keeps under its cap | Events B's plan moves that stay in Standard |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 30% | plan rewritten on B | 1 cap row | 3,289 | 0 | 0 | 0 | 0 | 0 |
| 30% | A's cap, unchanged | 1 cap row | 3,505 | +216 | 0 | 103 | 212 | 34 |
| 30% | A's logger-class filters | 8 | 4,658 | +1,369 | 0 | 0 | 0 | 321 |
| 30% | A's logger-class filters, `-status:(error OR warn)` | 8 | 4,658 | +1,369 | 0 | 0 | 0 | 321 |
| 50% | plan rewritten on B | 1 cap row | 3,303 | 0 | 0 | 0 | 0 | 0 |
| 50% | A's cap, unchanged | 1 cap row | 3,531 | +228 | 0 | 101 | 213 | 26 |
| 50% | A's logger-class filters | 8 | 4,658 | +1,355 | 0 | 0 | 0 | 324 |
| 50% | A's logger-class filters, `-status:(error OR warn)` | 8 | 4,658 | +1,355 | 0 | 0 | 0 | 324 |
| 70% | plan rewritten on B | 1 cap row | 3,321 | 0 | 0 | 0 | 0 | 0 |
| 70% | A's cap, unchanged | 1 cap row | 3,493 | +172 | 0 | 95 | 205 | 50 |
| 70% | A's logger-class filters | 8 | 4,658 | +1,337 | 0 | 0 | 0 | 328 |
| 70% | A's logger-class filters, `-status:(error OR warn)` | 8 | 4,658 | +1,337 | 0 | 0 | 0 | 328 |
| 90% | plan rewritten on B | 1 cap row | 3,295 | 0 | 0 | 0 | 0 | 0 |
| 90% | A's cap, unchanged | 1 cap row | 3,555 | +260 | 0 | 106 | 214 | 20 |
| 90% | A's logger-class filters | 8 | 4,658 | +1,363 | 0 | 0 | 0 | 313 |
| 90% | A's logger-class filters, `-status:(error OR warn)` | 8 | 4,658 | +1,363 | 0 | 0 | 0 | 313 |
<!-- /generated:capture-b -->

<!-- generated:capture-b-verdict -->
- **30%**: of B's 6,226 events, A's 8 filters move 4,658 (every one still matches) and none of the 317 lifecycle events; A's cap moves 3,505, 103 of them lifecycle events over the cap; the plan rewritten on B moves 3,289 and 0 lifecycle events.
- **50%**: of B's 6,226 events, A's 8 filters move 4,658 (every one still matches) and none of the 317 lifecycle events; A's cap moves 3,531, 101 of them lifecycle events over the cap; the plan rewritten on B moves 3,303 and 0 lifecycle events.
- **70%**: of B's 6,226 events, A's 8 filters move 4,658 (every one still matches) and none of the 317 lifecycle events; A's cap moves 3,493, 95 of them lifecycle events over the cap; the plan rewritten on B moves 3,321 and 0 lifecycle events.
- **90%**: of B's 6,226 events, A's 8 filters move 4,658 (every one still matches) and none of the 317 lifecycle events; A's cap moves 3,555, 106 of them lifecycle events over the cap; the plan rewritten on B moves 3,295 and 0 lifecycle events.
<!-- /generated:capture-b-verdict -->

## Against the prediction

<!-- generated:prediction -->
- **At most 9 classes match the plan at every target.** 8 classes at every target, 535 to 604 events over the plan. Held.
- **The filters move about a hundred rare lines that share those classes.** 0. Every pattern in the chosen classes is churn the plan also moves; the producer-state loading lines log under `kafka.log.UnifiedLog$`, a logger name of its own. Did not hold.
- **On B the same classes still match.** Every class matches on B. Held.
- **Both arms keep the lifecycle lines.** The filters move 0 of 317; A's cap moves 95 to 106. Held for the filters, not for the cap.
- **Close to a draw on events; what differs is the rule count.** 8 filters against one cap row. Held.
<!-- /generated:prediction -->

## Counting conditions

- Datadog counts indexed events; with the shipped forwarder path one record is one event,
  and the Receiver groups the lines of a multi-line event into one record.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its
  pattern's cap takes the container's action. Patterns under 5% of their container's bytes
  in the window are not capped, the first 5 events of a pattern in a window pass, and the
  severity floors keep a tenth of INFO, DEBUG and TRACE, three tenths of WARN and half of
  ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within
  that noise. One cap row moves whole patterns: every pattern above the cap, which sits at
  the largest pattern the container keeps.
- The tool takes a file's span from its records' timestamps. These records carry no
  timestamp field, so it takes one hour, and each cap it writes is bytes per 240 s window
  of that hour. Replayed on its own capture inside one window, a cap is multiplied by
  3,600 / 240 = 15. Applied to B, A's cap is carried from A's ten hours to B's two:
  15 × 7,200 / 36,000 = 3. `results/policy-*.json` records each file and its factor.
- Lifecycle events are the events of the patterns B's slice has and A's does not.
- The patterns the plan keeps under the cap are those the engine marked nothing of under it.
- Errors and warnings are ERROR, WARN, CRITICAL and FATAL. Datadog's `status:error` and
  `status:warn` match ERROR and WARN.
- Every count is taken two ways, from the emitted records and from the engine's own
  aggregators, and the run fails if they differ; the class rows are required to equal those
  counts.

## Reproduce

```sh
./run.sh                  # everything
./run.sh plan replay      # some stages only, in the order given
```

Stages: `data plan control policy replay count report`. Needs Docker, Node 18 or later and
about 1 GB of disk; the whole run takes under ten minutes. `plan` installs the pinned
log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; every other stage runs the
pinned engine image on a slice. `ACCT_TARGETS` sets the targets (default `30 50 70 90`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `slice.py` | one container's records from a capture, byte for byte |
| `classes.py` | each event's logger class, read from its text, added to the counted rows |
| `arms.py` | the selection rule and every arm, from the class rows |
| `report.py` | renders `results/results.md`, `results/results.json` and the tables above; `--check` fails CI if the committed figures do not follow from the kept outputs |
| `../accounting-lib/` | the plan request, the replay, the policy scaling and the two counts, shared with the other accounting benchmarks |
| `results/plan-<A or B>-<target>.json` | the plan the MCP wrote |
| `results/policy-<A, AonB or B>-<target>.*` | the files the engine read, with the factor |
| `results/<run>.tally.json`, `results/<run>.classes.json` | the counts per route, severity and pattern, and per logger class |
| `results/replay-config.diff` | the one field added to the shared replay config: each event's text |

## Data

- **Capture A.** `otel-sample-200mb.log` from
  [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1),
  215,039,161 bytes, 197,430 lines, sha256
  `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`: about ten hours of the
  OpenTelemetry demo through Fluentd, the asset [`datadog-flex-accounting/`](../datadog-flex-accounting/)
  runs on.
- **Capture B.** `rec1155.log.gz` from
  [intent-data-v1](https://github.com/log-10x/benchmarks/releases/tag/intent-data-v1), sha256
  `d9ebe8c79e3ef6c1ca656599203d588831b6ed72e1f245cc32cd26124b6c4301`, expanded 51,439,789 bytes,
  41,713 lines, sha256 `df78e200d929bc57f826a396fb8e1764717bf6b61544970261f3647163351b77`: two
  hours of the unmodified demo images through Fluent Bit, the recording
  [`intent/`](../intent/) runs on.
- **The slices.** Each capture's records whose `kubernetes.container_name` is `kafka`,
  written byte for byte by `slice.py`; `run.sh` checks their sha256 and
  `results/results.md` lists them.
