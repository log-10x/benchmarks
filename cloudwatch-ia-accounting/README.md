# CloudWatch Logs Infrequent Access accounting

The expensive line on a CloudWatch Logs bill is ingestion, the charge for each GB ingested, with storage after it costing far less. The Infrequent Access log class ingests at half the Standard rate, $0.25 a GB against $0.50 in us-east-1, and an event offloaded to S3 pays no CloudWatch ingestion. Under a log10x plan to cut the bill 30%, the 10x engine moved 69.7% of the bytes of a ten-hour OpenTelemetry demo capture to Infrequent Access.

A log group's class is fixed at creation, so the forwarder sends the events the engine marks to a second log group in the Infrequent Access class. The classes differ in ingestion cost only, so a cut made there takes about twice its share of the bill in bytes.

## What left the Standard log class

| Target | Bill share the plan states | GB to Infrequent Access | GB to S3 | Share of bytes moved |
|---:|---:|---:|---:|---:|
| 30% | 30.4% | 0.150 | 0.000 | 69.7% |
| 50% | 56.9% | 0.067 | 0.099 | 77.4% |
| 70% | 70.6% | 0.002 | 0.165 | 77.7% |

At 50% and 70% the plans also send whole containers to S3, at $0.023 per GB-month to store. Both left 0.048 GB in Standard.

- The 30% plan moved no errors or warnings. At 50% and 70%, 53 and 51 ERROR events went to S3 with their containers, since the engine keeps half the ERROR events over a cap.
- The plan works from a 12,000-line sample, so at 30% the engine moved 0.150 GB to Infrequent Access against the plan's 0.136 GB. At 70% the plan states 0.030 GB and the engine marked 0.002 GB, because offload acts on the whole container, including patterns the plan lists for Infrequent Access.

## How the event message bytes were counted

The capture is 0.215 GB, 197,430 lines of output from 36 Kubernetes containers in a cluster running the OpenTelemetry demo. For each target, the log10x planning tool wrote a byte cap and an action per container, and the engine replayed the whole capture, moving each pattern's bytes over its cap. Caps apply per 240-second window and the replay fits inside one, so each cap was multiplied by 15 for the hour the plan covers. Bytes are the UTF-8 size of each emitted record, which the forwarder sends as the event message CloudWatch bills.

## Limits

- No AWS bill or usage meter was read. Dollars are list prices read on 2026-10-11.
- The GB figures come from one small demo cluster, and only the per-GB rates carry to another account.
- AWS's log class table lists metric filters, subscription filters, Live Tail and Anomaly Detection among the features Infrequent Access lacks.
- Each severity's kept share is drawn at random per event, so reruns differ slightly.

## Run it

```
cd cloudwatch-ia-accounting
python3 report.py --check   # recompute every figure from the committed counts
./run.sh                    # the full run: plan, replay, count, report
```

The check needs only Python 3. The full run needs Docker, Node 18 or later and about 1 GB of disk, takes under ten minutes and needs no AWS account.

[RECORD.md](RECORD.md) has each plan's actions by container, a month at this volume, and every feature Infrequent Access lacks.
