# Hot-tier run: 2026-10-24T21:01:14.000Z

Hot tier: 12 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 89 MB within 2 hours, with 1.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 9 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.23 bytes of store kept, 0.56 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.7 GB a day; 37 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 182 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 182 MB a day on hot, more than the 37 MB a day that fits, so hot settles above 74 MB at about 89 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4445 |
| ad | the frozen tier | 1 | 53 MB | 2 MB | 1 | 5608 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 98 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 268 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 485 |
| cart | the frozen tier | 1 | 128 MB | 1 MB | 1 | 3654 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3055 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 114 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 431 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 562 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 190 |
| fluentd-10x | the frozen tier | 1 | 14 MB | 4 MB | 1 | 11217 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 490 |
| frontend | the frozen tier | 1 | 30 MB | 12 MB | 1 | 33541 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 1 | 12543 |
| grafana | the frozen tier | 1 | 56 MB | 52 MB | 1 | 144592 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 833 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1178 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1010 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 720 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 1 | 8600 |
| kafka | the frozen tier | 1 | 260 MB | 21 MB | 1 | 58865 |
| kube-proxy | the frozen tier | 1 | 7 MB | 4 MB | 1 | 11652 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 884 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3066 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 1 | 26471 |
| opentelemetry-collector | the frozen tier | 1 | 1.1 GB | 56 MB | 1 | 155747 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 524 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1661 |
| prometheus-server | the frozen tier | 1 | 2 MB | 1 MB | 1 | 4089 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 53 |
| recommendation | the frozen tier | 1 | 38 MB | 1 MB | 1 | 2703 |
| valkey-cart | the frozen tier | 1 | 3 MB | 2 MB | 1 | 6942 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2703 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
