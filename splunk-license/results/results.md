# What 10x in front of Splunk does to licence-metered volume

**Splunk 10.4.3 (build 4174a2deda5d)**. Forwarder path: Universal Forwarder, file monitor, S2S to the indexer on 9997. Licence: Splunk Enterprise download trial, 500 MB/day. Rollup written 09-18-2026 at local midnight, closing the licence day that holds the whole run. Container timezone `Etc/GMT+1`.

## The two arms, in Splunk's own meter

| Arm | Index / sourcetype | What it is | Licence-metered bytes | GB/day |
|---|---|---|---:|---:|
| baseline | `tenx_base/tenx_raw_json` | the capture as it is | 214,841,731 | 0.200087 |
| compact | `tenx_enc/tenx_encoded` | the compact events | 75,014,513 | 0.069863 |
| compact | `tenx_dml/tenx_dml_raw_json` | the template dictionary | 3,190,538 | 0.002971 |
| compact | `tenx_dml/tenx_dml_pure` | the app re-indexing each template | 2,438,316 | 0.002271 |
| **baseline** | | **total** | **214,841,731** | **0.200087** |
| **compact** | | **total** | **80,643,367** | **0.075105** |

**Licence-metered reduction: 62.46%.** Counting only what crosses the wire, with the app's own re-index of the templates left out, it is 63.6%; that re-index costs 2,438,316 metered bytes and no measurement taken on files can see it.

## Where each figure comes from

The daily rollup, `type=RolloverSummary`, is one line per licence pool on this version and carries no `idx`, so it gives the licence day's total and nothing per arm: **295,485,098 bytes**, 0.275192 GB. The split between the arms comes from `type=Usage`, the per-minute records, binned to the same day. That is what Splunk's own Monitoring Console does: its Historic License Usage view reads RolloverSummary when unsplit and switches to Usage the moment it is split by index.

The two agree to the byte. The per-index Usage bytes sum to 295,485,098, which is the rollup's own total: **yes**.

Monitoring Console, Historic License Usage, no split, from the rollup:

```
_time            volume
--------------------------- ------
2026-09-17 00:00:00.000 UTC  0.275
```

Monitoring Console, Historic License Usage, split by index, from the per-minute records:

```
_time            tenx_base tenx_dml tenx_enc
--------------------------- --------- -------- --------
2026-09-17 00:00:00.000 UTC     0.200    0.005    0.070
```

## The same data measured as files, for comparison

- capture 215,039,161 bytes, 197,430 lines
- compact form 78,365,265 bytes (75,171,741 encoded + 3,193,524 templates), 157,228 records, 2,986 templates
- file reduction **63.56%**, round trip BYTE-IDENTICAL
- with the engine's own `maxRecurIndexes: 10`, which this app cannot decode, the file reduction would be 63.71%

## Where the gap is smallest

Per Kubernetes container, compact events against the text they came from, both on the meter's basis. The template dictionary is not split across containers and is left out of this table, so each row reads slightly better than the same slice would in a deployment. Containers with fewer than 100 events are not ranked.

| | Container | Events | Raw bytes | Compact bytes | Reduction |
|---|---|---:|---:|---:|---:|
| **worst** | `ad` | 7,114 | 6,798,676 | 2,864,638 | 57.86% |
|  | `kube-proxy` | 287 | 282,497 | 118,369 | 58.1% |
|  | `fluentd-10x` | 1,429 | 1,480,626 | 592,691 | 59.97% |
| best | `opensearch` | 516 | 642,494 | 197,415 | 69.27% |

## Expansion

Every compact event read back through the app's own `tenx-inflate` macro and compared, byte for byte, with the text that went in.

| Search head timezone | Events | Byte-identical | Wrong text | Unexpanded |
|---|---:|---:|---:|---:|
| UTC | 157,228 | 61,982 (39.42%) | 95,201 | 45 |
| Etc/GMT+1 | 157,228 | 22,550 (14.34%) | 134,633 | 45 |

Engine `ghcr.io/log-10x/edge-10x@sha256:14357d8d570cb36ba6ca254802a1b8eedb11d8acf6916a936893f8e3babb41f4`. 10x Splunk app `542839ac511c5599abc3a1bf61184d0c59f7a2f1`.

