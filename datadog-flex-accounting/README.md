# Datadog Flex Logs accounting

One benchmark in the [log10x benchmarks](../) repository. It answers one question:
when the released engine moves events out of Datadog's Standard index into Flex Logs
under the plan the released MCP writes, how many events and GB move, and what do those
events cost at Datadog's list prices.

Everything here is computed from the engine's own counts at list price. Nothing was
metered by Datadog, and no Datadog account is needed to rerun it.

## The result

The OpenTelemetry demo capture, 197,430 lines, 157,228 events after grouping, 0.215 GB
over ten hours. Engine `log10x/pipeline-10x:1.1.139`, log10x-mcp 1.30.46, prices read
2026-10-11.

| Target | Patterns planned | Containers capped | Events to Flex | GB to Flex | Events in Standard | Errors and warnings to Flex | Events to Flex per month | Standard indexing avoided per month, 15-day annual | Flex storage added per month, annual | Flex compute tier |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 30% | 2 | 1 | 57,163 | 0.073 | 100,065 | 0 | 4,115,736 | $7.00 | $0.21 | Starter |
| 50% | 4 | 1 | 57,193 | 0.073 | 100,035 | 0 | 4,117,896 | $7.00 | $0.21 | Starter |
| 70% | 12 | 4 | 57,270 | 0.073 | 99,958 | 0 | 4,123,440 | $7.01 | $0.21 | Starter |

The engine moves the excess of each pattern over its container's cap. The planner wrote
the same cap at every target, 63,128 bytes per pattern per 240 s window, so the same
three patterns move at every target, the collector's `Traces`, `Logs` and `Metrics` lines;
the targets differ in which containers are capped, and no pattern outside the collector
exceeds the cap. Ingestion is unchanged: every event is ingested once, at $0.10 per GB,
before any index routing.

**What one million moved events cost at list.** Standard indexing avoided: $1.70 at 15-day
retention and $2.50 at 30-day, annual; $2.55 and $3.75 on demand. Flex storage added: $0.05
per million events stored per month, annual, $0.075 on demand, billed for at least 30 days.
Flex Starter, compute bundled, for volumes below 2 billion events a month: $0.60 per million
stored per month. Flex compute above Starter: "Contact Us for Pricing". The full rate table
with every URL is in [`results/results.md`](results/results.md).

**Custom metrics.** The engine's Datadog metric output publishes two counters for every
label set of two aggregators. On this capture that is 10,848 custom metrics from one node,
10,748 above a Pro host's allotment of 100: $537.40 a month at $5 per 100, if every series
reports every hour. This line is larger than every other line in the table.

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
- The replay delivers the capture inside one window; the plan's cap is multiplied by the
  window the MCP was told the capture covers over 240 s, and the plan's patterns are placed
  in the containers that produced them in the control run. `results/policy-*.json` records
  each step.
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
| `../accounting-lib/policy.py` | the plan's patterns and cap mapped onto the engine's per-container files, with the arithmetic recorded |
| `../accounting-lib/count.py` | the two counts, records and aggregators, required to agree |
| `results/plan-<target>.json` | the plan the MCP wrote, its notes and the caps row it rendered |
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
