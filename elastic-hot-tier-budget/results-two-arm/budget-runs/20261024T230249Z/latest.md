# Hot-tier run: 2026-10-24T23:02:49.000Z

Hot tier: 53 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 928 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 48 MB in 10 indices; its tier_down lines not yet moved: 5 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 8 moved indices).
- Each counted byte takes 0.84 bytes of store kept, 0.40 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 832 MB a day fits the size, so each statement keeps up to 82 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 81 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 704 |
| ad | the frozen tier | 1 | 55 MB | 55 MB | 228385 | 152397 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 28 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 77 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 140 |
| cart | the frozen tier | 1 | 132 MB | 131 MB | 228385 | 363826 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 710 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 33 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 124 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 162 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 55 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 228385 | 29543 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 141 |
| frontend | the frozen tier | 1 | 31 MB | 31 MB | 228385 | 85547 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 228385 | 2827 |
| grafana | the frozen tier | 1 | 16 MB | 16 MB | 228385 | 44350 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 241 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 340 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 292 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 207 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 228385 | 2259 |
| kafka | the frozen tier | 1 | 248 MB | 248 MB | 228385 | 688623 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 228385 | 4496 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 255 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 886 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 228385 | 9507 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 289 MB | 228385 | 802334 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 151 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 480 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 228385 | 3404 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 228385 | 15 |
| recommendation | the frozen tier | 1 | 39 MB | 39 MB | 228385 | 107633 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 228385 | 10576 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 228385 | 704 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
