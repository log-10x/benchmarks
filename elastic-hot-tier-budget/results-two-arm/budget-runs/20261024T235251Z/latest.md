# Hot-tier run: 2026-10-24T23:52:52.000Z

Hot tier: 61 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 982 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 58 MB in 11 indices; its tier_down lines not yet moved: 3 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 13 moved indices).
- Each counted byte takes 0.86 bytes of store kept, 0.44 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 795 MB a day fits the size, so each statement keeps up to 67 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 68 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 110 |
| ad | the frozen tier | 1 | 55 MB | 55 MB | 186372 | 153005 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 24 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 67 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 122 |
| cart | the frozen tier | 1 | 147 MB | 123 MB | 186372 | 341064 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 468 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 28 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 108 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 141 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 48 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 186372 | 29266 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 123 |
| frontend | the frozen tier | 1 | 34 MB | 34 MB | 186372 | 94628 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 186372 | 1705 |
| grafana | the frozen tier | 1 | 10 MB | 10 MB | 186372 | 28014 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 209 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 296 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 253 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 180 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 186372 | 1749 |
| kafka | the frozen tier | 1 | 267 MB | 267 MB | 186372 | 742103 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 186372 | 2530 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 221 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 770 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 186372 | 6974 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 243 MB | 186372 | 676002 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 131 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 417 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 186372 | 3485 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 186372 | 13 |
| recommendation | the frozen tier | 1 | 41 MB | 41 MB | 186372 | 113311 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 186372 | 10789 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 186372 | 417 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
