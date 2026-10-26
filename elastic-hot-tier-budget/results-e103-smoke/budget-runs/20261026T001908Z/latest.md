# Hot-tier run: 2026-10-26T00:19:09.000Z

Hot tier: 5 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 85 MB within 2 hours, with 992 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 3 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.27 bytes of store kept, 0.61 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.3 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 327 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 327 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 41 MB at about 85 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 41 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 3 MB | 3 MB | 1 | 8904 |
| ad | the frozen tier | 1 | 36 MB | 2 MB | 1 | 6144 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 170 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 809 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1030 |
| cart | the frozen tier | 1 | 79 MB | 2 MB | 1 | 4289 |
| coredns | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5266 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 243 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 709 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2288 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 404 |
| fluentd-10x | the frozen tier | 1 | 14 MB | 6 MB | 1 | 15612 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 604 |
| frontend | the frozen tier | 1 | 18 MB | 12 MB | 1 | 34653 |
| frontend-proxy | the frozen tier | 1 | 10 MB | 10 MB | 1 | 26643 |
| grafana | the frozen tier | 1 | 107 MB | 105 MB | 1 | 292016 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1770 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2504 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1795 |
| image-provider | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4501 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1487 |
| jaeger | the frozen tier | 1 | 7 MB | 7 MB | 1 | 18183 |
| kafka | the frozen tier | 1 | 192 MB | 30 MB | 1 | 82001 |
| kube-proxy | the frozen tier | 1 | 13 MB | 7 MB | 1 | 19177 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2049 |
| metrics-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6413 |
| opensearch | the frozen tier | 1 | 18 MB | 18 MB | 1 | 50179 |
| opentelemetry-collector | the frozen tier | 1 | 772 MB | 105 MB | 1 | 291405 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 696 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6486 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6366 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 112 |
| recommendation | the frozen tier | 1 | 24 MB | 1 MB | 1 | 2932 |
| valkey-cart | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6616 |
| wait-for-kafka | the frozen tier | 1 | 6 MB | 1 MB | 1 | 1399 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1226 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 3611 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
