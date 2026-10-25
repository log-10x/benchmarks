# Hot-tier run: 2026-10-25T05:26:22.000Z

Hot tier: 9 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 2.4 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 9 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 9 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.32 bytes of store kept, 1.32 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.9 GB a day; 508 MB a day fits the size, so each statement keeps up to 15 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 161 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 41199 | 3650 |
| ad | the frozen tier | 1 | 92 MB | 36 MB | 41199 | 100572 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 81 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 220 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 398 |
| cart | the frozen tier | 1 | 249 MB | 30 MB | 41199 | 82868 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 41199 | 2509 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 94 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 354 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 461 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 156 |
| fluentd-10x | the frozen tier | 1 | 18 MB | 18 MB | 41199 | 50232 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 403 |
| frontend | the frozen tier | 1 | 53 MB | 15 MB | 41199 | 41510 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 41199 | 10300 |
| grafana | the frozen tier | 1 | 50 MB | 50 MB | 41199 | 138241 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 684 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 968 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 829 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 591 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 41199 | 7062 |
| kafka | the frozen tier | 1 | 426 MB | 209 MB | 41199 | 580239 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 41199 | 15734 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 726 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 41199 | 2517 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 41199 | 25456 |
| opentelemetry-collector | the frozen tier | 1 | 1.9 GB | 101 MB | 41199 | 279681 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 430 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 1364 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 41199 | 5807 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 41199 | 43 |
| recommendation | the frozen tier | 1 | 63 MB | 15 MB | 41199 | 41366 |
| valkey-cart | the frozen tier | 1 | 5 MB | 5 MB | 41199 | 14946 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 41199 | 2509 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
