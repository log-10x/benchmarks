# Hot-tier run: 2026-10-23T14:45:40.000Z

Hot tier: 63 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 53 MB within 2 hours, with 4.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 2 MB on hot. The Receiver's kept lines: 48 MB in 11 indices; its tier_down lines not yet moved: 13 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 55 moved indices).
- Each counted byte takes 0.95 bytes of store kept, 0.59 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.5 GB a day; 435 MB a day fits the size, so each statement keeps up to 13 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 100 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 90% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 172 |
| ad | the frozen tier | 1 | 162 MB | 35 MB | 37263 | 98377 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 38 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 101 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 184 |
| cart | the frozen tier | 1 | 395 MB | 27 MB | 37263 | 75526 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 707 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 44 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 167 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 214 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 72 |
| fluentd-10x | the frozen tier | 1 | 31 MB | 21 MB | 37263 | 57880 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 191 |
| frontend | the frozen tier | 1 | 88 MB | 13 MB | 37263 | 37497 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 37263 | 4833 |
| grafana | the frozen tier | 1 | 36 MB | 36 MB | 37263 | 99111 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 317 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 449 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 387 |
| hb-inventory | the frozen tier | 1 | 36 MB | 13 MB | 37263 | 37263 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 283 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 37263 | 3296 |
| kafka | the frozen tier | 1 | 703 MB | 179 MB | 37263 | 497279 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 37263 | 5786 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 343 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 1171 |
| opensearch | the frozen tier | 1 | 7 MB | 7 MB | 37263 | 18275 |
| opentelemetry-collector | the frozen tier | 1 | 3 GB | 71 MB | 37263 | 197589 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 205 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 633 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 37263 | 7086 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 37263 | 19 |
| recommendation | the frozen tier | 1 | 112 MB | 13 MB | 37263 | 37341 |
| valkey-cart | the frozen tier | 1 | 9 MB | 9 MB | 37263 | 25416 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 37263 | 670 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
