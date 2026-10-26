# Hot-tier run: 2026-10-26T00:24:12.000Z

Hot tier: 15 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 143 MB within 2 hours, with 1.3 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 12 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.38 bytes of store kept, 1.09 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 218 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 218 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 143 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5293 |
| ad | the frozen tier | 1 | 46 MB | 2 MB | 1 | 5784 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 101 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 481 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 612 |
| cart | the frozen tier | 1 | 107 MB | 1 MB | 1 | 3801 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3655 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 144 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 421 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1360 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 240 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 5 MB | 1 | 12656 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 359 |
| frontend | the frozen tier | 1 | 24 MB | 12 MB | 1 | 34051 |
| frontend-proxy | the frozen tier | 1 | 6 MB | 6 MB | 1 | 15837 |
| grafana | the frozen tier | 1 | 68 MB | 64 MB | 1 | 178420 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1052 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1488 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1067 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2675 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 884 |
| jaeger | the frozen tier | 1 | 4 MB | 4 MB | 1 | 10809 |
| kafka | the frozen tier | 1 | 230 MB | 23 MB | 1 | 64436 |
| kube-proxy | the frozen tier | 1 | 8 MB | 5 MB | 1 | 13328 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1218 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3812 |
| opensearch | the frozen tier | 1 | 12 MB | 12 MB | 1 | 32073 |
| opentelemetry-collector | the frozen tier | 1 | 939 MB | 67 MB | 1 | 187441 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 414 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3855 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4548 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 67 |
| recommendation | the frozen tier | 1 | 33 MB | 1 MB | 1 | 2757 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7071 |
| wait-for-kafka | the frozen tier | 1 | 4 MB | 0 MB | 1 | 1253 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 782 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2716 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
