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

## The floor after a buyer's own levers

A buyer reaches a per-pattern plan after the native levers, because the bill still grows.
This section measures what is left for the plan once those levers are in place, on both
whole captures.

**The levers, applied as written.** An index filter per service with
`-status:(error OR warn)` for `opentelemetry-collector`, `kafka` and `cart`, the set the
service filters need at [`datadog-flex-accounting/`](../datadog-flex-accounting/)'s 70%
target, and DEBUG and TRACE dropped everywhere. What stays in Standard is the floor.

**The plan.** The MCP's plan at 70% on each whole capture, applied through the engine as
written. It says which patterns the plan moves and which it keeps.

**The buckets, defined before the count.** Every floor event is in exactly one:

1. errors and warnings (ERROR, WARN, CRITICAL, FATAL), which both arms keep;
2. INFO and unlevelled events in a service one more service filter could move whole: (2a)
   the plan moves every such pattern of the service, or (2b) the plan moves none of it;
3. INFO and unlevelled events in a mixed service, one with both patterns the plan moves and
   patterns it keeps, split into the moved patterns (E, the events the plan moves beyond the
   buyer's filters) and the kept ones;
4. of bucket 3's moved patterns: those a native attribute cell selects alone, those a cell
   selects only together with other moved patterns, and those only the pattern ID
   (`@tenx_hash`) selects.

**What a native filter can name, fixed before the count.** `service`, `status`, `source`
and `host` on every log; the attributes Datadog's documented integration pipeline parses for
the container; and the top-level keys of a line that is a JSON object. A pattern's cell is
every attribute value all its events share, and a filter on the cell takes every pattern that
falls in it. Exact values only. The containers that are mixed on either capture, and `kafka`:

<!-- generated:floor-integrations -->
| Container | Integration page | Attributes the pipeline parses |
|---|---|---|
| `kafka` | [kafka](https://docs.datadoghq.com/integrations/kafka/) | `logger.name` |
| `postgresql` | [postgres](https://docs.datadoghq.com/integrations/postgres/) | `postgres.pid`, `postgres.error_severity`, `postgres.message` |
| `fluentd-10x` | [fluentd](https://docs.datadoghq.com/integrations/fluentd/) | none: the page covers forwarding logs to Datadog through Fluentd; no pipeline for Fluentd's own log lines |
| `opensearch` | [opensearch](https://docs.datadoghq.com/integrations/opensearch/) | none: no integration page (404 on 2026-10-13) |
| `valkey-cart` | [valkey](https://docs.datadoghq.com/integrations/valkey/) | none: no integration page (404 on 2026-10-13) |
| `recommendation` | none | none: a demo application service, Python; Datadog's Python pages document attribute extraction for JSON logs only, and these lines are not JSON |
| `product-reviews` | none | none: a demo application service, Python; plain-text lines |
| `llm` | none | none: a demo application service, Python; plain-text lines |
| `email` | none | none: a demo application service, Ruby; plain-text lines |
| `quote` | none | none: a demo application service, PHP; plain-text lines |
<!-- /generated:floor-integrations -->

Each bucket is shown with the frequency band of its patterns: each pattern's events over the
whole capture, binned as [`pattern-identity/`](../pattern-identity/) bins them, so a claim
that the money sits in high-volume lines can be checked against the floor rather than the
whole stream.

**The result that flips the verdict, stated before the run.** A buyer's assistant set its
own condition on 2026-10-13: the one-day measurement must show E x (S - F x R) well above
$1,490 a month, the list price of log10x's Growth tier for up to 300 nodes, where E is the
events moved beyond the buyer's filters, S the Standard rate avoided, F the Flex rate and R
the months retained. At its buyer's volume, about 21 billion indexed events a month, S - F x
R at 15-day Standard on a scalable Flex tier is about $1.65 per million before compute, so E
must exceed roughly 0.9 billion events a month, 4.3% of the indexed stream. In shares, which
is all a demo capture can give: the verdict flips if bucket 3's moved patterns are 5% or
more of the capture's events and more than half of them only the ID selects. Then the
assistant's own condition sends the buyer to a canary. If bucket 3 is under 5%, or most of it
is selectable natively, building in house stands on the demo.

**Prediction, written before the run.** The floor on capture A is about 14.5% of events
after the three service filters, less once DEBUG and TRACE are dropped (TRACE is mostly
`ad`); about 6,500 of it is errors, warnings and criticals. The rest is small services:
`recommendation` (one statement, movable whole), `grafana`, `frontend`, `fluentd-10x`,
`valkey-cart`, `opensearch`. Bucket 3 is therefore a few thousand events, 2 to 4% of the
capture, and part of that is isolable by a logfmt or class attribute where Datadog parses
one. The prediction is that the floor does not flip the verdict on the public captures:
building in house stands on the demo, narrowly, and the floor composition that would flip it
belongs to a real estate. The tables are published as they come out.

<!-- generated:floor -->
**Capture A.** 157,228 events. The floor: 15,644 events, 0.034 GB, 10% of the capture. The plan at 70% caps 17 containers and plans 55 patterns.

| Bucket | Events | Share of the capture | Patterns | seen once | 2 to 10 | 11 to 100 | 101 to 1,000 | over 1,000 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1. Errors and warnings | 6,571 | 4.2% | 67 | 38 | 69 | 281 | 126 | 6,057 |
| 2a. INFO and unlevelled, a service whose every such pattern the plan moves | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 |
| 2b. INFO and unlevelled, a service the plan moves none of | 3,120 | 2% | 1,882 | 1,699 | 439 | 359 | 623 | 0 |
| 3. Mixed service, patterns the plan moves (E) | 5,539 | 3.5% | 13 | 0 | 0 | 149 | 843 | 4,547 |
| 3. Mixed service, patterns the plan keeps | 414 | 0.3% | 286 | 247 | 148 | 19 | 0 | 0 |
| 4. Of E, a native cell holds the pattern alone | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 |
| 4. Of E, a native cell holds it with moved patterns only | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 |
| 4. Of E, only the ID selects it | 5,539 | 3.5% | 13 | 0 | 0 | 149 | 843 | 4,547 |

**Capture B.** 41,573 events. The floor: 10,892 events, 0.015 GB, 26.2% of the capture. The plan at 70% caps 12 containers and plans 46 patterns.

| Bucket | Events | Share of the capture | Patterns | seen once | 2 to 10 | 11 to 100 | 101 to 1,000 | over 1,000 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1. Errors and warnings | 582 | 1.4% | 21 | 16 | 13 | 0 | 553 | 0 |
| 2a. INFO and unlevelled, a service whose every such pattern the plan moves | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 |
| 2b. INFO and unlevelled, a service the plan moves none of | 1,314 | 3.2% | 146 | 141 | 4 | 0 | 1,169 | 0 |
| 3. Mixed service, patterns the plan moves (E) | 4,882 | 11.7% | 22 | 0 | 0 | 164 | 4,718 | 0 |
| 3. Mixed service, patterns the plan keeps | 4,114 | 9.9% | 120 | 24 | 20 | 2,720 | 1,350 | 0 |
| 4. Of E, a native cell holds the pattern alone | 23 | 0.1% | 1 | 0 | 0 | 23 | 0 | 0 |
| 4. Of E, a native cell holds it with moved patterns only | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 |
| 4. Of E, only the ID selects it | 4,859 | 11.7% | 21 | 0 | 0 | 141 | 4,718 | 0 |
<!-- /generated:floor -->

The mixed services and what the plan does in each:

<!-- generated:floor-services -->
| Capture | Mixed service | Events the plan moves | Patterns | Events the plan keeps | Patterns |
|---|---|---:|---:|---:|---:|
| A | `recommendation` | 3,430 | 1 | 1 | 1 |
| A | `fluentd-10x` | 1,283 | 3 | 144 | 106 |
| A | `valkey-cart` | 600 | 5 | 6 | 6 |
| A | `opensearch` | 226 | 4 | 263 | 173 |
| B | `llm` | 2,025 | 8 | 452 | 22 |
| B | `product-reviews` | 1,309 | 4 | 3,621 | 67 |
| B | `recommendation` | 602 | 1 | 1 | 1 |
| B | `email` | 391 | 1 | 1 | 1 |
| B | `quote` | 391 | 1 | 1 | 1 |
| B | `valkey-cart` | 116 | 5 | 9 | 9 |
| B | `postgresql` | 48 | 2 | 29 | 19 |
<!-- /generated:floor-services -->

<!-- generated:floor-verdict -->
- **Capture A**: the verdict does not flip. Bucket 3's moved patterns are 3.5% of the capture, and 100% of their events only the ID selects. Moving whole the mixed services where the plan keeps a single event (`recommendation`) leaves 1.3% of the capture in bucket 3's moved patterns, 100% of it ID-only: it does not flip.
- **Capture B**: the verdict flips. Bucket 3's moved patterns are 11.7% of the capture, and 99.5% of their events only the ID selects. Moving whole the mixed services where the plan keeps a single event (`email`, `quote`, `recommendation`) leaves 8.4% of the capture in bucket 3's moved patterns, 99.3% of it ID-only: it still flips.
<!-- /generated:floor-verdict -->

**Growth from A to B.** A covers ten hours of demo 2.1.3 and B two hours of demo 2.2.0, so
the floor is compared per hour. A service present only at the later tag is new code; inside
a service present at both, a pattern seen in both captures moves with traffic and a pattern
seen in one only is a statement added, removed or reworded.

<!-- generated:floor-growth -->
The floor per hour: 1,564 on A, 5,446 on B.

| Change from A to B, floor events per hour | Events per hour | Where |
|---|---:|---|
| Services in B and not in A, new code | +3,704 | `product-reviews`, `llm` |
| Services in A and not in B's capture | -507 | `grafana`, `fluentd-10x`, `opensearch`, `kube-proxy`, `prometheus-server`, `jaeger`, and others |
| Services in both, patterns seen in both: traffic | +50 |  |
| Services in both, patterns seen in B only: statements added or reworded | +1,270 | `accounting`, `payment`, `quote`, `email` |
| Services in both, patterns seen in A only: statements gone or reworded | -636 | `opentelemetry-collector`, `frontend` |
| Patterns inside the filtered services the filters no longer match | 0 | none: a service filter matches its service at both tags |
<!-- /generated:floor-growth -->

**Against the prediction.**

<!-- generated:floor-prediction -->
- **The floor on A is about 14.5% after the three service filters, less once DEBUG and TRACE are dropped, about 6,500 of it errors, warnings and criticals.** 10% with DEBUG and TRACE dropped; bucket 1 holds 6,571. Held.
- **Bucket 3 is 2 to 4% of the capture.** A: 3.5%. B: 11.7%. Held on A, not on B.
- **Part of it is isolable by a logfmt or class attribute.** Only `LOG_checkpoint_starting_time` in `postgresql` on B (23 events, by postgres.error_severity, postgres.message, postgres.pid) sits in a native cell without a kept pattern; every other moved pattern shares its cell with patterns the plan keeps. Held for 23 of the 10,421 events.
- **The floor does not flip the verdict on the public captures.** A: does not flip. B: flips. Did not hold on B.
<!-- /generated:floor-prediction -->

`results/results.md` lists every one of bucket 3's moved patterns with its cell, its band and
what selects it.

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

Stages: `data plan control policy replay count report` for the kafka slices and
`floor-plan floor-replay floor-count` for the floor. Needs Docker, Node 18 or later and
about 2 GB of disk; the whole run takes under twenty minutes. `plan` installs the pinned
log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; every other stage runs the
pinned engine image on a slice. `ACCT_TARGETS` sets the targets (default `30 50 70 90`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `slice.py` | one container's records from a capture, byte for byte |
| `classes.py` | each event's logger class, read from its text, added to the counted rows |
| `arms.py` | the selection rule and every arm, from the class rows |
| `floor.py` | the floor, its buckets, the flip test and the growth split |
| `attrs.py` | each pattern's native attribute cell on a whole capture |
| `integrations.json` | the attributes each container's documented Datadog pipeline parses, with the pages read |
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
