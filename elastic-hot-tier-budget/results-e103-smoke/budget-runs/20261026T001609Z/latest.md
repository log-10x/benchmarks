# Hot-tier run: 2026-10-26T00:16:09.000Z

Hot tier: 3 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 74 MB within 2 hours, with 502 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 2 MB in 1 indices; its tier_down lines not yet moved: 1 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.20 bytes of store kept, 0.58 as tier_down (measured on the indices on hot).
- The Receiver's statements send 999 MB a day; 164 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 497 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 497 MB a day on hot, more than the 164 MB a day that fits, so hot settles above 41 MB at about 74 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 5 MB | 5 MB | 1 | 14129 |
| ad | the frozen tier | 1 | 16 MB | 2 MB | 1 | 6743 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 287 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1361 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1732 |
| cart | the frozen tier | 1 | 37 MB | 2 MB | 1 | 5115 |
| coredns | the frozen tier | 1 | 4 MB | 3 MB | 1 | 7035 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 408 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1192 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3847 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 680 |
| fluentd-10x | the frozen tier | 1 | 15 MB | 8 MB | 1 | 23495 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1016 |
| frontend | the frozen tier | 1 | 8 MB | 8 MB | 1 | 23318 |
| frontend-proxy | the frozen tier | 1 | 16 MB | 16 MB | 1 | 44521 |
| grafana | the frozen tier | 1 | 174 MB | 174 MB | 1 | 482478 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2977 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4210 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3018 |
| image-provider | the frozen tier | 1 | 3 MB | 3 MB | 1 | 6959 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2501 |
| jaeger | the frozen tier | 1 | 9 MB | 9 MB | 1 | 26309 |
| kafka | the frozen tier | 1 | 128 MB | 40 MB | 1 | 109746 |
| kube-proxy | the frozen tier | 1 | 22 MB | 10 MB | 1 | 29007 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3445 |
| metrics-server | the frozen tier | 1 | 4 MB | 4 MB | 1 | 10784 |
| opensearch | the frozen tier | 1 | 30 MB | 28 MB | 1 | 78270 |
| opentelemetry-collector | the frozen tier | 1 | 486 MB | 164 MB | 1 | 455772 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1171 |
| postgresql | the frozen tier | 1 | 4 MB | 4 MB | 1 | 10651 |
| prometheus-server | the frozen tier | 1 | 3 MB | 3 MB | 1 | 8542 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 189 |
| recommendation | the frozen tier | 1 | 13 MB | 1 MB | 1 | 3226 |
| valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 1 | 4089 |
| wait-for-kafka | the frozen tier | 1 | 10 MB | 1 MB | 1 | 1644 |
| wait-for-valkey-cart | the frozen tier | 1 | 1 MB | 0 MB | 1 | 1313 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 4150 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
