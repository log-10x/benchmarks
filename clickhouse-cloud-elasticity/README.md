# ClickHouse Cloud elasticity

When a ClickHouse Cloud service is sent fewer log rows, how far does its compute bill fall, and how soon? In three of four paired runs, writing 65.3% of the rows took the service from 4 units to 3, and billed compute settled at 0.749 of the full feed's rate. The step came 2.9 to 4.3 hours after the cut, and until then both arms paid for 4 units. In the other, which started at 3 units, the same cut changed nothing in 10.25 hours.

The autoscaler's documented rule explains the difference: between 37.5% and 75% CPU it takes no action. On 4 units the busiest replica ran at a median 0.440 to 0.486 of its CPU with every row and 0.337 to 0.351 with the kept rows, below the band. On 3 units both arms stayed inside the band.

## Result

One unit is 8 GiB and 2 vCPU. Arm A writes every row, arm B the 65.3% the 10x engine kept.

| Pair | Arm A's size set by | Settled units, A to B | Billed $ per 15 min, A to B | Hours from cut to step down |
|---|---|---:|---:|---:|
| 1 | the autoscaler | 4.0 to 2.997 | 0.298 to 0.224 | 4.33 |
| 2 | the autoscaler, after pair 1 | 3.0 to 3.0 | 0.224 to 0.224 | no step in 10.25 |
| 3 | config, released at the cut | 4.0 to 3.0 | 0.298 to 0.224 | 4.21 |
| 4 | config, released at the cut | 4.0 to 3.0 | 0.298 to 0.224 | 2.91 |

The billed rate is $1.196 an hour at 4 units against $0.896 at 3. Size fell to 0.75 while rows fell to 0.653, because the service made one step, from 16 GiB to 12 GiB per replica.

- The autoscaler's documented scale-down window is 3 hours. Why pair 4 stepped 1.3 hours sooner than pairs 1 and 3 was not measured.
- Below the load that lifts the full feed off the 2-unit minimum, between 50,000 and 70,000 rows a second, both arms cost $0.60 an hour.

## How it was measured

The service ran on the Scale tier in AWS us-east-1, ClickHouse 26.6, with 2 replicas autoscaling from 8 to 32 GiB each. Both arms wrote into the ClickStack `otel_logs` schema under seven queries a minute. Arm A replayed all 171,807 records of a 215 MB OpenTelemetry sample at 70,000 rows a second, arm B the 112,205 kept rows at 45,716. In pairs 3 and 4, config pinned arm A at 16 GiB per replica until the cut, so each step down was the autoscaler's own. Size and CPU were read every 60 seconds, dollars from the usageCost API every 10 minutes.

## Limits

- One service shape in one region, with seven queries a minute instead of a production mix.
- Both arms inserted from staged tables, so neither the engine nor the parsing of network inserts ran live.
- Which replica the autoscaler reads, and how often it decides, was not measured.

## Run it

The pair ratios recompute from committed logs:

```
cd clickhouse-cloud-elasticity
python3 cloud/arms_report.py --raw results/raw --lag-min 30
```

A full rerun needs a ClickHouse Cloud API key, Docker and a `clickhouse` client, and this run spent $42.61 of credit. The steps are in [RECORD.md](RECORD.md#rerun).

[RECORD.md](RECORD.md) has the run summary and rerun steps, and [RESULT.md](RESULT.md) every figure with the file it came from.
