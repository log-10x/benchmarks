# 10x compact events in ClickHouse's own ClickStack schema

Measured 2026-09-13 by `run.sh` in this folder. Every byte count is read from `system.parts`, `system.parts_columns` or `system.data_skipping_indices` after `OPTIMIZE FINAL`; every timing is `query_duration_ms` from `system.query_log`. Nothing here is copied from a post.

## The five lines

1. **Body column at ZSTD(1), row for row: 1,865,254 to 1,426,008 bytes, 23.55%.** Same 159,170 rows and the same attribute values on both sides, so this is the templating layer alone.
2. **Whole table at ZSTD(1): 8,225,547 to 6,999,850 bytes, 14.9%,** on 197,430 rows against 159,170 rows. The compact figure includes the template dictionary (348,040 bytes on disk). The row counts differ because the engine folds a multi-line event into one event; that reduction is inside this number and outside line 1.
3. **One text filter on `checkout`: 6 ms native, 531 ms compact through the ISO expand path, 590 ms through the format-preserving one.** Fastest of ten, first run discarded; see the timing table for the spread.
4a. **LZ4:** Body 21.31%, whole table 14.36% (8,526,421 to 7,301,881 bytes).
4b. **ZSTD(3):** Body 21.91%, whole table 13.86% (7,374,889 to 6,353,017 bytes).
5. **It would not survive one, and the storage figure is not the reason.** 124,220 of 159,170 rows, 78.0%, do not expand back to the text they came from, because the shipped SQL decoder implements neither the `$N` back-reference nor the `/` escape nor the JSON unescape that INNER mode needs. The compact form does still hold the text, which `reference_decode.py` shows by getting it back, so this is a decoder to fix rather than a claim to withdraw. But until it is fixed there is no lossless read path on ClickHouse for a storage number to sit on. And the number itself, 14.9% on the whole table at the ClickStack default, is below the 30% a ClickHouse maintainer has already called achievable against a well-sorted ZSTD column, on a schema of their choosing.

## What this was measured on

- ClickHouse `26.8.3.105` from `clickhouse/clickhouse-server:latest`, 8 GiB and 8 CPUs, one container, all arms in it at once.
- Engine `log10x/pipeline-10x@sha256:aeb3784c8895bf990e9a88f49c68d59f5729f6738c44c6e8fd87a489f725d316`, INNER encode, config `tenx-encode-inner.config.yaml` in this folder.
- Capture `otel-sample-200mb.log` from the `otel-sample-v2` release of `log-10x/config`, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`, 197,430 lines.
- 159,170 compact events and 2,627 templates came out of the encode.
- Schema: the ClickStack `otel_logs` DDL from https://clickhouse.com/docs/use-cases/observability/clickstack/ingesting-data/schemas , copied into `schema.sql.tpl` with the codec substituted and the TTL placeholder removed. Typed columns, `LowCardinality`, the two attribute maps, all eight skip indexes and the published `ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)`.

## The three arms

| Arm | Rows | Body | Attributes |
|---|---:|---|---|
| `native` | 197,430 | the line's message | from that line's envelope |
| `compact` | 159,170 | the compact event `~<hash>,<values>` | from the same envelope |
| `native_folded` | 159,170 | the original text of that same event | identical to `compact` |

`native` against `compact` is what a deployment sees and carries both the templating and the event folding. `native_folded` against `compact` holds the row count and every other column fixed and isolates the templating. `native` against `native_folded` is the folding on its own.

## On disk, whole table

`sum(bytes_on_disk)` from `system.parts`, active parts, after `OPTIMIZE FINAL`. The compact column adds the template dictionary table, without which the arm cannot be read.

| Codec | native | native_folded | compact | compact + dictionary | compact vs native | compact vs native_folded |
|---|---:|---:|---:|---:|---:|---:|
| ZSTD(1) | 8,225,547 | 7,570,122 | 6,651,810 | 6,999,850 | 14.9% | 7.53% |
| ZSTD(3) | 7,374,889 | 6,891,440 | 6,004,977 | 6,353,017 | 13.86% | 7.81% |
| LZ4 | 8,526,421 | 8,170,520 | 6,953,841 | 7,301,881 | 14.36% | 10.63% |

Rows: `native` 197,430, `compact` and `native_folded` 159,170. Template dictionary on disk: 348,040 bytes for 2,627 templates, 914,000 bytes allocated in memory.

## Per column, ZSTD(1)

`system.parts_columns`, compressed and uncompressed. The attribute columns are the same values in every arm, so the Body row is where the comparison lives; the rest is here so nobody has to take that on trust.

| Column | native | native_folded | compact | native uncompressed | compact uncompressed |
|---|---:|---:|---:|---:|---:|
| `Body` | 1,888,235 | 1,865,254 | 1,426,008 | 41,933,765 | 12,408,451 |
| `EventName` | 328 | 297 | 291 | 603 | 459 |
| `LogAttributes` | 104,860 | 85,045 | 84,993 | 4,542,022 | 3,661,786 |
| `ResourceAttributes` | 2,096,720 | 1,747,839 | 1,747,913 | 100,826,621 | 82,590,501 |
| `ResourceSchemaUrl` | 777 | 684 | 684 | 198,536 | 160,020 |
| `ScopeAttributes` | 1,208 | 1,027 | 1,027 | 1,579,456 | 1,273,376 |
| `ScopeName` | 328 | 297 | 291 | 603 | 459 |
| `ScopeSchemaUrl` | 777 | 684 | 684 | 198,536 | 160,020 |
| `ScopeVersion` | 777 | 684 | 684 | 198,536 | 160,020 |
| `ServiceName` | 3,445 | 3,330 | 3,353 | 199,089 | 160,537 |
| `SeverityNumber` | 333 | 315 | 299 | 603 | 459 |
| `SeverityText` | 777 | 684 | 684 | 198,536 | 160,020 |
| `SpanId` | 328 | 297 | 291 | 603 | 459 |
| `Timestamp` | 333,333 | 332,103 | 332,103 | 1,579,440 | 1,273,360 |
| `TraceFlags` | 333 | 315 | 299 | 603 | 459 |
| `TraceId` | 328 | 297 | 291 | 603 | 459 |
| `__hdx_materialized_deployment.environment.name` | 777 | 684 | 684 | 198,536 | 160,020 |
| `__hdx_materialized_k8s.cluster.name` | 777 | 684 | 684 | 198,536 | 160,020 |
| `__hdx_materialized_k8s.container.name` | 3,445 | 3,330 | 3,353 | 199,089 | 160,537 |
| `__hdx_materialized_k8s.deployment.name` | 777 | 684 | 684 | 198,536 | 160,020 |
| `__hdx_materialized_k8s.namespace.name` | 1,081 | 962 | 915 | 198,576 | 160,060 |
| `__hdx_materialized_k8s.node.name` | 981 | 877 | 825 | 198,598 | 160,082 |
| `__hdx_materialized_k8s.pod.name` | 3,732 | 3,617 | 3,641 | 199,520 | 160,978 |
| `__hdx_materialized_k8s.pod.uid` | 3,873 | 3,754 | 3,778 | 199,979 | 161,426 |
| `_block_number` | 7,670 | 6,233 | 6,233 | 1,579,440 | 1,273,360 |
| `_block_offset` | 7,891 | 6,402 | 6,402 | 1,579,440 | 1,273,360 |

Skip indexes, compressed, ZSTD(1): `native` 3,724,080, `compact` 2,987,743, `native_folded` 3,466,940.

## The Body column alone

| Codec | native | native_folded | compact | compact vs native_folded |
|---|---:|---:|---:|---:|
| ZSTD(1) | 1,888,235 | 1,865,254 | 1,426,008 | 23.55% |
| ZSTD(3) | 1,860,555 | 1,860,310 | 1,452,751 | 21.91% |
| LZ4 | 3,463,300 | 3,458,311 | 2,721,226 | 21.31% |

Before ClickHouse touches it, the same text is 40,392,585 bytes native and 11,135,091 bytes compact, 72.43%.

## Does the compact arm come back

Checked on the multiset, because the schema has no column to order rows by: same row count, same total length, same sum of per-row hashes as `native_folded`.

| Expand path | Rows | Total length | Rows that are not any original | Matches |
|---|---:|---:|---:|---|
| `native_folded` (the original) | 159,170 | 40,392,585 | 0 | reference |
| `tenx_inflate` | 159,170 | 43,390,578 | 124,220 | NO |
| `tenx_inflate_iso` | 159,170 | 43,471,949 | 139,469 | NO |

**It does not.** 124,220 of 159,170 rows, 78.0%, expand to text that is not any line in the capture, and that is through the format-preserving path, the one meant to reproduce the original exactly. The expanded text is **longer** than the original, which is the first clue: this is not lossy compaction, it is the SQL decoder failing to read constructs the engine writes into a template.

| Template construct | Templates | What `install.sql` does with it |
|---|---:|---|
| `$N`, a back-reference to the value N slots earlier | 192 | matches the `$` and leaves the digits as literal text, so the digit is printed and the value cursor runs one position ahead |
| `//`, how the engine writes a literal `/` inside a template | 476 | never reverses it, so every path and URL comes back with its slashes doubled |
| either | 590 of 2,627 | |

Compact event, and what the shipped SQL returns for it:

```
~-E.<WC^*uQu,CORECLR
  -> [CORECLR_PROFILER_PATH, //app//OpenTelemetry.AutoInstrumentation.Native.so]
~MML]JSnua<
  -> [DOTNET_STARTUP_HOOKS, //app//OpenTelemetry.AutoInstrumentation.StartupHook.dll]
~2!2nwSbV_C,10,100,90,228,9092
  -> [KAFKA_PORT, tcp:////10.100.90.228:9092]
```

### Is the text still in the compact form

Two explanations fit a decoder that returns the wrong text, and they are not close in consequence: either the compaction lost the original, or it held it and the SQL misread it. `reference_decode.py` decides it by decoding the same events in Python with the four rules `install.sql` does not implement, and nothing else: `//` for a literal `/`, `/$` for a literal `$`, `$N` for a back-reference, and the JSON unescape that INNER mode needs.

**24,494 of 24,501**, 99.97%, of the compact events whose template carries no timestamp slot come back byte-identical. The seven that do not are a back-reference case that reference decoder gets wrong. Events with a timestamp slot are left out of this count, all 134,669 of them: the slot holds an epoch integer and rendering it back needs a Joda formatter, which is a separate question from the decode rules above.

So the text is there. What is broken is the SQL that reads it.

None of this is in the compact form. The `otel-sample-v2` release states and shows how to check that the engine's own round trip on this capture returns all 215,039,161 bytes byte-identical. Every one of these defects is in the SQL, and they are in `../clickhouse-inflate/install-fixed.sql` and in the `install.sql` that `log-10x/clickhouse-app` ships. The earlier ClickHouse benchmark did not catch them: its byte-identity check compared the pre-fix decoder's output with the post-fix decoder's output, never with the original log text.

## One text filter per arm

`SELECT count() ... WHERE position(Body, 'checkout') > 0`, and for the compact arm the same filter over the expanded text, which is how a user who does not know the template hash would ask. Ten runs, the first discarded, from `system.query_log`.

These are the one set of numbers here that a busy host moves. On a laptop carrying other work the compact arm read anywhere from 0.5 s to 4 s for the same query while the byte counts did not move at all. This run was taken on a machine with other work on it, so the fastest run is the column to read: it is the closest to the query's own cost. Every run is printed so the spread is visible rather than described.

| Arm | Fastest ms | Median ms | Every run | Rows read | Bytes read | Result |
|---|---:|---:|---|---:|---:|---:|
| native | 6 | 6 | 6, 6, 6, 6, 6, 6, 7, 7, 8, 18 | 32,768 | 2,737,012 | 2316 |
| native_folded | 6 | 7 | 6, 6, 6, 6, 7, 7, 7, 8, 8, 9 | 16,384 | 3,724,610 | 2316 |
| compact, `tenx_inflate_iso` | 531 | 554 | 531, 540, 547, 553, 554, 554, 555, 557, 563, 566 | 159,170 | 11,612,601 | 2316 |
| compact, `tenx_inflate` | 590 | 597 | 590, 593, 593, 597, 597, 598, 602, 607, 607, 612 | 159,170 | 11,612,601 | 2316 |

## Ingest

CPU as ClickHouse accounted for the `INSERT`. Each arm was loaded from a JSONEachRow file, so this includes parsing a payload that is a different size in each arm. It is not collector-to-ClickHouse ingest over the native protocol and should not be read as that number.

| Table | CPU seconds | Wall ms | Rows written |
|---|---:|---:|---:|
| `otel_logs_compact_lz4` | 3.5 | 4,292 | 159,170 |
| `otel_logs_compact_zstd1` | 2.7 | 3,318 | 159,170 |
| `otel_logs_compact_zstd3` | 1.8 | 2,368 | 159,170 |
| `otel_logs_native_folded_lz4` | 3.1 | 3,804 | 159,170 |
| `otel_logs_native_folded_zstd1` | 4.4 | 5,132 | 159,170 |
| `otel_logs_native_folded_zstd3` | 3.4 | 4,023 | 159,170 |
| `otel_logs_native_lz4` | 3.5 | 4,265 | 197,430 |
| `otel_logs_native_zstd1` | 16.5 | 22,011 | 197,430 |
| `otel_logs_native_zstd3` | 6.4 | 8,669 | 197,430 |

