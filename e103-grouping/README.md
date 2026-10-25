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

It exits 1 when there is any cross-container record, missing line or duplicated line, and 0 otherwise.

`score.py --self-test` builds a clean input, which must pass, and the README's shape (a jaeger record holding kafka's banner lines), which must fail. Both verdicts came out as expected. On the full manifest, a simulated grouping in arrival order per tag gives 1,536 cross-container records and exit 1. A simulated grouping per container gives 0 and exit 0.

## Running

Docker must have no other rig running: `run.sh up` refuses to start when any container not named `e103-*` is up. A run takes about 6 minutes.

```
./run.sh all                       # 1.1.150 as shipped, results in results/shipped-1.1.150/
./run.sh extract /path/to/e103-fix # the image's own config and modules, to patch
E103_CONFIG_DIR=/path/to/e103-fix/config E103_MODULES_DIR=/path/to/e103-fix/modules E103_LABEL=fix ./run.sh all
```

`run.sh all` starts the containers with `docker run -d --name e103-*`, sends, waits for the returned records, saves logs and Fluent Bit's counters, scores, gzips the data and removes the containers and the network (`docker rm -f -v`).

## Result on 1.1.150

Run pending.
