# Datadog ceiling

One benchmark in the [log10x benchmarks](../) repository. It answers one question: with a
monthly budget X for Datadog Standard indexing, does the released Receiver, driven by the
released MCP's hourly budget run, hold Standard at X while log volume grows 2 to 3x, as
Datadog's own usage metric counts it?

Every line went to a real Datadog org. The proof is Datadog's meter,
`datadog.estimated_usage.logs.ingested_events{datadog_is_excluded:false}` by `datadog_index`,
read hourly; numbers taken from it are labelled "meter". The rig's own captures (what the
Receiver returned, split by `routeState`) are labelled "local" and agree with the meter to
within 16 events an hour in every hour both were read.

## The result

Engine `log10x/edge-10x:1.1.146`, log10x-mcp 1.30.71, OpenTelemetry demo 3.1.0, one Receiver
for every container, 2026-10-20.

| | Criterion | Result |
|---|---|---|
| 1 | Hourly Standard (`main`, meter) at or under the allowed rate plus the allowances through the growth; Flex absorbs the rest | **Pass.** 20,123, 21,020, 22,744, 21,138 and 21,080 events (meter, 04:00 to 08:00) against 22,351 allowed and 23,826 to 25,136 with the allowances. Ingested events 2.91x, 2.69x and 2.63x the baseline at 06:00, 07:00 and 08:00; Flex took 42,268, 38,957 and 37,651 (meter). |
| 2 | A statement new mid-run is held from its first window | **Pass.** A new service, `inventory`, with one new statement at 476 lines a window: 31 lines a window in Standard from its first window (the `*` row's total of 31; 35 once and 27 the next), the rest in Flex, until the 07:00 run gave it a row of its own (85). |
| 3 | The budget run runs at least twice, an hour or more apart, and its files change with spend | **Pass.** Six applied runs, hourly from 04:02 to 09:00, each a direct commit to the policy branch with a diff ([`results/budget-runs/`](results/budget-runs/)). |
| 4 | Error lines in Standard per storming error statement per node per window at most the statement's limit plus K = 50, the rule the [regulator page](https://doc.log10x.com/run/receive/rate/) states | **Pass, within one line.** The storming payment statement put 68, 66 and 69 lines a window in Standard against 68 (limit 18 plus 50), the 69 in the window that spans the 06:00 run, and 151, 118 and 119 against 188 once that run raised its limit to 138, with 328 to 460 a window moved to Flex. |
| 5 | One service with `service_budgets` held to its own number | **Pass.** `frontend`, own number $0.88 a month (1,792 events an hour): 1,774, 1,763, 1,760 and 1,770 events (meter, `service:frontend`, 05:00 to 08:00). Its 04:00 hour reads 1,957 because 165 lines passed in the 3 minutes before the first budget run; after it, 1,790 in 57 minutes. Metered spend through 07:59: 16,021 events, $0.027 of the $0.88. |
| 6 | Delivery complete; an error monitor still fires | **Pass.** 381,856 of 381,856 non-blank lines the Receiver received came back in its returned records, and every returned record went to Datadog (pass to `main`, tier_down to `tenx-offload`). A log monitor on the payment error statement in `main` went to Alert at 06:03:43 during the storm and back to OK at 06:22:43, after the storm line stopped at 06:16. |

Month to date the budget run read 164,330 Standard events ($0.28 of $10.89) at 09:00, against
170,061 on the path X allows (59,139 at 04:02:21 plus 22,351 an hour).

## How X and the limits were set

Written before the first budget run in [`results/x-method.txt`](results/x-method.txt) and not
changed during the run; the numbers are in [`results/x.json`](results/x.json).

- **Baseline.** The Receiver with the install's seed policy (every line passes), 5 load
  generator users, no flags. Two full hours, 02:00 and 03:00 UTC: 22,143 and 22,576 Standard
  events (meter), so B = 22,359.5 events an hour.
- **X.** Month to date from the budget run's own read at 04:02:21 (a dry run): 59,139
  Standard events, 283.96 hours left in October. X = (59,139 + 22,359.5 x 283.96) x $1.70 per
  million (Standard, 15-day retention, list, the MCP's default) = **$10.89 a month**. The
  allowed rate for the rest of the month is **22,351 events an hour**.
- **frontend's own number.** Its baseline was 3,592.5 events an hour (meter, `service:frontend`);
  held to half of it: (8,898 spent + 1,796 x 283.96) x $1.70 per million = **$0.88 a month**,
  1,792 events an hour. It is part of X; the rest of the account gets $10.01.
- **Allowances** (criterion 1): for every window and every statement that had lines moved in
  it, 5 sample lines, and 50 more for an error statement (one node). Per hour they came to
  1,475 to 2,785 events ([`results/hourly.csv`](results/hourly.csv)).
- **Fixed for the run:** keep_count 50, `standard_indexes: [main]`, `default_action: tier_down`,
  one node per container, the policy's 24-hour lookback, the Receiver's values as rendered.

## The hourly table

Datadog's meter was read at 08:01 UTC and again at 18:04 UTC, which gave the same counts for
01:00 to 07:00 and the first complete count for 08:00. Every complete hour matched the local
count within 16 events.

| Hour (UTC) | Phase | Standard, meter | Flex, meter | Standard, local | Flex, local | Ingested vs baseline | Allowed + allowances | frontend Standard (allowed 1,792) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 01:00 | startup | 13,645 | 10 | 13,639 | 0 | 0.61 | | 1,582 |
| 02:00 | baseline | 22,143 | 0 | 22,144 | 0 | 0.99 | | 3,519 |
| 03:00 | baseline | 22,576 | 0 | 22,570 | 0 | 1.01 | | 3,666 |
| 04:00 | budget from 04:02 | 20,123 | 16,434 | 20,123 | 16,440 | 1.64 | 23,826 | 1,957 |
| 05:00 | budget | 21,020 | 22,090 | 21,028 | 22,093 | 1.93 | 24,166 | 1,774 |
| 06:00 | budget | 22,744 | 42,268 | 22,735 | 42,259 | 2.91 | 25,136 | 1,763 |
| 07:00 | budget | 21,138 | 38,957 | 21,138 | 38,957 | 2.69 | 24,606 | 1,760 |
| 08:00 | budget | 21,080 | 37,651 | 21,080 | 37,635 | 2.63 | 24,196 | 1,770 |

The 01:00 hour holds the 20 routing-check lines (10 in each index). The 06:00 hour is 393
events over the allowed rate alone and inside the allowances.

## What ran, in order (UTC, 2026-10-20)

| Time | Step |
|---|---|
| 01:20 | Routing check: 10 lines with `routeState:tier_down` and 10 with `pass`; the meter counted 10 in `tenx-offload` and 10 in `main` |
| 01:23 | Rig up with the seed policy; 5 users |
| 02:00 to 04:00 | Baseline |
| 04:02:53 | First budget run, X = $10.89 (commit c1d8669) |
| 04:08, 04:27 | Load 12 users, then 24 (12 gave 1.42x) |
| 05:00 | Budget run (409766a) |
| 05:08 | Load 40 users; the demo slowed (below), back to 24 at 05:21 |
| 05:22 (lines from 05:52) | Replay of the baseline capture at 0.8x its own pace, in parallel with the live demo |
| 05:32 to 06:02 | `paymentFailure` 100%; from 05:52 to 06:16 the same payment error line also sent at 2 a second |
| 06:00 | Budget run (538c500): over budget, each statement held at 2,072 an hour |
| 06:17 to 07:17 | New service `inventory`, 2 lines a second, one statement |
| 07:00, 08:00, 09:00 | Budget runs (74739d5, 028813e, 46dda27) |
| 09:05 | Demo down |

## Datadog changes

Two us5 orgs are named "me". The SSM keys `/l1x/tooling/datadog-api-key` and `-pat` reach the
l1x.co user's org (free plan, no Flex, org id 1300662860); the first 20 routing-check lines
(`check:rc-1792458671`) went there and are the only events this run sent to it. The run used
the talw.gx@gmail.com org (public id prefix a982f610, Pro with on-demand usage, Flex Logs
Starter) through `/l1x/tooling/datadog-run-api-key` and `-run-app-key`.

In the run org, before the run: one index `main` (filter `*`, Standard 15 days), one read-only
integration pipeline (`python`, `source:python`), no exclusion filters, archives, log metrics,
custom destinations or monitors, no hosts, and no log usage this month
([`results/datadog-state/`](results/datadog-state/)). Changes, all left in place:

1. Index `tenx-offload`, created by Tal in the UI: filter `@routeState:tier_down`, Standard
   none, Flex 90 days, ordered before `main`; the API reports a daily limit of 200 million
   events on it. Undo: delete the index in the UI.
2. Log monitor 23222383, "tenx ceiling rig: payment error statement in Standard", created at
   05:38:14 with no notification target; its query changed at 06:03:05 to select by
   `@kubernetes.container_name` (see below). Undo: `DELETE /api/v1/monitor/23222383`.
3. Events: 326,871 records from the rig (pass and tier_down, local count) and the 20
   routing-check lines (`check:rc2-1792459230`). The meter counted 264,130 through its last
   read at 08:01.

## Findings

- **Flex events count in the usage metric with `datadog_is_excluded:false`**, tagged
  `datadog_index:tenx-offload`. `standard_indexes` is what keeps them out of spend.
- **The meter lags minutes, not hours, on this org**: a complete hour read 1 to 6 minutes
  after it ended matched the local count within 10 events.
- **A JSON message can remove the service tag.** Datadog parses a JSON message into
  attributes; pino's `service.name` field (payment's lines) replaces the `service` attribute
  the forwarder set, and the usage metric counts those lines under `service:N/A`. A
  `service_budgets` entry for such a service would find no metered spend under its name. The
  monitor's first query (`service:payment`) matched nothing for that reason; selecting by
  `@kubernetes.container_name` fixed it.
- **An error storm's Standard lines rise with the run's level.** Over its limit an error
  statement passes K = 50 more per window, so its lines in Standard are the limit plus 50:
  68, 66 and 69 with the limit at 18, 151 at most with the limit at 138. They reach the
  5-line sample plus 50 only when the level is at the sample.
- **Statement rates read low during growth.** The budget run divides each statement's events
  by the hours its series spans over a 24-hour lookback, so at 07:00 it read 32,447 events an
  hour where about 60,000 arrived. Standard stayed bounded because each service's total is
  written from the allowance and the totals add up to it.
- **The demo saturates near 2x by load alone.** On an 8-CPU Docker VM, 24 users gave 2.0x and
  40 users gave less than 24 (product-catalog at 194% CPU). Growth beyond 2x came from
  replaying the baseline capture alongside the live demo.

## Rig

The containment rig ([`../datadog-containment/rig/`](../datadog-containment/rig/)) with these
differences, all in [`rig/`](rig/):

- **Logs to Datadog.** Fluent Bit sends the Receiver's returned records with `routeState` to
  Datadog's logs intake (`datadog` output, gzip): pass and tier_down; offload would stay local
  and none occurred. `service` is the container. Local per-route files are kept.
- **The Receiver's values** come from log10x-mcp 1.30.71's own functions
  ([`rig/gen-receiver-values.mjs`](rig/gen-receiver-values.mjs)): `receiverFleetValues` with
  `regulator_unit: events` and keep count 50, then the Fluent Bit overlay's `renderValues` with
  the Datadog metrics backend and `policy_git`. The Receiver ran with `rateReceiverUnit events`,
  `rateReceiverKeepCounts` ERROR, CRITICAL and FATAL at 50, `@run/output/metric/datadog`, and
  GH_ENABLED pulling `log10x/policy/*.csv` from `log-10x/config` branch
  `test/datadog-ceiling-policy` ([`results/values/`](results/values/)). Substituted for a
  cluster: env vars the values read from Secrets (GH_TOKEN, DD_API_KEY, DD_APP_KEY) passed from
  the shell by name, and a tmpfs at `/tmp` for the chart's emptyDir.
- **Policy branch.** Seeded by the install's own seed step (`results/values/seed.sh`) with the
  four files and `regulator-unit` = events; deleted after the run. Both workflows in
  `log-10x/config` run on `pull_request` only, so the pushes ran nothing.
- **The budget run** is `tenx-recur` from the 1.30.71 package on a `policy.yaml` written by
  the MCP's own `emitPolicyYaml` ([`rig/gen-policy.mjs`](rig/gen-policy.mjs)), gitops delivery,
  `nodes_by_container` 1 for every demo container; the emitter's default branch name is the
  one substitution. [`rig/budget-run.sh`](rig/budget-run.sh) keeps each run's report, files and
  commit diff; [`rig/budget-phase.sh`](rig/budget-phase.sh) ran them on the hourly preset with
  the load, flag and injection steps.
- **Load.** The load generator's users (`run.sh load`), the replay of the baseline capture and
  the error line at a higher rate (`run.sh replay`, [`rig/forward_send.py`](rig/forward_send.py),
  sent to Fluent Bit over the Forward protocol as the Docker driver sends), the new service
  (`run.sh inject`), and flags through flagd-ui's own storage write (`run.sh flag`).
- **Guards.** Disk floor 4.5 GB, a stop at 2.5 million events sent, and a hard stop; none
  fired. The lowest free disk was 8.6 GB.

Rig effects worth knowing: the replay sends every container under one tag, so a multi-line
group can take a neighbour's line (about 500 email lines landed inside cart and payment
records; the delivery totals are unaffected); the Receiver's windows start at a fixed phase
(201 s past each 240 s epoch slot, measured from the data), which every per-window figure uses.

## Versions

| Part | Version |
|---|---|
| Receiver | `log10x/edge-10x:1.1.146@sha256:4d7be22e5e91ffe344ec9878b45063d21a9c2eb4909799a6d5a7f456db5f0c3a`, its own config and modules |
| MCP | log10x-mcp 1.30.71 from npm (tarball sha256 `a9173584294d1431939faf6066c932a1edf7fbc46958837575e27fafac4569e8`) |
| Demo | opentelemetry-demo 3.1.0, `compose.yaml` + `compose.full.yaml`, `FLAGD_CACHE=disabled` on checkout |
| Forwarder | `fluent/fluent-bit:4.2` |
| Datadog | us5, Pro with on-demand usage, Flex Logs Starter |

## Files

| Path | What it is |
|---|---|
| `results/results.json` | Every measure, from `rig/analyze.py` |
| `results/hourly.csv` | The hourly table with the allowances |
| `results/x.json`, `results/x-method.txt` | X, the frontend number, and how they were set |
| `results/policy.yaml` | The policy the budget runs read |
| `results/budget-runs/<stamp>/` | Each run: the report, the four files and the report as committed, the diff |
| `results/policy-branch-log.txt` | The policy branch's commits |
| `results/meter-hourly-0801.json`, `results/meter-hourly-1804.json` | Datadog's meter, hourly, as read at 08:01 and 18:04 |
| `results/captures/*.tsv.gz` | The rig's captures without log text: container, times, route, hash, statement, level, lines |
| `results/datadog-state/` | The org before the run, and the monitor |
| `results/timeline.jsonl` | Every step with its time |
| `results/values/` | The rendered Receiver values and what was applied |

## Reproduce

Prerequisites: Docker Desktop with about 8 GB for the VM; the demo at tag 3.1.0; the images
above pulled; `rig/load-generator/Dockerfile` built as `rig/load-generator:3.1.0`; log10x-mcp
1.30.71 unpacked with its dependencies installed; a Datadog org with Flex Logs and a Flex-only
index whose filter is `@routeState:tier_down`, ordered before the Standard index; its API and
application keys in SSM (or edit `rig/ddenv.sh`); `gh` signed in with write access to a policy
repo whose workflows do not run on push.

```
export MCP=/path/to/log10x-mcp-1.30.71 RESULTS=$PWD/datadog-ceiling/results
node rig/gen-receiver-values.mjs $RESULTS/values <owner/repo> <branch>
GH_TOKEN=$(gh auth token) bash $RESULTS/values/seed.sh
GH_TOKEN=$(gh auth token) rig/ddenv.sh rig/run.sh up && rig/run.sh wait-healthy
# two full hours of baseline, then X from x-method.txt and:
node rig/gen-policy.mjs $RESULTS/policy.yaml <X> frontend <frontend usd> $RESULTS/policy-clone <branch> <containers>
GH_TOKEN=$(gh auth token) rig/ddenv.sh rig/budget-run.sh
B0=<epoch of that run> USERS_2X=24 USERS_3X=24 GH_TOKEN=$(gh auth token) rig/ddenv.sh rig/budget-phase.sh
rig/run.sh replay start 0.8      # for growth past 2x
rig/ddenv.sh python3 rig/analyze.py   # after the last hour has reported
```

`rig/analyze.py` reads `results/data/` when the full captures are there and the committed
`results/captures/` otherwise; without Datadog keys it reads the saved meter file.
