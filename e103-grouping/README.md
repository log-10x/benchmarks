# Multi-line grouping across containers

When several containers send to the 10x engine through Fluent Bit under one tag, does each container's multi-line event come back in its own record? On the shipped 1.1.150 image it did not: 1,533 of 5,836 returned records mixed lines from more than one container. A build with a grouping fix returned no mixed records, and neither build lost or duplicated a line.

The shipped Fluent Bit input takes an event's source from the Forward tag, and the step that joins multi-line events counts its flush timeout per source. In the [Elasticsearch hot-tier benchmark](../elastic-hot-tier-budget/) every container shared the tag `app.replay`, and 71 of 848,190 returned records were mixed. This rig repeats that record shape and path without Elasticsearch.

## Result

A stack trace counts as whole when its head and all its continuation lines came back alone in one record.

| Case | Mixed, shipped | Mixed, fix | Traces whole, shipped | Traces whole, fix |
|---|---:|---:|---:|---:|
| a: other container inside a trace | 512 | 0 | 0 of 512 | 509 of 512 |
| b: kafka startup lines after jaeger | 509 | 0 | none sent | none sent |
| c: two traces interleaved | 512 | 0 | 0 of 1,024 | 1,021 of 1,024 |
| d: one container (control) | 0 | 0 | 509 of 512 | 509 of 512 |
| e: a, b, c, one tag each | 0 | 0 | 508 of 511 | 508 of 511 |
| Total | 1,533 | 0 | 1,017 of 2,559 | 2,547 of 2,559 |

On the shipped image, cases a and c produced a mixed record in every episode. Case e sends the same patterns with one tag per container and returned none, so the mixing follows the shared tag. With the fix, all 5,868 records containing sent lines came back under the tag they were sent with.

- Both builds returned all 22,557 lines sent, each exactly once.
- The fix build still split 12 traces, all in episodes paused 5 or 6 s against a 5 s group flush timeout. The six in cases d and e also split on the shipped image.

## How it was measured

A Python sender writes Fluent Forward records to Fluent Bit 4.2, which forwards them to the 10x engine over one connection and writes what comes back to a file. `score.py` matches each returned line to the line sent through a sequence token at the end of every line. Each case sends 500 episodes back to back and 12 more paused between 1 and 6 s, 22,557 lines in all. The engine ran with 0.5 CPU, 512 MB and no budget set.

## Limits

- One run per build of about five minutes, on lines from a sender script. Real container logs were not tested.
- The fix build is a local image of 1.1.150 with the engine jar and modules from the fix commits.
- The shipped run did not record the tag each record came back under, so the tag check covers the fix run only.

## Run it

Scoring recomputes from the committed results, in this directory:

```
python3 score.py --self-test
python3 score.py results/shipped-1.1.150/data   # exits 1: mixed records
python3 score.py results/fix2-1.1.151/data      # exits 0
./run.sh all                                    # full rerun of 1.1.150
```

Scoring needs only Python 3. A full rerun needs Docker with no other rig running and takes about five minutes. Running a fix build is in [RECORD.md](RECORD.md#running).

The complete record is in [RECORD.md](RECORD.md): the engine arguments, every case's line sequence, the scoring rules and each build's image and commits.
