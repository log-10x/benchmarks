# Hot-tier run: 2026-10-26T00:14:52.000Z

Hot tier: 2 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 67 MB within 2 hours, with 191 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 2 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.03 bytes of store kept, 1.03 as tier_down (measured on the indices on hot).
- The Receiver's statements send 777 MB a day; 281 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 586 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 586 MB a day on hot, more than the 281 MB a day that fits, so hot settles above 41 MB at about 67 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 8 MB | 6 MB | 1 | 18023 |
| ad | the frozen tier | 1 | 10 MB | 3 MB | 1 | 7339 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 405 |
| aws-node | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1921 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2446 |
| cart | the frozen tier | 1 | 18 MB | 2 MB | 1 | 5928 |
| coredns | the frozen tier | 1 | 6 MB | 3 MB | 1 | 8044 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 577 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1682 |
| flagd | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5430 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 960 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1435 |
| frontend | the frozen tier | 1 | 5 MB | 5 MB | 1 | 13578 |
| frontend-proxy | the frozen tier | 1 | 23 MB | 23 MB | 1 | 62843 |
| grafana | the frozen tier | 1 | 245 MB | 244 MB | 1 | 676544 |
| grafana-sc-alerts | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4203 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5943 |
| grafana-sc-datasources | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4261 |
| image-provider | the frozen tier | 1 | 4 MB | 3 MB | 1 | 9150 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3531 |
| jaeger | the frozen tier | 1 | 13 MB | 13 MB | 1 | 37137 |
| kafka | the frozen tier | 1 | 122 MB | 49 MB | 1 | 135731 |
| kube-proxy | the frozen tier | 1 | 32 MB | 14 MB | 1 | 38945 |
| load-generator | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4863 |
| metrics-server | the frozen tier | 1 | 5 MB | 5 MB | 1 | 15222 |
| opensearch | the frozen tier | 1 | 42 MB | 38 MB | 1 | 105815 |
| opentelemetry-collector | the frozen tier | 1 | 217 MB | 163 MB | 1 | 453312 |
| wait-for-kafka | the frozen tier | 1 | 14 MB | 1 MB | 1 | 1893 |
| wait-for-valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1401 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 1 | 5928 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
