# The OpenTelemetry return path, three defects reproduced

One command, two containers, 56 crafted lines. No ClickStack, no MinIO, no
capture. The three defects the ClickStack end to end run reported on 2026-09-14
(`clickstack-e2e/results/clickstack-e2e-2026-09-14.md`, section "What did not
work, or was skipped") are two defects, and the reproduction says which line of
which file produces each.

```
./repro.sh                 all four variants
./repro.sh resource        one variant
```

## Components

| Part | Image | Digest |
|---|---|---|
| engine | `ghcr.io/log-10x/edge-10x:latest` | `sha256:4d6f596ed0c943d282a63def579a13d877e8e8dda252d4ee254566f656ea3f0d` |
| collector | `otel/opentelemetry-collector-contrib:0.160.0` | `sha256:799dc6cf12c96192af37b5bdba804da8c10b3bc563b43cb90c3f3c58d9572ad6` |

Both are the images the ClickStack harness pinned. The engine config is the tree
inside that image with the same edits the harness makes, each asserted: the
OpenTelemetry Collector forwarder input enabled, the pattern text added to the
`fullText` splice list, and the regulator's warmup and baseline count set to
zero for a short run. The policy is one container, `kafka`, with a cap of
100000 and the action `offload`.

## What is fed

`lines/crafted.jsonl`, written by `make_lines.py`. Every line is the released
capture's envelope shape: Fluent's envelope, the log line in `log`, the
container `kafka`.

| Block | Lines | What it varies |
|---|---:|---|
| cases | 6 | the six message shapes the handoff asks for, A to F |
| sweep | 41 | the escape count in the message, 0 to 40, nothing else |
| noise | 9 | the escape count in a field that is NOT the message, 0 to 30 |

56 lines in, 55 records back in every variant. Case F is a message that is
itself a JSON object and carries no timestamp, so the engine groups it onto
case E as a continuation line. That is the engine's multiline grouping, not a
defect, and it is the only line that does not return on its own.

## The four variants

| Variant | What changes |
|---|---|
| `resource` | the kubernetes container is copied to the resource attribute `service.name`, so the input renderer writes `_tenx_resource_keys` |
| `noresource` | the same lines with no resource attribute, so `_tenx_time` is the field that follows `tag` |
| `nodrop` | `resource`, with `drop:tag` removed from the receiver's own extractor, everything else identical |
| `withtime` | `resource`, with a record time set on the way in, so `_tenx_time` reaching the output appender is not zero |

## The verdict

**The working hypothesis is right about the arithmetic and wrong about the
mechanism.** The cut does land N characters late, where N is the count of
escape sequences in the message ahead of the `tag` field: 41 of 41 sweep values
are consistent with a shift of exactly N, and 4 of them are ambiguous within
one character only because the character at the splice boundary repeats.

The reader offsets are not the cause. `probe/run.sh` replays
`EventJsonExtractor`'s offset arithmetic over eclipse parsson 1.1.7, the
version the engine builds against, at every alignment from 0 to 2600 against 0,
1, 2, 5 and 30 escapes in the record: 13005 trials, and the computed drop range
is the true range in every one of them. Parsson's stream offsets count raw
characters, and `syntheticCharsGenerated` already accounts for the synthetic
bracket the reader writes.

The cause is a coordinate mismatch inside the extractor, and the `noise` block
is what separates the two. Thirty escape sequences in a field the extractor
does not capture do no damage at all: `NOISE_00` through `NOISE_30` come back
with 11 attributes and no anomalous key. The same 30 escapes in the captured
message destroy the record. Only a captured string is unescaped, and it is that
unescape that moves everything after it.

## D1 and D3 are one defect

`BaseEventExtractor.processUnescapes` (engine `main`, line 337) JSON-unescapes
every captured string in place, then registers the leftover gap through
`receiver.redactRange`, which shifts the live tail of the record left by the
number of characters the unescape collapsed. It records the gap in
`redactionsMap` so later readers can translate. `dispatchMatches` and
`processFields` both translate through that ledger, with
`redactStartOffset` and `redactLengthOffset`.

`processRedactions` does not. At line 495 it calls

```java
receiver.redactRange(insertPos, insertData, matchStart, matchLength);
```

with the offsets the JSON parse produced, which are the coordinates the buffer
held *before* the unescape shifted it. The `drop:tag` range therefore lands N
characters late, where N is the number of characters the unescape collapsed
ahead of it, and the cut keeps the first N characters of `,"tag":"<value>"`
and eats N characters of whatever follows.

What follows is `_tenx_resource_keys` when the record carries a resource
attribute and `_tenx_time` when it does not, which is why the damaged names in
the ClickStack run are all misspellings of one field. Small N leaves a record
that still parses and carries a damaged key. From N of 6 the JSON is no longer
an object, the output appender's parse fails and it takes the raw path: the
whole rendered record becomes the body, no attributes, ingest time. Those are
the 19436 unmarked records.

The handoff's suspicion that the trigger is a message that is itself JSON with
a `body` key is wrong. It correlated because a message that is JSON carries
many quotes. The sweep lines contain no `body` key at all and break at the same
escape counts.

`nodrop` is the control. With `drop:tag` removed and nothing else changed, all
55 records come back parsed, with no anomalous attribute name, and the resource
set on every one.

The service arriving in two places is the same defect. A damaged
`_tenx_resource_keys` is not read by the appender, so the resource attribute
stays a log attribute. In `resource`, 15 of 55 records carry a resource and 10
carry `service.name` as a log attribute instead. In `nodrop`, 55 carry a
resource and none carries the log attribute.

## D2 is separate and simple

`OtlpLogsOutputAppender.setTimestamps` (pipeline-extensions `main`, line 315)
returns true whenever `_tenx_time` is present, and the input renderer writes
`_tenx_time` on every record, as the value the incoming record carried. OTLP
reads 0 as unset, so a record that arrived with no record time renders
`_tenx_time: 0`, `setTimestamps` stamps 0 and returns true, and the fallback at
line 201 never runs.

`nodrop` shows the defect on its own: all 55 records parse, all 55 carry the
marks, and not one carries a `timeUnixNano`. `withtime` sets a record time on
the way in and all 55 come back with one.

In `resource`, the 30 records that carry a time are exactly the 30 the appender
could not parse, which take the raw path and stamp ingest time there, and the
overlap between "carries the marks" and "carries a time" is zero. In
`noresource` nine records carry both, and they are the ones where the shifted
cut destroyed the `_tenx_time` key itself: with neither marker readable
`setTimestamps` returns false and the fallback does run. A defect papering over
a defect is not a fix.

## The patches

`patches/0001-engine-drop-range-in-current-coordinates.diff` translates the
drop and redact ranges through the same ledger `dispatchMatches` uses, before
handing them to `redactRange`.

`patches/0002-appender-zero-tenx-time-is-absent.diff` reads a `_tenx_time` of 0
as absent, falls back to the observed time when there is one and lets the
caller's fallback run when there is not.

Neither patch is applied and neither is built here. Both are cut against the
file as it stands on each repository's `main`, which is not what the eclipse
checkout holds: that checkout's last engine commit is 2026-06-18 and it does
not contain `processUnescapes` at all.

# The numbers

## Variant `resource`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 25 |
| carrying no attribute at all | 30 |
| carrying `routeState` | 25 |
| carrying `tenx_hash` | 25 |
| carrying `message_pattern` | 25 |
| `timeUnixNano` set | 30 |
| `timeUnixNano` zero or absent | 25 |
| `observedTimeUnixNano` set | 55 |
| a resource attribute present | 15 |
| `service.name` as a log attribute | 10 |

Attribute names nothing configured:

| Name | Records | Shift of the drop range that produces it |
|---|---:|---:|
| `_keys` | 2 | 16 |
| `_teys` | 2 | 18 |
| `ttenx_resource_keys` | 1 | 3 |
| `taenx_resource_keys` | 1 | 4 |
| `tagnx_resource_keys` | 1 | 5 |
| `_tens` | 1 | 20 |
| `_tenx` | 1 | 21 |

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 1 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 2 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 3 | 3 | yes | parsed, key `ttenx_resource_keys` | 12 |
| 4 | 4 | yes | parsed, key `taenx_resource_keys` | 12 |
| 5 | 5 | yes | parsed, key `tagnx_resource_keys` | 12 |
| 6 | 6 | yes | not parsed, whole record in the body | 0 |
| 7 | 7 | yes | not parsed, whole record in the body | 0 |
| 8 | 8 | yes | not parsed, whole record in the body | 0 |
| 9 | 9 | yes | not parsed, whole record in the body | 0 |
| 10 | 10 | yes | not parsed, whole record in the body | 0 |
| 11 | 11 | yes | not parsed, whole record in the body | 0 |
| 12 | 12 | yes | not parsed, whole record in the body | 0 |
| 13 | 13 | yes | not parsed, whole record in the body | 0 |
| 14 | 14 | yes | not parsed, whole record in the body | 0 |
| 15 | 15 | yes | not parsed, whole record in the body | 0 |
| 16 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 17 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 18 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 19 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 20 | 20 | yes | parsed, key `_tens` | 12 |
| 21 | 21 | yes | parsed, key `_tenx` | 12 |
| 22 | 22 | yes | not parsed, whole record in the body | 0 |
| 23 | 23 | yes | not parsed, whole record in the body | 0 |
| 24 | 24 | yes | not parsed, whole record in the body | 0 |
| 25 | 25 | yes | not parsed, whole record in the body | 0 |
| 26 | 26 | yes | not parsed, whole record in the body | 0 |
| 27 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 28 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 29 | 29 | yes | not parsed, whole record in the body | 0 |
| 30 | 30 | yes | not parsed, whole record in the body | 0 |
| 31 | 31 | yes | not parsed, whole record in the body | 0 |
| 32 | 32 | yes | not parsed, whole record in the body | 0 |
| 33 | 33 | yes | not parsed, whole record in the body | 0 |
| 34 | 34 | yes | not parsed, whole record in the body | 0 |
| 35 | 35 | yes | not parsed, whole record in the body | 0 |
| 36 | 36 | yes | not parsed, whole record in the body | 0 |
| 37 | 37 | yes | not parsed, whole record in the body | 0 |
| 38 | not distinguishable | yes | parsed, damage inside the `_tenx_` markers the appender strips | 11 |
| 39 | 39 | yes | not parsed, whole record in the body | 0 |
| 40 | 40 | yes | not parsed, whole record in the body | 0 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 0 | 1789439384004741834 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\` |
| CASE_D | 30 | 0 | 1789439384004798284 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_D \"f0\" \"f1\" \"f2\" \"f3\" \"f4\` |
| CASE_E | 1 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |


## Variant `noresource`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 35 |
| carrying no attribute at all | 20 |
| carrying `routeState` | 35 |
| carrying `tenx_hash` | 35 |
| carrying `message_pattern` | 35 |
| `timeUnixNano` set | 29 |
| `timeUnixNano` zero or absent | 26 |
| `observedTimeUnixNano` set | 47 |
| a resource attribute present | 0 |
| `service.name` as a log attribute | 0 |

Attribute names nothing configured:

| Name | Records | Shift of the drop range that produces it |
|---|---:|---:|
| `d_time` | 2 | 30 |
| `ttenx_time` | 1 | 3 |
| `taenx_time` | 1 | 4 |
| `tagnx_time` | 1 | 5 |
| `_t_tenx_observed_time` | 1 | 17 |
| `_tetenx_observed_time` | 1 | 18 |
| `_tenenx_observed_time` | 1 | 19 |
| `_tenxnx_observed_time` | 1 | 20 |
| `__time` | 1 | 31 |
| `_ttime` | 1 | 32 |
| `_teime` | 1 | 33 |
| `_tenme` | 1 | 34 |
| `_tenxe` | 1 | 35 |

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 1 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 2 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 3 | 3 | yes | parsed, key `ttenx_time` | 11 |
| 4 | 4 | yes | parsed, key `taenx_time` | 11 |
| 5 | 5 | yes | parsed, key `tagnx_time` | 11 |
| 6 | 6 | yes | not parsed, whole record in the body | 0 |
| 7 | 7 | yes | not parsed, whole record in the body | 0 |
| 8 | 8 | yes | not parsed, whole record in the body | 0 |
| 9 | 9 | yes | not parsed, whole record in the body | 0 |
| 10 | 10 | yes | not parsed, whole record in the body | 0 |
| 11 | 11 | yes | not parsed, whole record in the body | 0 |
| 12 | 12 to 13 | yes | not parsed, whole record in the body | 0 |
| 13 | 12 to 13 | yes | not parsed, whole record in the body | 0 |
| 14 | 14 | yes | not parsed, whole record in the body | 0 |
| 15 | 15 | yes | not parsed, whole record in the body | 0 |
| 16 | 16 | yes | not parsed, whole record in the body | 0 |
| 17 | 17 | yes | parsed, key `_t_tenx_observed_time` | 11 |
| 18 | 18 | yes | parsed, key `_tetenx_observed_time` | 11 |
| 19 | 19 | yes | parsed, key `_tenenx_observed_time` | 11 |
| 20 | 20 | yes | parsed, key `_tenxnx_observed_time` | 11 |
| 21 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 22 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 23 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 24 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 25 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 26 | 26 | yes | not parsed, whole record in the body | 0 |
| 27 | 27 | yes | not parsed, whole record in the body | 0 |
| 28 | 28 | yes | not parsed, whole record in the body | 0 |
| 29 | 29 | yes | not parsed, whole record in the body | 0 |
| 30 | 30 | yes | parsed, key `d_time` | 11 |
| 31 | 31 | yes | parsed, key `__time` | 11 |
| 32 | 32 | yes | parsed, key `_ttime` | 11 |
| 33 | 33 | yes | parsed, key `_teime` | 11 |
| 34 | 34 | yes | parsed, key `_tenme` | 11 |
| 35 | 35 | yes | parsed, key `_tenxe` | 11 |
| 36 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 37 | 37 | yes | not parsed, whole record in the body | 0 |
| 38 | none | no | not parsed, whole record in the body | 0 |
| 39 | none | no | not parsed, whole record in the body | 0 |
| 40 | none | no | not parsed, whole record in the body | 0 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 0 | 1789439415629420099 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\` |
| CASE_D | 30 | 11 | absent | `d_time` | `[2025-10-01 20:34:05,556] INFO CASE_D "f0" "f1" "f2" "f3" "f4" "f5" "f6" "f7" "f` |
| CASE_E | 1 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |


## Variant `nodrop`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 55 |
| carrying no attribute at all | 0 |
| carrying `routeState` | 55 |
| carrying `tenx_hash` | 55 |
| carrying `message_pattern` | 55 |
| `timeUnixNano` set | 0 |
| `timeUnixNano` zero or absent | 55 |
| `observedTimeUnixNano` set | 55 |
| a resource attribute present | 55 |
| `service.name` as a log attribute | 0 |

No attribute name outside the configured set.

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 1 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 2 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 3 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 4 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 5 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 6 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 7 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 8 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 9 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 10 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 11 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 12 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 13 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 14 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 15 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 16 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 17 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 18 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 19 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 20 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 21 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 22 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 23 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 24 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 25 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 26 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 27 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 28 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 29 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 30 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 31 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 32 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 33 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 34 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 35 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 36 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 37 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 38 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 39 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 40 | not distinguishable | no | parsed, nothing visibly wrong | 10 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_C keys "a" "b" "c" "d" "e" settled.` |
| CASE_D | 30 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_D "f0" "f1" "f2" "f3" "f4" "f5" "f6" "f7" "f` |
| CASE_E | 1 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |


## Variant `withtime`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 25 |
| carrying no attribute at all | 30 |
| carrying `routeState` | 25 |
| carrying `tenx_hash` | 25 |
| carrying `message_pattern` | 25 |
| `timeUnixNano` set | 55 |
| `timeUnixNano` zero or absent | 0 |
| `observedTimeUnixNano` set | 55 |
| a resource attribute present | 15 |
| `service.name` as a log attribute | 10 |

Attribute names nothing configured:

| Name | Records | Shift of the drop range that produces it |
|---|---:|---:|
| `_keys` | 2 | 16 |
| `_teys` | 2 | 18 |
| `ttenx_resource_keys` | 1 | 3 |
| `taenx_resource_keys` | 1 | 4 |
| `tagnx_resource_keys` | 1 | 5 |
| `_tens` | 1 | 20 |
| `_tenx` | 1 | 21 |

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | 0 to 2 | yes | parsed, nothing visibly wrong | 10 |
| 1 | 0 to 2 | yes | parsed, nothing visibly wrong | 10 |
| 2 | 0 to 2 | yes | parsed, nothing visibly wrong | 10 |
| 3 | 3 | yes | parsed, key `ttenx_resource_keys` | 12 |
| 4 | 4 | yes | parsed, key `taenx_resource_keys` | 12 |
| 5 | 5 | yes | parsed, key `tagnx_resource_keys` | 12 |
| 6 | 6 | yes | not parsed, whole record in the body | 0 |
| 7 | 7 | yes | not parsed, whole record in the body | 0 |
| 8 | 8 | yes | not parsed, whole record in the body | 0 |
| 9 | 9 | yes | not parsed, whole record in the body | 0 |
| 10 | 10 | yes | not parsed, whole record in the body | 0 |
| 11 | 11 | yes | not parsed, whole record in the body | 0 |
| 12 | 12 | yes | not parsed, whole record in the body | 0 |
| 13 | 13 | yes | not parsed, whole record in the body | 0 |
| 14 | 14 | yes | not parsed, whole record in the body | 0 |
| 15 | 15 | yes | not parsed, whole record in the body | 0 |
| 16 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 17 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 18 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 19 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 20 | 20 | yes | parsed, key `_tens` | 12 |
| 21 | 21 | yes | parsed, key `_tenx` | 12 |
| 22 | 22 | yes | not parsed, whole record in the body | 0 |
| 23 | 23 | yes | not parsed, whole record in the body | 0 |
| 24 | 24 | yes | not parsed, whole record in the body | 0 |
| 25 | 25 | yes | not parsed, whole record in the body | 0 |
| 26 | 26 | yes | not parsed, whole record in the body | 0 |
| 27 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 28 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 29 | 29 | yes | not parsed, whole record in the body | 0 |
| 30 | 30 | yes | not parsed, whole record in the body | 0 |
| 31 | 31 | yes | not parsed, whole record in the body | 0 |
| 32 | 32 | yes | not parsed, whole record in the body | 0 |
| 33 | 33 | yes | not parsed, whole record in the body | 0 |
| 34 | 34 | yes | not parsed, whole record in the body | 0 |
| 35 | 35 | yes | not parsed, whole record in the body | 0 |
| 36 | 36 | yes | not parsed, whole record in the body | 0 |
| 37 | 37 | yes | not parsed, whole record in the body | 0 |
| 38 | not distinguishable | yes | parsed, damage inside the `_tenx_` markers the appender strips | 11 |
| 39 | 39 | yes | not parsed, whole record in the body | 0 |
| 40 | 40 | yes | not parsed, whole record in the body | 0 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 0 | 1789439478478160376 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\` |
| CASE_D | 30 | 0 | 1789439478478214984 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_D \"f0\" \"f1\" \"f2\" \"f3\" \"f4\` |
| CASE_E | 1 | 10 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |

# Raw records

Straight out of `out/<variant>/wire/returned.json`, which the collector's file exporter wrote with no processor in between. The full files are in the folder.


## `resource`

clean, line SWEEP_00:

```json
{
 "timeUnixNano": null,
 "observedTimeUnixNano": "1789439381748402214",
 "resource": {
  "service.name": "kafka"
 },
 "attributes": {
  "kubernetes": {
   "container_name": "kafka",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "pod_ip": "192.168.37.206",
   "labels": {
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569",
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka"
   },
   "namespace_name": "default",
   "host": "ip-192-168-42-205.ec2.internal"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "k8s_namespace": "default",
  "log.file.name": "crafted.jsonl",
  "stream": "stdout",
  "k8s_container": "kafka",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_00  settled."
}
```

damaged key, line SWEEP_03:

```json
{
 "timeUnixNano": null,
 "observedTimeUnixNano": "1789439381748403724",
 "resource": {},
 "attributes": {
  "k8s_container": "kafka",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "k8s_namespace": "default",
  "log.file.name": "crafted.jsonl",
  "kubernetes": {
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "pod_ip": "192.168.37.206",
   "labels": {
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka",
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569"
   },
   "container_name": "kafka",
   "namespace_name": "default",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "host": "ip-192-168-42-205.ec2.internal"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "stream": "stdout",
  "service.name": "kafka",
  "ttenx_resource_keys": [
   "service.name"
  ],
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_03 \"\"\" settled."
}
```

not parsed, line SWEEP_06:

```json
{
 "timeUnixNano": "1789439384005160628",
 "observedTimeUnixNano": "1789439384005160628",
 "resource": {},
 "attributes": {},
 "body": "{\"body\":\"[2025-10-01 20:34:05,556] INFO SWEEP_06 \\\"\\\"\\\"\\\"\\\"\\\" settled.\",\"tenx_tag\":\"kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log\",\"k8s_namespace\":\"default\",\"log.file.name\":\"crafted.jsonl\",\"stream\":\"stdout\",\"k8s_container\":\"kafka\",\"docker\":{\"container_id\":\"21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c\"},\"kubernetes\":{\"pod_name\":\"kafka-5ff8667569-jbfmv\",\"container_image\":\"ghcr.io/open-telemetry/demo:2.1.3-kafka\",\"container_image_id\":\"ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0\",\"pod_ip\":\"192.168.37.206\",\"pod_id\":\"4bdaf655-5d02-4653-ba57-fece182730aa\",\"host\":\"ip-192-168-42-205.ec2.internal\",\"labels\":{\"app.kubernetes.io/component\":\"kafka\",\"app.kubernetes.io/name\":\"kafka\",\"opentelemetry.io/name\":\"kafka\",\"pod-template-hash\":\"5ff8667569\"},\"container_name\":\"kafka\",\"namespace_name\":\"default\"},\"service.name\":\"kafka\",\"tag\"x_resource_keys\":[\"service.name\"],\"_tenx_time\":0,\"_tenx_observed_time\":1789439381748405320,\"tenx_hash\":\"tm5Xi-TdIAs\",\"message_pattern\":\"INFO_SWEEP_settled\",\"routeState\":\"pass\"}"
}
```


## `noresource`

clean, line SWEEP_00:

```json
{
 "timeUnixNano": null,
 "observedTimeUnixNano": "1789439413294792182",
 "resource": {},
 "attributes": {
  "kubernetes": {
   "namespace_name": "default",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_ip": "192.168.37.206",
   "labels": {
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569",
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka"
   },
   "container_name": "kafka",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "host": "ip-192-168-42-205.ec2.internal"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "k8s_namespace": "default",
  "log.file.name": "crafted.jsonl",
  "stream": "stdout",
  "k8s_container": "kafka",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_00  settled."
}
```

damaged key, line SWEEP_03:

```json
{
 "timeUnixNano": null,
 "observedTimeUnixNano": "1789439413294793954",
 "resource": {},
 "attributes": {
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "k8s_namespace": "default",
  "log.file.name": "crafted.jsonl",
  "kubernetes": {
   "pod_ip": "192.168.37.206",
   "host": "ip-192-168-42-205.ec2.internal",
   "labels": {
    "app.kubernetes.io/name": "kafka",
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569",
    "app.kubernetes.io/component": "kafka"
   },
   "container_name": "kafka",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "namespace_name": "default",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "stream": "stdout",
  "k8s_container": "kafka",
  "ttenx_time": "0",
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_03 \"\"\" settled."
}
```

not parsed, line SWEEP_06:

```json
{
 "timeUnixNano": "1789439415629767933",
 "observedTimeUnixNano": "1789439415629767933",
 "resource": {},
 "attributes": {},
 "body": "{\"body\":\"[2025-10-01 20:34:05,556] INFO SWEEP_06 \\\"\\\"\\\"\\\"\\\"\\\" settled.\",\"kubernetes\":{\"container_name\":\"kafka\",\"namespace_name\":\"default\",\"pod_name\":\"kafka-5ff8667569-jbfmv\",\"pod_id\":\"4bdaf655-5d02-4653-ba57-fece182730aa\",\"host\":\"ip-192-168-42-205.ec2.internal\",\"container_image\":\"ghcr.io/open-telemetry/demo:2.1.3-kafka\",\"container_image_id\":\"ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0\",\"pod_ip\":\"192.168.37.206\",\"labels\":{\"app.kubernetes.io/component\":\"kafka\",\"app.kubernetes.io/name\":\"kafka\",\"opentelemetry.io/name\":\"kafka\",\"pod-template-hash\":\"5ff8667569\"}},\"tenx_tag\":\"kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log\",\"k8s_namespace\":\"default\",\"log.file.name\":\"crafted.jsonl\",\"stream\":\"stdout\",\"k8s_container\":\"kafka\",\"docker\":{\"container_id\":\"21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c\"},\"tag\"x_time\":0,\"_tenx_observed_time\":1789439413294795800,\"tenx_hash\":\"tm5Xi-TdIAs\",\"message_pattern\":\"INFO_SWEEP_settled\",\"routeState\":\"pass\"}"
}
```


## `nodrop`

clean, line SWEEP_00:

```json
{
 "timeUnixNano": null,
 "observedTimeUnixNano": "1789439444782603733",
 "resource": {
  "service.name": "kafka"
 },
 "attributes": {
  "log.file.name": "crafted.jsonl",
  "k8s_container": "kafka",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "kubernetes": {
   "namespace_name": "default",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "pod_ip": "192.168.37.206",
   "labels": {
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569",
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka"
   },
   "container_name": "kafka",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "host": "ip-192-168-42-205.ec2.internal"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "stream": "stdout",
  "k8s_namespace": "default",
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_00  settled."
}
```


## `withtime`

clean, line SWEEP_00:

```json
{
 "timeUnixNano": "1759350845556000000",
 "observedTimeUnixNano": "1789439476220743740",
 "resource": {
  "service.name": "kafka"
 },
 "attributes": {
  "stream": "stdout",
  "k8s_container": "kafka",
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "kubernetes": {
   "host": "ip-192-168-42-205.ec2.internal",
   "container_name": "kafka",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "labels": {
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka",
    "opentelemetry.io/name": "kafka",
    "pod-template-hash": "5ff8667569"
   },
   "namespace_name": "default",
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "pod_ip": "192.168.37.206"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "k8s_namespace": "default",
  "log.file.name": "crafted.jsonl",
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_00  settled."
}
```

damaged key, line SWEEP_03:

```json
{
 "timeUnixNano": "1759350845556000000",
 "observedTimeUnixNano": "1789439476220745288",
 "resource": {},
 "attributes": {
  "docker": {
   "container_id": "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"
  },
  "kubernetes": {
   "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
   "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
   "pod_ip": "192.168.37.206",
   "host": "ip-192-168-42-205.ec2.internal",
   "labels": {
    "pod-template-hash": "5ff8667569",
    "app.kubernetes.io/component": "kafka",
    "app.kubernetes.io/name": "kafka",
    "opentelemetry.io/name": "kafka"
   },
   "namespace_name": "default",
   "pod_name": "kafka-5ff8667569-jbfmv",
   "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
   "container_name": "kafka"
  },
  "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log",
  "stream": "stdout",
  "k8s_namespace": "default",
  "log.file.name": "crafted.jsonl",
  "k8s_container": "kafka",
  "service.name": "kafka",
  "ttenx_resource_keys": [
   "service.name"
  ],
  "tenx_hash": "tm5Xi-TdIAs",
  "message_pattern": "INFO_SWEEP_settled",
  "routeState": "pass"
 },
 "body": "[2025-10-01 20:34:05,556] INFO SWEEP_03 \"\"\" settled."
}
```

not parsed, line SWEEP_06:

```json
{
 "timeUnixNano": "1789439478478486362",
 "observedTimeUnixNano": "1789439478478486362",
 "resource": {},
 "attributes": {},
 "body": "{\"body\":\"[2025-10-01 20:34:05,556] INFO SWEEP_06 \\\"\\\"\\\"\\\"\\\"\\\" settled.\",\"stream\":\"stdout\",\"k8s_container\":\"kafka\",\"docker\":{\"container_id\":\"21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c\"},\"kubernetes\":{\"pod_name\":\"kafka-5ff8667569-jbfmv\",\"container_image\":\"ghcr.io/open-telemetry/demo:2.1.3-kafka\",\"pod_id\":\"4bdaf655-5d02-4653-ba57-fece182730aa\",\"pod_ip\":\"192.168.37.206\",\"host\":\"ip-192-168-42-205.ec2.internal\",\"container_name\":\"kafka\",\"namespace_name\":\"default\",\"container_image_id\":\"ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0\",\"labels\":{\"opentelemetry.io/name\":\"kafka\",\"pod-template-hash\":\"5ff8667569\",\"app.kubernetes.io/component\":\"kafka\",\"app.kubernetes.io/name\":\"kafka\"}},\"tenx_tag\":\"kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c.log\",\"k8s_namespace\":\"default\",\"log.file.name\":\"crafted.jsonl\",\"service.name\":\"kafka\",\"tag\"x_resource_keys\":[\"service.name\"],\"_tenx_time\":1759350845556000000,\"_tenx_observed_time\":1789439476220746499,\"tenx_hash\":\"tm5Xi-TdIAs\",\"message_pattern\":\"INFO_SWEEP_settled\",\"routeState\":\"pass\"}"
}
```


# Verified against the patched engine, 2026-09-15

Both patches applied, built and rerun. The reproduction's own `analyze.py`
produced every number below from `out-patched/<variant>/wire/returned.json`.

| Part | What ran |
|---|---|
| engine | the JVM build of `log-10x/engine` `main` + `0001`, with `log-10x/pipeline-extensions` `main` + `0002`, as `run-cloud-<version>-all.jar` on `eclipse-temurin:23-jre` |
| collector | `otel/opentelemetry-collector-contrib:0.160.0`, the image the reproduction pinned |
| config, modules | `log-10x/config` and `log-10x/modules` at `main`, the pairing CI builds `main` against, with the same asserted edits `patch_config.py` makes |

The shipped `ghcr.io/log-10x/edge-10x` image is a native binary, so a patched
engine cannot be dropped into it and no image was published for this. The
topology is otherwise the run `repro.sh` performs: two containers on one
network, the engine listening on 4317, the return arriving on 24225, the
collector's file exporter writing every returned record with no processor in
between. `verify-patched.sh` is the runner.

## The 56 crafted lines, all four variants

| Measure | `resource` | `noresource` | `nodrop` | `withtime` |
|---|---:|---:|---:|---:|
| records returned | 55 | 55 | 55 | 55 |
| carrying attributes | 55 | 55 | 55 | 55 |
| carrying no attribute at all | 0 | 0 | 0 | 0 |
| carrying `routeState` | 55 | 55 | 55 | 55 |
| carrying `tenx_hash` | 55 | 55 | 55 | 55 |
| carrying `message_pattern` | 55 | 55 | 55 | 55 |
| `timeUnixNano` set | 55 | 55 | 55 | 55 |
| `timeUnixNano` zero or absent | 0 | 0 | 0 | 0 |
| `observedTimeUnixNano` set | 55 | 55 | 55 | 55 |
| a resource attribute present | 55 | 0 | 55 | 55 |
| `service.name` as a log attribute | 0 | 0 | 0 | 0 |
| attribute names nothing configured | 0 | 0 | 0 | 0 |

Read against the unpatched run in "The numbers" above:

- **D1 and D3 are gone.** Every record parses, in every variant, at every
  escape count from 0 to 40. No `taenx_resource_keys`, no `_tes`, no variant
  spelling of anything: the count of attribute names outside the configured set
  is zero across all four variants, where `resource` alone previously carried
  five of them. The `noise` block still comes back with 11 attributes, so the
  fix did not buy the clean sweep by suppressing a field.
- **The service is in one place.** `resource` now sets the OTLP resource on 55
  of 55 and writes `service.name` as a log attribute on none, where it was 15
  and 10. `noresource` sets no resource, which is what that variant asks for.
  This was never a quirk of the collector; a damaged `_tenx_resource_keys` was
  simply not readable by the appender.
- **D2 is gone.** 55 of 55 carry a `timeUnixNano` in every variant, `nodrop`
  included, where `nodrop` previously carried none. The no-record-time input is
  the interesting one: `_tenx_time` renders as 0, `_tenx_observed_time` carries
  the collector's observed time, and the appender now uses it. `withtime`,
  which sets a record time on the way in, still returns that time rather than
  the observed one.
- **The two fixes are independent and both are needed.** `nodrop` isolates D2
  (no drop configured, so the coordinates never matter) and it passes. The
  sweep isolates D1 and D3 and they pass with the drop in place.

## The 50,000 line slice

`clickstack-e2e/data/slice.log`, the slice the ClickStack harness ran, through
the same patched engine and the same collector.

| Measure | Original run, engine 1.1.74 | Patched engine |
|---|---:|---:|
| records returned | 37519 | 37540 |
| marked | 18083 | 37540 |
| unmarked | 19436 | 0 |
| carrying a `timeUnixNano` | 19436 | 37540 |
| carrying a resource attribute | not measured | 37540 |
| attribute names nothing configured | 8 spellings, 2133 records | 0 |

Every returned record carries `routeState`, so every one of them is routable:
the half of the sample that used to take the default path into the hot table
because it carried no mark is now zero. The 21 record difference in the total
is the multiline grouping landing a few continuation lines differently between
the two runs, not a change in what returns.

## Unit tests

| Repo | Test | Cases |
|---|---|---:|
| `log-10x/engine` | `ExtractDropRangeCoordinatesTest` | 9 |
| `log-10x/pipeline-extensions` | `OtlpLogsOutputAppenderTimestampsTest` | 7 |

Both are falsifiable against the file as it stood. The extractor test fails at
5 and 30 escape sequences without `0001`; 0, 1 and 2 pass either way, because
the character at the splice boundary repeats, which is the ambiguity the sweep
already measured. The appender test's zero cases fail without `0002`: the old
body returned true and stamped 0, measured by running it verbatim.

Suites of the touched modules, all green: engine `:tests` 308 tests,
`edge-extensions` 7, `cloud-extensions` 257 with 14 skipped (the skips are the
Azurite and live-service integration tests, unrelated).
