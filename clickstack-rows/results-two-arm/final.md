# Rows run, final criteria

Wire: 204399 returned, by route {"offload": 115861, "pass": 88538}. Hot 89471, cold 115875, hot plus cold 205346.

## 5. Delivery: returned records in the table or the bucket: FAIL (totals; a loss and a duplicate cancel in it)
Lines the pacers wrote: 242324; records returned: 204399; FAIL on lines in equals records back (the Receiver folds multi-line events, so a difference is read against the fold count, not as loss).

## 3 and 4. The ten largest moved statements: wire against hot plus cold, and the Merge table against the local count

| hash | wire total | hot | cold (S3 view) | hot + cold | merge table | 3 | 4 |
|---|---:|---:|---:|---:|---:|---|---|
| Gl3Gtr_SH5w | 39337 | 8405 | 30948 | 39353 | 39353 | MISS | MISS |
| KG8Fq0QFuoY | 38089 | 8277 | 29834 | 38111 | 38111 | MISS | MISS |
| p1GC1pHzuvI | 11977 | 494 | 11483 | 11977 | 11977 | ok | ok |
| PuWB8kkVbfw | 15262 | 5391 | 9876 | 15267 | 15267 | MISS | MISS |
| i0pN68Etup8 | 9595 | 1402 | 8193 | 9595 | 9595 | ok | ok |
| YZplfQ4a1Xw | 13116 | 4996 | 8120 | 13116 | 13116 | ok | ok |
| eDSYlCMPqVY | 7127 | 3641 | 3486 | 7127 | 7127 | ok | ok |
| bz3kQNPdXvc | 3841 | 2577 | 1264 | 3841 | 3841 | ok | ok |
| bzLB1zZCTIw | 3698 | 2443 | 1255 | 3698 | 3698 | ok | ok |
| xHrytxJfUdw | 3305 | 2362 | 943 | 3305 | 3305 | ok | ok |

Criterion 3: FAIL. Criterion 4: FAIL.

## 7. The injected service

inventory rows in the bucket: 8193. Hot rows per 4-minute window (the `*` total of the applied run in force bounds each; read it from that run's totals.csv):

| window | hot rows |
|---|---:|
| 1792897920 | 76 |
| 1792898160 | 50 |
| 1792898400 | 50 |
| 1792898640 | 53 |
| 1792898880 | 88 |
| 1792899120 | 82 |
| 1792899360 | 85 |
| 1792899600 | 85 |
| 1792899840 | 60 |
| 1792900080 | 72 |
| 1792900320 | 68 |
| 1792900560 | 70 |
| 1792900800 | 70 |
| 1792901040 | 68 |
| 1792901280 | 69 |
| 1792901520 | 70 |
| 1792901760 | 70 |
| 1792902000 | 70 |
| 1792902240 | 73 |
| 1792902480 | 73 |
