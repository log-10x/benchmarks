# Hot-tier run: 2026-10-25T05:28:24.000Z

Hot tier: 10 MB of 56 MB (0.056 GB set in the policy) on 1 hot node; at these limits it settles at about 56 MB within 2 hours, with 2.7 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 10 MB in 2 indices; its tier_down lines not yet moved: 0 MB in 0 on hot, 21 MB in 1 off hot, outside the size.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); the tier_down write index is off hot, so moved lines take no room on hot while they wait for their mount.
- Each counted byte takes 1.28 bytes of store kept, 1.28 as tier_down (measured on the indices on hot).
- The Receiver's statements send 3.2 GB a day; 525 MB a day fits the size, so each statement keeps up to 16 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 151 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 44148 | 3300 |
| ad | the frozen tier | 1 | 102 MB | 39 MB | 44148 | 108776 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 73 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 199 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 360 |
| cart | the frozen tier | 1 | 272 MB | 32 MB | 44148 | 88722 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 44148 | 2268 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 84 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 320 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 417 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 141 |
| fluentd-10x | the frozen tier | 1 | 20 MB | 20 MB | 44148 | 54627 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 364 |
| frontend | the frozen tier | 1 | 59 MB | 16 MB | 44148 | 44429 |
| frontend-proxy | the frozen tier | 1 | 3 MB | 3 MB | 44148 | 9311 |
| grafana | the frozen tier | 1 | 47 MB | 47 MB | 44148 | 130879 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 618 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 875 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 750 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 535 |
| jaeger | the frozen tier | 1 | 2 MB | 2 MB | 44148 | 6384 |
| kafka | the frozen tier | 1 | 470 MB | 221 MB | 44148 | 614294 |
| kube-proxy | the frozen tier | 1 | 5 MB | 5 MB | 44148 | 14582 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 656 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 44148 | 2276 |
| opensearch | the frozen tier | 1 | 9 MB | 9 MB | 44148 | 24333 |
| opentelemetry-collector | the frozen tier | 1 | 2.1 GB | 101 MB | 44148 | 280449 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 389 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 1233 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 44148 | 6355 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 44148 | 39 |
| recommendation | the frozen tier | 1 | 72 MB | 16 MB | 44148 | 44299 |
| valkey-cart | the frozen tier | 1 | 6 MB | 6 MB | 44148 | 16642 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 44148 | 2268 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
