# OTel sample on three denominators

Written by `run.sh`. Every byte count is `wc -c` on a file this run produced; the percentage is recomputed from those counts by `report.py`.

- engine image: `log10x/pipeline-10x@sha256:fccff37a6a41e52eb4df8a108d042b0176210842b7ed25f08b1419df3a37904f`
- configs: `../drain3-vs-log10x/tenx-encode.config.yaml` and `tenx-decode.config.yaml`
- capture, gzipped as published: sha256 `c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9`
- capture, expanded: sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`

| Case | Input bytes | Lines | Encoded | Templates bytes | Compact | Reduction | Templates | Round trip |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| (a) as captured | 215,039,161 | 197,430 | 74,142,102 | 3,279,142 | 77,421,244 | **64.00%** | 3,028 | byte-identical |
| (b) SIEM-billed | 88,975,911 | 111,691 | 30,452,359 | 2,949,044 | 33,401,403 | **62.46%** | 2,978 | byte-identical |
| (c) message only | 40,551,755 | 197,430 | 10,610,578 | 601,676 | 11,212,254 | **72.35%** | 2,625 | byte-identical |

What each denominator is:

- **(a) as captured**: the release asset, untouched.
- **(b) SIEM-billed**: the injected `tenx_tag` field removed, the collector's debug-exporter lines dropped, envelope kept.
- **(c) message only**: the `log` value alone, one message per line.

Round trip is `cmp` against that case's own input, so each row decodes back to the bytes it was measured on, not to some other file.

Every case returned byte-identical.

