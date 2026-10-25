# Hot-tier run: 2026-10-25T07:53:51.000Z

Hot tier: 60 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 968 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 59 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 3 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.88 bytes of store kept, 0.88 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 851 MB a day fits the size, so each statement keeps up to 77 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 70 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 117 |
| ad | the frozen tier | 1 | 58 MB | 58 MB | 213353 | 161397 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 26 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 72 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 131 |
| cart | the frozen tier | 1 | 168 MB | 133 MB | 213353 | 369919 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 501 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 30 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 116 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 151 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 51 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 213353 | 31543 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 131 |
| frontend | the frozen tier | 1 | 34 MB | 34 MB | 213353 | 95204 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 213353 | 1825 |
| grafana | the frozen tier | 1 | 10 MB | 10 MB | 213353 | 28378 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 224 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 317 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 271 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 193 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 213353 | 1872 |
| kafka | the frozen tier | 1 | 277 MB | 277 MB | 213353 | 768171 |
| kube-proxy | the frozen tier | 1 | 1 MB | 1 MB | 213353 | 2578 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 237 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 825 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 213353 | 7181 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 274 MB | 213353 | 762084 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 140 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 447 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 213353 | 3920 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 213353 | 14 |
| recommendation | the frozen tier | 1 | 41 MB | 41 MB | 213353 | 113658 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 213353 | 11064 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 213353 | 447 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
