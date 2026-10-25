# Hot-tier run: 2026-10-25T09:23:51.000Z

Hot tier: 59 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 0 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 2 MB on hot. The Receiver's kept lines: 57 MB in 11 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 0 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.92 bytes of store kept, 0.92 as tier_down (measured on the indices on hot).
- The Receiver's statements send 709 MB a day, under the 799 MB a day that fits the size; every statement keeps its lines, with room to grow 1.1 times.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 91 MB a day on hot whatever the limits; the size holds down to that floor.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 247 | 247 |
| ad | the frozen tier | 1 | 55 MB | 62 MB | 77785 | 171317 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 56 | 56 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 41 | 152 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 41 | 276 |
| cart | the frozen tier | 1 | 82 MB | 93 MB | 139744 | 257059 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 306 | 1055 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 64 | 64 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 148 | 244 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 48 | 319 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 38 | 108 |
| fluentd-10x | the frozen tier | 1 | 15 MB | 17 MB | 37631 | 46831 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 230 | 277 |
| frontend | the frozen tier | 1 | 33 MB | 37 MB | 103102 | 103317 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 359 | 3773 |
| grafana | the frozen tier | 1 | 15 MB | 17 MB | 21502 | 48289 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 57 | 472 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 117 | 667 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 152 | 571 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 406 | 406 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 271 | 3800 |
| kafka | the frozen tier | 1 | 285 MB | 321 MB | 72773 | 892572 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 967 | 5129 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 499 | 499 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 245 | 1736 |
| opensearch | the frozen tier | 1 | 4 MB | 5 MB | 3911 | 12763 |
| opentelemetry-collector | the frozen tier | 1 | 176 MB | 198 MB | 131044 | 549943 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 295 | 295 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 137 | 941 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 2979 | 5799 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 30 | 30 |
| recommendation | the frozen tier | 1 | 30 MB | 34 MB | 94920 | 95036 |
| valkey-cart | the frozen tier | 1 | 5 MB | 5 MB | 3129 | 14904 |
| `*` (any other service) | the frozen tier | 1 | | 90 MB | 249140 | 249140 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
