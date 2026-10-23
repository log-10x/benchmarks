# Hot-tier run: 2026-10-23T13:05:38.000Z

Hot tier: 47 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 57 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 2 MB on hot. The Receiver's kept lines: 43 MB in 9 indices; its tier_down lines not yet moved: 3 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 25 moved indices).
- Each counted byte takes 0.87 bytes of store kept, 0.52 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 712 MB a day fits the size, so each statement keeps up to 46 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 88 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 746 |
| ad | the frozen tier | 1 | 55 MB | 55 MB | 127053 | 154058 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 30 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 81 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 147 |
| cart | the frozen tier | 1 | 130 MB | 92 MB | 127053 | 254282 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 748 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 35 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 134 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 172 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 57 |
| fluentd-10x | the frozen tier | 1 | 10 MB | 10 MB | 127053 | 27106 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 153 |
| frontend | the frozen tier | 1 | 30 MB | 30 MB | 127053 | 84270 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 127053 | 3871 |
| grafana | the frozen tier | 1 | 23 MB | 23 MB | 127053 | 62740 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 254 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 360 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 310 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 226 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 127053 | 2640 |
| kafka | the frozen tier | 1 | 270 MB | 270 MB | 127053 | 749078 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 127053 | 5105 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 274 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 937 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 127053 | 11810 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 178 MB | 127053 | 493224 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 164 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 507 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 127053 | 3400 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 127053 | 15 |
| recommendation | the frozen tier | 1 | 40 MB | 40 MB | 127053 | 110258 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 127053 | 10231 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 127053 | 746 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
