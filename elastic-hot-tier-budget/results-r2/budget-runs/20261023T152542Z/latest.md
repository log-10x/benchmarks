# Hot-tier run: 2026-10-23T15:25:42.000Z

Hot tier: 62 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 54 MB within 2 hours, with 3.7 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 4 MB on hot. The Receiver's kept lines: 46 MB in 11 indices; its tier_down lines not yet moved: 12 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 67 moved indices).
- Each counted byte takes 1.00 bytes of store kept, 0.61 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.1 GB a day; 416 MB a day fits the size, so each statement keeps up to 9 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 147 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 92% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 275 |
| ad | the frozen tier | 1 | 143 MB | 27 MB | 26098 | 74929 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 60 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 162 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 294 |
| cart | the frozen tier | 1 | 335 MB | 19 MB | 26098 | 53295 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 26098 | 3433 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 70 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 267 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 343 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 115 |
| fluentd-10x | the frozen tier | 1 | 30 MB | 19 MB | 26098 | 52143 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 306 |
| frontend | the frozen tier | 1 | 80 MB | 12 MB | 26098 | 32779 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 26098 | 7731 |
| grafana | the frozen tier | 1 | 48 MB | 47 MB | 26098 | 130137 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 508 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 719 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 620 |
| hb-inventory | the frozen tier | 1 | 44 MB | 9 MB | 26098 | 26098 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 453 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 26098 | 5272 |
| kafka | the frozen tier | 1 | 693 MB | 150 MB | 26098 | 418016 |
| kube-proxy | the frozen tier | 1 | 9 MB | 9 MB | 26098 | 26014 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 549 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 26098 | 1873 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 26098 | 25739 |
| opentelemetry-collector | the frozen tier | 1 | 2.6 GB | 85 MB | 26098 | 237254 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 329 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 1013 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 26098 | 6850 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 26098 | 31 |
| recommendation | the frozen tier | 1 | 103 MB | 9 MB | 26098 | 26223 |
| valkey-cart | the frozen tier | 1 | 8 MB | 8 MB | 26098 | 20853 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 26098 | 1443 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
