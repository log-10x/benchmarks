# Multi-line grouping across containers

Fluent Bit's Forward protocol sends every record with a tag, and the Fluent Bit input in the shipped 10x engine image, 1.1.150, takes each event's source from that tag. The engine joins a multi-line event such as a stack trace into one record, and the step that joins lines counts its flush timeout per source. Across five cases, the shipped image returned 1,533 of 5,836 records mixing lines from more than one container, all in cases that send every container under one tag. A build with a fix for this returned none, and neither build lost or duplicated any of the 22,557 lines sent.

The [Elasticsearch hot-tier benchmark](../elastic-hot-tier-budget/RECORD.md) also sent every container under one tag, and 71 of its 848,190 returned records were mixed.

## Records returned to Fluent Bit, per case

Each case sends 512 episodes, short runs of lines, and 12 of them pause for 1 to 6 s partway through. A stack trace counts as whole when its head and every continuation line came back in one record with nothing else.

| Case | Mixed, shipped | Mixed, fix | Traces whole, shipped | Traces whole, fix |
|---|---:|---:|---:|---:|
| a: other container inside a trace | 512 | 0 | 0 of 512 | 509 of 512 |
| b: kafka startup lines after jaeger | 509 | 0 | none sent | none sent |
| c: two traces interleaved | 512 | 0 | 0 of 1,024 | 1,021 of 1,024 |
| d: one container (control) | 0 | 0 | 509 of 512 | 509 of 512 |
| e: a, b, c, a tag per container | 0 | 0 | 508 of 511 | 508 of 511 |
| Total | 1,533 | 0 | 1,017 of 2,559 | 2,547 of 2,559 |

On the shipped image, every episode in cases a and c produced a mixed record, paused or not, as did case b except three episodes paused 5 or 6 s. Case e sends the same patterns with one tag per container and returned none, so the mixing follows the shared tag. One mixed record from case b, filed under the jaeger container, contains kafka's four startup lines:

```
{"level":"info","ts":1792968679.3069091,"caller":"grpc@v1.60.0/clientconn.go:532","msg":"[core][Channel #1] Channel Connectivity change to READY","system":"grpc","grpc_log":true,"e103id":"4429"}
===> User e103id=4430
uid=1000(appuser) gid=1000(appuser) groups=1000(appuser) e103id=4431
===> Setting default values of environment variables if not already set. e103id=4432
===> Configuring ... e103id=4433
```

- With the fix, all 5,868 records with sent lines came back under `tenx.` plus their sent tag. The shipped run did not record returned tags.
- The fix build still split 12 traces, all in episodes paused 5 or 6 s against a 5 s group flush timeout. The six in cases d and e split on the shipped image too.

## How the lines were sent and matched

A Python sender writes Fluent Forward records to Fluent Bit 4.2, which forwards them to the 10x engine over one connection and writes what comes back to a file. A sequence token ending every line lets `score.py` match each returned line to its sent line. Apart from the 12 pauses, episodes go out 1 ms apart. The engine ran with 0.5 CPU and 512 MB.

## Scope of the run

- One run per build, about five minutes each, on lines from a sender script, not real container logs.
- The fix build is a local image: the shipped image with the engine jar and modules from the fix commits.

## Run it

```
# from this directory: rescore the committed results, then rerun
python3 score.py --self-test
python3 score.py results/shipped-1.1.150/data   # exits 1: mixed records
python3 score.py results/fix2-1.1.151/data      # exits 0
./run.sh all                                    # full rerun of 1.1.150
```

Scoring needs only Python 3. A full rerun needs Docker with no other rig running and takes about five minutes. Running a fix build is in [RECORD.md](RECORD.md#running).

The complete record is in [RECORD.md](RECORD.md): engine arguments, every case's line sequence, scoring rules and each build's image and commits.
