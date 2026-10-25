# Hot-tier run: 2026-10-25T05:11:13.000Z

Hot tier: 3 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 449 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 0 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.97 bytes of store kept, 0.97 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.1 GB a day; 694 MB a day fits the size, so each statement keeps up to 6 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 525 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 6 MB | 6 MB | 15535 | 17493 |
| ad | the frozen tier | 1 | 18 MB | 13 MB | 15535 | 37229 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 15535 | 389 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 15535 | 1056 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 1909 |
| cart | the frozen tier | 1 | 46 MB | 12 MB | 15535 | 33325 |
| coredns | the frozen tier | 1 | 4 MB | 4 MB | 15535 | 12024 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 15535 | 450 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 1698 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 2213 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 15535 | 749 |
| fluentd-10x | the frozen tier | 1 | 17 MB | 16 MB | 15535 | 43907 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 1931 |
| frontend | the frozen tier | 1 | 11 MB | 11 MB | 15535 | 29839 |
| frontend-proxy | the frozen tier | 1 | 18 MB | 18 MB | 15535 | 49050 |
| grafana | the frozen tier | 1 | 192 MB | 192 MB | 15535 | 534591 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 3280 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 15535 | 4639 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 3976 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 2836 |
| jaeger | the frozen tier | 1 | 10 MB | 10 MB | 15535 | 29143 |
| kafka | the frozen tier | 1 | 151 MB | 137 MB | 15535 | 381481 |
| kube-proxy | the frozen tier | 1 | 25 MB | 24 MB | 15535 | 67515 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 3478 |
| metrics-server | the frozen tier | 1 | 4 MB | 4 MB | 15535 | 12064 |
| opensearch | the frozen tier | 1 | 33 MB | 33 MB | 15535 | 90593 |
| opentelemetry-collector | the frozen tier | 1 | 573 MB | 188 MB | 15535 | 522008 |
| payment | the frozen tier | 1 | 1 MB | 1 MB | 15535 | 2062 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 15535 | 6539 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 15535 | 9411 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 15535 | 209 |
| recommendation | the frozen tier | 1 | 15 MB | 6 MB | 15535 | 16338 |
| valkey-cart | the frozen tier | 1 | 2 MB | 2 MB | 15535 | 4505 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 15535 | 6539 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
