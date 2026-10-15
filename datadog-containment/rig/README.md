# Containment demo rig

OpenTelemetry demo 3.1.0 under docker compose, every container's stdout routed through
Fluent Bit to the log10x Receiver, released image `log10x/edge-10x:1.1.142`
(`sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`) with its own
config and modules, launched with the values log10x-mcp 1.30.58 renders for a Datadog
Fluent Bit Receiver with a fleet default. The flagd-ui scheduler fires the demo's feature
flags on its own. Fluent Bit keeps what arrived (`raw.jsonl`) and what the Receiver returned,
one file per `routeState` (`pass.jsonl`, `offload.jsonl`, `tier_down.jsonl`, `other.jsonl`).
Nothing leaves the machine.

## Versions

| Part | Version |
|---|---|
| Receiver | `log10x/edge-10x:1.1.142@sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`, no mounted or patched trees |
| Plan and values | log10x-mcp 1.30.58 from npm (tarball sha256 `ea1ec0c4b4b68475c61e79520c9276d0bebb211ac9b7f5c2b07a283d08eb9ee0`) |
| Demo | opentelemetry-demo tag 3.1.0 (`dedc0178`), `compose.yaml` + `compose.full.yaml` |
| Forwarder | `fluent/fluent-bit:4.2` |
| Scheduler | flagd-ui 3.1.0, seed 20261014, interval 600 s, hold 240 to 480 s, one flag at a time |

## Layout

| Path | What it is |
|---|---|
| `compose.rig.yaml` | Overlay for the demo's compose files: Fluent Bit at 172.28.0.250 on the demo's private network (no published port), the Docker `fluentd` log driver on every demo container, `FLAGD_CACHE=disabled` on checkout (see "checkout's flag cache"). |
| `fluent-bit/fluent-bit.conf`, `fluent-bit/rig.lua` | Ingest, raw copy, hand-off to the Receiver over Fluent Forward, return path split by `routeState`. The ingest filter puts the container in `kubernetes.container_name` (see "The container field"); the return filter stamps `rb_ts`. |
| `run-planner.mjs` | log10x-mcp `poc_from_local`, file mode, on the quiet capture, with the fleet default. |
| `gen-receiver-values.mjs` | Renders the Receiver values through the MCP's own functions and writes `compose.receiver.yaml` from them (see below). |
| `run.sh` | Phase commands: `up`, `wait-healthy`, `quiet-start`, `quiet-end`, `receiver`, `sched`, `logs`, `down`. |
| `run-unattended.sh` | The scheduled phase: starts the scheduler, moves the deadline to the planned end, runs `run.sh down` there. |
| `hard-stop.sh` | Stops the demo once the deadline in `results/deadline` has passed and the run has not ended. |
| `disk-guard.sh` | Free-disk log every 5 minutes; under `FLOOR_MB` (4,500) confirmed 60 s later, `run.sh down`. |
| `detach.py` | Starts a process in its own session, so it outlives the shell that launched it. |
| `go.sh` | The whole run, one command. |
| `analyze.py`, `report.py` | Every measure in `results/results.md`, then the page itself. |
| `previous-run.py` | Earlier runs, each measured by the same `analyze.py` from its committed captures in git, into `results/previous-runs.json` for the comparison tables. |
| `memory/run.sh`, `memory/replay.py`, `memory/fluent-bit.conf`, `memory/summarize.py` | The Receiver's memory and CPU: `raw.jsonl` replayed at its captured pace over the Fluent Forward protocol through Fluent Bit into the Receiver launched from `results/values-fleet/launch.json`, on a private internal Docker network, with `docker stats` every 10 s; writes `results/memory/`. |
| `load-generator/Dockerfile` | The demo's load generator without the browser install. |
| `NOTES.md` | Working log. |

## The Receiver's values

`gen-receiver-values.mjs` calls the two functions `log10x_advise_install` calls for a
Receiver plan with `log_destination: "datadog"`: `receiverFleetValues` with the POC's
`fleet_default` (`cap_bytes_per_window_per_node`, `action`, `error_floor`), then the Fluent
Bit Receiver overlay's `renderValues`. `advise_install` itself needs a cluster snapshot from
`log10x_discover_env`, which a compose rig has none of. The rendered overlay is kept verbatim
(`results/values-fleet/values.yaml`), and the Receiver is launched with:

- the image, and every argument after the app in the order the overlay lists them
  (`symbolMessageHashField`, `rateReceiverAbsoluteCap`, `rateReceiverDefaultAction`, the
  share, warm-up, always-pass and retention settings, `rateReceiverSeverityFloors` once per
  level);
- every environment variable with a plain value (`TENX_AIRGAPPED`, `outputOffload`);
- the CPU and memory limits;
- the policy files: the POC's `log10x-caps.csv` and `log10x-actions.csv` when it writes rows
  (in a cluster `log10x_configure_engine` puts them in the policy ConfigMap in place of the
  install seed), otherwise the seed `policy-configmap.yaml` carries.

Substituted, because there is no cluster (the MCP's own
`scripts/check-fleet-default-floors` does the same): the ConfigMap pull (`K8S_NAMESPACE`,
`K8S_ENABLED`, `K8S_CONFIGMAP`, `CONFIG_GENERATION_FILE`) is left out, and
`CAP_LOOKUP_FILE` and `ACTION_LOOKUP_FILE` point at the mounted policy files. Rig plumbing:
`TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit`, since Fluent Bit is another container, not the same
pod. Measurement only, after every MCP argument: `outputEncodeField
fullText("tenx_hash","routeState","message_pattern","severity_level")`; the shipped config
computes `fullText("tenx_hash","routeState")` from the values, and the rig's list keeps both
and adds the pattern name and level to the returned record. It does not reach the regulator.

The quiet run uses the same generator with no fleet default (`results/values-quiet`): the
values a Datadog Receiver gets before one, which set no cap, so every record passes.

## This run's generated values

POC on the quiet capture (12:24:23 to 12:46:23 UTC, 9,118 lines): `fleet_default` computed
71,247 bytes per window per node, 2 x 35,623.7
(otel-collector `error_Error_scraping_metrics`), action `offload`, error floor 0.5. The Receiver
ran with these arguments after the image (`results/values-fleet/values.yaml` is the rendered
overlay, `results/values-fleet/launch.json` what was applied):

```text
@run/input/forwarder/fluentbit
@apps/receiver
symbolMessageHashField
tenx_hash
rateReceiverAbsoluteCap
71247
rateReceiverDefaultAction
offload
rateReceiverMinSharePercent
0
rateReceiverWarmupMs
0
rateReceiverBaselineCount
5
rateReceiverMinRetentionThreshold
0
rateReceiverSeverityFloors
TRACE=0
rateReceiverSeverityFloors
DEBUG=0
rateReceiverSeverityFloors
INFO=0
rateReceiverSeverityFloors
WARN=0
rateReceiverSeverityFloors
ERROR=0.5
rateReceiverSeverityFloors
CRITICAL=0.5
rateReceiverSeverityFloors
FATAL=0.5
```

Environment: `TENX_AIRGAPPED=true`, `outputOffload=true`; `CAP_LOOKUP_FILE` and
`ACTION_LOOKUP_FILE` on the mounted policy files below; limits 0.5 CPU and
512M. The POC's policy files, applied as written:

```text
container,cap
accounting,2765::accounting any statement above 691 lines a day goes to Flex. Today that is these 45 statements about $0.16 a month.
ad,1::ad every statement goes to Flex. Today that is these 7 statements about $0.32 a month.
cart,1::cart every statement goes to Flex. Today that is these 9 statements about $1.8 a month.
email,1::email every statement goes to Flex. Today that is these 4 statements about $0.16 a month.
fraud-detection,1::fraud-detection every statement goes to Flex. Today that is these 2 statements about $0.16 a month.
frontend,30210::frontend any statement above 8189 lines a day goes to Flex. Today that is these 7 statements about $3.5 a month.
frontend-proxy,1::frontend-proxy every statement goes to Flex. Today that is this one statement about $0 a month.
kafka,20074::kafka any statement above 1889 lines a day goes to Flex. Today that is these 12 statements about $1.6 a month.
otel-collector,61996::otel-collector any statement above 2508 lines a day goes to Flex. Today that is these 9 statements about $12 a month.
payment,2344::payment any statement above 204 lines a day goes to Flex. Today that is these 27 statements about $0.31 a month.
quote,1::quote every statement goes to Flex. Today that is this one statement about $0.16 a month.
recommendation,2330::recommendation any statement above 315 lines a day goes to Flex. Today that is these 6 statements about $0.32 a month.
shipping,2721::shipping any statement above 849 lines a day goes to Flex. Today that is these 13 statements about $0.47 a month.
telemetry-docs,1::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.81 a month.
valkey-cart,1::valkey-cart every statement goes to Flex. Today that is these 5 statements about $0.07 a month.
```

```text
container,action
accounting,tier_down::accounting any statement above 691 lines a day goes to Flex. Today that is these 45 statements about $0.16 a month.
ad,tier_down::ad every statement goes to Flex. Today that is these 7 statements about $0.32 a month.
cart,tier_down::cart every statement goes to Flex. Today that is these 9 statements about $1.8 a month.
email,tier_down::email every statement goes to Flex. Today that is these 4 statements about $0.16 a month.
fraud-detection,tier_down::fraud-detection every statement goes to Flex. Today that is these 2 statements about $0.16 a month.
frontend,tier_down::frontend any statement above 8189 lines a day goes to Flex. Today that is these 7 statements about $3.5 a month.
frontend-proxy,tier_down::frontend-proxy every statement goes to Flex. Today that is this one statement about $0 a month.
kafka,tier_down::kafka any statement above 1889 lines a day goes to Flex. Today that is these 12 statements about $1.6 a month.
otel-collector,tier_down::otel-collector any statement above 2508 lines a day goes to Flex. Today that is these 9 statements about $12 a month.
payment,tier_down::payment any statement above 204 lines a day goes to Flex. Today that is these 27 statements about $0.31 a month.
quote,tier_down::quote every statement goes to Flex. Today that is this one statement about $0.16 a month.
recommendation,tier_down::recommendation any statement above 315 lines a day goes to Flex. Today that is these 6 statements about $0.32 a month.
shipping,tier_down::shipping any statement above 849 lines a day goes to Flex. Today that is these 13 statements about $0.47 a month.
telemetry-docs,tier_down::telemetry-docs every statement goes to Flex. Today that is this one statement about $0.81 a month.
valkey-cart,tier_down::valkey-cart every statement goes to Flex. Today that is these 5 statements about $0.07 a month.
```

The scheduled run: seed 20261014, interval 600 s, hold 240 to 480 s, 75 minutes from the
scheduler start (12:47:51 to 14:02:55 UTC). `results/results.md` has every measure.

## The container field

The Docker `fluentd` driver puts the container at the top of the record (`container_name`).
Fluent Bit's ingest filter (`fluent-bit/rig.lua`) moves it into `kubernetes.container_name`
(with `container_id` as `kubernetes.docker_id`), the way a Kubernetes forwarder ships a
pod's records. That is the field both sides read:

- the MCP's file mode takes a pattern's service from `kubernetes.container_name` (or
  Datadog's `service`), and the fleet default needs a kept statement in a named container;
- the released Receiver keys the cap on `k8sContainerNameField`, which its fluentK8s
  extractor fills from `kubernetes.container_name`.

Finding: with plain Docker records the MCP attributes nothing (the 1.1.140 run's plan
reported every pattern `(unattributed)` and wrote header-only policy files), so
`fleet_default` has no baseline to compute, and the Receiver, given the MCP's values and no
`rateReceiverContainerField`, keys every container as one: `rate-object-cap.js` uses
`__node__` when the container field is empty.

## checkout's flag cache

The rig sets one environment variable on a demo service: `FLAGD_CACHE=disabled` on checkout.
checkout is the service that turns kafkaQueueProblems into the incident: after each order it
reads the flag through the Go flagd provider (go-sdk-contrib `providers/flagd` v0.6.0 in demo
3.1.0) and, when the flag is on, publishes the order 100 more times. The provider caches
resolved values by default. In the run of 2026-10-15 that started at 10:56 UTC (commit
4c2b610) the cached value did not follow the flag: flagd's own metrics counted 4 resolutions
of kafkaQueueProblems through the provider for the whole run, the activation reached
fraud-detection (which logged its consumer delay) and never reached checkout, and no duplicate
order was published. With the cache disabled every evaluation is a call to flagd, so a change
the scheduler makes reaches checkout on its next order, which is how the demo's own failure
injection is meant to work. In the published run flagd counted 5 resolutions for checkout's
first 4 orders, and the kafkaQueueProblems activation at 12:59:19 UTC produced the
duplicate-order flood 11 s later. Nothing about the Receiver, the plan or the values depends
on it.

## Differences from a cluster install

- The records come from the Docker `fluentd` driver, reshaped as above; a cluster's
  kubernetes filter adds more keys (pod, namespace, labels) and, with `Merge_Log On`, lifts
  JSON log fields into the record.
- The policy files reach the Receiver as mounted files, not through the ConfigMap pull: the
  values' `K8S_NAMESPACE`, `K8S_ENABLED`, `K8S_CONFIGMAP` and `CONFIG_GENERATION_FILE` are
  left out, and `CAP_LOOKUP_FILE` and `ACTION_LOOKUP_FILE` name the mounted files instead of
  `/tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/`.
- The MCP's Fluent Bit overlay excludes `*otel-collector*.log` from collection. The rig
  forwards the demo's collector, whose debug exporter writes every batch it receives to
  stdout.
- One Receiver serves every container, as one node's sidecar would.

## Reproduce

Prerequisites: Docker Desktop with about 8 GB for the VM; the demo cloned at tag 3.1.0
(`git clone --depth 1 --branch 3.1.0 https://github.com/open-telemetry/opentelemetry-demo.git`);
`log10x/edge-10x:1.1.142` and `fluent/fluent-bit:4.2` pulled; the load generator built from
`load-generator/Dockerfile`; log10x-mcp 1.30.58 unpacked with its dependencies installed.

```
DEMO=/path/to/opentelemetry-demo MCP=/path/to/log10x-mcp-1.30.58 rig/go.sh
```

`go.sh` brings the demo up with the quiet values, marks a 22-minute quiet run, runs the POC
on its raw capture, renders the fleet values, relaunches the Receiver with them, and starts
the scheduled phase, the disk guard and the hard stop as detached processes; the run stops
itself 75 minutes after the scheduler starts. This run started `go.sh` itself through
`detach.py` (`python3 rig/detach.py results/go.out env DEMO=... MCP=... rig/go.sh`), so no
step depended on the shell that launched it. Then `python3 rig/analyze.py && python3
rig/previous-run.py 8e416c6='1.1.141 run' 4c2b610='first 1.1.142 run' && python3 rig/report.py`.

Kafka's health window in the demo is short (10 s start period, 10 retries at 5 s); on a
loaded host its JVM misses it, `compose up` exits 1 with "dependency failed to start" and
leaves the Kafka-dependent containers in Created. `run.sh up` waits for kafka healthy and runs
`compose up` again.

The scheduler is seeded, so the flag sequence repeats for the same seed and the same flags:
kafkaQueueProblems (on), cartFailure (100%), paymentFailure (100%), recommendationCacheFailure
(on), loadGeneratorFloodHomepage (on), emailMemoryLeak (1000x). aiRunawayAgent needs the agent
stack (`compose.agent.yaml`), which this rig does not run.
