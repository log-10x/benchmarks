# Hot-tier run: 2026-10-25T05:11:04.000Z

Hot tier: 2 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 302 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 2 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 0 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.82 bytes of store kept, 0.82 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.1 GB a day; 814 MB a day fits the size, so each statement keeps up to 20 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 536 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 7 MB | 7 MB | 56216 | 18175 |
| ad | the frozen tier | 1 | 17 MB | 17 MB | 56216 | 47821 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 56216 | 404 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 56216 | 1097 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 1983 |
| cart | the frozen tier | 1 | 40 MB | 36 MB | 56216 | 99687 |
| coredns | the frozen tier | 1 | 4 MB | 4 MB | 56216 | 12493 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 56216 | 468 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 1765 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 2299 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 56216 | 779 |
| fluentd-10x | the frozen tier | 1 | 17 MB | 17 MB | 56216 | 46567 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 2006 |
| frontend | the frozen tier | 1 | 9 MB | 9 MB | 56216 | 24730 |
| frontend-proxy | the frozen tier | 1 | 18 MB | 18 MB | 56216 | 50963 |
| grafana | the frozen tier | 1 | 200 MB | 200 MB | 56216 | 554741 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 3408 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 56216 | 4820 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 4131 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 2946 |
| jaeger | the frozen tier | 1 | 11 MB | 11 MB | 56216 | 30280 |
| kafka | the frozen tier | 1 | 146 MB | 146 MB | 56216 | 405324 |
| kube-proxy | the frozen tier | 1 | 26 MB | 26 MB | 56216 | 71411 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 3614 |
| metrics-server | the frozen tier | 1 | 5 MB | 5 MB | 56216 | 12535 |
| opensearch | the frozen tier | 1 | 34 MB | 34 MB | 56216 | 94127 |
| opentelemetry-collector | the frozen tier | 1 | 549 MB | 252 MB | 56216 | 698675 |
| payment | the frozen tier | 1 | 1 MB | 1 MB | 56216 | 2142 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 56216 | 6794 |
| prometheus-server | the frozen tier | 1 | 4 MB | 4 MB | 56216 | 9778 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 56216 | 217 |
| recommendation | the frozen tier | 1 | 15 MB | 15 MB | 56216 | 40850 |
| valkey-cart | the frozen tier | 1 | 2 MB | 2 MB | 56216 | 4680 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 56216 | 6794 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
