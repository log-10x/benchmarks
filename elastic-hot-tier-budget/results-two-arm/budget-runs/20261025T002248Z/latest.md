# Hot-tier run: 2026-10-25T00:22:49.000Z

Hot tier: 79 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 4.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 55 MB in 11 indices; its tier_down lines not yet moved: 23 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 15 moved indices).
- Each counted byte takes 0.90 bytes of store kept, 0.54 as tier_down (measured on the indices on hot).
- The Receiver's statements send 4.6 GB a day; 384 MB a day fits the size, so each statement keeps up to 14 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 66 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 80% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 114 |
| ad | the frozen tier | 1 | 159 MB | 36 MB | 37657 | 99097 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 25 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 70 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 127 |
| cart | the frozen tier | 1 | 432 MB | 27 MB | 37657 | 75465 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 488 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 30 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 113 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 147 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 50 |
| fluentd-10x | the frozen tier | 1 | 25 MB | 16 MB | 37657 | 44484 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 128 |
| frontend | the frozen tier | 1 | 93 MB | 14 MB | 37657 | 37756 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 37657 | 1699 |
| grafana | the frozen tier | 1 | 15 MB | 15 MB | 37657 | 42506 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 218 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 308 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 264 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 187 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 37657 | 1790 |
| kafka | the frozen tier | 1 | 721 MB | 179 MB | 37657 | 497331 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 37657 | 2713 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 230 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 803 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 37657 | 9620 |
| opentelemetry-collector | the frozen tier | 1 | 3.1 GB | 65 MB | 37657 | 181520 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 136 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 435 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 37657 | 6564 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 37657 | 13 |
| recommendation | the frozen tier | 1 | 115 MB | 14 MB | 37657 | 37710 |
| valkey-cart | the frozen tier | 1 | 8 MB | 8 MB | 37657 | 23233 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 37657 | 435 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
