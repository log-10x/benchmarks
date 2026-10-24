# Rows run, final criteria

Wire: 194524 returned, by route {"offload": 111506, "pass": 83018}. Hot 83018, cold 111506, hot plus cold 194524.

## 5. Delivery: returned records in the table or the bucket: PASS (totals; a loss and a duplicate cancel in it)
Lines the pacers wrote: 242357; records returned: 194524; FAIL on lines in equals records back (the Receiver folds multi-line events, so a difference is read against the fold count, not as loss).

## 3 and 4. The ten largest moved statements: wire against hot plus cold, and the Merge table against the local count

| hash | wire total | hot | cold (S3 view) | hot + cold | merge table | 3 | 4 |
|---|---:|---:|---:|---:|---:|---|---|
| Gl3Gtr_SH5w | 39346 | 8796 | 30550 | 39346 | 39346 | ok | ok |
| KG8Fq0QFuoY | 38098 | 8668 | 29430 | 38098 | 38098 | ok | ok |
| p1GC1pHzuvI | 11968 | 504 | 11464 | 11968 | 11968 | ok | ok |
| PuWB8kkVbfw | 15270 | 5572 | 9698 | 15270 | 15270 | ok | ok |
| YZplfQ4a1Xw | 13672 | 5240 | 8432 | 13672 | 13672 | ok | ok |
| i0pN68Etup8 | 9591 | 1466 | 8125 | 9591 | 9591 | ok | ok |
| eDSYlCMPqVY | 7439 | 3785 | 3654 | 7439 | 7439 | ok | ok |
| bz3kQNPdXvc | 3842 | 2638 | 1204 | 3842 | 3842 | ok | ok |
| bzLB1zZCTIw | 3699 | 2513 | 1186 | 3699 | 3699 | ok | ok |
| xHrytxJfUdw | 3306 | 2445 | 861 | 3306 | 3306 | ok | ok |

Criterion 3: PASS. Criterion 4: PASS.

## 7. The injected service

inventory rows in the bucket: 8125. Hot rows per 4-minute window (the `*` total of the applied run in force bounds each; read it from that run's totals.csv):

| window | hot rows |
|---|---:|
| 1792815600 | 86 |
| 1792815840 | 43 |
| 1792816080 | 43 |
| 1792816320 | 67 |
| 1792816560 | 92 |
| 1792816800 | 84 |
| 1792817040 | 88 |
| 1792817280 | 88 |
| 1792817520 | 65 |
| 1792817760 | 76 |
| 1792818000 | 68 |
| 1792818240 | 72 |
| 1792818480 | 72 |
| 1792818720 | 76 |
| 1792818960 | 76 |
| 1792819200 | 72 |
| 1792819440 | 74 |
| 1792819680 | 74 |
| 1792819920 | 75 |
| 1792820160 | 75 |
