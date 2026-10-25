# Hot-tier run: 2026-10-25T05:13:26.000Z

Hot tier: 3 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 586 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 2 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.85 bytes of store kept, 0.85 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.4 GB a day; 792 MB a day fits the size, so each statement keeps up to 29 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 374 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 4 MB | 4 MB | 79715 | 11250 |
| ad | the frozen tier | 1 | 38 MB | 38 MB | 79715 | 104187 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 250 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 679 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 1227 |
| cart | the frozen tier | 1 | 80 MB | 58 MB | 79715 | 160879 |
| coredns | the frozen tier | 1 | 3 MB | 3 MB | 79715 | 7733 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 289 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 1092 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 79715 | 1423 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 482 |
| fluentd-10x | the frozen tier | 1 | 15 MB | 15 MB | 79715 | 42742 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 1242 |
| frontend | the frozen tier | 1 | 17 MB | 17 MB | 79715 | 48312 |
| frontend-proxy | the frozen tier | 1 | 11 MB | 11 MB | 79715 | 31745 |
| grafana | the frozen tier | 1 | 127 MB | 127 MB | 79715 | 353002 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 79715 | 2110 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 79715 | 2983 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 79715 | 2557 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 79715 | 1824 |
| jaeger | the frozen tier | 1 | 8 MB | 8 MB | 79715 | 21767 |
| kafka | the frozen tier | 1 | 200 MB | 200 MB | 79715 | 554973 |
| kube-proxy | the frozen tier | 1 | 16 MB | 16 MB | 79715 | 44205 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 79715 | 2237 |
| metrics-server | the frozen tier | 1 | 3 MB | 3 MB | 79715 | 7759 |
| opensearch | the frozen tier | 1 | 22 MB | 22 MB | 79715 | 60050 |
| opentelemetry-collector | the frozen tier | 1 | 797 MB | 232 MB | 79715 | 645809 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 1326 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 79715 | 4205 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 79715 | 7366 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 79715 | 134 |
| recommendation | the frozen tier | 1 | 24 MB | 24 MB | 79715 | 65818 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 79715 | 7053 |
| `*` (any other service) | the frozen tier | 1 | | 3 MB | 79715 | 7053 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
