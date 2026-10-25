# Hot-tier run: 2026-10-24T21:08:15.000Z

Hot tier: 20 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 74 MB within 2 hours, with 2.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 6 MB in 3 indices; its tier_down lines not yet moved: 13 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 1.66 bytes of store kept, 0.56 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.9 GB a day; 418 MB a day fits the size, so each statement keeps up to 12 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 144 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 32928 | 3073 |
| ad | the frozen tier | 1 | 97 MB | 30 MB | 32928 | 84348 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 68 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 185 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 335 |
| cart | the frozen tier | 1 | 243 MB | 24 MB | 32928 | 66253 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 32928 | 2112 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 79 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 298 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 388 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 131 |
| fluentd-10x | the frozen tier | 1 | 17 MB | 14 MB | 32928 | 37891 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 339 |
| frontend | the frozen tier | 1 | 56 MB | 12 MB | 32928 | 33427 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 32928 | 8672 |
| grafana | the frozen tier | 1 | 45 MB | 45 MB | 32928 | 123901 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 576 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 815 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 698 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 498 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 32928 | 5946 |
| kafka | the frozen tier | 1 | 438 MB | 168 MB | 32928 | 465667 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 32928 | 13750 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 611 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 32928 | 2119 |
| opensearch | the frozen tier | 1 | 8 MB | 8 MB | 32928 | 23209 |
| opentelemetry-collector | the frozen tier | 1 | 1.9 GB | 82 MB | 32928 | 228445 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 362 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 1149 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 32928 | 5933 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 32928 | 36 |
| recommendation | the frozen tier | 1 | 65 MB | 12 MB | 32928 | 33069 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 32928 | 15424 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 32928 | 2112 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
