# Hot-tier run: 2026-10-25T08:53:53.000Z

Hot tier: 63 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 3.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 2 MB on hot. The Receiver's kept lines: 62 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 16 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.92 bytes of store kept, 0.92 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.3 GB a day; 798 MB a day fits the size, so each statement keeps up to 27 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 146 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 99% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 174 |
| ad | the frozen tier | 1 | 144 MB | 62 MB | 75413 | 172078 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 39 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 107 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 194 |
| cart | the frozen tier | 1 | 400 MB | 54 MB | 75413 | 151055 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 75413 | 2263 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 45 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 171 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 224 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 76 |
| fluentd-10x | the frozen tier | 1 | 23 MB | 23 MB | 75413 | 63233 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 194 |
| frontend | the frozen tier | 1 | 81 MB | 27 MB | 75413 | 75564 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 75413 | 9064 |
| grafana | the frozen tier | 1 | 61 MB | 61 MB | 75413 | 170818 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 331 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 469 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 401 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 285 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 75413 | 4379 |
| kafka | the frozen tier | 1 | 599 MB | 370 MB | 75413 | 1028910 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 75413 | 16562 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 350 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 1220 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 75413 | 28376 |
| opentelemetry-collector | the frozen tier | 1 | 2.9 GB | 140 MB | 75413 | 388407 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 207 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 661 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 75413 | 6644 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 75413 | 21 |
| recommendation | the frozen tier | 1 | 106 MB | 27 MB | 75413 | 75494 |
| valkey-cart | the frozen tier | 1 | 7 MB | 7 MB | 75413 | 18638 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 75413 | 661 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
