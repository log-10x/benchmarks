# Datadog Flex Logs accounting

When the 10x engine moves Datadog log events from Standard indexing to Flex Logs, does the move save money at list price? On a 10-hour OpenTelemetry demo capture of 157,228 events, plans targeting 30%, 50% and 70% of the volume moved 67,505 to 119,833 events, none of them errors or warnings. At this volume every move lands in Flex Starter, which saves money against 30-day Standard indexing and costs more than 15-day indexing.

On annual pricing, Standard indexing lists at $1.70 per million events for 15-day retention and $2.50 for 30-day. Flex Starter lists at $0.60 per million stored per month for at least 3 months, so a moved event costs at least $1.80 per million. That sits between the two indexing prices.

## Result

Net is the Standard indexing avoided minus what Flex Starter adds, per month at this capture's volume, and a minus means the move costs more than it saves.

| Target | Events moved to Flex | Share of bytes moved | Net vs 15-day | Net vs 30-day |
|---:|---:|---:|---:|---:|
| 30% | 67,505 | 39.9% | -$0.49 | +$3.40 |
| 50% | 90,555 | 56.1% | -$0.66 | +$4.56 |
| 70% | 119,833 | 71.2% | -$0.86 | +$6.04 |

The dollars are small because the demo cluster is small.

Against Datadog's own index filters, one per service and matched on events:

- At 30%, one filter on `service:opentelemetry-collector` with `-status:(error OR warn)` does nearly the same job. Of the 18,281 extra events it moves, 47 come from patterns the plan leaves entirely in Standard.
- At 50% and 70%, the filters leave 23,161 and 11,181 events in Standard that the plan moves.
- Without the status clause, every filter set moves 3,953 to 3,955 errors and warnings to Flex.

## How it was measured

The capture is Kubernetes output from 36 OpenTelemetry demo containers, 197,430 lines (157,228 events after multi-line grouping) and 0.215 GB. For each target, `log10x-mcp` sampled 12,000 lines and wrote a plan that moves whole log patterns. The released 10x engine replayed the full capture under that plan, counting every event from its output records and its own aggregators, and the run fails if the two differ. Dollars are those counts at Datadog list prices read on 2026-10-13. Datadog metered nothing.

## Limits

- One small demo capture, replayed rather than sent to Datadog. Monthly dollars scale its 10 hours to a 720-hour month.
- Only Flex Starter is priced. Above 2 billion events a month, Datadog prices Flex compute on request.
- Datadog's price list gives Starter retention as 6, 12 or 15 months, and its Flex docs add the 3 the table uses. At 6 months Starter costs $17.50, $23.47 and $31.06 a month, more than the indexing avoided at either retention.

## Run it

```
# from the repository root: recompute every figure from the committed counts and prices
python3 datadog-flex-accounting/report.py --check

# full rerun
cd datadog-flex-accounting && ./run.sh
```

The full rerun needs Docker, Node 18 or later and about 1 GB of disk. A run takes under ten minutes and needs no Datadog account.

[RECORD.md](RECORD.md) has every price source, the plan and engine files per target, the full filter comparison and the counting conditions.
