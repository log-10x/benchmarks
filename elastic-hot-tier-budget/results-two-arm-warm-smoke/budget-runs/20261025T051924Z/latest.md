# Hot-tier run: 2026-10-25T05:19:25.000Z

Hot tier: 9 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 1.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 9 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 8 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.89 bytes of store kept, 1.89 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.6 GB a day; 356 MB a day fits the size, so each statement keeps up to 6 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 219 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 15420 | 5731 |
| ad | the frozen tier | 1 | 49 MB | 15 MB | 15420 | 41764 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 127 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 346 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 625 |
| cart | the frozen tier | 1 | 114 MB | 11 MB | 15420 | 31580 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 15420 | 3939 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 147 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 556 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 725 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 245 |
| fluentd-10x | the frozen tier | 1 | 14 MB | 14 MB | 15420 | 37560 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 632 |
| frontend | the frozen tier | 1 | 26 MB | 12 MB | 15420 | 33649 |
| frontend-proxy | the frozen tier | 1 | 6 MB | 6 MB | 15420 | 16170 |
| grafana | the frozen tier | 1 | 69 MB | 69 MB | 15420 | 192451 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 1074 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 15420 | 1519 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 1302 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 929 |
| jaeger | the frozen tier | 1 | 4 MB | 4 MB | 15420 | 11087 |
| kafka | the frozen tier | 1 | 241 MB | 97 MB | 15420 | 270569 |
| kube-proxy | the frozen tier | 1 | 8 MB | 8 MB | 15420 | 23141 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 1139 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 15420 | 3952 |
| opensearch | the frozen tier | 1 | 12 MB | 12 MB | 15420 | 33290 |
| opentelemetry-collector | the frozen tier | 1 | 986 MB | 87 MB | 15420 | 242054 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 675 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 15420 | 2142 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 15420 | 4867 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 15420 | 68 |
| recommendation | the frozen tier | 1 | 35 MB | 6 MB | 15420 | 15684 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 15420 | 9096 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 15420 | 3939 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
