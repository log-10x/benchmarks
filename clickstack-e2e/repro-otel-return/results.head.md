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
