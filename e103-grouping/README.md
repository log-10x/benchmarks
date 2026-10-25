# E103: multi-line grouping across containers

A minimal reproduction of engine ask E103 on the shipped engine image. In the `elastic-hot-tier-budget` run, 71 of 848,190 returned records held lines from more than one container: kafka's four startup lines (seq 2751 to 2754) joined the jaeger record at seq 2750 and were filed under jaeger. This rig sends the same record shape over the same path and counts such records.

## What runs

The path is the hot-tier rig's, with Elasticsearch dropped. A sender writes Fluent Forward records to Fluent Bit on 24224. Fluent Bit moves the container into a `kubernetes` map (`fluent-bit/prep.lua`, the rig's `prep`), copies every record to `in.jsonl`, and forwards to the Receiver on `tenx:24224` with one worker and one connection. The Receiver returns records to Fluent Bit's second forward input on 24225, which writes them to `returned.jsonl`.

The Receiver is started the way `gen-receiver-values.mjs` rendered it for the two-arm runs (`elastic-hot-tier-budget/results-two-arm*/values/compose.receiver.yaml`):

- image `ghcr.io/log-10x/edge-10x:1.1.150@sha256:3e755bbc14780a27e643e09b76dfd7ec9616cab67833f70daf9420eff646d350`
- arguments `@run/input/forwarder/fluentbit @apps/receiver symbolMessageHashField tenx_hash outputEncodeField fullText("tenx_hash","routeState","message_pattern","severity_level","utf8Size")`
- environment `TENX_AIRGAPPED=true` and `TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit`
- 0.5 CPU, 512 MB, tmpfs on `/tmp`

The rendered `GH_*` variables (the policy branch) are left out, so no cap is set and nothing is held. The image keeps its config at `/etc/tenx/config` (`TENX_CONFIG`) and its modules at `/opt/tenx-edge/lib/app/modules` (`TENX_MODULES`). `E103_CONFIG_DIR` and `E103_MODULES_DIR` mount host directories read-only over them, so a candidate fix can be tested on the same image. `run.json` records the image ID and each directory's git commit.

In the shipped modules, the Fluent Bit input takes the event's source from the Forward tag (`pipelines/run/modules/input/forwarder/fluentbit/stream.yaml`, `sourcePattern: \"tag\":\"(.*?)\"`). The group step's flush timeout counts per source (`pipelines/run/units/transform/group/unit.yaml`). The hot-tier sender gave every container the tag `app.replay`.

## Cases

`send.py` uses `pack` and `Sender` from `elastic-hot-tier-budget/rig/forward_send.py`. Every record carries `container_name`, `container_id`, `source`, `log` and `seq`. Every line ends with the token `e103id=<seq>`, which sits inside the JSON on the jaeger line. Each case has its own container names, and cases are 10 s apart. Cases a to d send every container under the tag `app.replay`, the way the hot-tier sender did.

- **a.** orders logs an ERROR head. Then billing's timestamped INFO lines (1 to 3) arrive, and then orders' stack trace (3 to 8 lines of `\tat ...`, `Caused by: ...` and `\t... N more`).
- **b.** jaeger logs its JSON line. kafka's four startup lines from the hot-tier run follow (no timestamp, no level), then kafka's own timestamped INFO line.
- **c.** orders and payments are both partway through a stack trace. orders' head and two frames go out, then payments' head, then the remaining frames of both, alternating.
- **d.** Control with one container. orders sends a head and its stack trace, then 0 to 2 INFO lines.
- **e.** Cases a, b and c in rotation, with one tag per container (`docker.<id12>`, the fluentd driver's default tag).

Each case sends 500 episodes back to back. Lines within an episode go out with no sleep between them, and episodes are 1 ms apart. Twelve paused episodes are spread through each case, with pauses of 1, 2, 3, 4, 5 and 6 s, twice each. The pause comes right after the first container's head, and in case c after orders' second frame. The full run sends 22,557 lines in 6,461 events. `groupFlushTimeout` is 5 s, and on a forwarder input a batch reaches the group step up to about 2 s after its line.

## Scoring

`score.py <results>/data` splits each returned record's `log` on `"\n"` and matches every line to the line sent by its token. It reports the following, per case and in total:

- records returned and lines returned
- cross-container records: records whose lines came from more than one sender container
- lines missing and lines duplicated
- stack-trace events returned whole: the head and every continuation line in one record that holds nothing else
- cross-container records by the pause in their episode
- records returned under the wrong tag: Fluent Bit stores the tag a record came back under as `_fb_tag`, and the scorer checks it equals `tenx.` followed by the tag its first line was sent under

It exits 1 when there is any cross-container record, missing line, duplicated line or wrong tag, and 0 otherwise.

`score.py --self-test` builds three inputs. A clean input must pass. The README's shape (a jaeger record holding kafka's banner lines) must fail, and so must a record returned under the wrong tag. All three verdicts came out as expected. On the full manifest, a simulated grouping in arrival order per tag gives 1,536 cross-container records and exit 1. A simulated grouping per container gives 0 and exit 0.

## Running

Docker must have no other rig running: `run.sh up` refuses to start when any container is up other than `e103-*` and `census-ch`. The rig publishes no host port. A run takes about 5 minutes.

```
./run.sh all                       # 1.1.150 as shipped, results in results/shipped-1.1.150/
./run.sh extract /path/to/e103-fix # the image's own config and modules, to patch
E103_CONFIG_DIR=/path/to/e103-fix/config E103_MODULES_DIR=/path/to/e103-fix/modules E103_LABEL=fix ./run.sh all
E103_IMAGE=local/edge-10x:e103 E103_JAVA_HEAP=320M E103_LABEL=fix-1.1.151 ./run.sh all   # another image
```

`E103_JAVA_HEAP` sets `TENX_JAVA_HEAP` for an image that runs the engine jar on a JVM, so the heap fits the 512 MB limit.

`run.sh all` starts the containers with `docker run -d --name e103-*`, sends, waits for the returned records, saves logs and Fluent Bit's counters, scores, gzips the data and removes the containers and the network (`docker rm -f -v`).

## Result on 1.1.150

Run 2026-10-25 from 22:50 to 22:55 UTC. Fluent Bit did not yet store the returned tag, so this run has no tag check. Results are in `results/shipped-1.1.150/`: `run.json` holds the image ID and launch, and `data/` holds the lines sent, the records Fluent Bit received and returned, and `score.json`.

**Verdict: FAIL, with 1,533 cross-container records.** Fluent Bit took in 22,557 records, forwarded 22,557 to the Receiver and wrote 5,836 returned records. One of those is the Receiver's own connect message.

| Case | Lines sent | Records | Lines returned | Cross-container records | Lines missing | Lines duplicated | Stack traces whole |
|---|---:|---:|---:|---:|---:|---:|---:|
| a | 4,428 | 1,554 | 4,428 | 512 | 0 | 0 | 0 of 512 |
| b | 3,072 | 1,036 | 3,072 | 509 | 0 | 0 | none sent |
| c | 6,602 | 1,024 | 6,602 | 512 | 0 | 0 | 0 of 1,024 |
| d | 3,781 | 1,027 | 3,781 | 0 | 0 | 0 | 509 of 512 |
| e | 4,674 | 1,194 | 4,674 | 0 | 0 | 0 | 508 of 511 |
| Total | 22,557 | 5,836 | 22,557 | 1,533 | 0 | 0 | |

In cases a and c, every episode produced one cross-container record, paused or not. In case b, 509 of 512 episodes did. The three that did not were the two 6 s pauses and one 5 s pause, where the jaeger record was sealed before kafka's lines arrived. Case e sends the same three patterns with one tag per container and returns no cross-container record, so the cross-container records follow the shared tag.

**Example from case b, the hot-tier shape.** The record with seq 4429 is filed under b-jaeger. It holds seq 4429 (b-jaeger, the JSON line) and seq 4430 to 4433 (b-kafka: `===> User`, `uid=1000(appuser) ...`, `===> Setting default values ...` and `===> Configuring ...`). All five lines were sent under the tag `app.replay`.

Six stack traces in cases d and e came back split, three in each case. All six were in episodes paused 5 or 6 s after the head, and each came back as 4 to 7 records.

## Result with the E103 fix

Run 2026-10-25 from 23:38 to 23:43 UTC. Results are in `results/fix-1.1.151/`.

The fix is engine commit `bc9ff152dad46a78b16ef2fdfe8864a3c82725c6` (log-10x/engine, branch `fix/e103-sequence-key`: "Key an input's open group by its source and sequence values"). It ships with modules commit `a35b44a94bb80f3ce1a9d49260d5424f14423f8e` (log-10x/modules, branch `fix/e103-sequence-key`: "Forwarder inputs group by container and stream within a tag"). The image `local/edge-10x:e103` (`sha256:70b27f0700f35c1a5382b02411174b99b77f2e02f0bef4882768ea2033d8d7ca`) is the 1.1.150 image with the engine jar from that commit and those modules at `/opt/tenx-edge/lib/app/modules`. Its modules match the modules commit file for file. The jar runs on a JVM, so the Receiver had `TENX_JAVA_HEAP=320M`. The arguments, other environment and limits are the same as the 1.1.150 run.

**Verdict: PASS.** Fluent Bit took in 22,557 records, forwarded 22,557 and wrote 5,869 returned records, one of them the Receiver's connect message. All 5,868 records holding sent lines came back under `tenx.` followed by their sent tag: 4,674 under `tenx.app.replay` and 1,194 under `tenx.docker.<id12>`.

| Case | Lines sent | Records (1.1.150) | Records (fix) | Lines returned | Cross-container records | Lines missing | Lines duplicated | Wrong tag | Stack traces whole (1.1.150) | Stack traces whole (fix) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a | 4,428 | 1,554 | 1,566 | 4,428 | 0 | 0 | 0 | 0 | 0 of 512 | 508 of 512 |
| b | 3,072 | 1,036 | 1,044 | 3,072 | 0 | 0 | 0 | 0 | none sent | none sent |
| c | 6,602 | 1,024 | 1,037 | 6,602 | 0 | 0 | 0 | 0 | 0 of 1,024 | 1,021 of 1,024 |
| d | 3,781 | 1,027 | 1,027 | 3,781 | 0 | 0 | 0 | 0 | 509 of 512 | 509 of 512 |
| e | 4,674 | 1,194 | 1,194 | 4,674 | 0 | 0 | 0 | 0 | 508 of 511 | 508 of 511 |
| Total | 22,557 | 5,836 | 5,869 | 22,557 | 0 | 0 | 0 | 0 | 1,017 | 2,546 |

Every stack trace returned whole on 1.1.150 is returned whole with the fix. Cases d and e split the same six traces on both runs, all in episodes paused 5 or 6 s.

In cases a and c, no trace was whole on 1.1.150, so these splits have nothing to compare against. Four of the seven splits there were in episodes paused 5 or 6 s. The lines sent before the pause came back together, and each continuation line sent after it came back as a one-line record. The other three were in case a episodes with no pause:

- Record seq 1033 (a-orders, episode 120) also holds seq 1557. That line is the last frame of a-orders' trace in episode 179, sent 2.2 s later. The rest of episode 179's trace is in a record of its own.
- Episode 508's frames, seq 4397 to 4401, came back as five one-line records. All five were returned before the record holding their head, seq 4394.

These three keep lines within one container, but not in that container's order.
