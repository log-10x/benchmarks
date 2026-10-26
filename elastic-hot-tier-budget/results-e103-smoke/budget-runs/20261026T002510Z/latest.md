# Hot-tier run: 2026-10-26T00:25:10.000Z

Hot tier: 15 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 133 MB within 2 hours, with 1.3 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 12 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.25 bytes of store kept, 1.01 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 206 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 206 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 133 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4912 |
| ad | the frozen tier | 1 | 47 MB | 2 MB | 1 | 5746 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 94 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 446 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 568 |
| cart | the frozen tier | 1 | 111 MB | 1 MB | 1 | 3750 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3485 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 134 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 391 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1262 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 223 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 4 MB | 1 | 12161 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 333 |
| frontend | the frozen tier | 1 | 26 MB | 12 MB | 1 | 33987 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 1 | 14696 |
| grafana | the frozen tier | 1 | 63 MB | 60 MB | 1 | 166340 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 976 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1381 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 990 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2483 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 820 |
| jaeger | the frozen tier | 1 | 4 MB | 4 MB | 1 | 10030 |
| kafka | the frozen tier | 1 | 233 MB | 23 MB | 1 | 62586 |
| kube-proxy | the frozen tier | 1 | 8 MB | 5 MB | 1 | 12710 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1130 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3537 |
| opensearch | the frozen tier | 1 | 11 MB | 11 MB | 1 | 30067 |
| opentelemetry-collector | the frozen tier | 1 | 957 MB | 64 MB | 1 | 176464 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 384 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3578 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4502 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 62 |
| recommendation | the frozen tier | 1 | 33 MB | 1 MB | 1 | 2738 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7026 |
| wait-for-kafka | the frozen tier | 1 | 3 MB | 0 MB | 1 | 1237 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 725 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2610 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
