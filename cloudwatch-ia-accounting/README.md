# CloudWatch Logs Infrequent Access accounting

One benchmark in the [log10x benchmarks](../) repository. It answers one question:
when the released engine moves events out of a CloudWatch Standard log group into an
Infrequent Access group, or offloads them to S3, under the plan the released MCP writes,
how many bytes move, and what do they cost at AWS's list prices.

Everything here is computed from the engine's own counts at list price for us-east-1.
Nothing was metered by AWS, and no AWS account is needed to rerun it.

## The result

The OpenTelemetry demo capture, 197,430 lines, 157,228 events after grouping, 0.215 GB
over ten hours. Engine `log10x/pipeline-10x:1.1.139`, log10x-mcp 1.30.47 with the S3
retriever declared installed, prices read 2026-10-11.

**Dollars per GB at list.** Ingest: $0.50 Standard, $0.25 Infrequent Access. Storage: $0.03
per GB-month in both classes, on compressed bytes at AWS's stated 0.15 ratio. Logs
Insights: $0.005 per GB scanned. S3 Standard: $0.023 per GB-month and $0.005 per 1,000 PUT
requests. A GB moved to Infrequent Access costs $0.25 instead of $0.50 to ingest and the
same to store; a GB offloaded costs nothing to ingest and $0.023 a month in S3. The 26 bytes
per event in the PutLogEvents batch-size rule are shown as a separate line; no AWS page read
bills them. The full table with every URL is in [`results/results.md`](results/results.md).

**What moves, per target.** The MCP's plan applied as written, its `caps.csv` and
`actions.csv` on the released engine, with each cap scaled to the one-window replay. The
plan's percentages are of the bill, and Infrequent Access halves the ingest rate, so a 30%
cut in dollars is about 60% of the bytes:

| Target | Patterns planned | Containers | GB the plan states to IA | GB the engine marked to IA | GB offloaded | GB in Standard | Share of the bill the plan states | Share of the bytes the engine moved | Errors and warnings moved |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30% | 22 | 5 | 0.136 | 0.150 | 0.000 | 0.065 | 30.4% | 69.7% | 0 |
| 50% | 55 | 17 | 0.071 | 0.067 | 0.099 | 0.049 | 56.9% | 77.3% | 53 |
| 70% | 55 | 17 | 0.030 | 0.002 | 0.165 | 0.048 | 70.6% | 77.7% | 52 |

At 30% the plan tiers down 22 patterns in five containers, each capped at the largest
pattern it keeps. At 50% it offloads the collector's `Traces` and `Logs` lines and tiers
down 16 other containers; at 70% it offloads the collector, the cart, the ad and
recommendation services and kafka. Offload acts on the whole container, its cap is the
one-byte minimum, so the patterns the plan still lists as tier_down inside an offloaded
container are offloaded with it, which is where the 70% row's 0.030 GB stated against
0.002 GB marked goes. The engine's bytes run above the plan's because the plan is stated
from a 12,000-line sample scaled to the file and the engine counts the whole capture. At
50% and 70%, 4 planned patterns carried no container and are not in the files.

**A month at this capture's volume, an illustration.** The capture's ten hours scaled to a
720-hour month, at the rates above. The volume is one small demo cluster's; the rates are
what carry.

| Target | GB to IA per month | Ingest at the IA rate | Ingest at Standard the same GB would cost | GB offloaded per month | Ingest avoided by offload |
|---:|---:|---:|---:|---:|---:|
| 30% | 10.778 | $2.69 | $5.39 | 0.000 | $0.00 |
| 50% | 4.831 | $1.21 | $2.42 | 7.130 | $3.56 |
| 70% | 0.127 | $0.03 | $0.06 | 11.901 | $5.95 |

**What Infrequent Access lacks**, from AWS's log class table: Facets, natural language
query assist, Anomaly Detection, Live Tail, field indexing, compare to previous time range,
subscription filters, metric filters, Container Insights and Lambda Insights log ingestion,
embedded metric format, the GetLogEvents and FilterLogEvents API operations, and the Logs
Insights commands `pattern`, `diff`, `filterIndex` and `unmask`. Logs Insights queries
otherwise run, as do CloudWatch pipelines, export to S3, scheduled queries, KMS encryption
and masking. A log group's class is fixed when it is created.

## Counting conditions

- CloudWatch bills ingestion by the bytes of each event message. Bytes here are the UTF-8
  size of each record the engine emitted; with the shipped forwarder path the forwarder
  sends that record as the event message. A multi-line event is one message whose lines are
  joined by newlines.
- The split is forwarder-side: the `tenx.tier_down` tag goes to a log group in the
  Infrequent Access class, `tenx.offload` to the S3 output.
- The regulator caps each pattern's bytes per container per 240 s window; an event over its
  pattern's cap takes the container's action. Patterns under 5% of their container's bytes
  in the window are not capped, the first 5 events of a pattern in a window pass, and the
  severity floors keep a tenth of INFO, DEBUG and TRACE, three tenths of WARN and half of
  ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within
  that noise.
- The replay delivers the capture inside one window; each cap the plan wrote is multiplied
  by the span the plan covers over 240 s, 15 here, and nothing else in the plan's files is
  changed. A container takes the one action its row names; the planner gives it the strongest
  action among its patterns, offload before tier_down. `results/policy-*.json` records the
  files and the factor.
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
log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio with the S3 retriever
declared installed; the server runs the pinned engine image for its own sampling. Every
other stage runs the engine image on the capture. `ACCT_TARGETS` sets the targets (default
`30 50 70`), `ACCT_WINDOW` the span the capture covers (default `10h`).

| File | What it is |
|---|---|
| `run.sh` | the whole run, in stages |
| `prices.json` | every price used, with its URL and the date read |
| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |
| `../accounting-lib/` | the MCP driver, the engine run, the policy mapping and the two-way count, shared with [`datadog-flex-accounting/`](../datadog-flex-accounting/) |
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
