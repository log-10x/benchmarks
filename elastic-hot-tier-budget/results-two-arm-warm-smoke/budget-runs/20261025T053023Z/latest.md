# Hot-tier run: 2026-10-25T05:30:24.000Z

Hot tier: 8 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 2.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 8 MB in 3 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 12 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.97 bytes of store kept, 0.97 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.9 GB a day; 694 MB a day fits the size, so each statement keeps up to 24 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 143 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 66078 | 3015 |
| ad | the frozen tier | 1 | 95 MB | 54 MB | 66078 | 151258 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 67 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 182 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 329 |
| cart | the frozen tier | 1 | 250 MB | 48 MB | 66078 | 132546 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 66078 | 2072 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 77 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 292 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 381 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 129 |
| fluentd-10x | the frozen tier | 1 | 18 MB | 18 MB | 66078 | 50395 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 332 |
| frontend | the frozen tier | 1 | 55 MB | 24 MB | 66078 | 66336 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 66078 | 8508 |
| grafana | the frozen tier | 1 | 44 MB | 44 MB | 66078 | 121127 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 565 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 799 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 685 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 488 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 66078 | 5833 |
| kafka | the frozen tier | 1 | 428 MB | 322 MB | 66078 | 895662 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 66078 | 13489 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 599 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 66078 | 2079 |
| opensearch | the frozen tier | 1 | 8 MB | 8 MB | 66078 | 22650 |
| opentelemetry-collector | the frozen tier | 1 | 1.9 GB | 129 MB | 66078 | 359209 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 355 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 1127 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 66078 | 5828 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 66078 | 36 |
| recommendation | the frozen tier | 1 | 67 MB | 24 MB | 66078 | 66217 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 66078 | 15613 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 66078 | 2072 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
