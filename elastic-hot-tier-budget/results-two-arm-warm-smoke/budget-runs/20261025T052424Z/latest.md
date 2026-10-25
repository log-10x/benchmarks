# Hot-tier run: 2026-10-25T05:24:24.000Z

Hot tier: 7 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 1.9 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 7 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 6 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.11 bytes of store kept, 1.11 as tier_down (measured on the indices on hot).
- The Receiver's statements send 2.5 GB a day; 605 MB a day fits the size, so each statement keeps up to 19 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 172 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 52049 | 4068 |
| ad | the frozen tier | 1 | 69 MB | 42 MB | 52049 | 117967 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 90 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 245 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 444 |
| cart | the frozen tier | 1 | 212 MB | 38 MB | 52049 | 104623 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 52049 | 2796 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 104 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 395 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 514 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 174 |
| fluentd-10x | the frozen tier | 1 | 16 MB | 16 MB | 52049 | 45238 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 449 |
| frontend | the frozen tier | 1 | 43 MB | 19 MB | 52049 | 52396 |
| frontend-proxy | the frozen tier | 1 | 4 MB | 4 MB | 52049 | 11479 |
| grafana | the frozen tier | 1 | 53 MB | 53 MB | 52049 | 147129 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 763 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 1079 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 924 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 659 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 52049 | 7871 |
| kafka | the frozen tier | 1 | 351 MB | 262 MB | 52049 | 726408 |
| kube-proxy | the frozen tier | 1 | 6 MB | 6 MB | 52049 | 17092 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 809 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 52049 | 2806 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 52049 | 25823 |
| opentelemetry-collector | the frozen tier | 1 | 1.6 GB | 121 MB | 52049 | 336236 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 479 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 52049 | 1520 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 52049 | 5310 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 52049 | 48 |
| recommendation | the frozen tier | 1 | 55 MB | 19 MB | 52049 | 52236 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 52049 | 11732 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 52049 | 2796 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
