# Hot-tier run: 2026-10-25T05:29:25.000Z

Hot tier: 8 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 2.5 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 8 MB in 3 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 12 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.97 bytes of store kept, 0.97 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3.1 GB a day; 694 MB a day fits the size, so each statement keeps up to 23 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 147 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 65225 | 3148 |
| ad | the frozen tier | 1 | 101 MB | 54 MB | 65225 | 150722 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 70 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 190 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 343 |
| cart | the frozen tier | 1 | 269 MB | 47 MB | 65225 | 130856 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 65225 | 2164 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 81 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 305 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 398 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 134 |
| fluentd-10x | the frozen tier | 1 | 19 MB | 19 MB | 65225 | 53276 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 347 |
| frontend | the frozen tier | 1 | 59 MB | 24 MB | 65225 | 65493 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 65225 | 8885 |
| grafana | the frozen tier | 1 | 46 MB | 46 MB | 65225 | 126523 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 590 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 835 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 715 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 510 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 65225 | 6092 |
| kafka | the frozen tier | 1 | 456 MB | 319 MB | 65225 | 886445 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 65225 | 14087 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 626 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 65225 | 2171 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 65225 | 23654 |
| opentelemetry-collector | the frozen tier | 1 | 2.1 GB | 130 MB | 65225 | 359999 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 371 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 1177 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 65225 | 6131 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 65225 | 37 |
| recommendation | the frozen tier | 1 | 72 MB | 24 MB | 65225 | 65369 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 65225 | 16533 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 65225 | 2164 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
