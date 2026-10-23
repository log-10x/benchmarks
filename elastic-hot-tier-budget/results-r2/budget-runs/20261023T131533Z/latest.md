# Hot-tier run: 2026-10-23T13:15:34.000Z

Hot tier: 51 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 57 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 2 MB on hot. The Receiver's kept lines: 47 MB in 10 indices; its tier_down lines not yet moved: 3 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 28 moved indices).
- Each counted byte takes 0.87 bytes of store kept, 0.51 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 708 MB a day fits the size, so each statement keeps up to 60 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 84 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 679 |
| ad | the frozen tier | 1 | 50 MB | 50 MB | 167157 | 137840 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 27 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 74 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 134 |
| cart | the frozen tier | 1 | 134 MB | 106 MB | 167157 | 294423 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 680 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 32 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 121 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 156 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 52 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 167157 | 29760 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 139 |
| frontend | the frozen tier | 1 | 31 MB | 31 MB | 167157 | 85651 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 167157 | 3519 |
| grafana | the frozen tier | 1 | 21 MB | 21 MB | 167157 | 59234 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 231 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 327 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 282 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 206 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 167157 | 2400 |
| kafka | the frozen tier | 1 | 217 MB | 217 MB | 167157 | 603543 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 167157 | 4742 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 250 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 852 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 167157 | 11165 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 221 MB | 167157 | 615274 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 149 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 461 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 167157 | 3642 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 167157 | 14 |
| recommendation | the frozen tier | 1 | 36 MB | 36 MB | 167157 | 100200 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 167157 | 9670 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 167157 | 679 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
