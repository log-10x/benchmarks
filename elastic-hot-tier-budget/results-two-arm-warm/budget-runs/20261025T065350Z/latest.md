# Hot-tier run: 2026-10-25T06:53:51.000Z

Hot tier: 42 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 42 MB in 7 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 3 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.82 bytes of store kept, 0.82 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.9 GB a day; 912 MB a day fits the size, so each statement keeps up to 88 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 94 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 970 |
| ad | the frozen tier | 1 | 60 MB | 60 MB | 245123 | 166211 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 39 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 107 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 193 |
| cart | the frozen tier | 1 | 159 MB | 143 MB | 245123 | 395927 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 978 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 45 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 171 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 224 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 76 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 245123 | 31732 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 195 |
| frontend | the frozen tier | 1 | 33 MB | 33 MB | 245123 | 90803 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 245123 | 3895 |
| grafana | the frozen tier | 1 | 19 MB | 19 MB | 245123 | 53584 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 332 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 469 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 402 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 286 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 245123 | 3113 |
| kafka | the frozen tier | 1 | 275 MB | 275 MB | 245123 | 762723 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 245123 | 5712 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 351 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 1221 |
| opensearch | the frozen tier | 1 | 4 MB | 4 MB | 245123 | 11004 |
| opentelemetry-collector | the frozen tier | 1 | 1.3 GB | 316 MB | 245123 | 877627 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 208 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 661 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 245123 | 3823 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 245123 | 21 |
| recommendation | the frozen tier | 1 | 40 MB | 40 MB | 245123 | 110610 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 245123 | 10551 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 245123 | 970 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
