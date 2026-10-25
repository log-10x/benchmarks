# Hot-tier run: 2026-10-25T00:52:50.000Z

Hot tier: 64 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 62 MB within 2 hours, with 4.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 46 MB in 10 indices; its tier_down lines not yet moved: 17 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 18 moved indices).
- Each counted byte takes 0.93 bytes of store kept, 0.55 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.7 GB a day; 441 MB a day fits the size, so each statement keeps up to 13 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 143 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 98% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 239 |
| ad | the frozen tier | 1 | 167 MB | 33 MB | 35739 | 92544 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 54 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 147 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 266 |
| cart | the frozen tier | 1 | 435 MB | 26 MB | 35739 | 71794 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 35739 | 2792 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 62 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 235 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 308 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 104 |
| fluentd-10x | the frozen tier | 1 | 26 MB | 15 MB | 35739 | 41641 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 267 |
| frontend | the frozen tier | 1 | 97 MB | 13 MB | 35739 | 35947 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 35739 | 12343 |
| grafana | the frozen tier | 1 | 78 MB | 78 MB | 35739 | 215791 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 341 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 483 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 413 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 391 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 35739 | 2795 |
| kafka | the frozen tier | 1 | 745 MB | 171 MB | 35739 | 474841 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 35739 | 3788 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 361 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 1256 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 35739 | 12455 |
| opentelemetry-collector | the frozen tier | 1 | 3 GB | 68 MB | 35739 | 190080 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 213 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 681 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 35739 | 6938 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 35739 | 21 |
| recommendation | the frozen tier | 1 | 129 MB | 13 MB | 35739 | 35823 |
| valkey-cart | the frozen tier | 1 | 7 MB | 7 MB | 35739 | 20479 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 35739 | 681 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
