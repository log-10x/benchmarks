# Hot-tier run: 2026-10-22T22:01:14.000Z

Hot tier: 25 MB of 45 MB (0.0448 GB set in the policy) on 1 hot node; at these limits it settles at about 45 MB within 6 hours, with 510 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 16 MB in 2 indices; its tier_down lines not yet moved: 8 MB in 3.
- A kept line stays on hot 6 hours (ILM policy tenx-keep (rollover max_age 1h + frozen min_age 5h)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 0.87 bytes of store kept, 0.58 as tier_down (measured on the indices on hot).
- The Receiver's statements send 602 MB a day; 91 MB a day fits the size, so each statement keeps up to 3 MB a day and the noisiest give way first.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 511 |
| ad | the frozen tier | 1 | 20 MB | 7 MB | 7824 | 18835 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 12 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 33 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 60 |
| cart | the frozen tier | 1 | 49 MB | 6 MB | 7824 | 15719 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 232 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 14 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 54 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 70 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 23 |
| fluentd-10x | the frozen tier | 1 | 4 MB | 4 MB | 7824 | 10116 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 62 |
| frontend | the frozen tier | 1 | 8 MB | 3 MB | 7824 | 7871 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 7824 | 1586 |
| grafana | the frozen tier | 1 | 8 MB | 8 MB | 7824 | 22352 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 104 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 147 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 127 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 93 |
| jaeger | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 1081 |
| kafka | the frozen tier | 1 | 89 MB | 39 MB | 7824 | 108560 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 7824 | 2481 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 112 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 384 |
| opensearch | the frozen tier | 1 | 2 MB | 2 MB | 7824 | 4167 |
| opentelemetry-collector | the frozen tier | 1 | 404 MB | 17 MB | 7824 | 47492 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 67 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 207 |
| prometheus-server | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 987 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 7824 | 6 |
| recommendation | the frozen tier | 1 | 14 MB | 3 MB | 7824 | 7849 |
| valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 7824 | 2453 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 7824 | 232 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
