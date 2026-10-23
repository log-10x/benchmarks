# Hot-tier run: 2026-10-23T12:45:38.000Z

Hot tier: 39 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 57 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 35 MB in 7 indices; its tier_down lines not yet moved: 3 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 19 moved indices).
- Each counted byte takes 0.87 bytes of store kept, 0.54 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 714 MB a day fits the size, so each statement keeps up to 45 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 99 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 934 |
| ad | the frozen tier | 1 | 58 MB | 58 MB | 125126 | 161355 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 38 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 102 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 184 |
| cart | the frozen tier | 1 | 133 MB | 90 MB | 125126 | 249979 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 937 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 44 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 167 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 215 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 72 |
| fluentd-10x | the frozen tier | 1 | 10 MB | 10 MB | 125126 | 26726 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 192 |
| frontend | the frozen tier | 1 | 29 MB | 29 MB | 125126 | 81845 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 125126 | 4844 |
| grafana | the frozen tier | 1 | 26 MB | 26 MB | 125126 | 72373 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 318 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 450 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 388 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 284 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 125126 | 3304 |
| kafka | the frozen tier | 1 | 270 MB | 270 MB | 125126 | 749072 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 125126 | 6067 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 344 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 1173 |
| opensearch | the frozen tier | 1 | 5 MB | 5 MB | 125126 | 13222 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 178 MB | 125126 | 494927 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 206 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 635 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 125126 | 3893 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 125126 | 19 |
| recommendation | the frozen tier | 1 | 36 MB | 36 MB | 125126 | 98652 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 125126 | 10541 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 125126 | 934 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
