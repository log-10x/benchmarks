# Two engine instances on halves of one stream

Written by `bench/engine_split.py`. The protocol of `bench/identity.py`, section 2 of the README, with the 10x engine in place of Drain3: the same sample, seed, split and probe sequence per trial. Each half goes through its own engine container in the order Drain3 receives it, followed by the probe records; the two instances' answers for each probe record are compared.

- image: `log10x/pipeline-10x:1.1.142@sha256:22ae67148bd7f6cbdf171c1b8da1c9c6c801290d43488693dfd8527e27138d05`
- app: `@apps/dev` with its shipped configuration and the image's own symbol library, plus `bench/engine_split.config.yaml`, which writes each event's pattern name, pattern hash and template hash
- trials: 10; probes per trial: 30,000; seed: 100
- records: 197,430; each instance reads its half (98,715 records) and then the 30,000 probes
- engine reference run over the whole stream: 157,228 events, 2,687 pattern hashes, 3,028 template hashes
- the Drain3 column is the strong arm rerun per probe; its counts over all probes equal `results/identity_raw.json` trial by trial

Each cell is the share of probe records on which the two instances agree, a mean across trials. The pattern hash is `tenx_hash`, the hash of the pattern name.

## Under Drain3's strata (the probes of each row in `identity.md`)

All probes:

| line frequency | probes/trial | pattern hash | pattern name | template hash | Drain3 strong, template |
|---|---:|---:|---:|---:|---:|
| seen once | 136 | 1.0000 | 1.0000 | 1.0000 | 0.9859 |
| 2 to 10 | 204 | 1.0000 | 1.0000 | 1.0000 | 0.6022 |
| 11 to 100 | 589 | 1.0000 | 1.0000 | 1.0000 | 0.9118 |
| 101 to 1,000 | 916 | 1.0000 | 1.0000 | 0.9962 | 0.9788 |
| over 1,000 | 28,152 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| all events | 30,000 | 1.0000 | 1.0000 | 0.9998 | 0.9949 |

Probes whose Drain3 shape occurs in both halves:

| line frequency | probes/trial | pattern hash | pattern name | template hash | Drain3 strong, template |
|---|---:|---:|---:|---:|---:|
| 2 to 10 | 164 | 1.0000 | 1.0000 | 1.0000 | 0.6555 |
| 11 to 100 | 589 | 1.0000 | 1.0000 | 1.0000 | 0.9123 |
| 101 to 1,000 | 916 | 1.0000 | 1.0000 | 0.9962 | 0.9788 |
| over 1,000 | 28,152 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| all events | 29,822 | 1.0000 | 1.0000 | 0.9998 | 0.9957 |

## Under the engine's own strata

A probe's frequency is the number of records in the whole stream whose event carries its pattern hash in the reference run.

All probes:

| line frequency | probes/trial | pattern hash | pattern name | template hash | Drain3 strong, template |
|---|---:|---:|---:|---:|---:|
| seen once | 338 | 1.0000 | 1.0000 | 1.0000 | 0.7519 |
| 2 to 10 | 131 | 1.0000 | 1.0000 | 1.0000 | 0.7944 |
| 11 to 100 | 262 | 1.0000 | 1.0000 | 1.0000 | 0.9021 |
| 101 to 1,000 | 319 | 1.0000 | 1.0000 | 0.9896 | 0.9465 |
| over 1,000 | 28,948 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| all events | 30,000 | 1.0000 | 1.0000 | 0.9998 | 0.9949 |

Probes whose pattern hash occurs in both halves:

| line frequency | probes/trial | pattern hash | pattern name | template hash | Drain3 strong, template |
|---|---:|---:|---:|---:|---:|
| 2 to 10 | 93 | 1.0000 | 1.0000 | 1.0000 | 0.8126 |
| 11 to 100 | 262 | 1.0000 | 1.0000 | 1.0000 | 0.9021 |
| 101 to 1,000 | 319 | 1.0000 | 1.0000 | 0.9896 | 0.9465 |
| over 1,000 | 28,948 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| all events | 29,623 | 1.0000 | 1.0000 | 0.9998 | 0.9979 |

## The same line in both halves, no shared traffic

No probe pass: each instance's answers for the records of its own half, fed in the order above. A line is a record's exact bytes. For every record that both instances named as an event of its own (one record long) and whose line also occurs in the other half, the record agrees when every copy of that line the other instance named as an event of its own got the same answer. Binned under Drain3's strata.

Records the feed joined to the record before them are left out: each half is fed shuffled, as Drain3 is, so an indented line follows an unrelated record and joins that record's event, which takes the unrelated record's name. That grouping comes from the shuffle, not from the stream; in the reference run, fed in stream order, 133,173 of 197,430 records are events of their own; in the shuffled halves, 62,274 of 98,715 on average.

| line frequency | records/trial | pattern hash | template hash |
|---|---:|---:|---:|
| 2 to 10 | 15 | 1.0000 | 1.0000 |
| 11 to 100 | 34 | 1.0000 | 1.0000 |
| over 1,000 | 17,432 | 1.0000 | 1.0000 |
| all events | 17,481 | 1.0000 | 1.0000 |

## Falsifier

Fixed before the run: two instances give a probe record the same pattern hash less than 0.99 of the time in a stratum, under Drain3's strata.

- seen once: 1.0000, not triggered
- 2 to 10: 1.0000, not triggered
- 11 to 100: 1.0000, not triggered
- 101 to 1,000: 1.0000, not triggered
- over 1,000: 1.0000, not triggered

## Disagreements

Of 300,000 probe records, 3 got different pattern hashes from the two instances and 44 more got the same pattern hash and different template hashes. Every one is in `results/engine_split_raw.json` with both answers and the event that held it.

Different pattern hashes:

| trial | probe position | instance A: pattern, records in event | instance B: pattern, records in event | log |
|---:|---:|---|---|---|
| 10 | 0 | `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_a`, 5 | `metrics_data_points_docker_kubernetes`, 4 | `      GetCartAsync called with userId=` |
| 10 | 1 | `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_a`, 5 | `metrics_data_points_docker_kubernetes`, 4 | `      GetCartAsync called with userId=e1a51f7e-9f44-11f0-9b9` |
| 10 | 2 | `Deleted_producer_state_snapshot_tmp_kafka_logs_cluster_org_a`, 5 | `metrics_data_points_docker_kubernetes`, 4 | `}` |

Same pattern hash, different template hashes, by pattern:

| pattern | probe records | trials |
|---|---:|---:|
| `notify_retry_canceled_due_unrecoverable_error_after_attempts_SMTP_not_configured_check_you` | 44 | 2 |
