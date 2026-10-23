# Hot-tier run: 2026-10-23T14:35:34.000Z

Hot tier: 63 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 53 MB within 2 hours, with 3.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 3 MB on hot. The Receiver's kept lines: 49 MB in 11 indices; its tier_down lines not yet moved: 11 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 52 moved indices).
- Each counted byte takes 0.96 bytes of store kept, 0.62 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3.9 GB a day; 451 MB a day fits the size, so each statement keeps up to 16 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 82 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 91% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 113 |
| ad | the frozen tier | 1 | 144 MB | 37 MB | 43213 | 102184 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 25 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 67 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 121 |
| cart | the frozen tier | 1 | 348 MB | 31 MB | 43213 | 87326 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 465 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 29 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 110 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 141 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 47 |
| fluentd-10x | the frozen tier | 1 | 21 MB | 17 MB | 43213 | 47091 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 126 |
| frontend | the frozen tier | 1 | 82 MB | 16 MB | 43213 | 43352 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 43213 | 3180 |
| grafana | the frozen tier | 1 | 25 MB | 25 MB | 43213 | 68140 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 209 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 295 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 255 |
| hb-inventory | the frozen tier | 1 | 37 MB | 16 MB | 43213 | 43213 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 186 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 43213 | 2169 |
| kafka | the frozen tier | 1 | 638 MB | 206 MB | 43213 | 571550 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 43213 | 3717 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 225 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 770 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 43213 | 12378 |
| opentelemetry-collector | the frozen tier | 1 | 2.5 GB | 74 MB | 43213 | 204755 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 135 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 417 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 43213 | 4829 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 43213 | 13 |
| recommendation | the frozen tier | 1 | 109 MB | 16 MB | 43213 | 43264 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 43213 | 12085 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 43213 | 441 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
