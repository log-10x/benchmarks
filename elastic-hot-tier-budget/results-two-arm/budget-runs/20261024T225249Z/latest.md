# Hot-tier run: 2026-10-24T22:52:49.000Z

Hot tier: 46 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 890 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 43 MB in 9 indices; its tier_down lines not yet moved: 2 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 8 moved indices).
- Each counted byte takes 0.83 bytes of store kept, 0.48 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.7 GB a day; 830 MB a day fits the size, so each statement keeps up to 75 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 84 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 775 |
| ad | the frozen tier | 1 | 53 MB | 53 MB | 209510 | 147330 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 31 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 85 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 154 |
| cart | the frozen tier | 1 | 132 MB | 128 MB | 209510 | 354200 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 782 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 36 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 137 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 179 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 60 |
| fluentd-10x | the frozen tier | 1 | 10 MB | 10 MB | 209510 | 27036 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 155 |
| frontend | the frozen tier | 1 | 30 MB | 30 MB | 209510 | 83940 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 209510 | 3113 |
| grafana | the frozen tier | 1 | 17 MB | 17 MB | 209510 | 46286 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 265 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 375 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 321 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 228 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 209510 | 2487 |
| kafka | the frozen tier | 1 | 267 MB | 267 MB | 209510 | 742374 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 209510 | 4835 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 280 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 975 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 209510 | 9910 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 269 MB | 209510 | 747145 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 166 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 528 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 209510 | 3513 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 209510 | 16 |
| recommendation | the frozen tier | 1 | 43 MB | 43 MB | 209510 | 118704 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 209510 | 9891 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 209510 | 775 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
