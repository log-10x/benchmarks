# Hot-tier run: 2026-10-25T05:27:25.000Z

Hot tier: 7 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 2.4 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 6 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 10 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.94 bytes of store kept, 0.94 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3.1 GB a day; 716 MB a day fits the size, so each statement keeps up to 24 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 156 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 66603 | 3460 |
| ad | the frozen tier | 1 | 99 MB | 55 MB | 66603 | 153731 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 77 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 208 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 377 |
| cart | the frozen tier | 1 | 264 MB | 48 MB | 66603 | 133652 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 66603 | 2378 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 89 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 336 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 437 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 148 |
| fluentd-10x | the frozen tier | 1 | 20 MB | 20 MB | 66603 | 54511 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 382 |
| frontend | the frozen tier | 1 | 58 MB | 24 MB | 66603 | 66898 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 66603 | 9764 |
| grafana | the frozen tier | 1 | 48 MB | 48 MB | 66603 | 134068 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 649 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 917 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 786 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 561 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 66603 | 6695 |
| kafka | the frozen tier | 1 | 460 MB | 327 MB | 66603 | 908169 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 66603 | 15104 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 688 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 66603 | 2386 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 66603 | 24913 |
| opentelemetry-collector | the frozen tier | 1 | 2 GB | 135 MB | 66603 | 375324 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 408 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 1293 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 66603 | 6187 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 66603 | 41 |
| recommendation | the frozen tier | 1 | 69 MB | 24 MB | 66603 | 66761 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 66603 | 16529 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 66603 | 2378 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
