# Hot-tier run: 2026-10-25T08:43:52.000Z

Hot tier: 63 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 3.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 62 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 19 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.91 bytes of store kept, 0.91 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.4 GB a day; 822 MB a day fits the size, so each statement keeps up to 29 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 138 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 171 |
| ad | the frozen tier | 1 | 149 MB | 65 MB | 80035 | 179461 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 38 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 105 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 191 |
| cart | the frozen tier | 1 | 419 MB | 58 MB | 80035 | 160297 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 80035 | 2076 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 44 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 169 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 221 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 75 |
| fluentd-10x | the frozen tier | 1 | 22 MB | 22 MB | 80035 | 61072 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 192 |
| frontend | the frozen tier | 1 | 87 MB | 29 MB | 80035 | 80184 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 80035 | 8286 |
| grafana | the frozen tier | 1 | 53 MB | 53 MB | 80035 | 147991 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 327 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 462 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 396 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 281 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 80035 | 4000 |
| kafka | the frozen tier | 1 | 621 MB | 391 MB | 80035 | 1085256 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 80035 | 14875 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 346 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 1203 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 80035 | 25389 |
| opentelemetry-collector | the frozen tier | 1 | 2.9 GB | 145 MB | 80035 | 401820 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 204 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 652 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 80035 | 6651 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 80035 | 20 |
| recommendation | the frozen tier | 1 | 118 MB | 29 MB | 80035 | 80115 |
| valkey-cart | the frozen tier | 1 | 7 MB | 7 MB | 80035 | 20526 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 80035 | 652 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
