# ClickHouse Cloud elasticity

ClickHouse Cloud bills compute by the unit, so fewer rows show on the bill only when they let the autoscaler step down a size. One service took two feeds in four pairs of runs: the full feed of a 215 MB OpenTelemetry capture, then the 65.3% of its rows the 10x engine kept. From a 4-unit start, the kept rows took the service to 3 units in three pairs, and billed compute settled at 0.749 of the full feed's rate. The step came 2.9 to 4.3 hours after the cut, and until then both feeds paid for 4 units. From a 3-unit start, the same cut changed nothing in 10.25 hours.

## Units and billed compute in each pair

| Pair | Full feed's size set by | Units, full feed to kept rows | Billed $ per 15 min | Hours from cut to step down |
|---|---|---:|---:|---:|
| 1 | the autoscaler | 4.0 to 2.997 | 0.298 to 0.224 | 4.33 |
| 2 | the autoscaler, after pair 1 | 3.0 to 3.0 | 0.224 to 0.224 | no step in 10.25 |
| 3 | a 16 GiB minimum | 4.0 to 3.0 | 0.298 to 0.224 | 4.21 |
| 4 | a 16 GiB minimum | 4.0 to 3.0 | 0.298 to 0.224 | 2.91 |

Billed compute is the usageCost API's 15-minute postings, $1.196 an hour at 4 units against $0.896 at 3. Rows fell to 0.653, and the service made one step, from 16 to 12 GiB per replica, which is 0.75.

- A service at its minimum saves nothing. Below the load that lifts the full feed off 2 units, between 50,000 and 70,000 rows a second, both feeds cost $0.60 an hour.
- Why pair 4 stepped down 1.3 hours sooner than pairs 1 and 3 was not measured.

## The autoscaler's CPU band

By its documentation, the autoscaler takes no action between 37.5% and 75% CPU. On 4 units the busiest replica ran at a median 0.440 to 0.486 of its CPU with the full feed, inside the band, and 0.337 to 0.351 with the kept rows, below it. In pair 2, on 3 units, both feeds stayed inside the band, at 0.637 and 0.455.

## How the service and its bill were read

The service ran on the Scale tier in AWS us-east-1, ClickHouse 26.6, with 2 replicas autoscaling from 8 to 32 GiB each, where a unit is 8 GiB and 2 vCPUs. Both feeds wrote into the ClickStack `otel_logs` schema under seven queries a minute, the full feed at 70,000 rows a second and the kept rows at 45,716. In pairs 3 and 4 a 16 GiB minimum set the full feed's size and was lowered to 8 GiB at the cut, so each step down was the autoscaler's own. Size and CPU were read every 60 seconds and billed compute every 10 minutes.

## Limits

- One service shape in one region, with a fixed query load.
- Both feeds were inserted from staged tables, so neither the engine nor network insert parsing ran live.
- Which replica the autoscaler reads, and how often it decides, was not measured.

## Run it

The pair ratios recompute offline from the committed logs:

```
cd clickhouse-cloud-elasticity
python3 cloud/arms_report.py --raw results/raw --lag-min 30
```

A full rerun needs a ClickHouse Cloud API key, Docker and a `clickhouse` client, and this run spent $42.61 of credit. [RECORD.md](RECORD.md#rerun) has the rerun steps, and [RESULT.md](RESULT.md) every figure with its source.
