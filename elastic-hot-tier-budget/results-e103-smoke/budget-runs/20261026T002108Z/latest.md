# Hot-tier run: 2026-10-26T00:21:09.000Z

Hot tier: 9 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 111 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 5 MB in 1 indices; its tier_down lines not yet moved: 4 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 2.34 bytes of store kept, 0.60 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.4 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 270 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 270 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 111 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7010 |
| ad | the frozen tier | 1 | 40 MB | 2 MB | 1 | 5955 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 134 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 637 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 811 |
| cart | the frozen tier | 1 | 94 MB | 1 MB | 1 | 4033 |
| coredns | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4421 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 191 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 558 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1801 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 318 |
| fluentd-10x | the frozen tier | 1 | 14 MB | 5 MB | 1 | 14184 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 476 |
| frontend | the frozen tier | 1 | 21 MB | 12 MB | 1 | 34338 |
| frontend-proxy | the frozen tier | 1 | 8 MB | 8 MB | 1 | 20975 |
| grafana | the frozen tier | 1 | 87 MB | 84 MB | 1 | 232242 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1394 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1971 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1413 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3543 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1171 |
| jaeger | the frozen tier | 1 | 5 MB | 5 MB | 1 | 14315 |
| kafka | the frozen tier | 1 | 213 MB | 26 MB | 1 | 72784 |
| kube-proxy | the frozen tier | 1 | 11 MB | 6 MB | 1 | 16109 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1613 |
| metrics-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5049 |
| opensearch | the frozen tier | 1 | 15 MB | 15 MB | 1 | 41262 |
| opentelemetry-collector | the frozen tier | 1 | 861 MB | 85 MB | 1 | 236874 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 548 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5106 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5590 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 88 |
| recommendation | the frozen tier | 1 | 29 MB | 1 MB | 1 | 2840 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7271 |
| wait-for-kafka | the frozen tier | 1 | 5 MB | 0 MB | 1 | 1322 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1035 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 3192 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
