# Datadog Flex Logs accounting

One benchmark in the [log10x benchmarks](../) repository. It answers one question:
when the released engine moves events out of Datadog's Standard index into Flex Logs
under the plan the released MCP writes, how many events and GB move, and what do those
events cost at Datadog's list prices.

Everything here is computed from the engine's own counts at list price. Nothing was
metered by Datadog, and no Datadog account is needed to rerun it.

## The result

<!-- generated:run -->
The OpenTelemetry demo capture, 197,430 lines, 157,228 events after grouping, 0.215 GB over 10 hours. Engine `log10x/pipeline-10x:1.1.140`, log10x-mcp 1.30.48, prices read 2026-10-11.
<!-- /generated:run -->

<!-- generated:rates -->
**What a moved event costs at list.** Standard indexing avoided: $1.70 per million events at 15-day retention and $2.50 at 30-day, annual; $2.55 and $3.75 on demand. Flex storage added: $0.05 per million events stored per month, annual, $0.075 on demand, billed for at least 30 days. Flex Starter, compute bundled, for volumes below 2 billion events a month: $0.60 per million stored per month. Flex compute above Starter: "Contact Us for Pricing". Ingestion, $0.10 per GB, is paid once on every event and unchanged by a move. The full rate table with every URL is in [`results/results.md`](results/results.md).
<!-- /generated:rates -->

**What moves, per target.** The MCP's plan applied as written, its `caps.csv` and
`actions.csv` on the released engine, with each cap scaled to the one-window replay:

<!-- generated:moves -->
| Target | Patterns planned | Containers capped | Events the plan states | Events the engine marked tier_down | Share of the volume the plan states | Share of the bytes the engine moved | Events in Standard | Errors and warnings to Flex |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30% | 3 | 1 | 60,783 | 67,505 | 40.3% | 39.9% | 89,723 | 0 |
| 50% | 7 | 4 | 82,585 | 90,555 | 50.6% | 56.1% | 66,673 | 0 |
| 70% | 55 | 17 | 112,944 | 119,833 | 68.4% | 71.2% | 37,395 | 0 |
<!-- /generated:moves -->

The plan moves whole patterns, so a target lands on the first set of patterns that reaches
it, each container capped at the largest pattern it keeps:

<!-- generated:moves-notes -->
- **30%**: 3 patterns in 1 container (`opentelemetry-collector`: `Traces`, `Logs`, `Metrics`).
- **50%**: 7 patterns in 4 containers (`opentelemetry-collector`: `Traces`, `Logs`, `Metrics`; `cart`: `cart_cartstore_ValkeyCartStore`; `recommendation`: `Receive_ListRecommendations_for_product_ids`; `ad`: `oteldemo_AdService_Targeted_ad_request_received_for`, `oteldemo_AdService_no_baggage_found_in_context_trace_id_span_flags`).
- **70%**: 55 patterns in 17 containers; 4 planned patterns carried no container and are not in the files.
<!-- /generated:moves-notes -->

The engine moves each pattern's excess over its container's cap, less the share the
severity floors keep. Its figure runs above the plan's because the plan is stated from a
12,000-line sample scaled to the file and the engine counts the whole capture, and because a
container capped at one byte (nothing kept) moves every pattern it has.

**A month at this capture's volume, an illustration.** The capture's span scaled to a
720-hour month, at the rates above. The volume is one small demo cluster's; the rates are
what carry.

<!-- generated:month -->
| Target | Events to Flex per month | Standard indexing avoided, 15-day annual | Flex storage added, annual | Flex compute tier | Custom metrics above a Pro allotment, 10 to 300 nodes |
|---:|---:|---:|---:|---|---:|
| 30% | 4,860,360 | $8.26 | $0.24 | Starter | $0 |
| 50% | 6,519,960 | $11.08 | $0.33 | Starter | $0 |
| 70% | 8,627,976 | $14.67 | $0.43 | Starter | $0 |
<!-- /generated:month -->

<!-- generated:custom-metrics -->
**Custom metrics.** The `metrics` stage replays the capture through the engine's shipped Datadog metric output, posting to a local stand-in for Datadog's intake; the one change to the image's config is the URI it posts to. Each series carried `k8s_container`, `k8s_namespace`, `message_pattern`, `routeState`, `severity_level`, `tenx_hash`, `tenx_reported_name`, `tenx_user_service`, and no host, pod or pipeline id, so every node posts the same series. The output keeps to the 200 tag sets with the most bytes, each from both aggregators: at most 776 series in one post without a move, and 768, 786 and 780 at 30, 50 and 70%. A Pro plan includes 100 custom metrics per host, so at 10, 100 and 300 nodes the line is $0. While ranks settle, tag sets enter and leave the top, and the replay, which delivers 10 hours in under a minute, saw 1,386 to 1,590 distinct series in all; on a live stream that settling happens once. Every tag set from every node would be 10,836 series per node, $5,368, $53,680 and $161,040 a month at $5 per 100.
<!-- /generated:custom-metrics -->

## Native filters at equal events

The question a Datadog buyer asks is whether a per-pattern plan moves anything their own
index filters would not. So each target has a control arm computed from the same capture,
engine and counts: what a person writes in Datadog today, an index filter per service.

**Selection rule, fixed before the run.** Datadog bills Standard indexing per million
events, so the arms are matched on events, with bytes alongside. Per target, the control
takes the fewest `service:<container>` filters, largest by events first, whose events reach
at least the events the engine marked tier_down under the plan, and reports the overshoot
without trimming it. A second variant adds `-status:(error OR warn)` to each filter, which
leaves ERROR and WARN events in Standard; CRITICAL maps to Datadog's `critical` status and
is not excluded by that clause. Errors and warnings are counted as the plan's column counts
them: ERROR, WARN, CRITICAL and FATAL.

**What would show the key adds nothing.** At a target, if the filters with the status
exclusion move no more errors and warnings than the plan, and none of the events of the
patterns the plan keeps under a container's cap (patterns in a capped container that the
engine marked nothing of), then per-pattern control adds nothing on this capture at that
target. The table is published as it comes out.

<!-- generated:native-filters -->
| Target | Arm | Index filters | Events moved | Over the plan | GB moved | Errors and warnings moved | Events of patterns the plan keeps under a cap | Events the plan moves that stay in Standard |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 30% | per-pattern plan | caps on 1 container | 67,505 | 0 | 0.086 | 0 | 0 | 0 |
| 30% | service filters | `service:opentelemetry-collector` | 89,739 | +22,234 | 0.118 | 3,953 | 4,000 | 0 |
| 30% | service filters, `-status:(error OR warn)` | `service:opentelemetry-collector` | 85,786 | +18,281 | 0.109 | 0 | 47 | 0 |
| 50% | per-pattern plan | caps on 4 containers | 90,555 | 0 | 0.121 | 0 | 0 | 0 |
| 50% | service filters | `service:opentelemetry-collector`, `service:kafka` | 118,778 | +28,223 | 0.149 | 3,954 | 4,000 | 23,161 |
| 50% | service filters, `-status:(error OR warn)` | `service:opentelemetry-collector`, `service:kafka` | 114,824 | +24,269 | 0.140 | 0 | 47 | 23,161 |
| 70% | per-pattern plan | caps on 17 containers | 119,833 | 0 | 0.153 | 0 | 0 | 0 |
| 70% | service filters | `service:opentelemetry-collector`, `service:kafka`, `service:cart` | 138,424 | +18,591 | 0.183 | 3,955 | 4,795 | 11,181 |
| 70% | service filters, `-status:(error OR warn)` | `service:opentelemetry-collector`, `service:kafka`, `service:cart` | 134,469 | +14,636 | 0.174 | 0 | 840 | 11,181 |
<!-- /generated:native-filters -->

<!-- generated:native-verdict -->
- **30%**: the falsifier does not hold. With the status exclusion, the filters move 47 events of 22 patterns the plan keeps under a cap (0.05% of the 85,786 events the filters move). They move 18,281 more events than the plan's 67,505, which the plan leaves in Standard.
- **50%**: the falsifier does not hold. With the status exclusion, the filters move 47 events of 22 patterns the plan keeps under a cap (0.04% of the 114,824 events the filters move). They move 24,269 more events than the plan's 90,555, which the plan leaves in Standard, and leave in Standard 23,161 events the plan moves, in services they do not name.
- **70%**: the falsifier does not hold. With the status exclusion, the filters move 840 events of 435 patterns the plan keeps under a cap (0.62% of the 134,469 events the filters move). They move 14,636 more events than the plan's 119,833, which the plan leaves in Standard, and leave in Standard 11,181 events the plan moves, in services they do not name.
<!-- /generated:native-verdict -->

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
