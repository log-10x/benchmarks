# Hot-tier run: 2026-10-24T20:52:18.000Z

Hot tier: 6 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 99 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 3 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.13 bytes of store kept, 0.74 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.4 GB a day; 87 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 347 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 347 MB a day on hot, more than the 87 MB a day that fits, so hot settles above 74 MB at about 99 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 4 MB | 4 MB | 1 | 10295 |
| ad | the frozen tier | 1 | 39 MB | 2 MB | 1 | 6071 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 229 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 621 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1123 |
| cart | the frozen tier | 1 | 86 MB | 2 MB | 1 | 4405 |
| coredns | the frozen tier | 1 | 3 MB | 2 MB | 1 | 5554 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 265 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 999 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1302 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 441 |
| fluentd-10x | the frozen tier | 1 | 15 MB | 6 MB | 1 | 16637 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1136 |
| frontend | the frozen tier | 1 | 19 MB | 12 MB | 1 | 34033 |
| frontend-proxy | the frozen tier | 1 | 10 MB | 10 MB | 1 | 29050 |
| grafana | the frozen tier | 1 | 117 MB | 115 MB | 1 | 318246 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1930 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2730 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2340 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1669 |
| jaeger | the frozen tier | 1 | 7 MB | 7 MB | 1 | 19918 |
| kafka | the frozen tier | 1 | 206 MB | 31 MB | 1 | 85295 |
| kube-proxy | the frozen tier | 1 | 15 MB | 7 MB | 1 | 20729 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2047 |
| metrics-server | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7100 |
| opensearch | the frozen tier | 1 | 20 MB | 20 MB | 1 | 54191 |
| opentelemetry-collector | the frozen tier | 1 | 834 MB | 113 MB | 1 | 314565 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1213 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3848 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6936 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 123 |
| recommendation | the frozen tier | 1 | 26 MB | 1 MB | 1 | 2971 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7213 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 3848 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
