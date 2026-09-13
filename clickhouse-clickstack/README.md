# clickhouse-clickstack

What does the 10x compact form cost or save on disk in **ClickHouse's own
recommended log schema**, measured the way a ClickHouse engineer would ask for it.

The question is narrow on purpose. ClickHouse has published its own log
compression work: [178x on nginx with typed columns][nginx] (52x once ordered by
time, "more representative of actual usage"), and [19x to 22x from Drain3 log
clustering, 45x with per-service typed tables][clustering]. Against that, a
compression claim measured on a single `String` column is not a claim a
ClickHouse engineer has any reason to read. So this benchmark uses the
[ClickStack `otel_logs` schema][clickstack] as published: typed columns,
`LowCardinality`, the two attribute maps, all eight skip indexes, `ZSTD(1)`, and
`ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)`.

## Run it

```bash
./run.sh              # everything, reusing whatever is already in data/
FRESH=1 ./run.sh      # drop the cached engine output and rebuild it
KEEP=1 ./run.sh       # leave the ClickHouse container up afterwards
```

Needs Docker, about 4 GB of free disk and roughly 20 minutes on a warm host. It
writes `results/results.json` and `results/clickstack-storage-<date>.md`.

## Three arms, because two would hide something

The engine folds a multi-line event (a stack trace, a config dump) into one
event. That changes the row count, and a single ratio between "raw" and
"compact" would carry both the folding and the templating inside one number
without saying so. Three arms take them apart.

| Arm | Rows | `Body` | Everything else |
|---|---|---|---|
| `native` | one per captured line | that line's message | from that line's envelope |
| `compact` | one per compact event | `~<templateHash>,<values>` | from the same envelope |
| `native_folded` | one per compact event | the original text of that event | identical to `compact` |

`native` against `compact` is what a deployment sees. `native_folded` against
`compact` holds the row count and every other column fixed, so it is the
templating layer on its own. `native` against `native_folded` is the folding on
its own. The results file reports all three and states both row counts every
time it states a ratio.

The compact arm's total also carries the template dictionary, without which the
arm cannot be read.

## INNER encode, not OUTER

The public `otel-sample-v2` release ships an OUTER-mode encoding: the template
covers the whole Fluentd JSON record, so the compact event has no envelope left
to map into `ServiceName`, `ResourceAttributes` and `LogAttributes`. Putting that
form in `Body` and then filling the attribute columns from the raw record would
put the Kubernetes metadata on the compact side twice.

So `run.sh` re-encodes the same released capture in **INNER** mode with
[`tenx-encode-inner.config.yaml`](tenx-encode-inner.config.yaml): the envelope
stays JSON and only the `log` value is compacted. That is also the only mode the
ClickHouse app supports ("The plugin requires INNER encode mode; OUTER encode is
not supported on ClickHouse"), and it is the shape of the corpus in
[`../clickhouse-inflate/corpus/`](../clickhouse-inflate/corpus/). The source
logs are the released capture either way, and its sha256 is checked on every run.

## How the two arms are aligned

A compact event covers K consecutive captured lines. K is recovered exactly from
the event's own template, because the engine joins folded lines with a newline
and the template carries K-1 of them. `build_arms.py` refuses to write anything
unless both invariants hold on every record:

1. the line count reconstructed this way equals the number of lines in the capture;
2. the envelope of each compact record, every field except `log`, is byte-identical
   to the envelope of the first captured line it covers.

## The timestamp

The Fluentd envelope has no timestamp field; the time is inside the message. This
benchmark does not write a second timestamp parser. It reads the one the engine
already produced: a template with a timestamp slot carries that slot's value as
an epoch integer in the compact event, and the scale comes from the digit count.
84.6% of compact events carry one; for the rest the last value seen for that
container is carried forward. Every arm gets the same value for the same event,
so `ORDER BY` and `PARTITION BY` see the same data in each.

## The decode path

The compact form itself is lossless: the engine's round trip on this capture
returns all 215,039,161 bytes byte-identical, which
[`../otel-denominators/`](../otel-denominators/) reproduces in one command. What
is broken is the SQL that reads it back inside ClickHouse, which this benchmark
measures and `reference_decode.py` diagnoses.

The compact arm is read through the **corrected** inflate functions in
[`../clickhouse-inflate/install-fixed.sql`](../clickhouse-inflate/install-fixed.sql),
not the ones `log-10x/clickhouse-app` ships. The shipped `tenx_inflate_core`
builds its result with an index lambda that captures the `literals` and `slots`
arrays; that is quadratic and aborts a full-table decode at 7.2 GiB.
[`../clickhouse-inflate/`](../clickhouse-inflate/) has that measurement. The fix
has not been applied back to the product repo.

## The second rung: `run_typed.sh`

`run.sh` stores the compact event the way the ClickHouse app does today, as one
text string in `Body`. ClickHouse's own [log-clustering post][clustering] measured
that shape at 22x against 19x raw, and 45x once the template sat in a
low-cardinality column and the values in typed columns. `run_typed.sh` climbs
the same ladder on the same events, against the container `KEEP=1 ./run.sh`
leaves up:

| Layout | What changes |
|---|---|
| `compact_sorted` | the template hash materialised and added to ClickStack's sort key; `Body` unchanged |
| `compact_typed` | `Body` replaced by the hash plus typed value arrays, same sort key |
| `compact_typed_bytemplate` | the typed layout sorted by (service, template, time) |

`build_typed.py` splits every compact event into timestamp, integer and text
arrays, and refuses to write if any row does not reverse to its compact event
byte for byte; `run_typed.sh` rebuilds the events again inside ClickHouse and
compares hash sums with the text form. Ingest cost is measured table-to-table
with `INSERT ... SELECT`, three copies per layout, so no arm pays a JSON-parsing
cost and the CPU is what ClickHouse spends building and compressing that layout.

The result is in `results/typed-layout-<date>.md`. In short: the generic typed
arrays compress the payload worse than the text string, the template hash in the
sort key is the one cheap real win, and the large total savings all come from
ClickStack's full-text index on `Body` shrinking or disappearing rather than from
the data compressing better.

## The compute question: `run_compute.sh`

Storage is not where a ClickHouse bill is. ClickHouse Cloud meters compute per
unit-hour and storage at **$25.30 per compressed TB per month**, so an estate of
ordinary size carries tens of dollars of storage and the compute line is the
bill. `run_compute.sh` asks whether the product can move compute.

The claim under test is that compute follows row count, so removing rows is a
lever and making each row smaller is not. The falsifier is stated in the script
before the run: if halving the rows does not roughly halve insert-plus-merge
CPU, the claim is wrong.

Every arm holds the same original log text in the same schema; only the rows
present change. `sampled_75/50/25` is a seeded uniform sample, which holds the
content mix fixed and isolates row count. `bypattern_75/50/25` removes whole
message types largest first, which is the lever the product pulls. Inserts
arrive in batches of a fixed number of rows, so an arm with half the data sends
half the batches, and merges run on their own and are read from
`system.part_log`. Each arm loads three times after a discarded warm-up, fastest
kept.

Result: half the rows cost 39% of the CPU and a quarter cost 17%, both below the
row share, because fewer parts merge fewer times. Full detail in
`results/compute-vs-rows-<date>.md`.

## Per-message-type policy: `run_policy.sh`

Every other destination gives a log line a cheaper place to go, and the
assumption worth checking is that ClickHouse gives it none, leaving deletion as
the only lever. ClickHouse's own TTL grammar says otherwise: `DELETE`,
`RECOMPRESS codec`, `TO DISK`, `TO VOLUME`, plus `WHERE` and `GROUP BY`. Four
levers, three of which keep every line. What ClickHouse cannot do is aim any of
them at a message type, because nothing in the row says which message it is.

`run_policy.sh` adds a `templateHash` column and drives all four from one
expression over it, on its own small container in about two minutes. Results in
`results/per-pattern-policy-<date>.md`. In short: moving to a cheaper volume,
rolling up into counts and per-type retention all work per message type;
recompression fires and does nothing, because an explicit column codec beats the
part default and the ClickStack schema declares `CODEC(ZSTD(1))` on every
column, which reproduces hyperdxio/hyperdx issue 2525.

Two traps it surfaces for anyone writing these policies. A TTL move is decided
for a whole part, so a table not partitioned by time moves nothing at all. And a
column codec silently disables `TTL ... RECOMPRESS` against that column.

## What it does not measure

- **Ingest over the wire.** Each arm is loaded from a JSONEachRow file, so the
  CPU figure includes parsing a payload that is a different size in each arm. It
  is reported as that and not as collector-to-ClickHouse ingest.
- **Retention.** The published DDL ends in a `${TABLES_TTL}` placeholder, which
  has no value outside a ClickStack install. The TTL clause is dropped; nothing
  else in the DDL is changed.
- **Per-service typed tables.** ClickHouse's 45x figure comes from one table per
  service with the variable fields promoted to typed columns. This is the single
  `otel_logs` table, which is what ClickStack installs by default.

## Layout

| File | What |
|---|---|
| `run.sh` | the whole run: fetch, encode, map, load, measure, report |
| `tenx-encode-inner.config.yaml` | the INNER encode config |
| `build_arms.py` | the mapping into the ClickStack schema, and the alignment checks |
| `schema.sql.tpl` | the ClickStack DDL with the codec substituted |
| `report.py` | reads `system.parts`, `system.parts_columns`, `system.query_log` and writes `results/` |
| `run_typed.sh` | the second rung: sort key, typed arrays, clean ingest cost, against the container `run.sh` left up |
| `build_typed.py` | splits compact events into typed arrays, reversing every row before writing |
| `report_typed.py` | writes `results/typed-layout-<date>.md` |
| `run_compute.sh` | does compute follow rows: seven arms, batched inserts, background merges |
| `build_reduction.py` | labels every captured line with its message type and builds the reduction arms |
| `report_compute.py` | writes `results/compute-vs-rows-<date>.md` |
| `run_policy.sh` | the four TTL levers driven per message type, on its own container |
| `reference_decode.py` | decodes the same events with the four rules `install.sql` lacks, to tell a lost original from a misread one; `--self-test` runs in CI |
| `results/` | `results.json` and the dated results file |

[nginx]: https://clickhouse.com/blog/log-compression-170x
[clustering]: https://clickhouse.com/blog/improve-compression-log-clustering
[clickstack]: https://clickhouse.com/docs/use-cases/observability/clickstack/ingesting-data/schemas
