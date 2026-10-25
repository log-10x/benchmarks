# Hot-tier run: 2026-10-25T05:21:22.000Z

Hot tier: 10 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 1.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 10 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 9 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.87 bytes of store kept, 1.87 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.6 GB a day; 359 MB a day fits the size, so each statement keeps up to 7 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 196 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 19118 | 4940 |
| ad | the frozen tier | 1 | 51 MB | 18 MB | 19118 | 49522 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 110 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 298 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 539 |
| cart | the frozen tier | 1 | 118 MB | 14 MB | 19118 | 38873 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 19118 | 3396 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 127 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 479 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 625 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 211 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 13 MB | 19118 | 37132 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 545 |
| frontend | the frozen tier | 1 | 27 MB | 12 MB | 19118 | 33583 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 19118 | 13941 |
| grafana | the frozen tier | 1 | 61 MB | 61 MB | 19118 | 169342 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 926 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 1310 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 1123 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 801 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 19118 | 9559 |
| kafka | the frozen tier | 1 | 247 MB | 111 MB | 19118 | 308976 |
| kube-proxy | the frozen tier | 1 | 7 MB | 7 MB | 19118 | 20489 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 982 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 19118 | 3407 |
| opensearch | the frozen tier | 1 | 11 MB | 11 MB | 19118 | 29463 |
| opentelemetry-collector | the frozen tier | 1 | 1 GB | 84 MB | 19118 | 231968 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 582 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 19118 | 1847 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 19118 | 4388 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 19118 | 59 |
| recommendation | the frozen tier | 1 | 35 MB | 7 MB | 19118 | 19345 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 19118 | 9302 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 19118 | 3396 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
