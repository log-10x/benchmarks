# Hot-tier run: 2026-10-24T23:22:49.000Z

Hot tier: 59 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 933 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 50 MB in 11 indices; its tier_down lines not yet moved: 8 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 10 moved indices).
- Each counted byte takes 0.88 bytes of store kept, 0.85 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.7 GB a day; 722 MB a day fits the size, so each statement keeps up to 42 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 132 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 116 |
| ad | the frozen tier | 1 | 53 MB | 53 MB | 116475 | 147978 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 26 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 71 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 129 |
| cart | the frozen tier | 1 | 128 MB | 84 MB | 116475 | 233103 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 116475 | 1851 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 30 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 114 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 149 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 50 |
| fluentd-10x | the frozen tier | 1 | 12 MB | 12 MB | 116475 | 32947 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 130 |
| frontend | the frozen tier | 1 | 31 MB | 31 MB | 116475 | 86923 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 116475 | 8571 |
| grafana | the frozen tier | 1 | 58 MB | 58 MB | 116475 | 161706 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 221 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 313 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 268 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 190 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 116475 | 3772 |
| kafka | the frozen tier | 1 | 249 MB | 249 MB | 116475 | 691702 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 116475 | 17087 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 234 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 814 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 116475 | 25114 |
| opentelemetry-collector | the frozen tier | 1 | 1.1 GB | 170 MB | 116475 | 472523 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 138 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 441 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 116475 | 3461 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 116475 | 14 |
| recommendation | the frozen tier | 1 | 38 MB | 38 MB | 116475 | 104296 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 116475 | 9914 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 116475 | 441 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
