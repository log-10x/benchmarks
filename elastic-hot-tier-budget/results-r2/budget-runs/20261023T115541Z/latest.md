# Hot-tier run: 2026-10-23T11:55:42.000Z

Hot tier: 16 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 57 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 12 MB in 3 indices; its tier_down lines not yet moved: 3 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 4 moved indices).
- Each counted byte takes 0.82 bytes of store kept, 0.53 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.9 GB a day; 769 MB a day fits the size, so each statement keeps up to 87 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 119 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 240349 | 2281 |
| ad | the frozen tier | 1 | 39 MB | 39 MB | 240349 | 109353 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 51 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 137 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 248 |
| cart | the frozen tier | 1 | 137 MB | 135 MB | 240349 | 376235 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 240349 | 1566 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 59 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 225 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 289 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 97 |
| fluentd-10x | the frozen tier | 1 | 8 MB | 8 MB | 240349 | 23486 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 258 |
| frontend | the frozen tier | 1 | 25 MB | 25 MB | 240349 | 68298 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 240349 | 6513 |
| grafana | the frozen tier | 1 | 31 MB | 31 MB | 240349 | 86786 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 428 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 606 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 522 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 381 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 240349 | 4442 |
| kafka | the frozen tier | 1 | 168 MB | 168 MB | 240349 | 467304 |
| kube-proxy | the frozen tier | 1 | 4 MB | 4 MB | 240349 | 10064 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 462 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 240349 | 1578 |
| opensearch | the frozen tier | 1 | 6 MB | 6 MB | 240349 | 16544 |
| opentelemetry-collector | the frozen tier | 1 | 1.4 GB | 307 MB | 240349 | 852565 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 277 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 853 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 240349 | 3910 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 240349 | 26 |
| recommendation | the frozen tier | 1 | 33 MB | 33 MB | 240349 | 92599 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 240349 | 8576 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 240349 | 1566 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
