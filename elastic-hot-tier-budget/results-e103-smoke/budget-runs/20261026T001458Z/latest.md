# Hot-tier run: 2026-10-26T00:14:59.000Z

Hot tier: 2 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 65 MB within 2 hours, with 204 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 2 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.01 bytes of store kept, 1.01 as tier_down (measured on the indices on hot).
- The Receiver's statements send 775 MB a day; 280 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 571 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 571 MB a day on hot, more than the 280 MB a day that fits, so hot settles above 41 MB at about 65 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 7 MB | 6 MB | 1 | 17541 |
| ad | the frozen tier | 1 | 10 MB | 3 MB | 1 | 7243 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 390 |
| aws-node | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1852 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2357 |
| cart | the frozen tier | 1 | 18 MB | 2 MB | 1 | 5824 |
| coredns | the frozen tier | 1 | 5 MB | 3 MB | 1 | 7919 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 556 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1622 |
| flagd | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5234 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 926 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1383 |
| frontend | the frozen tier | 1 | 5 MB | 5 MB | 1 | 13088 |
| frontend-proxy | the frozen tier | 1 | 22 MB | 22 MB | 1 | 60576 |
| grafana | the frozen tier | 1 | 236 MB | 235 MB | 1 | 652799 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 4051 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5729 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 1 | 4107 |
| image-provider | the frozen tier | 1 | 4 MB | 3 MB | 1 | 8890 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3403 |
| jaeger | the frozen tier | 1 | 13 MB | 13 MB | 1 | 35797 |
| kafka | the frozen tier | 1 | 118 MB | 48 MB | 1 | 132522 |
| kube-proxy | the frozen tier | 1 | 31 MB | 14 MB | 1 | 37754 |
| load-generator | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4688 |
| metrics-server | the frozen tier | 1 | 5 MB | 5 MB | 1 | 14673 |
| opensearch | the frozen tier | 1 | 40 MB | 37 MB | 1 | 102386 |
| opentelemetry-collector | the frozen tier | 1 | 235 MB | 162 MB | 1 | 450790 |
| wait-for-kafka | the frozen tier | 1 | 14 MB | 1 MB | 1 | 1862 |
| wait-for-valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1390 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 1 | 5729 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
