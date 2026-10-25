# Hot-tier run: 2026-10-25T05:16:26.000Z

Hot tier: 4 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 798 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 4 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 3 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.94 bytes of store kept, 0.94 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 715 MB a day fits the size, so each statement keeps up to 25 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 272 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 3 MB | 3 MB | 70141 | 7586 |
| ad | the frozen tier | 1 | 43 MB | 43 MB | 70141 | 120366 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 168 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 458 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 828 |
| cart | the frozen tier | 1 | 102 MB | 51 MB | 70141 | 141260 |
| coredns | the frozen tier | 1 | 2 MB | 2 MB | 70141 | 5215 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 195 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 736 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 960 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 325 |
| fluentd-10x | the frozen tier | 1 | 15 MB | 15 MB | 70141 | 40447 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 837 |
| frontend | the frozen tier | 1 | 22 MB | 22 MB | 70141 | 62148 |
| frontend-proxy | the frozen tier | 1 | 8 MB | 8 MB | 70141 | 21407 |
| grafana | the frozen tier | 1 | 89 MB | 89 MB | 70141 | 246615 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 70141 | 1422 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 70141 | 2012 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 70141 | 1724 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 1230 |
| jaeger | the frozen tier | 1 | 5 MB | 5 MB | 70141 | 14678 |
| kafka | the frozen tier | 1 | 228 MB | 228 MB | 70141 | 633241 |
| kube-proxy | the frozen tier | 1 | 11 MB | 11 MB | 70141 | 30635 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 70141 | 1508 |
| metrics-server | the frozen tier | 1 | 2 MB | 2 MB | 70141 | 5232 |
| opensearch | the frozen tier | 1 | 15 MB | 15 MB | 70141 | 42328 |
| opentelemetry-collector | the frozen tier | 1 | 927 MB | 185 MB | 70141 | 514934 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 894 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 70141 | 2836 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 70141 | 5853 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 70141 | 90 |
| recommendation | the frozen tier | 1 | 31 MB | 25 MB | 70141 | 70489 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 70141 | 8118 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 70141 | 5215 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
