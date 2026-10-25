# Hot-tier run: 2026-10-24T22:02:52.000Z

Hot tier: 29 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 885 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 20 MB in 5 indices; its tier_down lines not yet moved: 8 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 3 moved indices).
- Each counted byte takes 0.82 bytes of store kept, 0.78 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.7 GB a day; 798 MB a day fits the size, so each statement keeps up to 76 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 94 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 211869 | 1422 |
| ad | the frozen tier | 1 | 53 MB | 53 MB | 211869 | 145950 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 31 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 85 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 155 |
| cart | the frozen tier | 1 | 109 MB | 109 MB | 211869 | 303229 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 977 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 36 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 138 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 179 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 60 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 211869 | 29268 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 157 |
| frontend | the frozen tier | 1 | 29 MB | 29 MB | 211869 | 80088 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 211869 | 4013 |
| grafana | the frozen tier | 1 | 23 MB | 23 MB | 211869 | 63693 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 266 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 377 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 323 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 230 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 211869 | 2751 |
| kafka | the frozen tier | 1 | 251 MB | 251 MB | 211869 | 697226 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 211869 | 6829 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 282 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 981 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 211869 | 12419 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 270 MB | 211869 | 748957 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 167 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 531 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 211869 | 3361 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 211869 | 17 |
| recommendation | the frozen tier | 1 | 37 MB | 37 MB | 211869 | 102111 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 211869 | 10327 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 211869 | 977 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
