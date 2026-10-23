# Rows run, final criteria

Wire: 194831 returned, by route {"offload": 110392, "pass": 84439}. Hot 84472, cold 110392, hot plus cold 194864.

## 5. Delivery: returned records in the table or the bucket: FAIL (totals; a loss and a duplicate cancel in it)
Lines the pacers wrote: 242741; records returned: 194831; FAIL on lines in equals records back (the Receiver folds multi-line events, so a difference is read against the fold count, not as loss).

## 3 and 4. The ten largest moved statements: wire against hot plus cold, and the Merge table against the local count

| hash | wire total | hot | cold (S3 view) | hot + cold | merge table | 3 | 4 |
|---|---:|---:|---:|---:|---:|---|---|
| Gl3Gtr_SH5w | 39424 | 8748 | 30676 | 39424 | 39424 | ok | ok |
| KG8Fq0QFuoY | 38170 | 8622 | 29548 | 38170 | 38170 | ok | ok |
| p1GC1pHzuvI | 11972 | 501 | 11471 | 11972 | 11972 | ok | ok |
| PuWB8kkVbfw | 15295 | 5450 | 9856 | 15306 | 15306 | MISS | MISS |
| YZplfQ4a1Xw | 13702 | 5237 | 8468 | 13705 | 13705 | MISS | MISS |
| i0pN68Etup8 | 9587 | 1494 | 8097 | 9591 | 9591 | MISS | MISS |
| eDSYlCMPqVY | 7456 | 3854 | 3604 | 7458 | 7458 | MISS | MISS |
| bzLB1zZCTIw | 3703 | 2462 | 1242 | 3704 | 3704 | MISS | MISS |
| bz3kQNPdXvc | 3847 | 2633 | 1216 | 3849 | 3849 | MISS | MISS |
| xHrytxJfUdw | 3309 | 2420 | 891 | 3311 | 3311 | MISS | MISS |

Criterion 3: FAIL. Criterion 4: FAIL.

## 7. The injected service

inventory rows in the bucket: 8097. Hot rows per 4-minute window (the `*` total of the applied run in force bounds each; read it from that run's totals.csv):

| window | hot rows |
|---|---:|
| 1792777920 | 96 |
| 1792778160 | 49 |
| 1792778400 | 49 |
| 1792778640 | 56 |
| 1792778880 | 70 |
| 1792779120 | 102 |
| 1792779360 | 71 |
| 1792779600 | 84 |
| 1792779840 | 85 |
| 1792780080 | 55 |
| 1792780320 | 99 |
| 1792780560 | 63 |
| 1792780800 | 72 |
| 1792781040 | 76 |
| 1792781280 | 76 |
| 1792781520 | 73 |
| 1792781760 | 74 |
| 1792782000 | 74 |
| 1792782240 | 74 |
| 1792782480 | 76 |
| 1792782720 | 20 |
