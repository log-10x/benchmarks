# clickhouse-inflate

The harness behind the post *We published a ClickHouse benchmark that measured nothing*.

It reproduces, on one command, both halves of that correction:

1. the original benchmark timed `SELECT count()`, and ClickHouse pruned the decode out of the
   plan: 1 row, 24 bytes, zero function nodes in the plan;
2. once the decode is actually forced, the shipped SQL dies of a quadratic lambda capture, and
   the one-line fix takes the same query to 568 ms with a 41 MiB peak, byte-identical output.

Every number in the table below was produced by `./run.sh` on the host described under
[What this was measured on](#what-this-was-measured-on). Nothing here is copied from the post.

## Run it

```bash
./run.sh                # 1 minute end to end on a warm host
SKIP_PREFIX=1 ./run.sh  # skip the two pre-fix out-of-memory probes
KEEP=1 ./run.sh         # leave the container up to poke at it
```

Requires Docker. The script pulls a pinned ClickHouse image, starts a container with a pinned
memory limit, builds the corpus, loads it, installs the SHIPPED (buggy) SQL, probes it, installs
the FIXED SQL, probes that, diffs the two outputs byte for byte, writes `results.json`, and
removes the container.

The two pre-fix probes run until they hit the memory cap and die. How long that takes varies with
memory pressure on the host: between 2 seconds and 10 minutes in our runs. `SKIP_PREFIX=1` skips
them; the pre-fix decode still runs once (under `max_block_size = 64`, where it survives) because
the byte-identity check needs its output.

## Results

Measured with `./run.sh`, ClickHouse 25.8.28.1, 8 GiB container, 8 CPUs, 137,418 rows.
Timings are the average of 3 runs with the first discarded, taken from `system.query_log`.
Full detail in [`results.json`](results.json).

| What | Query | Observed |
|---|---|---|
| The pruned count | `SELECT count() FROM tenx.events` | 18 ms, **read_rows = 1, read_bytes = 24**, **0 function nodes in the plan** |
| Forced decode, PRE-fix | `SELECT sum(length(decoded_log)) FROM tenx.events` | **aborts**, code 241, peak `memory_usage` **7.20 GiB** |
| Forced decode, PRE-fix | `SELECT decoded_log FROM tenx.events FORMAT Null` | **aborts**, code 241, peak `memory_usage` **7.20 GiB** |
| Forced decode, PRE-fix, bounded settings (below) | `SELECT sum(length(decoded_log)) FROM tenx.events` | completes: **4,290 ms, 2.86 GiB peak, 10.6 MiB read** (3 of 3 runs) |
| Forced decode, POST-fix | `SELECT sum(length(decoded_log)) FROM tenx.events` | **568 ms, 41.1 MiB peak** |
| Forced decode, POST-fix | `SELECT decoded_log FROM tenx.events FORMAT Null` | **608 ms, 40.9 MiB peak** |
| Forced decode, POST-fix | same, `tenx.events_native` (format-preserving view) | 657 ms, 78.0 MiB peak |
| Output equality | pre-fix output vs post-fix output, all 137,418 rows | **byte-identical**, 29,065,810 bytes, same sha256 |
| The quadratic term | counted from the corpus and the dictionary | necessary **800,397** array elements, materialized **189,949,597** |
| The template that dominates it | | **818 literals, 275 rows, 96.9%** of the materialized total |

Both pre-fix probes fail with:

```
Code: 241. DB::Exception: (total) memory limit exceeded: would use 7.49 GiB
(attempt to allocate chunk of 4.00 GiB bytes), current RSS: 3.10 GiB, maximum: 6.89 GiB
```

### Making the pre-fix decode finish

The buggy path only completes if the block size is small enough that no single block carries enough
wide-template rows to blow the cap. These are the settings, and a reader has to paste them; there is
no pre-fix full-table decode at ClickHouse defaults:

```sql
SELECT sum(length(decoded_log)) FROM tenx.events
SETTINGS max_block_size = 64, max_threads = 4, max_memory_usage = 6000000000;
-- 4,290 ms, 2.86 GiB peak, 137,418 rows / 11,112,745 bytes read
```

The same query post-fix reads the same 11,112,745 bytes and runs in 548 ms at 41 MiB, at defaults.
The compact events a full decode reads are **10.6 MiB**, not 8.94 MiB.

### Read the abort threshold correctly

The 7.20 GiB is the peak `memory_usage` ClickHouse recorded for the query at the moment it gave
up. It is not a constant of the bug, and it is not the memory cap. Two separate numbers:

- **The cap.** ClickHouse sets `max_server_memory_usage` to
  `max_server_memory_usage_to_ram_ratio` (default **0.9**) times the RAM it can see, and it takes
  the RAM it can see as the smaller of the cgroup limit and the host's `MemTotal`. `run.sh` pins
  the container to 8 GiB, so on any host with at least 8 GiB of RAM the cap is 0.9 x 8 GiB =
  **7.2 GiB**. On the Docker VM used here (`MemTotal` 7.66 GiB, below the 8 GiB cgroup limit)
  ClickHouse capped itself at **6.89 GiB** instead. `run.sh` prints the cap it actually got and
  records it in `results.json`.
- **The peak.** The decode asks for a 4 GiB chunk on top of roughly 3.1 GiB already tracked, so
  the tracker records about 7.2 GiB of would-be usage and throws. That is the 7.20 GiB in the
  table.

The transferable statement is not "it dies at 7.2 GiB". It is: **the pre-fix decode's demand grows
with the square of the template width, so it exceeds whatever cap ClickHouse is running under.**
Without a pinned container it would abort at 0.9 x the machine's RAM, wherever that lands. Pinning
`-m 8g` is what makes the failure identical for every reader.

### Decode nodes in the plan

The post's "zero decode nodes" for the pruned count reproduces in the strongest possible form: the
`SELECT count()` plan contains **no function nodes at all** and reads from
`_minmax_count_projection`. `run.sh` writes the plans to `.work/explain-*.txt`.

The forced-decode plan contains **27 function nodes** pre-fix and **25** post-fix (`EXPLAIN
actions = 1`, counting `FUNCTION` entries in the action DAG). Of those, 5 pre-fix and 8 post-fix
are the decode builtins (`dictGetOrDefault`, `arrayMap`, `arrayStringConcat`, `splitByChar`,
`arrayResize`). The figure of 14 that appears in the post matches neither count on this version and
should not be relied on; the load-bearing claim is that the count plan has none of them.

## What this was measured on

- Image `clickhouse/clickhouse-server:25.8.28.1`, pinned.
- Container: `-m 8g --cpus 8`. Docker Desktop VM with `MemTotal` 7.66 GiB, so ClickHouse's own cap
  came out at 6.89 GiB (see above).
- Query settings: ClickHouse defaults. `max_memory_usage = 0` (per-query limit off, so the server
  cap governs), `max_block_size = 65409`, `max_threads = auto(8)`. The one exception is the pre-fix
  reference decode used for the byte-identity check, which runs at `max_block_size = 64` because
  that is the only way the buggy path finishes at all.

Absolute timings will move with hardware. The shapes will not: the count reads 24 bytes, the pre-fix
decode exceeds the cap, the post-fix decode runs in hundreds of milliseconds at tens of MiB.

## The corpus

`corpus/sample-500.jsonl` is 500 compacted OpenTelemetry-demo Kubernetes log events (the fluentd
JSON envelope, with the log line replaced by `~<templateHash>,<values>`), and
`corpus/templates.json` is the 378 templates they decode against. Both are the sample published in
[log-10x/clickhouse-app](https://github.com/log-10x/clickhouse-app) under `demo/sample/`, produced
by the 10x engine from the OpenTelemetry demo's container logs. Checksums in `corpus/SHA256SUMS`.

`run.sh` cycles that sample to **137,418 rows**, the row count of the table in the post. Cycling
preserves the template mix, so the quadratic term lands exactly where the post says it does: 275 of
the rows carry the 818-literal template (a 21 KB multi-line container startup dump the engine folds
into one event), and that one template accounts for 96.9% of the materialized array elements.

## The SQL

| File | What it is |
|---|---|
| `install-buggy.sql` | `tenx-for-clickhouse/install.sql` as it shipped, verbatim from `main` of log-10x/clickhouse-app (`de67ad6`). The decode lambda indexes into its arrays. |
| `install-fixed.sql` | The same file with the fix, verbatim from the `fix/decode-quadratic-capture` branch (`39e0206`). The arrays are passed as `arrayMap` arguments. |
| `fix-functions-only.sql` | Only the two corrected core functions, used to demonstrate that replacing a function does not fix a view built on it. |

The whole fix is one line per function. Before:

```sql
arrayMap(i -> concat(literals[i], ...), range(1, length(literals)))
```

The lambda reaches `literals`, `slots` and `values` by subscript, so ClickHouse captures those
columns and replicates each of them once per mapped element: a row with N literals materializes N
copies of its N-element arrays. After:

```sql
arrayMap((lit, slot, val) -> concat(lit, tenx_substitute_slot(val, slot)),
         literals,
         arrayResize(slots,  length(literals), ''),
         arrayResize(arrayResize(values, length(slots), ''), length(literals), ''))
```

Arrays passed as arguments are walked element-wise, never replicated.

`run.sh` also checks the second trap the post describes: after `CREATE OR REPLACE FUNCTION` alone,
`SHOW CREATE VIEW tenx.events` still contains the old body (ClickHouse expands function bodies into
a view's stored AST at `CREATE VIEW` time), and the blow-up persists until the views are recreated.
`results.json` records that check as `view_inlining_trap`.

## What this harness does not cover

- The post reports byte-identity on **224,024 rows**, which is this table plus a second, wider
  corpus that is not published. This harness verifies byte-identity on the **137,418 rows** it
  builds, in full, and prints the sha256 of both outputs.
- The post's "wider stress corpus" figures (86,606 rows, 74 slots per row, 6.15 GiB / 19.9 s before
  and 71.9 MiB / 1.5 s after) come from that same unpublished corpus and are not reproduced here.
- The post reports 7,495 ms with a 3.65 GiB peak for the pre-fix `sum(length(decoded_log))`, and
  8.94 MiB read. None of the three reproduce. At ClickHouse defaults that query does not complete
  at all, it aborts. At the bounded settings where it does complete
  (`max_block_size = 64, max_threads = 4, max_memory_usage = 6000000000`) it takes **4,290 ms** with
  a **2.86 GiB** peak and reads **10.6 MiB**.
