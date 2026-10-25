# Hot-tier run: 2026-10-24T20:50:18.000Z

Hot tier: 4 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 96 MB within 2 hours, with 792 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 2 MB in 1 indices; its tier_down lines not yet moved: 2 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.05 bytes of store kept, 0.83 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.3 GB a day; 221 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 466 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 466 MB a day on hot, more than the 221 MB a day that fits, so hot settles above 74 MB at about 96 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 5 MB | 5 MB | 1 | 14197 |
| ad | the frozen tier | 1 | 27 MB | 2 MB | 1 | 6410 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 324 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 881 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1592 |
| cart | the frozen tier | 1 | 60 MB | 2 MB | 1 | 4962 |
| coredns | the frozen tier | 1 | 4 MB | 2 MB | 1 | 6837 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 375 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1417 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1846 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 625 |
| fluentd-10x | the frozen tier | 1 | 16 MB | 8 MB | 1 | 21896 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1611 |
| frontend | the frozen tier | 1 | 13 MB | 12 MB | 1 | 34389 |
| frontend-proxy | the frozen tier | 1 | 15 MB | 15 MB | 1 | 41183 |
| grafana | the frozen tier | 1 | 162 MB | 161 MB | 1 | 445892 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2737 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3870 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3317 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2366 |
| jaeger | the frozen tier | 1 | 9 MB | 9 MB | 1 | 24316 |
| kafka | the frozen tier | 1 | 175 MB | 37 MB | 1 | 103549 |
| kube-proxy | the frozen tier | 1 | 21 MB | 10 MB | 1 | 27401 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2902 |
| metrics-server | the frozen tier | 1 | 4 MB | 4 MB | 1 | 10066 |
| opensearch | the frozen tier | 1 | 28 MB | 26 MB | 1 | 73199 |
| opentelemetry-collector | the frozen tier | 1 | 684 MB | 155 MB | 1 | 430700 |
| payment | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1720 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5456 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 1 | 8414 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 174 |
| recommendation | the frozen tier | 1 | 19 MB | 1 MB | 1 | 3168 |
| valkey-cart | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5915 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 1 | 4962 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
