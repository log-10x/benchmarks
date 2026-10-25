# Hot-tier run: 2026-10-25T05:43:27.000Z

Hot tier: 7 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 442 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 7 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 0 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.71 bytes of store kept, 0.71 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 1.1 GB a day fits the size, so each statement keeps up to 120 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 282 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 3 MB | 3 MB | 333676 | 7954 |
| ad | the frozen tier | 1 | 43 MB | 43 MB | 333676 | 119704 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 177 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 480 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 868 |
| cart | the frozen tier | 1 | 100 MB | 100 MB | 333676 | 278417 |
| coredns | the frozen tier | 1 | 2 MB | 2 MB | 333676 | 5468 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 204 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 772 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 1006 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 340 |
| fluentd-10x | the frozen tier | 1 | 15 MB | 15 MB | 333676 | 40990 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 878 |
| frontend | the frozen tier | 1 | 22 MB | 22 MB | 333676 | 61061 |
| frontend-proxy | the frozen tier | 1 | 8 MB | 8 MB | 333676 | 22445 |
| grafana | the frozen tier | 1 | 93 MB | 93 MB | 333676 | 257169 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 333676 | 1491 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 333676 | 2109 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 333676 | 1808 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 1289 |
| jaeger | the frozen tier | 1 | 6 MB | 6 MB | 333676 | 15390 |
| kafka | the frozen tier | 1 | 225 MB | 225 MB | 333676 | 625233 |
| kube-proxy | the frozen tier | 1 | 12 MB | 12 MB | 333676 | 32121 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 333676 | 1582 |
| metrics-server | the frozen tier | 1 | 2 MB | 2 MB | 333676 | 5486 |
| opensearch | the frozen tier | 1 | 16 MB | 16 MB | 333676 | 44252 |
| opentelemetry-collector | the frozen tier | 1 | 916 MB | 474 MB | 333676 | 1315968 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 937 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 333676 | 2973 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 333676 | 5982 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 333676 | 95 |
| recommendation | the frozen tier | 1 | 30 MB | 30 MB | 333676 | 84575 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 333676 | 7926 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 333676 | 5468 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
