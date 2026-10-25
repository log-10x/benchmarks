# Hot-tier run: 2026-10-25T09:03:49.000Z

Hot tier: 61 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 3.7 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 60 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 17 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.93 bytes of store kept, 0.93 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.5 GB a day; 798 MB a day fits the size, so each statement keeps up to 31 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 84 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 176 |
| ad | the frozen tier | 1 | 156 MB | 69 MB | 85204 | 193016 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 40 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 108 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 196 |
| cart | the frozen tier | 1 | 426 MB | 61 MB | 85204 | 170641 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 752 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 46 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 174 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 227 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 77 |
| fluentd-10x | the frozen tier | 1 | 22 MB | 22 MB | 85204 | 61826 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 197 |
| frontend | the frozen tier | 1 | 90 MB | 31 MB | 85204 | 85358 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 85204 | 2720 |
| grafana | the frozen tier | 1 | 16 MB | 16 MB | 85204 | 45252 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 336 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 476 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 407 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 289 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 85204 | 2826 |
| kafka | the frozen tier | 1 | 667 MB | 405 MB | 85204 | 1126374 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 85204 | 4336 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 355 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 1238 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 85204 | 11358 |
| opentelemetry-collector | the frozen tier | 1 | 3 GB | 141 MB | 85204 | 390289 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 210 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 671 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 85204 | 6962 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 85204 | 21 |
| recommendation | the frozen tier | 1 | 123 MB | 31 MB | 85204 | 85286 |
| valkey-cart | the frozen tier | 1 | 8 MB | 8 MB | 85204 | 23442 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 85204 | 671 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
