# Hot-tier run: 2026-10-23T15:35:39.000Z

Hot tier: 59 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 55 MB within 2 hours, with 3.9 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 4 MB on hot. The Receiver's kept lines: 42 MB in 11 indices; its tier_down lines not yet moved: 13 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 70 moved indices).
- Each counted byte takes 1.01 bytes of store kept, 0.61 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.3 GB a day; 421 MB a day fits the size, so each statement keeps up to 12 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 114 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 96% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 223 |
| ad | the frozen tier | 1 | 155 MB | 35 MB | 34634 | 96804 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 49 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 132 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 239 |
| cart | the frozen tier | 1 | 362 MB | 25 MB | 34634 | 70312 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 917 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 57 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 217 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 278 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 93 |
| fluentd-10x | the frozen tier | 1 | 29 MB | 15 MB | 34634 | 40817 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 248 |
| frontend | the frozen tier | 1 | 90 MB | 13 MB | 34634 | 34909 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 34634 | 6271 |
| grafana | the frozen tier | 1 | 44 MB | 44 MB | 34634 | 121147 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 412 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 583 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 503 |
| hb-inventory | the frozen tier | 1 | 45 MB | 12 MB | 34634 | 34634 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 367 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 34634 | 4276 |
| kafka | the frozen tier | 1 | 713 MB | 166 MB | 34634 | 461729 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 34634 | 6344 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 445 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 34634 | 1519 |
| opensearch | the frozen tier | 1 | 8 MB | 8 MB | 34634 | 21086 |
| opentelemetry-collector | the frozen tier | 1 | 2.7 GB | 71 MB | 34634 | 198308 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 266 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 822 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 34634 | 7830 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 34634 | 25 |
| recommendation | the frozen tier | 1 | 103 MB | 13 MB | 34634 | 34736 |
| valkey-cart | the frozen tier | 1 | 8 MB | 8 MB | 34634 | 22019 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 34634 | 869 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
