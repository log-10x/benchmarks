# Per-message-type tier-down to S3-compatible object storage

Measured 2026-09-13 by `run_policy_s3.sh`, ClickHouse 26.8.3.105 with MinIO beside it as
the bucket. The earlier `run_policy.sh` used a second directory on the same filesystem as
the cold volume, which proved the move fires but not that the destination can be object
storage. This one declares the bucket as a ClickHouse disk of `type s3` and repeats the
move. Same three message types, same 300,000 rows over ninety days, same one-line policy:

```sql
TTL Timestamp + toIntervalDay(multiIf(
      templateHash = 'debug_exporter', 1,
      templateHash = 'healthcheck',    7,
      60)) TO VOLUME 'cold'
```

## Where the parts went

| Message type | threshold | parts on S3 | rows on S3 | rows still hot |
|---|---:|---:|---:|---:|
| `debug_exporter` | 1 day | 36 | 96,666 | 3,334 |
| `healthcheck` | 7 days | 36 | 93,332 | 6,668 |
| `order_placed` | 60 days | 18 | 33,330 | 66,670 |

`system.disks` reports the cold disk as `type ObjectStorage`. The bucket itself holds
2,700 objects, 4.8 MiB, listed with the MinIO client rather than inferred from ClickHouse.

## Read back

A query that only S3-resident parts can answer, `debug_exporter` older than thirty days,
returned 66,660 rows with their content. The table still reports 300,000 rows.

## What this settles

The per-type tier-down reaches object storage and the rows stay queryable. The move is one
TTL expression over the message-type column, and it needs nothing else from the product:
no decoder, no view, no compaction.

## What it does not settle

A price. MinIO in a container costs nothing, so the saving is the difference between the
hot disk and the bucket the operator actually uses, which `clickhouse_tierdown_model.py`
in marketing/vp/research works through from list prices. And ClickHouse Cloud, where
storage is already object storage at one price and users do not define storage policies,
so this lever does not exist there.
