# Hot-tier run: 2026-10-23T14:55:36.000Z

Hot tier: 61 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 54 MB within 2 hours, with 4.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 3 MB on hot. The Receiver's kept lines: 45 MB in 11 indices; its tier_down lines not yet moved: 13 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 58 moved indices).
- Each counted byte takes 0.97 bytes of store kept, 0.60 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.5 GB a day; 428 MB a day fits the size, so each statement keeps up to 14 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 101 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 93% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 174 |
| ad | the frozen tier | 1 | 159 MB | 35 MB | 38179 | 96862 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 38 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 103 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 187 |
| cart | the frozen tier | 1 | 399 MB | 28 MB | 38179 | 77372 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 717 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 44 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 169 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 218 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 73 |
| fluentd-10x | the frozen tier | 1 | 25 MB | 16 MB | 38179 | 43762 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 194 |
| frontend | the frozen tier | 1 | 95 MB | 14 MB | 38179 | 38416 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 38179 | 4905 |
| grafana | the frozen tier | 1 | 33 MB | 33 MB | 38179 | 91454 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 322 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 456 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 393 |
| hb-inventory | the frozen tier | 1 | 40 MB | 14 MB | 38179 | 38179 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 287 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 38179 | 3345 |
| kafka | the frozen tier | 1 | 735 MB | 183 MB | 38179 | 509374 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 38179 | 5048 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 348 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 1188 |
| opensearch | the frozen tier | 1 | 6 MB | 6 MB | 38179 | 16471 |
| opentelemetry-collector | the frozen tier | 1 | 2.9 GB | 73 MB | 38179 | 201966 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 208 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 643 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 38179 | 4958 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 38179 | 20 |
| recommendation | the frozen tier | 1 | 122 MB | 14 MB | 38179 | 38258 |
| valkey-cart | the frozen tier | 1 | 5 MB | 5 MB | 38179 | 13953 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 38179 | 680 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
