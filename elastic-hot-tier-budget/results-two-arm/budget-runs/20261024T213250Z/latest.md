# Hot-tier run: 2026-10-24T21:32:50.000Z

Hot tier: 15 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 1.7 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 7 MB in 2 indices; its tier_down lines not yet moved: 7 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 0.74 bytes of store kept, 0.65 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.5 GB a day; 816 MB a day fits the size, so each statement keeps up to 29 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 160 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 81582 | 3658 |
| ad | the frozen tier | 1 | 81 MB | 65 MB | 81582 | 180525 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 81 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 220 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 399 |
| cart | the frozen tier | 1 | 203 MB | 59 MB | 81582 | 163635 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 81582 | 2514 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 94 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 355 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 462 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 156 |
| fluentd-10x | the frozen tier | 1 | 18 MB | 18 MB | 81582 | 49749 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 403 |
| frontend | the frozen tier | 1 | 42 MB | 29 MB | 81582 | 81894 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 81582 | 10322 |
| grafana | the frozen tier | 1 | 50 MB | 50 MB | 81582 | 138639 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 686 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 970 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 831 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 593 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 81582 | 7078 |
| kafka | the frozen tier | 1 | 385 MB | 374 MB | 81582 | 1039240 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 81582 | 15370 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 727 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 81582 | 2523 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 81582 | 23741 |
| opentelemetry-collector | the frozen tier | 1 | 1.6 GB | 159 MB | 81582 | 441463 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 431 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 1367 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 81582 | 4932 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 81582 | 43 |
| recommendation | the frozen tier | 1 | 56 MB | 29 MB | 81582 | 81750 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 81582 | 11675 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 81582 | 2514 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
