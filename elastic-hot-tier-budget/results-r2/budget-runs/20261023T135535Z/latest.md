# Hot-tier run: 2026-10-23T13:55:35.000Z

Hot tier: 60 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 54 MB within 2 hours, with 1.9 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 2 MB on hot. The Receiver's kept lines: 52 MB in 10 indices; its tier_down lines not yet moved: 5 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 40 moved indices).
- Each counted byte takes 0.95 bytes of store kept, 0.56 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.5 GB a day; 575 MB a day fits the size, so each statement keeps up to 23 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 82 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 95% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 118 |
| ad | the frozen tier | 1 | 76 MB | 50 MB | 64081 | 139116 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 26 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 69 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 126 |
| cart | the frozen tier | 1 | 258 MB | 46 MB | 64081 | 128319 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 485 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 30 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 114 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 147 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 49 |
| fluentd-10x | the frozen tier | 1 | 12 MB | 12 MB | 64081 | 32531 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 131 |
| frontend | the frozen tier | 1 | 48 MB | 23 MB | 64081 | 64226 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 64081 | 3317 |
| grafana | the frozen tier | 1 | 21 MB | 21 MB | 64081 | 59695 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 218 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 308 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 266 |
| hb-inventory | the frozen tier | 1 | 2 MB | 2 MB | 64081 | 4840 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 194 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 64081 | 2262 |
| kafka | the frozen tier | 1 | 306 MB | 280 MB | 64081 | 778211 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 64081 | 3435 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 235 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 803 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 64081 | 10988 |
| opentelemetry-collector | the frozen tier | 1 | 1.7 GB | 104 MB | 64081 | 289596 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 141 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 434 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 64081 | 3715 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 64081 | 13 |
| recommendation | the frozen tier | 1 | 71 MB | 23 MB | 64081 | 64134 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 64081 | 9978 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 64081 | 460 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
