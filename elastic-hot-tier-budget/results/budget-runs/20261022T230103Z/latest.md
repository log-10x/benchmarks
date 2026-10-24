# Hot-tier run: 2026-10-22T23:01:03.000Z

Hot tier: 24 MB of 45 MB (0.0448 GB set in the policy) on 1 hot node; at these limits it settles at about 45 MB within 6 hours, with 384 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 17 MB in 3 indices; its tier_down lines not yet moved: 7 MB in 3.
- A kept line stays on hot 6 hours (ILM policy tenx-keep (rollover max_age 1h + frozen min_age 5h)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 0.78 bytes of store kept, 0.54 as tier_down (measured on the indices on hot).
- The Receiver's statements send 524 MB a day; 139 MB a day fits the size, so each statement keeps up to 5 MB a day and the noisiest give way first.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 342 |
| ad | the frozen tier | 1 | 15 MB | 12 MB | 15092 | 33273 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 8 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 22 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 40 |
| cart | the frozen tier | 1 | 44 MB | 11 MB | 15092 | 30233 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 155 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 9 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 36 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 47 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 15 |
| fluentd-10x | the frozen tier | 1 | 2 MB | 2 MB | 15092 | 6737 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 42 |
| frontend | the frozen tier | 1 | 8 MB | 5 MB | 15092 | 15124 |
| frontend-proxy | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 1062 |
| grafana | the frozen tier | 1 | 6 MB | 6 MB | 15092 | 16971 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 69 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 98 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 85 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 62 |
| jaeger | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 724 |
| kafka | the frozen tier | 1 | 70 MB | 67 MB | 15092 | 185813 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 15092 | 1743 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 75 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 257 |
| opensearch | the frozen tier | 1 | 1 MB | 1 MB | 15092 | 3185 |
| opentelemetry-collector | the frozen tier | 1 | 361 MB | 26 MB | 15092 | 72445 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 45 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 139 |
| prometheus-server | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 872 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 15092 | 4 |
| recommendation | the frozen tier | 1 | 13 MB | 5 MB | 15092 | 15109 |
| valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 15092 | 2513 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 15092 | 155 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
