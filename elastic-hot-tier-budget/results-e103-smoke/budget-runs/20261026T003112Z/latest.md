# Hot-tier run: 2026-10-26T00:31:12.000Z

Hot tier: 13 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 41 MB within 2 hours, with 2.7 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 4 MB in 2 indices; its tier_down lines not yet moved: 9 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 1.59 bytes of store kept, 0.53 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.9 GB a day; 179 MB a day fits the size, so each statement keeps up to 1 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 160 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 3081 | 3388 |
| ad | the frozen tier | 1 | 100 MB | 3 MB | 3081 | 9581 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 64 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 308 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 392 |
| cart | the frozen tier | 1 | 238 MB | 2 MB | 3081 | 6624 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 3081 | 2469 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 92 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 269 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 870 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 154 |
| fluentd-10x | the frozen tier | 1 | 19 MB | 3 MB | 3081 | 8553 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 230 |
| frontend | the frozen tier | 1 | 57 MB | 12 MB | 3081 | 33734 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 3081 | 10138 |
| grafana | the frozen tier | 1 | 52 MB | 44 MB | 3081 | 122725 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 673 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 952 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 683 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 3081 | 1712 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 566 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 3081 | 6919 |
| kafka | the frozen tier | 1 | 455 MB | 28 MB | 3081 | 78110 |
| kube-proxy | the frozen tier | 1 | 6 MB | 5 MB | 3081 | 14525 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 779 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 3081 | 2440 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 3081 | 25525 |
| opentelemetry-collector | the frozen tier | 1 | 1.9 GB | 48 MB | 3081 | 133965 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 265 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 3081 | 2390 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 3081 | 5813 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 42 |
| recommendation | the frozen tier | 1 | 62 MB | 1 MB | 3081 | 3245 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 3081 | 15762 |
| wait-for-kafka | the frozen tier | 1 | 2 MB | 1 MB | 3081 | 3217 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 3081 | 500 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 3081 | 2415 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
