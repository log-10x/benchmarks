# Hot-tier run: 2026-10-24T21:04:18.000Z

Hot tier: 14 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 74 MB within 2 hours, with 2.4 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 4 MB in 2 indices; its tier_down lines not yet moved: 10 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 1.28 bytes of store kept, 0.62 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3 GB a day; 530 MB a day fits the size, so each statement keeps up to 16 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 162 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 43340 | 3719 |
| ad | the frozen tier | 1 | 102 MB | 38 MB | 43340 | 106120 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 82 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 224 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 405 |
| cart | the frozen tier | 1 | 247 MB | 31 MB | 43340 | 87161 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 43340 | 2557 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 95 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 361 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 470 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 159 |
| fluentd-10x | the frozen tier | 1 | 19 MB | 18 MB | 43340 | 49347 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 410 |
| frontend | the frozen tier | 1 | 58 MB | 16 MB | 43340 | 43658 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 43340 | 10496 |
| grafana | the frozen tier | 1 | 52 MB | 52 MB | 43340 | 143935 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 697 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 986 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 845 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 603 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 43340 | 7196 |
| kafka | the frozen tier | 1 | 464 MB | 219 MB | 43340 | 608931 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 43340 | 16033 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 739 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 43340 | 2565 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 43340 | 26401 |
| opentelemetry-collector | the frozen tier | 1 | 1.9 GB | 105 MB | 43340 | 290431 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 438 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 43340 | 1390 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 43340 | 6206 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 43340 | 44 |
| recommendation | the frozen tier | 1 | 64 MB | 16 MB | 43340 | 43511 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 43340 | 15728 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 43340 | 2557 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
