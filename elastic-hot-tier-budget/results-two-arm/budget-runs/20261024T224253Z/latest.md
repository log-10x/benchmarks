# Hot-tier run: 2026-10-24T22:42:53.000Z

Hot tier: 42 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 925 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 38 MB in 8 indices; its tier_down lines not yet moved: 3 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 7 moved indices).
- Each counted byte takes 0.83 bytes of store kept, 0.44 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 834 MB a day fits the size, so each statement keeps up to 92 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 89 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 861 |
| ad | the frozen tier | 1 | 55 MB | 55 MB | 256852 | 152340 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 35 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 95 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 172 |
| cart | the frozen tier | 1 | 126 MB | 126 MB | 256852 | 349776 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 869 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 40 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 152 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 199 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 67 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 256852 | 29931 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 173 |
| frontend | the frozen tier | 1 | 30 MB | 30 MB | 256852 | 82317 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 256852 | 3459 |
| grafana | the frozen tier | 1 | 18 MB | 18 MB | 256852 | 48650 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 294 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 417 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 357 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 254 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 256852 | 2764 |
| kafka | the frozen tier | 1 | 225 MB | 225 MB | 256852 | 625951 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 256852 | 5245 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 312 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 1084 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 256852 | 10605 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 321 MB | 256852 | 892276 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 184 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 587 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 256852 | 4044 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 256852 | 18 |
| recommendation | the frozen tier | 1 | 33 MB | 33 MB | 256852 | 91771 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 256852 | 10675 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 256852 | 861 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
