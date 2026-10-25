# Hot-tier run: 2026-10-25T08:13:52.000Z

Hot tier: 65 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 61 MB within 2 hours, with 2.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 64 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 5 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.88 bytes of store kept, 0.88 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3 GB a day; 821 MB a day fits the size, so each statement keeps up to 34 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 69 MB a day on hot whatever the limits; the size holds down to that floor.
- Hot is above the size now; the allowance is held at 97% until it drains, which takes up to 2 hours as the indices on hot age out.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 109 |
| ad | the frozen tier | 1 | 82 MB | 74 MB | 94338 | 205969 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 24 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 67 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 122 |
| cart | the frozen tier | 1 | 247 MB | 68 MB | 94338 | 188822 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 468 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 28 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 108 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 141 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 48 |
| fluentd-10x | the frozen tier | 1 | 17 MB | 17 MB | 94338 | 48250 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 122 |
| frontend | the frozen tier | 1 | 47 MB | 34 MB | 94338 | 94434 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 94338 | 1704 |
| grafana | the frozen tier | 1 | 13 MB | 13 MB | 94338 | 36350 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 209 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 296 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 253 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 180 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 94338 | 1748 |
| kafka | the frozen tier | 1 | 435 MB | 419 MB | 94338 | 1163629 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 94338 | 2590 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 221 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 770 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 94338 | 7375 |
| opentelemetry-collector | the frozen tier | 1 | 2.1 GB | 148 MB | 94338 | 410466 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 131 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 417 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 94338 | 4125 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 94338 | 13 |
| recommendation | the frozen tier | 1 | 70 MB | 34 MB | 94338 | 94390 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 94338 | 17388 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 94338 | 417 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
