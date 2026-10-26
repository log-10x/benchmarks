# Hot-tier run: 2026-10-26T00:23:13.000Z

Hot tier: 13 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 138 MB within 2 hours, with 1.3 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 11 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.20 bytes of store kept, 1.10 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 232 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 232 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 138 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5747 |
| ad | the frozen tier | 1 | 45 MB | 2 MB | 1 | 5829 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 110 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 522 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 665 |
| cart | the frozen tier | 1 | 103 MB | 1 MB | 1 | 3862 |
| coredns | the frozen tier | 1 | 2 MB | 1 MB | 1 | 3858 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 156 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 457 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1476 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 261 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 5 MB | 1 | 13245 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 390 |
| frontend | the frozen tier | 1 | 23 MB | 12 MB | 1 | 34127 |
| frontend-proxy | the frozen tier | 1 | 6 MB | 6 MB | 1 | 17195 |
| grafana | the frozen tier | 1 | 73 MB | 69 MB | 1 | 192810 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1142 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1616 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1158 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2905 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 960 |
| jaeger | the frozen tier | 1 | 4 MB | 4 MB | 1 | 11735 |
| kafka | the frozen tier | 1 | 225 MB | 24 MB | 1 | 66640 |
| kube-proxy | the frozen tier | 1 | 9 MB | 5 MB | 1 | 14063 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1322 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 4139 |
| opensearch | the frozen tier | 1 | 13 MB | 12 MB | 1 | 34702 |
| opentelemetry-collector | the frozen tier | 1 | 923 MB | 72 MB | 1 | 200507 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 449 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4186 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4820 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 72 |
| recommendation | the frozen tier | 1 | 33 MB | 1 MB | 1 | 2779 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7123 |
| wait-for-kafka | the frozen tier | 1 | 4 MB | 0 MB | 1 | 1271 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 849 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2842 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
