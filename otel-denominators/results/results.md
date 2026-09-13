# OTel sample on three denominators

Written by `run.sh`. Every byte count is `wc -c` on a file this run produced; the percentage is recomputed from those counts by `report.py`.

- engine image: `log10x/pipeline-10x@sha256:aeb3784c8895bf990e9a88f49c68d59f5729f6738c44c6e8fd87a489f725d316`
- configs: `../drain3-vs-log10x/tenx-encode.config.yaml` and `tenx-decode.config.yaml`
- capture, gzipped as published: sha256 `c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9`
- capture, expanded: sha256 `aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`

| Case | Input bytes | Lines | Encoded | Templates bytes | Compact | Reduction | Templates | Round trip |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| (a) as captured | 215,039,161 | 197,430 | 74,841,891 | 3,226,416 | 78,068,307 | **63.70%** | 2,933 | byte-identical |
| (b) SIEM-billed | 88,975,911 | 111,691 | 30,496,832 | 2,903,267 | 33,400,099 | **62.46%** | 2,869 | byte-identical |
| (c) message only | 40,551,755 | 197,430 | 10,644,634 | 600,758 | 11,245,392 | **72.27%** | 2,631 | byte-identical |

What each denominator is:

- **(a) as captured**: the release asset, untouched.
- **(b) SIEM-billed**: the injected `tenx_tag` field removed, the collector's debug-exporter lines dropped, envelope kept.
- **(c) message only**: the `log` value alone, one message per line.

Round trip is `cmp` against that case's own input, so each row decodes back to the bytes it was measured on, not to some other file.

Every case returned byte-identical.

