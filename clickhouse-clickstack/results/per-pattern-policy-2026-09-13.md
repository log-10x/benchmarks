# Per-message-type retention policy on ClickHouse

Measured 2026-09-13 by `run_policy.sh`, ClickHouse 26.8.3.105 in its own container.
Three message types, 300,000 rows, ages spread over ninety days. Every figure is
read back from `system.parts`, `system.parts_columns` or the table itself after
the policy ran.

## The question

Splunk, Elastic, Datadog, CloudWatch and Azure Monitor each give a log line a
cheaper place to go: a frozen tier, a Flex tier, Infrequent Access, a Basic
table. The assumption worth checking is that ClickHouse offers nothing of the
kind, which would leave deletion as the only lever and make every saving lossy.

That assumption is wrong. ClickHouse's MergeTree TTL grammar is:

```
TTL expr
    [DELETE | RECOMPRESS codec | TO DISK 'x' | TO VOLUME 'x'][, ...]
    [WHERE conditions]
    [GROUP BY key_expr [SET v = aggr_func(v), ...]]
```

Four levers, and three of them keep every line. What ClickHouse has no way to do
is point any of them at a message type, because nothing in a log row says which
message it is. A `templateHash` column supplies that, and the TTL expression is
ordinary SQL, so the policy reads straight off it:

```sql
TTL Timestamp + toIntervalDay(multiIf(
      templateHash = 'debug_exporter', 1,
      templateHash = 'healthcheck',    7,
      60)) TO VOLUME 'cold'
```

One expression, one retention per message type. Below is what each of the four
levers actually did.

## 1. Move to cheaper storage, per message type. Lossless.

A one-day threshold for the noisy type, seven days for the middling one, sixty
for the one worth keeping hot.

| Message type | Threshold | Rows on cold | Rows on hot |
|---|---:|---:|---:|
| `debug_exporter` | 1 day | 96,666 | 3,334 |
| `healthcheck` | 7 days | 93,332 | 6,668 |
| `order_placed` | 60 days | 33,330 | 66,670 |

Every one of the 300,000 rows is still queryable. Only the disk under it changed.

**The trap worth knowing.** A TTL move is decided for a whole part, so a part
holding a spread of ages never expires and nothing moves at all. The first
version of this test partitioned by message type alone and moved zero rows. It
works once the table is partitioned by time as well, which the ClickStack schema
already does with `PARTITION BY toDate(Timestamp)`.

## 2. Roll a message type up into counts. Detail lost, volume kept.

`TTL Timestamp + INTERVAL 30 DAY GROUP BY templateHash SET events = sum(events)`.

| Message type | Rows after | Events still counted |
|---|---:|---:|
| `debug_exporter` | 33,341 | 100,000 |
| `healthcheck` | 33,341 | 100,000 |
| `order_placed` | 33,341 | 100,000 |

Rows older than the threshold collapse into aggregates and the counts survive in
full. This is logs turning into metrics, inside the database, per message type,
with no second pipeline.

## 3. A different retention per message type. Lossy, and chosen.

Seven days for `debug_exporter`, thirty for `healthcheck`, sixty for
`order_placed`, from one expression.

| Message type | Rows kept | Oldest row |
|---|---:|---:|
| `debug_exporter` | 10,002 | 6 days |
| `healthcheck` | 33,340 | 29 days |
| `order_placed` | 66,670 | 60 days |

300,000 rows to 110,012. This is the only lever of the four that discards
anything, and it is the one a person decides deliberately per message type
rather than applying to the whole table.

## 4. Recompress harder, per message type. Lossless, and blocked by ClickStack.

| Table | `Body` bytes | Part codec |
|---|---:|---|
| `recompress_control`, no TTL | 1,664,282 | LZ4 |
| `recompress_policy`, TTL, `Body` declared `CODEC(ZSTD(1))` | 1,663,936 | ZSTD(12) |
| `recompress_nocodec`, TTL, no column codec | 1,629,436 | ZSTD(12) |

**The recompression TTL fires and does nothing.** The part's default codec
becomes ZSTD(12) in both TTL arms, but the column only shrinks when `Body` has
no explicit codec of its own. An explicit column codec wins over the part
default, so `TTL ... RECOMPRESS` is a no-op against it.

The ClickStack schema declares `CODEC(ZSTD(1))` on every column, which disables
this lever for every ClickStack user. A HyperDX user reported exactly this on
2026-06-25: "Adding CODEC(ZSTD(1)) prevents further compression like ZSTD(8)
that can be enabled by TTL RECOMPRESS" (hyperdxio/hyperdx issue 2525). This run
reproduces it.

The 2.1% the working arm saved is not a number to quote. This test's `Body` is
synthetic text that is mostly digits, where ZSTD(12) has little left to find.
The mechanism is what is demonstrated, not the magnitude.

## What this changes

Three of the four levers keep every line, and all four can be addressed per
message type once the rows carry one. The cost story on ClickHouse does not
require throwing anything away.

The ordering a cautious operator would use: recompress first, because nothing is
lost and nothing moves; then tier to object storage, because nothing is lost and
the data stays queryable; then roll up into counts, which trades individual
lines for the volume and rate; and only then a shorter retention, on named
message types, decided one at a time.

## What this does not test

A real cold volume. The `cold` disk here is a second directory on the same
filesystem, which proves the move fires and names a destination; it is not S3
and there is no cost figure attached to it. Real log text, for the recompression
magnitude. And whether an operator would agree to any given policy, which is a
judgement about somebody's own logs.
