# Hot-tier run: 2026-10-23T01:01:17.000Z

Hot tier: 35 MB of 45 MB (0.0448 GB set in the policy) on 1 hot node; at these limits it settles at about 45 MB within 6 hours, with 319 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 29 MB in 5 indices; its tier_down lines not yet moved: 5 MB in 3.
- A kept line stays on hot 6 hours (ILM policy tenx-keep (rollover max_age 1h + frozen min_age 5h)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 0.86 bytes of store kept, 0.49 as tier_down (measured on the indices on hot).
- The Receiver's statements send 463 MB a day; 144 MB a day fits the size, so each statement keeps up to 6 MB a day and the noisiest give way first.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 228 |
| ad | the frozen tier | 1 | 12 MB | 12 MB | 16679 | 32449 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 10 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 26 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 48 |
| cart | the frozen tier | 1 | 31 MB | 12 MB | 16679 | 33417 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 186 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 11 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 44 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 56 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 19 |
| fluentd-10x | the frozen tier | 1 | 3 MB | 3 MB | 16679 | 7806 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 50 |
| frontend | the frozen tier | 1 | 8 MB | 6 MB | 16679 | 16718 |
| frontend-proxy | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 1277 |
| grafana | the frozen tier | 1 | 7 MB | 7 MB | 16679 | 19192 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 84 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 118 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 102 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 74 |
| jaeger | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 871 |
| kafka | the frozen tier | 1 | 65 MB | 65 MB | 16679 | 180601 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 16679 | 1575 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 90 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 309 |
| opensearch | the frozen tier | 1 | 1 MB | 1 MB | 16679 | 3449 |
| opentelemetry-collector | the frozen tier | 1 | 325 MB | 29 MB | 16679 | 80498 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 54 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 167 |
| prometheus-server | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 910 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 16679 | 5 |
| recommendation | the frozen tier | 1 | 7 MB | 6 MB | 16679 | 16700 |
| valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 16679 | 2483 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 16679 | 186 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
