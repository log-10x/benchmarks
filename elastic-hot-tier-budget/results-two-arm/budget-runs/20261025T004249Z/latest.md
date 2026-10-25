# Hot-tier run: 2026-10-25T00:42:49.000Z

Hot tier: 71 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 59 MB within 2 hours, with 4.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 49 MB in 11 indices; its tier_down lines not yet moved: 21 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 17 moved indices).
- Each counted byte takes 0.92 bytes of store kept, 0.58 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.8 GB a day; 369 MB a day fits the size, so each statement keeps up to 12 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 77 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 88% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 176 |
| ad | the frozen tier | 1 | 182 MB | 33 MB | 34244 | 93014 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 40 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 109 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 197 |
| cart | the frozen tier | 1 | 448 MB | 25 MB | 34244 | 68722 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 753 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 46 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 174 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 228 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 77 |
| fluentd-10x | the frozen tier | 1 | 31 MB | 18 MB | 34244 | 48868 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 197 |
| frontend | the frozen tier | 1 | 102 MB | 12 MB | 34244 | 34398 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 34244 | 2670 |
| grafana | the frozen tier | 1 | 20 MB | 19 MB | 34244 | 52762 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 336 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 476 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 408 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 289 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 34244 | 2756 |
| kafka | the frozen tier | 1 | 825 MB | 164 MB | 34244 | 455477 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 34244 | 3540 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 356 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 1238 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 34244 | 10872 |
| opentelemetry-collector | the frozen tier | 1 | 3.1 GB | 66 MB | 34244 | 183438 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 210 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 671 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 34244 | 6684 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 34244 | 21 |
| recommendation | the frozen tier | 1 | 128 MB | 12 MB | 34244 | 34327 |
| valkey-cart | the frozen tier | 1 | 8 MB | 8 MB | 34244 | 21868 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 34244 | 671 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
