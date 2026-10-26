# Hot-tier run: 2026-10-26T00:32:11.000Z

Hot tier: 15 MB of 41 MB (0.0406 GB set in the policy) on 1 hot node; at these limits it settles at about 41 MB within 2 hours, with 2.8 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 4 MB in 2 indices; its tier_down lines not yet moved: 12 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 1 moved indices).
- Each counted byte takes 1.41 bytes of store kept, 0.57 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3 GB a day; 186 MB a day fits the size, so each statement keeps up to 1 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 155 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 4051 | 3225 |
| ad | the frozen tier | 1 | 106 MB | 4 MB | 4051 | 12477 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 61 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 293 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 373 |
| cart | the frozen tier | 1 | 251 MB | 3 MB | 4051 | 8544 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 4051 | 2351 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 88 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 256 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 828 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 146 |
| fluentd-10x | the frozen tier | 1 | 20 MB | 3 MB | 4051 | 9261 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 219 |
| frontend | the frozen tier | 1 | 58 MB | 12 MB | 4051 | 33706 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 4051 | 9650 |
| grafana | the frozen tier | 1 | 50 MB | 43 MB | 4051 | 119257 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 641 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 907 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 650 |
| image-provider | the frozen tier | 1 | 1 MB | 1 MB | 4051 | 1630 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 538 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 4051 | 6586 |
| kafka | the frozen tier | 1 | 476 MB | 34 MB | 4051 | 94276 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 4051 | 14903 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 742 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 4051 | 2323 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 4051 | 25247 |
| opentelemetry-collector | the frozen tier | 1 | 2 GB | 48 MB | 4051 | 132004 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 252 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 4051 | 2275 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 4051 | 5894 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 40 |
| recommendation | the frozen tier | 1 | 67 MB | 2 MB | 4051 | 4208 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 4051 | 17153 |
| wait-for-kafka | the frozen tier | 1 | 2 MB | 2 MB | 4051 | 4182 |
| wait-for-valkey-cart | the frozen tier | 1 | 0 MB | 0 MB | 4051 | 476 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 4051 | 2299 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
