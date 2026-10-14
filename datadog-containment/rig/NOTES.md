# Rig notes (working log, facts only)

## Released engine, MCP values (2026-10-14, from 20:20 UTC)

### Sources
- Receiver `log10x/edge-10x:1.1.141@sha256:45157d0bdf506615aa015db7b8b7251ae39be5f4330233d2d2d659c69d1f93d1`,
  its own config and modules (no mounts). Its `rate-object-cap.js` reads
  `rateReceiverDefaultAction`; the rate config keys the cap on `k8sContainerNameField`, which
  the fluentK8s extractor fills from `kubernetes.container_name`.
- log10x-mcp 1.30.54 from npm (tarball sha256 98e90780...bb5aa). Its `build/` matches a build
  of the merged #266 branch (f293590) byte for byte on fleet-default-install.js,
  fleet-default.js, poc-from-local.js, build-report-data.js, reporter-forwarders.js and
  runtime-image.js. Dependencies linked from that branch's install (same dependency list).
- No Datadog credentials in the environment, so the POC's dependency check reports that it did
  not run.

### Record shape (why the `kubernetes` map)
- The MCP's file mode takes the service from `kubernetes.container_name` (or Datadog's
  `service`); a top-level `container_name` is not read. On the 1.1.140 run's Docker-shaped
  capture every pattern came back `(unattributed)`, and `fleet_default` needs a kept
  statement in a named container, so it would come back `computed: false`.
- The released Receiver keys the cap on the same field through its fluentK8s extractor; with no
  container the key is `__node__`.
- Fluent Bit's ingest filter therefore moves `container_name` and `container_id` into
  `kubernetes: {container_name, docker_id}`. Both the MCP and the Receiver then find the
  container with no extra option.

### Dry run (20:26 UTC, the 1.1.140 quiet capture reshaped, 8,347 lines)
- `poc_from_local` with `fleet_default {headroom 2, action offload, error_floor 0.5}`:
  `computed: true`, cap 10,249 bytes per window per node, baseline 5,124.7 (otel-collector
  `Error scraping metrics`); caps.csv and actions.csv with 11 container rows, all `tier_down`.
- The baseline is the kept statement's bytes over the whole capture scaled to one 240 s
  window (an average, not the largest window), in the MCP's byte measure.

### Smoke 4 (20:31 to 20:33 UTC, three emitters, the dry run's values)
- Fluent Bit on 172.28.0.250, no published port; the Docker log driver reached it at that
  address. `fluentd-sub-second-precision` gives `fb_ts` millisecond resolution; the return
  filter's `rb_ts` (LuaJIT `gettimeofday`) likewise.
- `cart` (caps.csv row, cap 1, tier_down): 5 pass, 295 tier_down. An unlisted container at
  263 bytes a record: 38 pass (9,994 bytes, within 10,249), 262 offload. An unlisted ERROR
  emitter: 221 pass, 179 offload of 400, about 41 under the cap and half of the rest.
- The regulator counts the compact JSON of the record as it arrives, `kubernetes` map
  included: the 39th record would have made 10,257 bytes and was the first offload.
- The cap file's staleness check is advisory (module.yaml: entries continue to apply).

### Disk and memory at the start
- 20:35 UTC: 4,989 MB free, swap 8.2 GB used of 9 GB (a ninth 1 GB swap file was created at
  16:30 local during the dry run and smoke). The Docker VM process held its full 8 GB.
  20:45: 8,884 MB free, swap 3.8 GB.
- Removed the four anonymous volumes the 13:53 rig run left (67 MB); the two linked to
  obj30-splunk stay.

### Previous run's captures
- While archiving, the 14:07 to 17:35 run's `raw.jsonl` and `pass.jsonl` were overwritten by a
  `mv` of the tracked morning gzips onto the same names, after the originals had been
  removed. No local snapshot exists. Its `offload.jsonl` is kept
  (`results/data/run-1.1.140/scheduled-run-offload.jsonl.gz`); its derived tables remain in
  git history (a66a7b9).

### Startup
- 20:35:53 Receiver ready (quiet values). The first `compose up` exited 1: kafka missed its
  health window (its JVM was still loading the OpenTelemetry agent; obj30-splunk at about
  300% CPU). `run.sh up` waited for kafka healthy and ran it again: demo up 20:46:45, healthy
  20:47:17.

### Quiet run, POC, values (20:49:17 to 21:12:28 UTC)
- Quiet run 20:49:17 to 21:11:20 (two minutes after demo healthy; 22 minutes): 9,054 raw
  lines, 7,979 returned records, none held, 16 containers, 5 full 4-minute windows.
- POC on those 9,054 lines (`results/planner`): `met: true` at 70.3%, 28 planned and 19 kept
  statements, every planned statement attributed (`unattributed_planned: 0`), span 1,321 s.
  Fleet default `computed: true`: 10,288 bytes per window per node, 2 x 5,144.1 (otel-collector
  `Error scraping metrics`), offload, error floor 0.5. caps.csv and actions.csv: 11 rows,
  every one `tier_down`; cap 1 (every statement) for accounting, cart, fraud-detection,
  recommendation and telemetry-docs.
- The MCP's baseline counts the unwrapped payload (the POC's note: "analysed bytes count the
  unwrapped payload"). The same statement's records in the Receiver's measure averaged 7,103
  bytes per quiet window (max 7,811), so the cap is 1.45 times that statement's average, not 2.
- Quiet cells of containers with no row, against 10,288: one pattern over it, astronomy-db
  `FATAL: role "root" does not exist` (11,750 bytes, 47 lines in one window); next is email
  `POST /send_order_confirmation` at 5,950.
- 21:11:55 Receiver relaunched from `results/values-fleet` (no launch warning beyond the
  evaluation licence; cap file loaded; Forward client connected 21:11:55.510).
- 21:12:28 scheduler started (`run-unattended.sh`, detached), planned end 22:27:28; disk guard
  and hard stop detached since 20:35.
- `results/planner/poc-envelope.json` is the POC's result as returned, except that the six em
  dashes in its markdown text are written as ", " in sentences and "-" in empty table cells.
- Coordinator, 21:13: the record shape and the plan rows plus fleet default are the
  customer's path; the cap stays as generated.

### Scheduled run (21:12:28 to 22:29:45 UTC)
- Eight activations: cartFailure, kafkaQueueProblems (21:23:56, the second, as with this seed
  before), paymentFailure, emailMemoryLeak twice, recommendationCacheFailure,
  loadGeneratorFloodHomepage, recommendationCacheFailure (reverted at 259 of 345 s by the stop).
- The stop ran unattended: `planned_end` 22:27:37, scheduler stopped 22:27:40, `run_end`
  22:27:44, demo down 22:29:45. The disk guard and the hard stop then exited on `run_end`.
  The hard stop's first deadline (21:35:40) was moved to the planned end when the scheduler
  started and never fired.
- Disk: lowest reading 5,553 MB free (21:40:52), no floor warning. `docker stats` read the
  Receiver at under 1% of a CPU at 20:43, 21:13 and 21:25 (the last during the kafka flood),
  against its 0.5 CPU limit.
- Removed the four anonymous volumes this run's demo left (created 20:35:54).
- The window phase comes from the Forward client's connection to the fleet Receiver
  (21:11:55.511, 235.5 s past a multiple of 240 s). A replay of the cap rule on those windows,
  keyed by `message_pattern` per container as the regulator keys it, matches the Receiver on
  all but 297 under-cap holds and 279 over-cap passes of levels with a 0 floor, out of 40,575.

## Earlier run: edge-10x 1.1.140 with patched config and modules (2026-10-14, 01:25 to 17:36 UTC)

### Sources
See `engine/SOURCES.txt`: config origin/main 657913c, modules origin/main 7551b9ff,
engine image log10x/edge-10x:1.1.140 (sha256:5c4159d5...), demo tag 3.1.0 (dedc0178).
The image's own copies under /etc/tenx/config and /opt/tenx-edge/lib/app/modules match
origin/main (md5 of rate-object-cap.js, rate-object-lookup-cap.js, forwarder/config.yaml,
rate/module.yaml all equal).

### Patches (engine/PATCHES.diff)
1. Both cap-variant scripts: `var action = TenXEnv.get("rateReceiverDefaultAction", "pass")`.
2. modules rate module.yaml: option `rateReceiverDefaultAction` (string, default pass).
3. Copied rate config.yaml: all severity floors 0 (list option; set in the file).

### Verified by smoke test 1 (2026-10-14 01:25 to 01:30 UTC, dummy inputs, no demo)
- The engine launches with TENX_CONFIG=rig copy, TENX_MODULES=rig copy, the patched
  option accepted on the CLI: `rateReceiverDefaultAction offload`.
- CLI form that worked: `@run/input/forwarder/fluentbit @apps/receiver <name> <value> ...`
  (bare name value pairs after the app, no dashes).
- `outputOffload=true` passed as a container env var (it is read with TenXEnv.get and is
  not a declared option).
- Return record shape on the Fluent Bit side (forward input on 24225, Tag_Prefix tenx.):
  `{"date":<log timestamp>,"fb_ts":"<ingest ts>","source":"stdout","container_name":"fast",
   "log":"...","tenx_hash":"bZ448WTyxpA","routeState":"offload"}`.
  Every returned record carries routeState: "pass" under the cap, "offload" over it.
- One extra record arrives on the return path at connect time:
  `{"date":...,"message":"10x engine connected to fb-smoke:24225"}` (no container_name).
- `rateReceiverContainerField container_name` keys the cap on the top-level record field.
- Built-in evaluation licence, airgapped (TENX_AIRGAPPED=true), no network calls.

### Measured by the 11-hour smoke (01:31 to 12:31 UTC, three dummy sources)
- Returned counts were 77% of the sent counts for every source (fast 5/s: 153,151 of
  ~199,000; 1/s sources: ~30,580 of ~39,550 each). The loss is uniform, not per source.
- Fluent Bit logged 117k retry warnings in 10 h: `no upstream connections available` and
  `connection #N to tcp://engine:24224 timed out after 10 seconds`. Connection numbers
  climbed past 150. The engine logged `client disconnected, waiting for new connection`
  about every 11 minutes (Fluent Bit keepalive recycle at 2000 uses).
- Reading: the engine's forward input serves one client connection at a time; Fluent Bit's
  forward output opened several. Fix under test: single worker, one keepalive connection.

### Verified by smoke test 2 (12:34 to 12:38 UTC, finite inputs)
- Fluent Bit forward output pinned to one worker and one keepalive connection
  (`Workers 1`, `net.max_worker_connections 1`, `net.keepalive_max_recycle 100000000`,
  `net.keepalive_idle_timeout 300`): 820 records sent (dummy `Samples` 600 + 120, plus 100
  lines from a container on the Docker fluentd log driver), 820 returned, 0 retry warnings.
  The 23% loss of the 11-hour smoke is gone.
- Docker Desktop: a container started with `--log-driver fluentd --log-opt
  fluentd-address=localhost:24224 --log-opt tag=app.{{.Name}}` reaches a Fluent Bit container
  that publishes 24224. Records carry `container_id`, `container_name` (leading slash,
  stripped by the lua filter), `source`, `log`.
- The engine's metric log (`@run/output/metric/log`) shows per-pattern counters with
  `message_pattern`, `severity_level` (INFO/WARN classified from the line), `routeState`,
  `tenx_hash`; `k8s_container` and `tenx_user_service` stay empty with this input (the
  fluentK8s extractor reads `kubernetes.container_name`, which the Docker driver does not
  send), so the cap is keyed with `rateReceiverContainerField container_name`.
- Smoke 1 keying evidence: two sources with the same line text, 5/s and 1/s, cap 2000
  bytes: the 1/s source stayed `pass` for its first 200 s while the 5/s source was
  `offload` from its 5th event on, so the counter is per (pattern, container).

### Verified by smoke test 3 (12:39 to 12:45 UTC)
- `outputEncodeField fullText("tenx_hash","routeState","message_pattern","severity_level")`
  passed on the CLI after the app is accepted and puts all four fields on every returned
  record. 821 returned for 820 sent, 0 warnings.
- Assigning a field inside the regulator getter is refused by the engine:
  `field: 'tenx_bytes' can not be assigned within function: 'shouldRetainEventWithCap'.
  Fields can only be assigned during object/class initialization`. The patch was reverted;
  the byte measure is reproduced outside the engine instead (next point).
- The engine's `all_events` / `emitted_events` `summaryBytes` divided by `summaryVolume`
  equals the size of the record as received, to the byte: 147 (fast), 152 (slow), 231
  (lg-smoke), where the record is the compact JSON of the fields Fluent Bit sent
  (`log`, `fb_ts`, `source`, `container_name`, and `container_id` for the Docker driver).
  analyze.py uses that measure for the fleet-default cells.
- A line starting with a timestamp then `ERROR` is classified `severity_level=ERROR`;
  `INFO` and `WARN` lines likewise.

### Disk
- The dangling `log10x/pipeline-10x` image (914 MB) was removed at 12:43 UTC once no
  container referenced it (the two containers that used it overnight were gone).
- Docker Desktop: DiskSizeMiB 61035, DiskTRIM on; the VM had 34 GB free inside while
  macOS `df` showed 5.6 GB; TRIM returned the deleted image within minutes (6.8 GB).
- The official `3.1.0-load-generator` image (526 MB compressed; the other demo images
  expand 3x to 5x on disk) was not pulled: the rig builds the demo's own load generator
  without the Chromium install instead (`load-generator/Dockerfile`).

### Run facts (2026-10-14, demo up at 12:50 UTC)
- The Docker fluentd driver stamps records at whole seconds, so `fb_ts` has 1 s resolution
  (`1791982255.000`). Per-minute and per-window measures are unaffected.
- First records: raw.jsonl carries `container_name`, `container_id`, `source`, `fb_ts`,
  `log`; pass.jsonl adds `tenx_hash`, `message_pattern`, `routeState` and, when the line
  has a level, `severity_level`. The Receiver's connect message lands in pass.jsonl once.
- Fluent Bit logged one retry at 12:50:56 (Receiver not yet connected), nothing after.
- Memory with 19 demo containers up: about 1.7 GB for the demo, Receiver 166 MB, Fluent
  Bit 9 MB, beside another chat's Splunk (1.6 GB) and tenx-dda (240 MB).
- Envoy (frontend-proxy) ships its access log to the OTel collector over gRPC
  (`envoy.access_loggers.open_telemetry` in src/frontend-proxy/envoy.tmpl.yaml), so its
  stdout carries only startup and admin lines. The collector's debug exporter echoes the
  telemetry it receives to stdout, which makes otel-collector one of the chattiest
  containers in the base demo configuration (369 lines in a 2-minute sample at startup).
- The load generator (locust `--skip-log-setup`) writes nothing to stdout; traffic is
  visible through ad, cart, payment, email, quote and shipping lines instead.
- Multi-line grouping: 6 returned kafka records covered 1,205 raw lines (the startup
  config dump), so delivery is measured in raw lines covered, not records.
- Quiet run marked at 12:55 UTC, 24 minutes (6 full 4-minute windows), scheduler off.

### Disk rules in force from 13:05 UTC (coordinator)
- No further image pulls. `disk-guard.sh` logs free space every 5 minutes to
  results/disk.log, gzip-rotates raw.jsonl past 1 GB, and under 4.5 GB free runs
  `run.sh down` (scheduler stop, log snapshot, compose down, images kept) and marks
  `disk_stop` in the timeline. Another agent's verification rig shares the host.

### Open question under test (13:05 UTC)
- shipping: the Receiver returned its first 7 lines (INFO, 12:50:56) and nothing after its
  first ERROR line at 12:50:57 (`opentelemetry_sdk: name="BatchLogProcessor.ExportError"
  error="Operation failed: HTTP export failed: network error"`), while 30+ later INFO
  lines arrived in raw.jsonl. Every other container returns within seconds of its raw
  lines. A replay of those exact lines through a standalone Receiver is running.
- Answer (replay, 13:07 UTC, 30 shipping lines through a standalone Receiver): the first 7
  INFO lines came back as 7 events with no `severity_level` (the Rust tracing format pads
  the level to five characters, so the line reads `<ESC>[32m INFO` and the level term does
  not match at the start of the word; `ERROR` is five characters and matches). The ERROR
  line came back as ONE event of 23 lines: it opened a group and every following line,
  having no recognised head, was appended to it. The group flushed once the sender went
  idle. In the live rig shipping keeps logging, so the group stays open (the shipped
  group transform has `maxSize 20000` and `flushTimeout 5s`; the timeout did not close
  it while lines kept arriving) and shipping's returns arrive in large batches with the
  ERROR line's pattern. No flag targets shipping; its lines are excluded from nothing,
  and any shipping hold is reported as what it is. The raw path is left as the demo
  produces it (no ANSI stripping in Fluent Bit).
- Preview on the first 3 full quiet windows (13:09 UTC): 119 cells, max 123,363 bytes
  (otel-collector, the debug exporter's `info Logs {...}` pattern, 240 events in the
  window), p99 122,961, p90 19,320, median 5,200; cap would be 246,726. frontend's pino
  JSON pattern is next at about 94 KB per window.

### Disk stop and restart (13:16 to 13:20 UTC)
- 13:15:29 the guard read 4340 MB, 13:16:29 the confirmation read 4400 MB: `run.sh down`
  ran (scheduler stop 13:16:34, run_end 13:16:39, compose down finished 13:17:27). The
  quiet run therefore covers 12:54:22 to 13:16:29: five full 4-minute windows.
- The disk churn was not the rig's: Docker.raw stayed at 24.1 GB and the rig's data
  files were 9 MB. This session's scratchpad holds 889 MB belonging to another agent's
  rig (`dda/` with three 114 MB engine logs, `node_modules/`); those files are not mine
  to remove. Free space read 5500 MB once that rig's containers were gone.
- Decision: restart the demo straight into the cap phase (images are on disk, nothing
  pulled), fleet default from the five quiet windows, same guard and floor. If the guard
  trips again the run stops there and results.md reports what exists.
- Churn source (13:19 UTC): another chat's benchmark writes
  /Users/talweiss/git/l1x-co/wt-bench-floor/datadog-service-control/runs/full-A-control/routed.jsonl
  (257 MB and growing at that time); five session scratchpads under /private/tmp/claude-501
  hold 173 to 856 MB each. None of it is this rig's. Docker.raw 24,305 MB.
- 13:20 UTC restart: `run.sh up` with RIG_CAP=246736 (Receiver in cap mode from the
  first event), then wait-healthy, a 3-minute settle, then the scheduler.
- 13:21 UTC: the restart's `compose up` exited 1: kafka missed its health window
  (`nc -z kafka 9092`, start_period 10 s, 10 retries at 5 s) because its JVM took about
  three minutes to print its first line under CPU contention (Splunk 180%, ad 160%, kafka
  240% of one core), so compose left checkout, accounting, fraud-detection, frontend,
  frontend-proxy and load-generator in Created. The chain was stopped before its
  `wait-healthy` timeout could start the scheduler on a partial demo. A second chain waits
  for kafka healthy, runs `compose up -d` again, and refuses to start the scheduler while
  any container is Created, Exited, unhealthy or starting. In run 1 kafka was healthy
  within a minute; the difference is host load, not the rig.

### Second disk stop (13:34 to 13:36 UTC)
- Scheduler started 13:29:55 (seed 20261014; first planned activation cartFailure 100%
  for 415 s inside the first 15-minute interval). 13:34:09 the guard read 3489 MB free
  (6612 MB five minutes earlier), 13:35:09 the confirmation read 3478 MB: `run.sh down`
  ran again. No flag had fired yet, so the scheduled run holds no incident. Free space on
  this Mac moved by 3 GB in five minutes twice in 20 minutes, both times while the rig's
  own files grew by under 5 MB and Docker's disk stayed flat; the writer is another chat's
  benchmark under /Users/talweiss/git/l1x-co/wt-bench-floor and its session scratchpads.
- The rig is complete and reproducible: `RIG_CAP=246736 ./run.sh up && ./run.sh
  wait-healthy && SEED=20261014 ./run.sh sched 900 240 480` restarts the scheduled run
  from the images already on disk once the host has room above the floor.

### Correction 1: fleet default from the plan's kept set (13:44 to 13:50 UTC)
- Ruling: the largest statement the PLAN KEEPS, fleet-wide, times 2.
- Planner: log10x-mcp 1.30.49 from npm (= origin/main version; tarball sha256 a0548c7c...),
  deps linked from the cached 1.30.21 npx install (same dependency list except
  @aws-sdk/client-s3, which the planner's import graph does not reach). Engine pinned by
  `LOG10X_TENX_MODE=docker LOG10X_RUNTIME_IMAGE=log10x/edge-10x:1.1.140`; the host's
  /usr/local/bin/tenx is 1.1.45 and auto-detect would have picked it. No licence mint
  (docker mode uses the image's built-in licence).
- Input: the quiet capture (8,347 raw lines, 3.5 MB, 12:54:22 to 13:16:29). Call:
  `poc_from_local {source: file, path, siem: datadog, forwarder: fluent-bit,
  target_percent_reduction: 70}`.
- Output: `met: false`, keep-everything lever tier_down, ceiling 47.5% of the Standard
  index volume; planned (tier_down) KG8Fq0QFuoY, Gl3Gtr_SH5w, PuWB8kkVbfw (otel-collector
  debug exporter Logs/Traces/Metrics) and INl44sUgFeY (frontend API request completed);
  55 kept. Hashes match the Receiver's tenx_hash one for one.
- Every pattern came back `(unattributed)`: the plan's `engine_policy` caps.csv and
  actions.csv are header-only (`unattributed_planned: 4`) even though the file sniffed as
  wrapped JSON and carries `container_name`.
- Largest kept cell: cart YZplfQ4a1Xw (`GetCartAsync called with userId`) 24,431 bytes in
  one window; cap 48,862. Sliding 240 s maximum of any kept pair over the quiet run:
  26,412 bytes, so no kept pattern would have crossed the cap in any window phase.

### Swap and disk (13:47 UTC on)
- Swap on this Mac lives in 1 GB files on /System/Volumes/VM, which shares the APFS
  container with /. At 13:47 swap was 7.5 GB used of 8 GB; at 13:51, 7.9 GB of 9 GB
  (a fifth swap file added); the Docker VM process held 6.2 GB resident with the demo
  down. The guard now logs swap use and the VM volume size with every reading.
- Removed the eight anonymous volumes my demo runs left (132 MB); named volumes untouched.

### Correction 2: rerun (13:52 UTC on)
- `run-scheduled.sh` with RIG_CAP=48862, seed 20261014, interval 600 s, hold 240 to 480 s,
  stop after 4 completed activations plus one window or 75 minutes. Kafka missed its
  health window again (first `compose up` failed, the driver waited for kafka healthy and
  re-ran it); demo healthy 14:01:54; 5-minute settle before the scheduler.
