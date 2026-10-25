# Hot-tier run: 2026-10-25T06:13:50.000Z

Hot tier: 23 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 985 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 22 MB in 4 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 4 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.80 bytes of store kept, 0.80 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.9 GB a day; 941 MB a day fits the size, so each statement keeps up to 105 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 106 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 292601 | 1784 |
| ad | the frozen tier | 1 | 56 MB | 56 MB | 292601 | 155774 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 39 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 107 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 194 |
| cart | the frozen tier | 1 | 132 MB | 132 MB | 292601 | 367196 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 1226 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 45 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 173 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 225 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 76 |
| fluentd-10x | the frozen tier | 1 | 12 MB | 12 MB | 292601 | 33100 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 196 |
| frontend | the frozen tier | 1 | 32 MB | 32 MB | 292601 | 88553 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 292601 | 5034 |
| grafana | the frozen tier | 1 | 28 MB | 28 MB | 292601 | 77135 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 334 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 473 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 405 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 289 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 292601 | 3452 |
| kafka | the frozen tier | 1 | 258 MB | 258 MB | 292601 | 715916 |
| kube-proxy | the frozen tier | 1 | 3 MB | 3 MB | 292601 | 8177 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 354 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 1230 |
| opensearch | the frozen tier | 1 | 5 MB | 5 MB | 292601 | 14432 |
| opentelemetry-collector | the frozen tier | 1 | 1.4 GB | 367 MB | 292601 | 1018255 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 210 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 667 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 292601 | 3619 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 292601 | 21 |
| recommendation | the frozen tier | 1 | 38 MB | 38 MB | 292601 | 105640 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 292601 | 9933 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 292601 | 1226 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
