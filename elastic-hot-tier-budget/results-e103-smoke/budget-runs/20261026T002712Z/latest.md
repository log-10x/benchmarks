# Hot-tier run: 2026-10-26T00:27:13.000Z

Hot tier: 12 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 89 MB within 2 hours, with 1.4 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 9 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.29 bytes of store kept, 0.60 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.6 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 186 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 186 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 89 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4261 |
| ad | the frozen tier | 1 | 49 MB | 2 MB | 1 | 5681 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 81 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 387 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 493 |
| cart | the frozen tier | 1 | 115 MB | 1 MB | 1 | 3661 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3105 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 116 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 339 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1094 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 193 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 4 MB | 1 | 11315 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 289 |
| frontend | the frozen tier | 1 | 27 MB | 12 MB | 1 | 33879 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 1 | 12749 |
| grafana | the frozen tier | 1 | 56 MB | 53 MB | 1 | 145931 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 847 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1198 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 859 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2154 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 711 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 1 | 8701 |
| kafka | the frozen tier | 1 | 239 MB | 21 MB | 1 | 59424 |
| kube-proxy | the frozen tier | 1 | 7 MB | 4 MB | 1 | 11656 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 980 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3068 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 1 | 26762 |
| opentelemetry-collector | the frozen tier | 1 | 986 MB | 57 MB | 1 | 157724 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 333 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3103 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 4101 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 54 |
| recommendation | the frozen tier | 1 | 35 MB | 1 MB | 1 | 2707 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 6950 |
| wait-for-kafka | the frozen tier | 1 | 3 MB | 0 MB | 1 | 1211 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 629 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2430 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
