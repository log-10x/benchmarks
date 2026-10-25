# Hot-tier run: 2026-10-24T23:42:51.000Z

Hot tier: 58 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 54 MB in 10 indices; its tier_down lines not yet moved: 3 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 12 moved indices).
- Each counted byte takes 0.88 bytes of store kept, 0.39 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.9 GB a day; 782 MB a day fits the size, so each statement keeps up to 69 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 71 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 119 |
| ad | the frozen tier | 1 | 60 MB | 60 MB | 190725 | 165694 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 27 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 73 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 133 |
| cart | the frozen tier | 1 | 159 MB | 119 MB | 190725 | 330449 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 509 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 31 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 117 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 154 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 52 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 190725 | 30455 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 133 |
| frontend | the frozen tier | 1 | 34 MB | 34 MB | 190725 | 94030 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 190725 | 1852 |
| grafana | the frozen tier | 1 | 10 MB | 10 MB | 190725 | 28276 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 227 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 322 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 275 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 195 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 190725 | 1900 |
| kafka | the frozen tier | 1 | 250 MB | 250 MB | 190725 | 693067 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 190725 | 2617 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 240 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 837 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 190725 | 7876 |
| opentelemetry-collector | the frozen tier | 1 | 1.3 GB | 249 MB | 190725 | 691352 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 142 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 454 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 190725 | 3538 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 190725 | 14 |
| recommendation | the frozen tier | 1 | 39 MB | 39 MB | 190725 | 106962 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 190725 | 10003 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 190725 | 454 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
