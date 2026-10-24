# Hot-tier run: 2026-10-23T03:01:16.000Z

Hot tier: 34 MB of 45 MB (0.0448 GB set in the policy) on 1 hot node; at these limits it settles at about 45 MB within 6 hours, with 286 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 29 MB in 6 indices; its tier_down lines not yet moved: 5 MB in 3.
- A kept line stays on hot 6 hours (ILM policy tenx-keep (rollover max_age 1h + frozen min_age 5h)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.02 bytes of store kept, 0.48 as tier_down (measured on the indices on hot).
- The Receiver's statements send 413 MB a day; 127 MB a day fits the size, so each statement keeps up to 5 MB a day and the noisiest give way first.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 19 |
| ad | the frozen tier | 1 | 11 MB | 11 MB | 14352 | 29753 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 4 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 11 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 20 |
| cart | the frozen tier | 1 | 31 MB | 10 MB | 14352 | 28729 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 80 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 5 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 18 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 24 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 8 |
| fluentd-10x | the frozen tier | 1 | 3 MB | 3 MB | 14352 | 7363 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 21 |
| frontend | the frozen tier | 1 | 9 MB | 5 MB | 14352 | 14368 |
| frontend-proxy | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 547 |
| grafana | the frozen tier | 1 | 4 MB | 4 MB | 14352 | 11699 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 36 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 50 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 43 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 32 |
| jaeger | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 373 |
| kafka | the frozen tier | 1 | 64 MB | 63 MB | 14352 | 175992 |
| kube-proxy | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 681 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 38 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 132 |
| opensearch | the frozen tier | 1 | 1 MB | 1 MB | 14352 | 2237 |
| opentelemetry-collector | the frozen tier | 1 | 280 MB | 23 MB | 14352 | 63000 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 23 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 71 |
| prometheus-server | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 855 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 14352 | 2 |
| recommendation | the frozen tier | 1 | 8 MB | 5 MB | 14352 | 14361 |
| valkey-cart | the frozen tier | 1 | 1 MB | 1 MB | 14352 | 2585 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 14352 | 71 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
