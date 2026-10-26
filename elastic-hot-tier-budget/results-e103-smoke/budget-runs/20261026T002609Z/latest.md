# Hot-tier run: 2026-10-26T00:26:09.000Z

Hot tier: 15 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 128 MB within 2 hours, with 1.3 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 13 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.28 bytes of store kept, 0.95 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 196 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 196 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 128 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4576 |
| ad | the frozen tier | 1 | 49 MB | 2 MB | 1 | 5712 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 87 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 416 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 529 |
| cart | the frozen tier | 1 | 113 MB | 1 MB | 1 | 3704 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3335 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 124 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 364 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1175 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 208 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 4 MB | 1 | 11725 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 310 |
| frontend | the frozen tier | 1 | 26 MB | 12 MB | 1 | 33931 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 1 | 13693 |
| grafana | the frozen tier | 1 | 60 MB | 56 MB | 1 | 156007 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 910 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1287 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 922 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2313 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 764 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 1 | 9345 |
| kafka | the frozen tier | 1 | 236 MB | 22 MB | 1 | 60957 |
| kube-proxy | the frozen tier | 1 | 7 MB | 4 MB | 1 | 12167 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1053 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3296 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 1 | 28546 |
| opentelemetry-collector | the frozen tier | 1 | 972 MB | 60 MB | 1 | 166809 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 358 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3333 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4310 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 58 |
| recommendation | the frozen tier | 1 | 34 MB | 1 MB | 1 | 2722 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 6987 |
| wait-for-kafka | the frozen tier | 1 | 3 MB | 0 MB | 1 | 1224 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 676 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2518 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
