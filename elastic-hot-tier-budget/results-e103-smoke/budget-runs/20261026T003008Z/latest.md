# Hot-tier run: 2026-10-26T00:30:08.000Z

Hot tier: 12 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 41 MB within 2 hours, with 2.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 8 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 1.39 bytes of store kept, 0.58 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.7 GB a day; 207 MB a day fits the size, so each statement keeps up to 2 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 165 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 5154 | 3585 |
| ad | the frozen tier | 1 | 91 MB | 6 MB | 5154 | 15821 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 68 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 325 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 414 |
| cart | the frozen tier | 1 | 225 MB | 4 MB | 5154 | 10798 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 5154 | 2613 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 97 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 285 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 921 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 162 |
| fluentd-10x | the frozen tier | 1 | 18 MB | 4 MB | 5154 | 10944 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 243 |
| frontend | the frozen tier | 1 | 53 MB | 12 MB | 5154 | 33767 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 5154 | 10726 |
| grafana | the frozen tier | 1 | 53 MB | 47 MB | 5154 | 130285 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 712 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 1008 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 722 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 5154 | 1812 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 598 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 5154 | 7320 |
| kafka | the frozen tier | 1 | 423 MB | 41 MB | 5154 | 113697 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 5154 | 16151 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 825 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 5154 | 2582 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 5154 | 25572 |
| opentelemetry-collector | the frozen tier | 1 | 1.7 GB | 53 MB | 5154 | 146596 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 280 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 5154 | 2529 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 5154 | 5994 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 45 |
| recommendation | the frozen tier | 1 | 59 MB | 2 MB | 5154 | 5328 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 5154 | 15775 |
| wait-for-kafka | the frozen tier | 1 | 2 MB | 2 MB | 5154 | 5299 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 5154 | 529 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 5154 | 2555 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
