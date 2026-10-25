# Hot-tier run: 2026-10-25T01:12:50.000Z

Hot tier: 45 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 44 MB within 2 hours, with 0 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 44 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 20 moved indices).
- Each counted byte takes 0.95 bytes of store kept, 0.95 as tier_down (measured on the indices on hot).
- The Receiver's statements send 532 MB a day, under the 776 MB a day that fits the size; every statement keeps its lines, with room to grow 1.5 times.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 84 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 324 | 324 |
| ad | the frozen tier | 1 | 42 MB | 61 MB | 75378 | 168389 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 73 | 73 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 53 | 200 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 54 | 362 |
| cart | the frozen tier | 1 | 63 MB | 92 MB | 134278 | 255231 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 401 | 1383 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 85 | 85 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 194 | 320 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 64 | 419 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 50 | 142 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 17 MB | 36282 | 46212 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 302 | 363 |
| frontend | the frozen tier | 1 | 28 MB | 41 MB | 113241 | 113523 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 2 MB | 471 | 4740 |
| grafana | the frozen tier | 1 | 14 MB | 20 MB | 25399 | 55089 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 75 | 619 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 153 | 875 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 199 | 749 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 532 | 532 |
| jaeger | the frozen tier | 1 | 1 MB | 2 MB | 356 | 4884 |
| kafka | the frozen tier | 1 | 195 MB | 285 MB | 66720 | 790662 |
| kube-proxy | the frozen tier | 1 | 1 MB | 2 MB | 1250 | 6038 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 654 | 654 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 322 | 2276 |
| opensearch | the frozen tier | 1 | 4 MB | 6 MB | 4864 | 15889 |
| opentelemetry-collector | the frozen tier | 1 | 137 MB | 200 MB | 127340 | 555534 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 387 | 387 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 180 | 1234 |
| prometheus-server | the frozen tier | 1 | 2 MB | 3 MB | 3875 | 7488 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 39 | 39 |
| recommendation | the frozen tier | 1 | 25 MB | 36 MB | 100138 | 100289 |
| valkey-cart | the frozen tier | 1 | 5 MB | 7 MB | 4025 | 19343 |
| `*` (any other service) | the frozen tier | 1 | | 243 MB | 675239 | 675239 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
