# Receiver memory and CPU

Written by `rig/memory/summarize.py` from the files in this folder.

`log10x/edge-10x:1.1.142@sha256:24e31c07a95e1f7dc356f11dc5cac4b21602ff91040ea831f94668b05afe6bf1`, limits 0.5 CPU and 512 MiB, 57,353 records replayed over 76.8 minutes (to 60 s after the last record), one `docker stats` sample every 10 s.

| measure | samples | median | p99 | max |
|---|---:|---:|---:|---:|
| memory (MiB) | 461 | 212.8 | 227.5 | 227.7 |
| CPU (% of one core) | 461 | 0.42 | 8.0 | 15.56 |

Before the first record: memory median 112.4 MiB, CPU median 0.08% (3 samples). OOM killed: false; restarts: 0.

Records the Receiver returned, by route: pass 16,836, offload 5,524, tier_down 22,655, other 0.
