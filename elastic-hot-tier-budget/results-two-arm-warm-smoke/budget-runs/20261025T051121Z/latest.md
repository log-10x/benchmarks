# Hot-tier run: 2026-10-25T05:11:21.000Z

Hot tier: 3 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 427 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 0 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.91 bytes of store kept, 0.91 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.2 GB a day; 740 MB a day fits the size, so each statement keeps up to 10 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 515 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 6 MB | 6 MB | 26722 | 16928 |
| ad | the frozen tier | 1 | 19 MB | 19 MB | 26722 | 53845 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 26722 | 376 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 26722 | 1022 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 1847 |
| cart | the frozen tier | 1 | 49 MB | 20 MB | 26722 | 55626 |
| coredns | the frozen tier | 1 | 4 MB | 4 MB | 26722 | 11636 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 26722 | 435 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 1644 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 2142 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 26722 | 725 |
| fluentd-10x | the frozen tier | 1 | 16 MB | 16 MB | 26722 | 45743 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 1868 |
| frontend | the frozen tier | 1 | 11 MB | 11 MB | 26722 | 31212 |
| frontend-proxy | the frozen tier | 1 | 17 MB | 17 MB | 26722 | 47764 |
| grafana | the frozen tier | 1 | 187 MB | 187 MB | 26722 | 518751 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 3174 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 26722 | 4489 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 3848 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 2744 |
| jaeger | the frozen tier | 1 | 10 MB | 10 MB | 26722 | 28202 |
| kafka | the frozen tier | 1 | 154 MB | 154 MB | 26722 | 428016 |
| kube-proxy | the frozen tier | 1 | 24 MB | 24 MB | 26722 | 66511 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 3366 |
| metrics-server | the frozen tier | 1 | 4 MB | 4 MB | 26722 | 11675 |
| opensearch | the frozen tier | 1 | 32 MB | 32 MB | 26722 | 87668 |
| opentelemetry-collector | the frozen tier | 1 | 597 MB | 207 MB | 26722 | 575457 |
| payment | the frozen tier | 1 | 1 MB | 1 MB | 26722 | 1995 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 26722 | 6328 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 26722 | 9107 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 26722 | 202 |
| recommendation | the frozen tier | 1 | 17 MB | 10 MB | 26722 | 27499 |
| valkey-cart | the frozen tier | 1 | 2 MB | 2 MB | 26722 | 4359 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 26722 | 6328 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
