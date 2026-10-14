# Containment demo rig

OpenTelemetry demo 3.1.0 under docker compose, every container's stdout routed through
Fluent Bit to the log10x Receiver (engine image `log10x/edge-10x:1.1.140`) with a
fleet-default per-pattern byte cap, and the flagd-ui scheduler firing feature flags on
its own. Fluent Bit keeps three local files: what arrived (`raw.jsonl`), what the Receiver
returned as `pass` (`pass.jsonl`) and as `offload` (`offload.jsonl`). Nothing leaves the
machine.

## Layout

| Path | What it is |
|---|---|
| `compose.rig.yaml` | Overlay for the demo's `compose.yaml` + `compose.full.yaml`: Fluent Bit and Receiver services, Docker `fluentd` log driver on every demo container, `RIG_CAP` into `rateReceiverAbsoluteCap`. |
| `fluent-bit/fluent-bit.conf` | Ingest from the log driver, raw copy, hand-off to the Receiver over Fluent Forward, return path split by `routeState`. |
| `engine/config`, `engine/modules` | Copies of the config and modules repos at the commits in `engine/SOURCES.txt`, with `engine/PATCHES.diff` applied. |
| `lookups/caps.csv` | Header-only cap file; it loads the cap class so the fleet-wide `rateReceiverAbsoluteCap` applies. |
| `scheduler.sh` | Starts, stops and reads the flagd-ui scheduler through the release's `rpc` entry point. |
| `run.sh` | Phase commands: `up`, `wait-healthy`, `quiet-start`, `quiet-end`, `cap <bytes>`, `sched`, `logs`, `down`. |
| `analyze.py` | Builds the fleet-default distribution, per-window counts, per-incident table, false holds and delivery check from the three files. |
| `report.py` | Renders `results/results-tables.md` from analyze.py's outputs. |
| `disk-guard.sh` | Free-disk log, raw-file rotation, clean stop under a floor. |
| `load-generator/Dockerfile` | The demo's load generator without the browser install (see results.md, deviations). |
| `NOTES.md` | Working log: what each smoke test proved. |

## Receiver settings

`@run/input/forwarder/fluentbit @apps/receiver` then, as bare `name value` pairs:
`rateReceiverCapLookupFile /etc/tenx/lookups/caps.csv`, `rateReceiverAbsoluteCap <cap>`,
`rateReceiverMinSharePercent 0`, `rateReceiverWarmupMs 0`, `rateReceiverBaselineCount 5`,
`rateReceiverMinRetentionThreshold 0`, `rateReceiverDefaultAction offload`,
`rateReceiverContainerField container_name`, `symbolMessageHashField tenx_hash`,
`outputEncodeField fullText("tenx_hash","routeState","message_pattern","severity_level")`.
Severity floors are all 0 in the copied `pipelines/run/receive/rate/config.yaml`.
`outputOffload=true` and `TENX_AIRGAPPED=true` are container environment variables.

## Reproduce

Prerequisites: Docker Desktop with about 8 GB for the VM and 7 GB of free disk for the
images; the demo cloned at tag 3.1.0 (`git clone --depth 1 --branch 3.1.0
https://github.com/open-telemetry/opentelemetry-demo.git`); `log10x/edge-10x:1.1.140`
and `fluent/fluent-bit:4.2` pulled.

```
export DEMO=/path/to/opentelemetry-demo   # the 3.1.0 clone
cd rig
RIG_CAP=0 ./run.sh up && ./run.sh wait-healthy
./run.sh quiet-start      # 24 minutes with no flag active
./run.sh quiet-end
python3 analyze.py        # prints the quiet-run distribution; cap = 2 x max cell
./run.sh cap <cap bytes>  # recreates the Receiver with the fleet default
SEED=20261014 ./run.sh sched 900 240 480   # interval 15 min, hold 4 to 8 min, one flag at a time
# run until four activations have reverted or two hours, whichever first
./run.sh down
python3 analyze.py
```

`disk-guard.sh` (optional, run alongside) logs free disk every 5 minutes to
`results/disk.log`, gzip-rotates `raw.jsonl` past 1 GB, and under `FLOOR_MB` (default
4500) runs `run.sh down`. Kafka's health window in the demo is short (10 s start period,
10 retries at 5 s); on a loaded host its JVM can miss it, `compose up` then exits 1 with
"dependency failed to start" and leaves the Kafka-dependent containers in Created. Once
`docker inspect kafka` reports healthy, run `up` again; it starts the rest.

The scheduler is seeded (`SEED`), so the flag sequence repeats for the same seed and the
same flag selection. Flags scheduled: kafkaQueueProblems (on), cartFailure (100%),
paymentFailure (100%), recommendationCacheFailure (on), loadGeneratorFloodHomepage (on),
emailMemoryLeak (1000x). aiRunawayAgent needs the agent stack (`compose.agent.yaml`), which
this rig does not run.
