# Hot-tier run: 2026-10-25T05:22:21.000Z

Hot tier: 6 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 6 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 7 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.17 bytes of store kept, 1.17 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.6 GB a day; 573 MB a day fits the size, so each statement keeps up to 17 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 187 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 48213 | 4619 |
| ad | the frozen tier | 1 | 51 MB | 39 MB | 48213 | 107755 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 102 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 278 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 504 |
| cart | the frozen tier | 1 | 121 MB | 35 MB | 48213 | 97022 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 48213 | 3175 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 118 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 448 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 584 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 198 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 13 MB | 48213 | 36736 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 510 |
| frontend | the frozen tier | 1 | 28 MB | 17 MB | 48213 | 48607 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 48213 | 13035 |
| grafana | the frozen tier | 1 | 58 MB | 58 MB | 48213 | 159896 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 866 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 1225 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 1050 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 749 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 48213 | 8937 |
| kafka | the frozen tier | 1 | 249 MB | 235 MB | 48213 | 651947 |
| kube-proxy | the frozen tier | 1 | 7 MB | 7 MB | 48213 | 19157 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 918 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 48213 | 3186 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 48213 | 27877 |
| opentelemetry-collector | the frozen tier | 1 | 1 GB | 122 MB | 48213 | 338242 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 544 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 48213 | 1727 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 48213 | 4283 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 48213 | 55 |
| recommendation | the frozen tier | 1 | 36 MB | 17 MB | 48213 | 48425 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 48213 | 9380 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 48213 | 3175 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
