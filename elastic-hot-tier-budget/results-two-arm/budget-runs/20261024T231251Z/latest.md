# Hot-tier run: 2026-10-24T23:12:52.000Z

Hot tier: 58 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 889 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 53 MB in 11 indices; its tier_down lines not yet moved: 5 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 9 moved indices).
- Each counted byte takes 0.84 bytes of store kept, 0.44 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.7 GB a day; 822 MB a day fits the size, so each statement keeps up to 67 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 137 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 702 |
| ad | the frozen tier | 1 | 56 MB | 56 MB | 187023 | 155547 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 39 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 107 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 193 |
| cart | the frozen tier | 1 | 126 MB | 115 MB | 187023 | 318601 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 187023 | 2106 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 45 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 171 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 224 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 76 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 187023 | 29345 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 194 |
| frontend | the frozen tier | 1 | 31 MB | 31 MB | 187023 | 85965 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 187023 | 9478 |
| grafana | the frozen tier | 1 | 59 MB | 59 MB | 187023 | 164419 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 331 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 468 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 401 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 285 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 187023 | 4539 |
| kafka | the frozen tier | 1 | 243 MB | 243 MB | 187023 | 674558 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 187023 | 17807 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 350 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 1218 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 187023 | 25965 |
| opentelemetry-collector | the frozen tier | 1 | 1.1 GB | 243 MB | 187023 | 674954 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 138 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 439 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 187023 | 3446 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 187023 | 14 |
| recommendation | the frozen tier | 1 | 36 MB | 36 MB | 187023 | 101344 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 187023 | 10251 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 187023 | 702 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
