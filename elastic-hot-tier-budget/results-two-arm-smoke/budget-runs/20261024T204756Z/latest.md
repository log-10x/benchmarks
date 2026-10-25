# Hot-tier run: 2026-10-24T20:47:56.000Z

Hot tier: 3 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 153 MB within 2 hours, with 246 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.95 bytes of store kept, 1.95 as tier_down (measured on the indices on hot).
- The Receiver's statements send 941 MB a day; 212 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 695 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 695 MB a day on hot, more than the 212 MB a day that fits, so hot settles above 74 MB at about 153 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 10 MB | 8 MB | 1 | 23507 |
| ad | the frozen tier | 1 | 13 MB | 3 MB | 1 | 7519 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 642 |
| aws-node | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1742 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3149 |
| cart | the frozen tier | 1 | 24 MB | 2 MB | 1 | 6819 |
| coredns | the frozen tier | 1 | 7 MB | 3 MB | 1 | 9041 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 743 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2802 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3651 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1237 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3185 |
| frontend | the frozen tier | 1 | 6 MB | 6 MB | 1 | 15365 |
| frontend-proxy | the frozen tier | 1 | 29 MB | 29 MB | 1 | 80919 |
| grafana | the frozen tier | 1 | 315 MB | 311 MB | 1 | 864513 |
| grafana-sc-alerts | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5412 |
| grafana-sc-dashboard | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7653 |
| grafana-sc-datasources | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6560 |
| init-config | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4679 |
| jaeger | the frozen tier | 1 | 17 MB | 17 MB | 1 | 48078 |
| kafka | the frozen tier | 1 | 157 MB | 57 MB | 1 | 159695 |
| kube-proxy | the frozen tier | 1 | 41 MB | 18 MB | 1 | 48999 |
| load-generator | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5739 |
| metrics-server | the frozen tier | 1 | 7 MB | 7 MB | 1 | 19903 |
| opensearch | the frozen tier | 1 | 53 MB | 48 MB | 1 | 131955 |
| opentelemetry-collector | the frozen tier | 1 | 245 MB | 169 MB | 1 | 468200 |
| `*` (any other service) | the frozen tier | 1 | | 3 MB | 1 | 7169 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
