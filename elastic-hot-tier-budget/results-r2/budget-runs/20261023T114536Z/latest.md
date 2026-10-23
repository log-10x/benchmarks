# Hot-tier run: 2026-10-23T11:45:36.000Z

Hot tier: 15 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 57 MB within 2 hours, with 1.7 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 8 MB in 2 indices; its tier_down lines not yet moved: 7 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 0.73 bytes of store kept, 0.73 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.5 GB a day; 789 MB a day fits the size, so each statement keeps up to 28 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 154 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 78529 | 3464 |
| ad | the frozen tier | 1 | 80 MB | 63 MB | 78529 | 174040 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 77 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 208 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 377 |
| cart | the frozen tier | 1 | 201 MB | 57 MB | 78529 | 157505 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 78529 | 2379 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 90 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 342 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 439 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 147 |
| fluentd-10x | the frozen tier | 1 | 18 MB | 18 MB | 78529 | 48815 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 392 |
| frontend | the frozen tier | 1 | 44 MB | 28 MB | 78529 | 78827 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 78529 | 9893 |
| grafana | the frozen tier | 1 | 48 MB | 48 MB | 78529 | 132496 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 650 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 920 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 793 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 580 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 78529 | 6747 |
| kafka | the frozen tier | 1 | 385 MB | 363 MB | 78529 | 1009578 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 78529 | 14722 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 702 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 78529 | 2397 |
| opensearch | the frozen tier | 1 | 8 MB | 8 MB | 78529 | 22750 |
| opentelemetry-collector | the frozen tier | 1 | 1.6 GB | 154 MB | 78529 | 426535 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 421 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 1297 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 78529 | 4701 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 78529 | 40 |
| recommendation | the frozen tier | 1 | 55 MB | 28 MB | 78529 | 78690 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 78529 | 11887 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 78529 | 2379 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
