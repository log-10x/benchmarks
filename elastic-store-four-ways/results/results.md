# Elasticsearch store, four ways: results

- Elasticsearch 9.5.5 (Lucene 10.5.1), `docker.elastic.co/elasticsearch/elasticsearch@sha256:13b4a40bb095774f5fda635e45fd5677cc6a26565e42b24997b0c72b88e75984`, licence `trial` `active`
- engine `ghcr.io/log-10x/edge-10x@sha256:3e755bbc14780a27e643e09b76dfd7ec9616cab67833f70daf9420eff646d350`
- sample `otel-sample-200mb.log`: 215,039,161 B, 197,430 lines, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`
- compact form: 157,228 events and 3,030 templates, 74,140,583 B encoded + 3,281,830 B dictionary = 77,422,413 B, 64.0% under the sample before any codec; decode BYTE-IDENTICAL

Documents differ by design: (a), (b) and (c) hold one per line, the compact variants one per event (multi-line events fold into one) plus one per template. Each index is checked against its own input.

| Variant | Index mode | `message` | Documents | Store, rep 1 | Store, rep 2 | Mean | Of (a) raw | Of (b) logsdb |
|---|---|---|---:|---:|---:|---:|---:|---:|
| raw | standard | `text` | 197,430 | 20,108,998 B | 20,106,803 B | 20,107,900 B | 100.0% | 167.6% |
| logsdb | logsdb | `text` | 197,430 | 12,003,158 B | 11,997,590 B | 12,000,374 B | 59.7% | 100.0% |
| pattern | logsdb, sorted on `message.template_id` | `pattern_text` | 197,430 | 6,977,160 B | 6,972,360 B | 6,974,760 B | 34.7% | 58.1% |
| compact | standard | encoded event, `text`, plus `l1x_tid` and the dictionary index | 157,228 + 3,030 | 14,909,550 B | 14,901,237 B | 14,905,394 B | 74.1% | 124.2% |
| compact_logsdb | logsdb | encoded event, `text`, plus `l1x_tid` and the dictionary index | 157,228 + 3,030 | 10,721,205 B | 10,718,972 B | 10,720,088 B | 53.3% | 89.3% |
| compact_logsdb_sorted | logsdb, sorted on `l1x_tid` | encoded event, `text`, plus `l1x_tid` and the dictionary index | 157,228 + 3,030 | 8,875,307 B | 8,872,791 B | 8,874,049 B | 44.1% | 73.9% |

**compact_logsdb against pattern:** 10,720,088 B against 6,974,760 B, 53.7% more store (153.7% of it).

The compact variant against each native one (mean of the repetitions):

| Against | Its store | Compact store | Compact as a share of it | Difference |
|---|---:|---:|---:|---:|
| raw | 20,107,900 B | 14,905,394 B | 74.1% | 25.9% smaller |
| logsdb | 12,000,374 B | 14,905,394 B | 124.2% | 24.2% larger |
| pattern | 6,974,760 B | 14,905,394 B | 213.7% | 113.7% larger |

The compact_logsdb variant against each native one (mean of the repetitions):

| Against | Its store | Compact store | Compact as a share of it | Difference |
|---|---:|---:|---:|---:|
| raw | 20,107,900 B | 10,720,088 B | 53.3% | 46.7% smaller |
| logsdb | 12,000,374 B | 10,720,088 B | 89.3% | 10.7% smaller |
| pattern | 6,974,760 B | 10,720,088 B | 153.7% | 53.7% larger |

The compact_logsdb_sorted variant against each native one (mean of the repetitions):

| Against | Its store | Compact store | Compact as a share of it | Difference |
|---|---:|---:|---:|---:|
| raw | 20,107,900 B | 8,874,049 B | 44.1% | 55.9% smaller |
| logsdb | 12,000,374 B | 8,874,049 B | 73.9% | 26.1% smaller |
| pattern | 6,974,760 B | 8,874,049 B | 127.2% | 27.2% larger |

## Checks

- pass: trial licence active (trial active)
- pass: rep 1 es4-raw: documents equal the input (197,430 indexed, 197,430 expected)
- pass: rep 1 es4-raw: one segment (1)
- pass: rep 1 es4-raw: best_compression (best_compression)
- pass: rep 1 es4-logsdb: documents equal the input (197,430 indexed, 197,430 expected)
- pass: rep 1 es4-logsdb: one segment (1)
- pass: rep 1 es4-logsdb: best_compression (best_compression)
- pass: rep 1 es4-logsdb: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 1 es4-logsdb: no _recovery_source left (0 B)
- pass: rep 1 es4-pattern: documents equal the input (197,430 indexed, 197,430 expected)
- pass: rep 1 es4-pattern: one segment (1)
- pass: rep 1 es4-pattern: best_compression (best_compression)
- pass: rep 1 es4-pattern: segments sorted on message.template_id first (sort message.template_id, @timestamp)
- pass: rep 1 es4-pattern: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 1 es4-pattern: no _recovery_source left (0 B)
- pass: rep 1 es4-compact: documents equal the input (157,228 indexed, 157,228 expected)
- pass: rep 1 es4-compact: one segment (1)
- pass: rep 1 es4-compact: best_compression (best_compression)
- pass: rep 1 es4-compact-dict: documents equal the input (3,030 indexed, 3,030 expected)
- pass: rep 1 es4-compact-dict: one segment (1)
- pass: rep 1 es4-compact-dict: best_compression (best_compression)
- pass: rep 1 es4-compact-logsdb: documents equal the input (157,228 indexed, 157,228 expected)
- pass: rep 1 es4-compact-logsdb: one segment (1)
- pass: rep 1 es4-compact-logsdb: best_compression (best_compression)
- pass: rep 1 es4-compact-logsdb: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 1 es4-compact-logsdb: no _recovery_source left (0 B)
- pass: rep 1 es4-compact-logsdb-sorted: documents equal the input (157,228 indexed, 157,228 expected)
- pass: rep 1 es4-compact-logsdb-sorted: one segment (1)
- pass: rep 1 es4-compact-logsdb-sorted: best_compression (best_compression)
- pass: rep 1 es4-compact-logsdb-sorted: segments sorted on l1x_tid first (sort l1x_tid, @timestamp)
- pass: rep 1 es4-compact-logsdb-sorted: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 1 es4-compact-logsdb-sorted: no _recovery_source left (0 B)
- pass: rep 2 es4-raw: documents equal the input (197,430 indexed, 197,430 expected)
- pass: rep 2 es4-raw: one segment (1)
- pass: rep 2 es4-raw: best_compression (best_compression)
- pass: rep 2 es4-logsdb: documents equal the input (197,430 indexed, 197,430 expected)
- pass: rep 2 es4-logsdb: one segment (1)
- pass: rep 2 es4-logsdb: best_compression (best_compression)
- pass: rep 2 es4-logsdb: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 2 es4-logsdb: no _recovery_source left (0 B)
- pass: rep 2 es4-pattern: documents equal the input (197,430 indexed, 197,430 expected)
- pass: rep 2 es4-pattern: one segment (1)
- pass: rep 2 es4-pattern: best_compression (best_compression)
- pass: rep 2 es4-pattern: segments sorted on message.template_id first (sort message.template_id, @timestamp)
- pass: rep 2 es4-pattern: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 2 es4-pattern: no _recovery_source left (0 B)
- pass: rep 2 es4-compact: documents equal the input (157,228 indexed, 157,228 expected)
- pass: rep 2 es4-compact: one segment (1)
- pass: rep 2 es4-compact: best_compression (best_compression)
- pass: rep 2 es4-compact-dict: documents equal the input (3,030 indexed, 3,030 expected)
- pass: rep 2 es4-compact-dict: one segment (1)
- pass: rep 2 es4-compact-dict: best_compression (best_compression)
- pass: rep 2 es4-compact-logsdb: documents equal the input (157,228 indexed, 157,228 expected)
- pass: rep 2 es4-compact-logsdb: one segment (1)
- pass: rep 2 es4-compact-logsdb: best_compression (best_compression)
- pass: rep 2 es4-compact-logsdb: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 2 es4-compact-logsdb: no _recovery_source left (0 B)
- pass: rep 2 es4-compact-logsdb-sorted: documents equal the input (157,228 indexed, 157,228 expected)
- pass: rep 2 es4-compact-logsdb-sorted: one segment (1)
- pass: rep 2 es4-compact-logsdb-sorted: best_compression (best_compression)
- pass: rep 2 es4-compact-logsdb-sorted: segments sorted on l1x_tid first (sort l1x_tid, @timestamp)
- pass: rep 2 es4-compact-logsdb-sorted: synthetic source (_source stored 0 B, mode setting SYNTHETIC)
- pass: rep 2 es4-compact-logsdb-sorted: no _recovery_source left (0 B)
- pass: two encodes byte-identical
- pass: compact form decodes to the sample byte for byte (BYTE-IDENTICAL)
- pass: repetitions agree within 1% (raw 0.01%, logsdb 0.05%, pattern 0.07%, compact 0.06%, compact_logsdb 0.02%, compact_logsdb_sorted 0.03%)

Per-index detail (settings, leases before the merge, per-field bytes) is in `rep<N>.json`; each index's mapping and `_disk_usage` output are in `rep<N>/`.
