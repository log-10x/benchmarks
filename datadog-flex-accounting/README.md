# Datadog Flex Logs accounting

One benchmark in the [log10x benchmarks](../) repository. It answers one question:
when the released engine moves events out of Datadog's Standard index into Flex Logs
under the plan the released MCP writes, how many events and GB move, and what do those
events cost at Datadog's list prices.

Everything here is computed from the engine's own counts at list price. Nothing was
metered by Datadog, and no Datadog account is needed to rerun it.

## The result

The OpenTelemetry demo capture, 197,430 lines, 157,228 events after grouping, 0.215 GB
over ten hours. Engine `log10x/pipeline-10x:1.1.139`, log10x-mcp 1.30.47, prices read
2026-10-11.

**What a moved event costs at list.** Standard indexing avoided: $1.70 per million events
at 15-day retention and $2.50 at 30-day, annual; $2.55 and $3.75 on demand. Flex storage
added: $0.05 per million events stored per month, annual, $0.075 on demand, billed for at
least 30 days. Flex Starter, compute bundled, for volumes below 2 billion events a month:
$0.60 per million stored per month. Flex compute above Starter: "Contact Us for Pricing".
Ingestion, $0.10 per GB, is paid once on every event and unchanged by a move. The full rate
table with every URL is in [`results/results.md`](results/results.md).

**What moves, per target.** The MCP's plan applied as written, its `caps.csv` and
`actions.csv` on the released engine, with each cap scaled to the one-window replay:

| Target | Patterns planned | Containers capped | Events the plan states | Events the engine marked tier_down | Share of the volume the plan states | Share of the bytes the engine moved | Events in Standard | Errors and warnings to Flex |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30% | 3 | 1 | 60,783 | 67,426 | 40.3% | 39.9% | 89,802 | 0 |
| 50% | 7 | 4 | 82,585 | 90,688 | 50.6% | 56.2% | 66,540 | 0 |
| 70% | 55 | 17 | 112,944 | 119,885 | 68.4% | 71.2% | 37,343 | 0 |

The plan moves whole patterns, so a target lands on the first set that reaches it: at 30%
the collector's `Traces`, `Logs` and `Metrics` lines, 40% of the volume, under a cap set
at the collector's largest kept line. At 50% the cart's `GetCartAsync` and the ad and
recommendation services join, each container capped at the largest pattern it keeps; at
70%, 55 patterns across 17 containers. The engine moves each pattern's excess over its
container's cap, less the share the severity floors keep. Its figure runs above the plan's
because the plan is stated from a 12,000-line sample scaled to the file and the engine
counts the whole capture, and because a container capped at one byte (nothing kept) moves
every pattern it has. At 70%, 4 planned patterns carried no container and are not in the
files.

**A month at this capture's volume, an illustration.** The capture's ten hours scaled to a
720-hour month, at the rates above. The volume is one small demo cluster's; the rates are
what carry.

| Target | Events to Flex per month | Standard indexing avoided, 15-day annual | Flex storage added, annual | Flex compute tier | Custom metrics above a Pro host's allotment, one node |
|---:|---:|---:|---:|---|---:|
| 30% | 4,854,672 | $8.25 | $0.24 | Starter | $537.40 |
| 50% | 6,529,536 | $11.10 | $0.33 | Starter | $538.40 |
| 70% | 8,631,720 | $14.67 | $0.43 | Starter | $543.60 |

**Custom metrics.** The engine's Datadog metric output publishes two counters for every
label set of two aggregators. On this capture that is 10,848 to 10,972 custom metrics from
one node, about 10,750 above a Pro host's allotment of 100: $537 to $544 a month at $5 per
100, if every series reports every hour. This line is larger than every other line in the
table.

## Counting conditions

- Datadog counts indexed events; with the shipped forwarder path one record is one event,
  and the Receiver groups the lines of a multi-line event into one record.
- The Flex route is Datadog's index filter on `@routeState:tier_down`, on a Flex index
  listed before the Standard one. Every event the engine marks `tier_down` carries that
  field.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its
  pattern's cap takes the container's action. Patterns under 5% of their container's bytes
  in the window are not capped, the first 5 events of a pattern in a window pass, and the
  severity floors keep a tenth of INFO, DEBUG and TRACE, three tenths of WARN and half of
  ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within
  that noise.
- The replay delivers the capture inside one window; each cap the plan wrote is multiplied
  by the span the plan covers over 240 s, 15 here, and nothing else in the plan's files is
  changed. `results/policy-*.json` records the files and the factor.
- Every count is taken two ways, from the emitted records and from the engine's own
  aggregators, and the run fails if they differ.
- A month is 720 hours; the capture covers 10. GB are decimal.

## Reproduce

```sh
./run.sh                  # everything
./run.sh plan replay      # some stages only, in the order given
```

Stages: `data plan control policy replay count report`. Needs Docker, Node 18 or later
and about 1 GB of disk; the whole run takes under ten minutes. `plan` installs the pinned
log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; the server runs the pinned
engine image for its own sampling. Every other stage runs the engine image on the capture.
`ACCT_TARGETS` sets the targets (default `30 50 70`), `ACCT_WINDOW` the span the capture
covers (default `10h`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `prices.json` | every price used, with its URL and the date read |
| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |
| `../accounting-lib/plan.mjs` | asks the released MCP for its plan over stdio and keeps what it wrote |
| `../accounting-lib/replay.config.yaml` | the engine run: shipped enrichment, regulator and aggregators, file in, file out |
| `../accounting-lib/policy.py` | the engine files the tool wrote, caps scaled to the one-window replay |
| `../accounting-lib/count.py` | the two counts, records and aggregators, required to agree |
| `results/plan-<target>.json` | the plan the MCP wrote, its notes and both engine files as it rendered them |
| `results/policy-<target>.caps.csv`, `.actions.csv`, `.json` | the files the engine read |
| `results/<target>.tally.json`, `results/control.tally.json` | the counts per route, container, severity and pattern |
| `results/results.md` | every table, with the per-target detail |

## Data

`otel-sample-200mb.log` from
[otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1),
215,039,161 bytes, 197,430 lines, sha256
`aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`: Kubernetes container
output captured through Fluentd from a cluster running the OpenTelemetry demo, 36
containers, about ten hours. The same asset the [`splunk-license/`](../splunk-license/)
and [`otel-denominators/`](../otel-denominators/) benchmarks run on.
