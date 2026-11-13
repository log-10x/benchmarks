# CloudWatch Logs Infrequent Access accounting

When a log10x plan moves CloudWatch events out of a Standard log group, to Infrequent Access or to S3, how many bytes move and what do they cost? On a ten-hour OpenTelemetry demo capture, the plan for a 30% target moved 69.7% of the bytes to Infrequent Access, where ingest costs $0.25 a GB instead of $0.50. The figures are the 10x engine's counts, priced at us-east-1 list rates.

Infrequent Access halves the ingest rate and keeps the $0.03 per GB-month storage price, so a bill cut made by moving bytes there takes about twice that share of the bytes.

## Result

Where the engine sent the capture's 0.215 GB at each target.

| Target | Bill share the plan states | GB to Infrequent Access | GB to S3 | Share of bytes moved |
|---:|---:|---:|---:|---:|
| 30% | 30.4% | 0.150 | 0.000 | 69.7% |
| 50% | 56.9% | 0.067 | 0.099 | 77.4% |
| 70% | 70.6% | 0.002 | 0.165 | 77.7% |

At 50% and 70% the plan also sends whole containers to S3, where a GB costs nothing to ingest and $0.023 a month to store. At 70% nearly all moved bytes went there.

- The 30% target moved no errors or warnings. At 50% and 70%, 53 and 51 error events went to S3 with their container, since the engine keeps only half of the error events over a cap.
- At 30% the engine moved 0.150 GB to Infrequent Access where the plan states 0.136 GB, because the plan works from a 12,000-line sample and the engine counts the whole capture.

## How it was measured

The data is a public capture of Kubernetes container output from the OpenTelemetry demo, 197,430 lines from 36 containers. For each target, the log10x planning tool sampled it and wrote a byte cap and destination per container, and the engine replayed the whole capture against them. Bytes are the UTF-8 size of each emitted record, which the forwarder sends as the event message CloudWatch bills. Every count was taken from the emitted records and from the engine's aggregators, and the run fails if they differ.

## Limits

- No AWS bill or usage meter was read. Dollars use list prices read on 2026-10-11.
- The dollar figures are small because the capture comes from one small demo cluster. The share of bytes moved depends on how its logs spread across patterns.
- An Infrequent Access log group lacks metric filters, subscription filters, Live Tail, Anomaly Detection and more, so logs that feed one of these lose it when moved. Logs Insights queries still run, apart from four commands.
- The kept share of each severity is drawn at random per event, so a rerun gives slightly different counts.

## Run it

```
cd cloudwatch-ia-accounting
python3 report.py --check   # recompute every figure from the committed counts
./run.sh                    # the full run: plan, replay, count, report
```

The check needs only Python 3. The full run needs Docker, Node 18 or later and about 1 GB of disk, takes under ten minutes and needs no AWS account.

[RECORD.md](RECORD.md) has the full record: planned against moved bytes per container, every feature Infrequent Access lacks, and the counting rules.
