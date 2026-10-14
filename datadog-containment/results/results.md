# Containment demo: OpenTelemetry demo 3.1.0 with a fleet-default per-pattern cap

## What ran

- OpenTelemetry demo at tag 3.1.0 (commit dedc0178), `compose.yaml` + `compose.full.yaml`
  (core services plus Kafka, accounting and fraud-detection), no observability stack, one
  Docker Desktop host (8 GB VM, 8 CPUs).
- Every demo container's stdout and stderr goes through the Docker `fluentd` log driver to
  Fluent Bit 4.2, which keeps a raw copy, hands each record to the log10x Receiver
  (`log10x/edge-10x:1.1.140`, config repo 657913c, modules repo 7551b9ff, patched as in
  `rig/engine/PATCHES.diff`) over Fluent Forward, takes the record back and writes it to
  `pass.jsonl` or `offload.jsonl` by the `routeState` the Receiver stamps.
- Receiver settings: `rateReceiverAbsoluteCap <fleet default>`, `rateReceiverMinSharePercent 0`,
  `rateReceiverWarmupMs 0`, `rateReceiverBaselineCount 5`, `rateReceiverMinRetentionThreshold 0`,
  severity floors all 0, `rateReceiverDefaultAction offload` (new option, see the patch),
  `rateReceiverContainerField container_name`, `symbolMessageHashField tenx_hash`,
  `outputOffload=true`. The 4-minute regulator window is the shipped default.
- The flagd-ui scheduler (demo 3.1.0) drove the incidents: seed SEED_PLACEHOLDER, interval
  900 s, hold 240 to 480 s, one flag at a time, flags kafkaQueueProblems (on),
  cartFailure (100%), paymentFailure (100%), recommendationCacheFailure (on),
  loadGeneratorFloodHomepage (on), emailMemoryLeak (1000x).

## Timeline (UTC, 2026-10-14)

| Time | Event |
|---|---|
| 12:50:40 | Fluent Bit and Receiver up (cap 0), demo containers starting |
| 12:52:49 | all 23 demo containers healthy |
| 12:54:22 | quiet run starts (scheduler off) |
| 13:16:29 | disk guard: free space confirmed under 4.5 GB (4400 MB); scheduler stopped, logs snapshotted, `docker compose down` (finished 13:17:27). Quiet run ends here: 5 full 4-minute windows. The churn was another benchmark on the same Mac writing a 257 MB file and several session scratchpads; Docker's disk stayed flat and the rig's own files were 9 MB. |
| 13:19:48 | Receiver restarted with the fleet default (`rateReceiverAbsoluteCap 246736`); demo restarted, no images pulled |
| 13:21:33 | first `compose up` exits 1: kafka missed its health window on the loaded host (its JVM took 3 minutes to start); six Kafka-dependent containers left in Created |
| 13:25:34 | kafka healthy; second `compose up` starts the rest (13:26:15), all 25 containers healthy |
| SCHED_START_PLACEHOLDER | scheduler started: seed 20261014, interval 900 s, hold 240 to 480 s, one flag at a time |
| RUN_END_PLACEHOLDER | run ends |

## How the numbers are measured

- A pattern is the Receiver's `tenx_hash` (the hash of `message_pattern`); a container is
  the Docker container name; severity is the Receiver's `severity_level`.
- Bytes are the size of the record as the Receiver received it (compact JSON of `log`,
  `fb_ts`, `source`, `container_name`, `container_id`), which is the measure the regulator
  counts: in a smoke test the Receiver's own `summaryBytes / summaryVolume` matched that
  size to the byte (147, 152, 231). Log-text bytes (the `log` field alone) are given next
  to it.
- Fleet default: in the quiet run (scheduler off) every (container, pattern, 4-minute
  window) cell's bytes were summed; the cap is 2 x the largest cell.
- First noisy minute: the first minute after a flag turned on in which some pattern of a
  container had at least 5 events and at least 5 x its per-minute rate over the 10 minutes
  before the flag (the quiet-run rate when the flag fired within 10 minutes of the
  scheduler start).
- First held line: the first `offload` record of that container after the flag turned on.
- Events held and kept, bytes never sent: `offload` and `pass` records of that container
  from the flag's on time to its off time plus one 4-minute window.
- False holds: `offload` records while no flag was active (outside every activation's
  on-to-off-plus-one-window span) during the scheduled run.
- Delivery: raw lines received by Fluent Bit against the lines the Receiver returned
  (a returned record can cover several raw lines when the Receiver joins a multi-line
  event).

## Fleet default (quiet run, scheduler off)

Quiet run 12:54:22 to 13:16:29 UTC on 2026-10-14, 5 full 4-minute windows (the run was cut at 13:16:29 by the disk floor; the partial sixth window is not counted). 7108 events, 15 containers, 48 (container, pattern) pairs, 197 cells.

| Bytes per pattern per container per 4-minute window | Value |
|---|---|
| max | 123,368 |
| p99 | 123,362 |
| p90 | 24,127 |
| median | 5,316 |
| **fleet default (cap = 2 x max)** | **246,736 bytes** |

Largest cell per container (bytes in one 4-minute window):

| container | pattern | events | bytes | sample |
|---|---|---|---|---|
| otel-collector | KG8Fq0QFuoY | 240 | 123,368 | `2026-10-14T12:54:22.346Z info Logs {"resource": {"service.instance.id": "fede5d4` |
| frontend | INl44sUgFeY | 230 | 110,771 | `{"level":30,"time":1791982463499,"pid":1,"hostname":"75896fbfdd3e","trace_id":"a` |
| cart | YZplfQ4a1Xw | 89 | 24,431 | `info: cart.cartstore.ValkeyCartStore[1662118147]
      GetCartAsync called with ` |
| accounting | -FtZD9XArpU | 17 | 15,411 | `info: Accounting.Consumer[722003269]
      Order details: { "orderId": "7a5ee600` |
| recommendation | bzLB1zZCTIw | 30 | 14,280 | `2026-10-14 12:54:22,532 INFO [main] [recommendation_server.py:47] [trace_id=a724` |
| telemetry-docs | zxRYTKQNyBY | 47 | 11,703 | `::1 - - [14/Oct/2026:12:54:23 +0000] "GET / HTTP/1.1" 200 29066 "-" "Wget"` |
| payment | 9WbTsopbiXk | 17 | 11,297 | `{"level":"info","time":1791982506513,"pid":1,"hostname":"37f614d3c647","trace_id` |
| astronomy-db | oUkuI8QT6s8 | 46 | 10,948 | `2026-10-14 12:54:25.364 UTC [439] FATAL:  role "root" does not exist` |
| fraud-detection | GKfNbCrpxxI | 17 | 6,647 | `2026-10-14 12:55:06 - fraud-detection - Consumed record with orderId: 7a5ee600-c` |
| ad | xHrytxJfUdw | 20 | 6,528 | `2026-10-14 12:54:26 - oteldemo.AdService - Targeted ad request received for [tel` |
| kafka | pFokWfyJRLU | 12 | 6,088 | `[2026-10-14 12:54:43,491] INFO [UnifiedLog partition=__cluster_metadata-0, dir=/` |
| email | 1zhBPd1E9Bc | 17 | 5,746 | `172.22.0.21 - - [14/Oct/2026:12:55:06 +0000] "POST /send_order_confirmation HTTP` |
| quote | c4yR2F2cVfk | 17 | 3,774 | `[2026-10-14 12:55:06+00:00] "POST /getquote HTTP/1.1" 200 6 ` |
| product-catalog | HEB27OwRkTA | 9 | 2,598 | `2026/10/14 13:02:59 traces export: exporter export timeout: rpc error: code = De` |
| valkey-cart | kodKFTs6ZHw | 1 | 255 | `425:C 14 Oct 2026 12:56:59.567 * Fork CoW for RDB: current 0 MB, peak 0 MB, aver` |

The cap is set by otel-collector: with no observability layer the collector's debug exporter echoes every received batch to stdout as one `info Logs {...}` or `info Traces {...}` line, about 240 lines of 500 bytes per window. frontend's pino JSON request log is next at about 94 KB per window.

INCIDENT_TABLES_PLACEHOLDER

## Deviations from the brief

- Demo scope: `compose.yaml` + `compose.full.yaml` (core plus Kafka, accounting,
  fraud-detection). The observability layer (`compose.observability.yaml`: Jaeger, Grafana,
  Prometheus, OpenSearch, OpAMP) and the agent layer (`compose.agent.yaml`) were not run:
  the Docker VM has 8 GB shared with another chat's Splunk and verification rig, and the
  Mac had 12 GB of disk free at the start with a 5 GB floor. With no observability layer
  the collector's base configuration exports to its debug exporter, which echoes every
  batch to stdout, so otel-collector is the chattiest container in the quiet run.
- aiRunawayAgent was not scheduled: it acts on the agent service, which is in the agent
  layer. Six flags were scheduled (see "What ran").
- Load generator: the official `3.1.0-load-generator` image (526 MB compressed, Chromium
  inside; the other demo images expand 3x to 5x on disk) would have taken free disk under
  the 5 GB floor. The rig builds the demo's own `src/load-generator` (same base image, same
  hash-pinned requirements, same `locustfile.py` and `people.json`) without the
  `playwright install chromium` step, and runs it with `LOCUST_BROWSER_TRAFFIC_ENABLED=false`
  (`rig/load-generator/Dockerfile`). HTTP load is the demo's own; browser-user traffic is off.
- Two wire additions on the Receiver beyond the brief's settings, both plain launch options:
  `outputEncodeField fullText("tenx_hash","routeState","message_pattern","severity_level")`
  puts the pattern text and the severity on every returned record (the brief asks for the
  pattern and severity of what was held), and `@run/output/metric/log` with the copied
  metric-log config stepped from 1 s to 60 s gives the Receiver's own per-pattern counters
  in `receiver.log` as a cross-check of the files.
- Severity floors: `rateReceiverSeverityFloors` is a list option; the floors were set to 0
  in the copied `pipelines/run/receive/rate/config.yaml` rather than on the command line.
- The engine refuses a field assignment inside the regulator getter (`field: 'tenx_bytes'
  can not be assigned within function: 'shouldRetainEventWithCap'`), so the regulator's
  byte measure was reproduced outside the engine; the smoke test showed the Receiver's own
  `summaryBytes` per event equals the record size as received, to the byte.
- Fluent Bit to Receiver transport: the Receiver's forward input serves one client
  connection at a time and Fluent Bit's forward output opens several by default; an
  11-hour smoke test lost 23% of records to connection churn. The rig pins the forward
  output to one worker and one keepalive connection (`Workers 1`,
  `net.max_worker_connections 1`), after which a 820-record smoke test returned 820.
- The flagd-ui scheduler has no HTTP endpoint; `rig/scheduler.sh` calls
  `FlagdUi.Scheduler.start_schedule/1` through the release's `rpc` entry point, the same
  call the Scheduler page makes. Its log lines are read from raw.jsonl (flagd-ui logs
  through the same driver as every other container).
- Disk: the dangling `log10x/pipeline-10x` image (914 MB) was removed once no container
  used it; Docker's dual-logging cache is off for the demo containers
  (`cache-disabled`), so container logs exist only in the three rig files; a disk guard
  (`rig/disk-guard.sh`) logged free space every 5 minutes and would have stopped the demo
  cleanly under 4.5 GB.
- Grouping on ANSI-coloured output: shipping (Rust tracing, colour codes on) returned its
  first 7 INFO lines as events with no severity, then its first ERROR line opened a group
  that absorbed every following line (` INFO` padded to five characters is not matched as
  a level at the start of the word, so those lines have no recognised head). The group
  closes only when the source goes idle, so shipping's lines return in large batches
  under the ERROR line's pattern. No flag targets shipping. The raw path was left as the
  demo produces it.

