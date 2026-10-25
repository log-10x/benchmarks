# Hot-tier run: 2026-10-25T05:18:26.000Z

Hot tier: 9 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 1.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 9 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 8 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.88 bytes of store kept, 1.88 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.6 GB a day; 357 MB a day fits the size, so each statement keeps up to 5 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 233 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 13687 | 6233 |
| ad | the frozen tier | 1 | 47 MB | 14 MB | 13687 | 38077 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 138 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 376 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 680 |
| cart | the frozen tier | 1 | 109 MB | 10 MB | 13687 | 28178 |
| coredns | the frozen tier | 1 | 2 MB | 2 MB | 13687 | 4285 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 160 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 605 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 788 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 267 |
| fluentd-10x | the frozen tier | 1 | 14 MB | 13 MB | 13687 | 35294 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 688 |
| frontend | the frozen tier | 1 | 25 MB | 12 MB | 13687 | 33692 |
| frontend-proxy | the frozen tier | 1 | 6 MB | 6 MB | 13687 | 17588 |
| grafana | the frozen tier | 1 | 75 MB | 75 MB | 13687 | 207224 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 1169 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 13687 | 1653 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 13687 | 1417 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 1010 |
| jaeger | the frozen tier | 1 | 4 MB | 4 MB | 13687 | 12060 |
| kafka | the frozen tier | 1 | 238 MB | 92 MB | 13687 | 254181 |
| kube-proxy | the frozen tier | 1 | 9 MB | 9 MB | 13687 | 25171 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 1239 |
| metrics-server | the frozen tier | 1 | 2 MB | 2 MB | 13687 | 4299 |
| opensearch | the frozen tier | 1 | 13 MB | 13 MB | 13687 | 35766 |
| opentelemetry-collector | the frozen tier | 1 | 975 MB | 90 MB | 13687 | 249290 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 734 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 13687 | 2330 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 13687 | 5051 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 13687 | 74 |
| recommendation | the frozen tier | 1 | 35 MB | 5 MB | 13687 | 13973 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 13687 | 8512 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 13687 | 4285 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
