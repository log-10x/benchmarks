# Datadog Flex Logs accounting

Datadog prices indexing per million events and ingestion per GB, and a pattern routed to Flex Logs stops paying the standard index rate. The 10x engine replayed a 10-hour OpenTelemetry demo capture under plans moving whole patterns to Flex at 30%, 50% and 70% targets. At annual list prices and this capture's volume, every move fell in Flex Starter, where it saves $3.40 to $6.04 a month against 30-day Standard indexing and costs $0.49 to $0.86 more than 15-day indexing.

Standard indexing lists at $1.70 per million events for 15-day retention and $2.50 for 30-day. Flex Starter bills storage and compute together at $0.60 per million stored per month for at least 3 months, so a moved event costs at least $1.80 per million. Ingestion is billed as before.

## Net per month against Standard indexing

Net is the indexing avoided less what Flex Starter adds, with the capture's 10 hours scaled to a 720-hour month.

| Target | Events moved in 10 hours | Share of bytes moved | Net vs 15-day | Net vs 30-day |
|---:|---:|---:|---:|---:|
| 30% | 67,505 | 39.9% | -$0.49 | +$3.40 |
| 50% | 90,555 | 56.1% | -$0.66 | +$4.56 |
| 70% | 119,833 | 71.2% | -$0.86 | +$6.04 |

Datadog's Flex docs give the 3-month minimum. At 6 months, the shortest retention on Datadog's price list, Starter costs $17.50 to $31.06 a month, more than the indexing avoided at either retention.

Each target lands on the first set of whole patterns reaching it, three at 30% and 55 at 70%. None of the moved events was an error or a warning.

## One Datadog index filter per service, at equal events

Each target is compared with the fewest `service:<container>` index filters reaching the events the plan moves.

- At 30%, one filter on `service:opentelemetry-collector` with `-status:(error OR warn)` moves every event the plan moves plus 18,281 more. All but 47 are the part of the three moved patterns that the plan leaves in Standard.
- At 50% and 70%, the filters leave in Standard 23,161 and 11,181 events the plan moves.
- Without the status clause, the filters move 3,953 to 3,955 errors and warnings to Flex, where Datadog runs no log monitors.

## How the events were counted and priced

The capture is [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1), 197,430 lines of Kubernetes output from 36 containers, which the engine groups into 157,228 events. The log10x planning tool wrote each plan as a byte cap per container from a 12,000-line sample. The engine replayed the capture in one 240-second window, each cap multiplied by 15 to cover the plan's hour. Events were counted from the output records and the engine's aggregators, and the run fails if they differ.

## What the accounting leaves out

- Datadog metered nothing. The dollars are the engine's counts at list prices read on 2026-10-13.
- The volume is one small demo cluster's. Above 2 billion events a month Datadog prices Flex compute on request, so only Starter is priced.

## Rerunning the accounting

```
# from the repository root: recompute every figure from the committed counts and prices
python3 datadog-flex-accounting/report.py --check

# full rerun
cd datadog-flex-accounting && ./run.sh
```

The full rerun takes under ten minutes and needs Docker, Node 18 or later, about 1 GB of disk and no Datadog account.

[RECORD.md](RECORD.md) has every rate, the plans, the filter comparison and the counting conditions.
