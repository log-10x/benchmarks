# Elasticsearch store, four ways: results

- Elasticsearch 9.5.5 (Lucene 10.5.1), `docker.elastic.co/elasticsearch/elasticsearch@sha256:13b4a40bb095774f5fda635e45fd5677cc6a26565e42b24997b0c72b88e75984`, licence `trial` `active`
- engine `ghcr.io/log-10x/edge-10x@sha256:3e755bbc14780a27e643e09b76dfd7ec9616cab67833f70daf9420eff646d350`
- sample `otel-sample-200mb.log`: 215,039,161 B, 197,430 lines, sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`
- compact form: 157,228 events and 3,030 templates, 74,140,583 B encoded + 3,281,830 B dictionary = 77,422,413 B, 64.0% under the sample before any codec; decode BYTE-IDENTICAL

Documents differ by design: (a), (b) and (c) hold one per line, the compact variants one per event (multi-line events fold into one) plus one per template. Each index is checked against its own input.

| Variant | Index mode | `message` | Documents | Store, rep 1 | Store, rep 2 | Mean | Of (a) raw | Of (b) logsdb |
|---|---|---|---:|---:|---:|---:|---:|---:|
| raw | standard | `text` | 197,430 | 20,120,143 B | 20,169,814 B | 20,144,978 B | 100.0% | 167.9% |
| logsdb | logsdb | `text` | 197,430 | 12,004,758 B | 11,997,974 B | 12,001,366 B | 59.6% | 100.0% |
| pattern | logsdb, sorted on `message.template_id` | `pattern_text` | 197,430 | 10,652,080 B | 10,647,728 B | 10,649,904 B | 52.9% | 88.7% |
| compact | standard | encoded event, `text`, plus `l1x_tid` and the dictionary index | 157,228 + 3,030 | 14,955,030 B | 14,892,170 B | 14,923,600 B | 74.1% | 124.3% |
| compact_logsdb | logsdb | encoded event, `text`, plus `l1x_tid` and the dictionary index | 157,228 + 3,030 | 10,723,204 B | 10,721,732 B | 10,722,468 B | 53.2% | 89.3% |

**compact_logsdb against pattern:** 10,722,468 B against 10,649,904 B, 0.7% more store (100.7% of it).

The compact variant against each native one (mean of the repetitions):

| Against | Its store | Compact store | Compact as a share of it | Difference |
|---|---:|---:|---:|---:|
| raw | 20,144,978 B | 14,923,600 B | 74.1% | 25.9% smaller |
| logsdb | 12,001,366 B | 14,923,600 B | 124.3% | 24.3% larger |
| pattern | 10,649,904 B | 14,923,600 B | 140.1% | 40.1% larger |

The compact_logsdb variant against each native one (mean of the repetitions):

| Against | Its store | Compact store | Compact as a share of it | Difference |
|---|---:|---:|---:|---:|
| raw | 20,144,978 B | 10,722,468 B | 53.2% | 46.8% smaller |
| logsdb | 12,001,366 B | 10,722,468 B | 89.3% | 10.7% smaller |
| pattern | 10,649,904 B | 10,722,468 B | 100.7% | 0.7% larger |

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
- FAIL: rep 1 es4-pattern: segments sorted on message.template_id (sort @timestamp)
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
- FAIL: rep 2 es4-pattern: segments sorted on message.template_id (sort @timestamp)
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
- pass: two encodes byte-identical
- pass: compact form decodes to the sample byte for byte (BYTE-IDENTICAL)
- pass: repetitions agree within 1% (raw 0.25%, logsdb 0.06%, pattern 0.04%, compact 0.42%, compact_logsdb 0.01%)

Per-index detail (settings, leases before the merge, per-field bytes) is in `rep<N>.json`; each index's mapping and `_disk_usage` output are in `rep<N>/`.
