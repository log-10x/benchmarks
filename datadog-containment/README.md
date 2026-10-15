# Datadog containment

One benchmark in the [log10x benchmarks](../) repository. It answers one question: when a
service starts flooding its logs, does the released Receiver, installed with the values the
released MCP writes for Datadog, hold the flood before it reaches Datadog, including in a
service nobody wrote a rule for, and what does it hold that it should not?

The incidents are the OpenTelemetry demo's own: demo 3.1.0 ships failure flags and a
scheduler that turns them on and off, seeded so a run repeats. Nothing was sent to a Datadog
account; the Receiver's output is split by the route it stamps (`pass`, `tier_down`,
`offload`) and counted. The full figures, rendered from the committed captures, are in
[`results/results.md`](results/results.md).

## The result

Engine `log10x/edge-10x:1.1.142` with its own config and modules, log10x-mcp 1.30.58, seed
20261014, a 22-minute quiet run for the MCP's POC, then 75 minutes of scheduled failures.

- **The flood was held, in a service with no rule.** `kafkaQueueProblems` makes checkout
  publish each order 100 extra times; accounting logs a duplicate for each copy and its
  insert fails, so Postgres writes an ERROR, a DETAIL and a STATEMENT line per copy. Postgres
  had no rule of its own; the fleet default held 5,555 of its lines (1.59 MB), the first 26 s
  after the first duplicate line, once the flood had filled the window's limit. accounting
  and fraud-detection, which the POC gave rules, were held within 5 s by their own rules.
- **No false holds.** Nothing was held by the fleet default outside a failure's causal path.
- **Failures that do not flood logs held nothing new**: emailMemoryLeak and the homepage flood.
- **Errors.** Above the limit, 48% of ERROR lines still reached Datadog against a floor of
  0.5. Postgres's DETAIL and STATEMENT lines carry no level, so an ERROR that passes arrives
  without them.
- **Latency.** Median 2.15 s, p99 7.16 s, max 10.3 s from Fluent Bit to Fluent Bit through the
  Receiver; every line written up to 60 s before the stop came back (72,187 of 72,187).

## How the limits were set

The MCP's own POC on the quiet run wrote 15 per-service rules (each service's limit between
its largest kept statement and its smallest moved one, with the margin stated) and a fleet
default for every other service: twice the largest per-window statement the plan keeps,
71,247 bytes per window per node here, with the excess going to S3 (`offload`) and half of
ERROR and CRITICAL kept above it. The Receiver ran with exactly the values the MCP rendered;
the only substitution is mounted policy files in place of the cluster's ConfigMap pull
([`results/results.md`](results/results.md), "The values the Receiver ran with").

## The Receiver's memory and CPU

The run's own capture, replayed: `results/data/raw.jsonl` from 12:47:16 UTC, when the Receiver came up with the fleet values, to the end of the capture, sent through Fluent Bit into the same image with the same arguments, policy files and container limits (0.5 CPU, 512 MiB memory) at the pace it was captured. 57,353 records over 76.8 minutes; `docker stats` sampled the Receiver every 10 s.

| measure | samples | median | p99 | max |
|---|---:|---:|---:|---:|
| memory, MiB (limit 512) | 461 | 212.8 | 227.5 | 227.7 |
| CPU, % of one core (limit 50) | 461 | 0.42 | 8.0 | 15.56 |

Before the first record the Receiver sat at 112.4 MiB. It was not OOM killed and did not restart. The replay returned 16,836 pass, 5,524 offload, 22,655 tier_down; the run itself returned 16,480 pass, 5,555 offload, 22,732 tier_down over the scheduled run, which starts 35 s later. `rig/memory/run.sh` reproduces it, and `results/memory/` holds every sample. No other container ran on the host during the replay.

## Limits of this run

- **One host, Docker.** The demo runs in Docker Compose; the rig reshapes each Docker record
  the way a Kubernetes forwarder ships it, because the MCP and the Receiver key on
  `kubernetes.container_name`. With plain Docker records the MCP attributes no service.
- **One demo setting.** `FLAGD_CACHE=disabled` on checkout: with the cache on, checkout's
  flagd provider answered from its cache and the scheduled Kafka failure never reached it
  (a first run on 1.1.142 had no flood for that reason; its latency and false-hold figures
  are kept beside this run's).
- **The fleet default depends on the quiet run.** It is twice the largest statement the plan
  keeps, so a noisy statement in the baseline raises it: 25,960 bytes in the first 1.1.142
  run, 71,247 in this one, after a burst of the collector's Kafka scrape errors. A larger
  default holds later in a flood (26 s here, 0.18 s at 10,288 bytes in an earlier run).
- **Memory from a replay.** The memory and CPU figures come from replaying the run's capture through the Receiver, not from the live run, and a replay sends each record as Fluent Bit wrote it, so the Receiver sees the same records and pace but not the demo's other containers beside it. The figures are what `docker stats` reports for the container.
- **The replay's policy files were older than the Receiver's retain interval.** At load the Receiver logged `rate receiver cap file is stale ... retainInterval: 600000` (`results/memory/receiver.log`): the mounted `caps.csv` kept its modification time from the git checkout, while the run's own file was written a minute before launch. The plan's rows still applied: the replay returned 22,655 tier_down and 5,524 offload records against the run's 22,732 and 5,555.
- **S3 only.** Locally there is no Flex index; the fleet default's action is `offload`.
- **Earlier runs.** On engine 1.1.141 the same rig showed a p99 of 28.9 s and a worst case of
  472 s from an input-wide flush timer, fixed in 1.1.142, and one false hold from a cap unit
  mismatch, fixed in log10x-mcp 1.30.55. Both runs are measured from git in
  `results/results.md`, "Against the earlier runs".

## Reproduce

`rig/README.md` lists the images by digest, the demo checkout, the seed and the one command
(`rig/go.sh`) that runs the quiet run, the POC, the install values and the scheduled run, and
stops itself. `rig/analyze.py` and `rig/report.py` regenerate `results/results.md` byte for
byte from the committed captures.
