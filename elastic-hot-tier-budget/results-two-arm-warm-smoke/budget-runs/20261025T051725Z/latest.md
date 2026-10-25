# Hot-tier run: 2026-10-25T05:17:26.000Z

Hot tier: 9 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 1.2 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 9 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 7 MB in 2 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.83 bytes of store kept, 1.83 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.5 GB a day; 367 MB a day fits the size, so each statement keeps up to 5 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 251 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 12562 | 6844 |
| ad | the frozen tier | 1 | 46 MB | 13 MB | 12562 | 36012 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 152 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 413 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 746 |
| cart | the frozen tier | 1 | 105 MB | 9 MB | 12562 | 26006 |
| coredns | the frozen tier | 1 | 2 MB | 2 MB | 12562 | 4704 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 176 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 664 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 866 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 293 |
| fluentd-10x | the frozen tier | 1 | 14 MB | 12 MB | 12562 | 33158 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 755 |
| frontend | the frozen tier | 1 | 24 MB | 12 MB | 12562 | 33743 |
| frontend-proxy | the frozen tier | 1 | 7 MB | 7 MB | 12562 | 19311 |
| grafana | the frozen tier | 1 | 81 MB | 81 MB | 12562 | 225089 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 1283 |
| grafana-sc-dashboard | the frozen tier | 1 | 1 MB | 1 MB | 12562 | 1815 |
| grafana-sc-datasources | the frozen tier | 1 | 1 MB | 1 MB | 12562 | 1555 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 1109 |
| jaeger | the frozen tier | 1 | 5 MB | 5 MB | 12562 | 13241 |
| kafka | the frozen tier | 1 | 233 MB | 89 MB | 12562 | 247018 |
| kube-proxy | the frozen tier | 1 | 10 MB | 10 MB | 12562 | 27635 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 1361 |
| metrics-server | the frozen tier | 1 | 2 MB | 2 MB | 12562 | 4720 |
| opensearch | the frozen tier | 1 | 14 MB | 14 MB | 12562 | 38670 |
| opentelemetry-collector | the frozen tier | 1 | 955 MB | 94 MB | 12562 | 261996 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 806 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 12562 | 2558 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 12562 | 5413 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 12562 | 81 |
| recommendation | the frozen tier | 1 | 33 MB | 5 MB | 12562 | 12876 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 12562 | 8334 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 12562 | 4704 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
