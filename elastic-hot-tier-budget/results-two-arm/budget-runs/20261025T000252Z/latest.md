# Hot-tier run: 2026-10-25T00:02:52.000Z

Hot tier: 61 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 1.3 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 57 MB in 11 indices; its tier_down lines not yet moved: 3 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 14 moved indices).
- Each counted byte takes 0.88 bytes of store kept, 0.42 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2 GB a day; 761 MB a day fits the size, so each statement keeps up to 48 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 69 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 111 |
| ad | the frozen tier | 1 | 70 MB | 70 MB | 133067 | 195085 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 25 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 68 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 124 |
| cart | the frozen tier | 1 | 156 MB | 96 MB | 133067 | 266280 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 474 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 29 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 109 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 143 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 48 |
| fluentd-10x | the frozen tier | 1 | 12 MB | 12 MB | 133067 | 34365 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 124 |
| frontend | the frozen tier | 1 | 34 MB | 34 MB | 133067 | 95626 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 133067 | 1728 |
| grafana | the frozen tier | 1 | 10 MB | 10 MB | 133067 | 29081 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 212 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 300 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 257 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 182 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 133067 | 1772 |
| kafka | the frozen tier | 1 | 294 MB | 294 MB | 133067 | 815319 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 133067 | 2564 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 224 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 781 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 133067 | 7028 |
| opentelemetry-collector | the frozen tier | 1 | 1.4 GB | 186 MB | 133067 | 517056 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 132 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 423 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 133067 | 3992 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 133067 | 13 |
| recommendation | the frozen tier | 1 | 46 MB | 46 MB | 133067 | 128712 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 133067 | 11617 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 133067 | 423 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
