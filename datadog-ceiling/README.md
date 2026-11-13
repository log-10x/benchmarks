# Datadog ceiling

Datadog's own usage metric showed Standard indexing staying at a set number while ingested events grew 2.6 to 2.9 times on synthetic traffic, and Flex took the rest. A pattern routed to Flex stops paying the standard index rate. The lines stay queryable in Datadog's own Log Explorer, with no rehydration step.

Setting a monthly number of Standard-indexed events comes first. An hourly run reads Datadog's usage metric month to date and writes a cap per pattern and a total per container into the policy the sidecars read, and a container the run has not seen yet keeps the level the known containers share. A pattern's first five events of each window stay in the standard tier, and an error pattern over its cap keeps 50 more there in each window on each node, so a monitor on an error keeps firing.

## Result

Events an hour on 2026-10-20 (UTC), as Datadog's usage metric counted them. The budget allowed 22,351 an hour in Standard.

| Hour | Phase | Standard | Flex | Ingested vs baseline |
|---|---|---:|---:|---:|
| 02:00 | baseline | 22,143 | 0 | 0.99x |
| 03:00 | baseline | 22,576 | 0 | 1.01x |
| 04:00 | budget on | 20,123 | 16,434 | 1.64x |
| 05:00 | budget on | 21,020 | 22,090 | 1.93x |
| 06:00 | budget on | 22,744 | 42,268 | 2.91x |
| 07:00 | budget on | 21,138 | 38,957 | 2.69x |
| 08:00 | budget on | 21,080 | 37,651 | 2.63x |

Four of the five budgeted hours came in under the allowed rate. The 06:00 hour was 393 events over it, inside the allowance for sample lines and error lines, which came to between 1,475 and 2,785 events an hour.

- During an error storm, a log monitor on the storming statement went to Alert at 06:03:43 and back to OK at 06:22:43, after the storm ended.
- 381,856 of 381,856 lines reached Datadog.

## How it was measured

The application is the OpenTelemetry demo, sending to a real Datadog org with Standard indexing at 15-day retention and one Flex index. The engine marks the events that should move with an attribute, and a Flex-only index whose filter matches that marker receives them, because Datadog indexes are first match wins and that index is ordered before the catch-all. Two baseline hours ran with no limits. Then the budget was switched on and load was raised.

Every number in the table comes from `datadog.estimated_usage.logs.ingested_events`, filtered to `datadog_is_excluded:false` and split by `datadog_index`.

## Limits

- One run of under eight hours, on a demo application, with a budget of $10.89 a month.
- Ingestion is billed as before, and Flex charges its own lower rate for storage plus compute for the queries that read it.
- Datadog runs no log monitors on Flex. Queries there run on Flex compute and are slower than the standard index.

## Run it

The table can be recomputed from the committed files without a Datadog account:

```
cd datadog-ceiling
python3 rig/analyze.py
```

A full rerun needs Docker, a Datadog org with Flex Logs and about eight hours. The steps are in [RECORD.md](RECORD.md#reproduce).

The complete record of the run is in [RECORD.md](RECORD.md): every check, how the budget was set, each hourly budget file and the rig.

The same measurement, with more context: https://www.log10x.com/blog/cut-datadog-log-bill-per-pattern/
