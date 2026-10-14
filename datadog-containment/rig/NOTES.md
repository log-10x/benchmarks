# Rig notes (working log, facts only)

## Sources
See `engine/SOURCES.txt`: config origin/main 657913c, modules origin/main 7551b9ff,
engine image log10x/edge-10x:1.1.140 (sha256:5c4159d5...), demo tag 3.1.0 (dedc0178).
The image's own copies under /etc/tenx/config and /opt/tenx-edge/lib/app/modules match
origin/main (md5 of rate-object-cap.js, rate-object-lookup-cap.js, forwarder/config.yaml,
rate/module.yaml all equal).

## Patches (engine/PATCHES.diff)
1. Both cap-variant scripts: `var action = TenXEnv.get("rateReceiverDefaultAction", "pass")`.
2. modules rate module.yaml: option `rateReceiverDefaultAction` (string, default pass).
3. Copied rate config.yaml: all severity floors 0 (list option; set in the file).

## Verified by smoke test 1 (2026-10-14 01:25 to 01:30 UTC, dummy inputs, no demo)
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

## Measured by the 11-hour smoke (01:31 to 12:31 UTC, three dummy sources)
- Returned counts were 77% of the sent counts for every source (fast 5/s: 153,151 of
  ~199,000; 1/s sources: ~30,580 of ~39,550 each). The loss is uniform, not per source.
- Fluent Bit logged 117k retry warnings in 10 h: `no upstream connections available` and
  `connection #N to tcp://engine:24224 timed out after 10 seconds`. Connection numbers
  climbed past 150. The engine logged `client disconnected, waiting for new connection`
  about every 11 minutes (Fluent Bit keepalive recycle at 2000 uses).
- Reading: the engine's forward input serves one client connection at a time; Fluent Bit's
  forward output opened several. Fix under test: single worker, one keepalive connection.

## Verified by smoke test 2 (12:34 to 12:38 UTC, finite inputs)
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

## Verified by smoke test 3 (12:39 to 12:45 UTC)
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

## Disk
- The dangling `log10x/pipeline-10x` image (914 MB) was removed at 12:43 UTC once no
  container referenced it (the two containers that used it overnight were gone).
- Docker Desktop: DiskSizeMiB 61035, DiskTRIM on; the VM had 34 GB free inside while
  macOS `df` showed 5.6 GB; TRIM returned the deleted image within minutes (6.8 GB).
- The official `3.1.0-load-generator` image (526 MB compressed; the other demo images
  expand 3x to 5x on disk) was not pulled: the rig builds the demo's own load generator
  without the Chromium install instead (`load-generator/Dockerfile`).

## Run facts (2026-10-14, demo up at 12:50 UTC)
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

## Disk rules in force from 13:05 UTC (coordinator)
- No further image pulls. `disk-guard.sh` logs free space every 5 minutes to
  results/disk.log, gzip-rotates raw.jsonl past 1 GB, and under 4.5 GB free runs
  `run.sh down` (scheduler stop, log snapshot, compose down, images kept) and marks
  `disk_stop` in the timeline. Another agent's verification rig shares the host.

## Open question under test (13:05 UTC)
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
