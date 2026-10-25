# Hot-tier run: 2026-10-25T05:53:51.000Z

Hot tier: 12 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 12 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 3 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.75 bytes of store kept, 0.75 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.1 GB a day; 1 GB a day fits the size, so each statement keeps up to 86 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 159 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 239919 | 3642 |
| ad | the frozen tier | 1 | 65 MB | 65 MB | 239919 | 179588 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 81 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 219 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 397 |
| cart | the frozen tier | 1 | 160 MB | 148 MB | 239919 | 410505 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 239919 | 2504 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 93 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 353 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 460 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 156 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 13 MB | 239919 | 35409 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 402 |
| frontend | the frozen tier | 1 | 32 MB | 32 MB | 239919 | 89562 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 239919 | 10278 |
| grafana | the frozen tier | 1 | 47 MB | 47 MB | 239919 | 131418 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 683 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 966 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 828 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 590 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 239919 | 7047 |
| kafka | the frozen tier | 1 | 292 MB | 292 MB | 239919 | 811237 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 239919 | 15304 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 724 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 239919 | 2512 |
| opensearch | the frozen tier | 1 | 8 MB | 8 MB | 239919 | 23121 |
| opentelemetry-collector | the frozen tier | 1 | 1.4 GB | 329 MB | 239919 | 913181 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 429 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 1361 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 239919 | 4755 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 239919 | 43 |
| recommendation | the frozen tier | 1 | 45 MB | 45 MB | 239919 | 126313 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 239919 | 11913 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 239919 | 2504 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
