# Datadog ceiling

Does a monthly budget for Datadog Standard indexing stay where it was set when log volume grows two to three times? In this run it did. Log volume grew to 2.9 times the baseline, Standard indexing stayed at the budgeted rate, and every line still reached Datadog.

The limit is set per log statement. Each hour, month-to-date usage is read from Datadog's own usage metric and a limit is written for every statement. Lines over a statement's limit go to a Flex index, so they stay searchable in Datadog. An error statement keeps 50 extra lines a window in Standard, so monitors on errors still fire.

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

Three more checks from the same run:

- A service that first appeared mid-run was limited from its first window. Of its 476 lines a window, 31 went to Standard until the 07:00 update gave it a limit of its own.
- During an error storm, a log monitor on the storming statement went to Alert at 06:03:43 and back to OK at 06:22:43, after the storm ended.
- 381,856 of 381,856 lines reached Datadog.

## How it was measured

The application is the OpenTelemetry demo, sending to a real Datadog org with Standard indexing at 15-day retention and one Flex index. Two baseline hours ran with no limits. Then the budget was switched on and load was raised.

Every number in the table comes from `datadog.estimated_usage.logs.ingested_events`, filtered to `datadog_is_excluded:false` and split by `datadog_index`. The rig's own counts agreed with that metric to within 16 events an hour.

## Limits

- One run of under eight hours, on a demo application, with a budget of $10.89 a month. The run shows the level staying put under growth and says nothing about money saved on a real bill.
- Logs only. Hosts, custom metrics and APM are outside this benchmark.
- Lines over the limit go to Flex, which has its own price and its own query compute. Datadog monitors do not run on Flex logs, and the org needs Flex Logs on its plan.

## Run it

The table can be recomputed from the committed files without a Datadog account:

```
cd datadog-ceiling
python3 rig/analyze.py
```

A full rerun needs Docker, a Datadog org with Flex Logs and about eight hours. The steps are in [RECORD.md](RECORD.md#reproduce).

The complete record of the run is in [RECORD.md](RECORD.md): every check, how the budget was set, each hourly budget file and the rig.
