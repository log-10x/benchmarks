# Hot-tier run: 2026-10-25T07:13:54.000Z

Hot tier: 52 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 911 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 52 MB in 9 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 4 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.83 bytes of store kept, 0.83 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 908 MB a day fits the size, so each statement keeps up to 92 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 84 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 774 |
| ad | the frozen tier | 1 | 58 MB | 58 MB | 254850 | 162410 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 31 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 85 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 154 |
| cart | the frozen tier | 1 | 141 MB | 141 MB | 254850 | 392495 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 781 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 36 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 137 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 179 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 60 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 254850 | 31580 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 155 |
| frontend | the frozen tier | 1 | 33 MB | 33 MB | 254850 | 92591 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 254850 | 3108 |
| grafana | the frozen tier | 1 | 17 MB | 17 MB | 254850 | 47803 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 264 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 374 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 321 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 228 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 254850 | 2484 |
| kafka | the frozen tier | 1 | 270 MB | 270 MB | 254850 | 749050 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 254850 | 4827 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 280 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 974 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 254850 | 10062 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 321 MB | 254850 | 892875 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 166 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 528 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 254850 | 3563 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 254850 | 16 |
| recommendation | the frozen tier | 1 | 41 MB | 41 MB | 254850 | 114648 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 254850 | 10422 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 254850 | 774 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
