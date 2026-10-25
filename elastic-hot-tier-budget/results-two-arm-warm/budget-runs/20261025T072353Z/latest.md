# Hot-tier run: 2026-10-25T07:23:54.000Z

Hot tier: 57 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 916 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 57 MB in 10 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 7 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 0.83 bytes of store kept, 0.83 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 903 MB a day fits the size, so each statement keeps up to 88 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 81 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 703 |
| ad | the frozen tier | 1 | 58 MB | 58 MB | 245455 | 160781 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 28 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 77 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 140 |
| cart | the frozen tier | 1 | 142 MB | 142 MB | 245455 | 395115 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 709 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 33 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 124 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 162 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 55 |
| fluentd-10x | the frozen tier | 1 | 11 MB | 11 MB | 245455 | 31597 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 141 |
| frontend | the frozen tier | 1 | 34 MB | 34 MB | 245455 | 93360 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 1 MB | 245455 | 2823 |
| grafana | the frozen tier | 1 | 16 MB | 16 MB | 245455 | 45730 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 240 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 340 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 291 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 207 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 245455 | 2256 |
| kafka | the frozen tier | 1 | 274 MB | 274 MB | 245455 | 760549 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 245455 | 4490 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 254 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 885 |
| opensearch | the frozen tier | 1 | 3 MB | 3 MB | 245455 | 9587 |
| opentelemetry-collector | the frozen tier | 1 | 1.2 GB | 310 MB | 245455 | 861268 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 150 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 479 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 245455 | 3658 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 245455 | 15 |
| recommendation | the frozen tier | 1 | 43 MB | 43 MB | 245455 | 120273 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 245455 | 10445 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 245455 | 703 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
