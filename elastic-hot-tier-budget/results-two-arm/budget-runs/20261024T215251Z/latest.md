# Hot-tier run: 2026-10-24T21:52:52.000Z

Hot tier: 21 MB of 63 MB (0.063 GB set in the policy) on 1 hot node; at these limits it settles at about 63 MB within 2 hours, with 912 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 16 MB in 4 indices; its tier_down lines not yet moved: 5 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.3 hours (rollover max_age 10m + a median 7 minutes from rollover to mount over 2 moved indices).
- Each counted byte takes 0.81 bytes of store kept, 0.41 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 868 MB a day fits the size, so each statement keeps up to 106 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 106 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 1 MB | 1 MB | 294889 | 1785 |
| ad | the frozen tier | 1 | 49 MB | 49 MB | 294889 | 136991 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 39 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 107 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 194 |
| cart | the frozen tier | 1 | 120 MB | 120 MB | 294889 | 333562 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 1227 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 45 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 173 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 225 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 76 |
| fluentd-10x | the frozen tier | 1 | 10 MB | 10 MB | 294889 | 26991 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 197 |
| frontend | the frozen tier | 1 | 26 MB | 26 MB | 294889 | 73345 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 294889 | 5038 |
| grafana | the frozen tier | 1 | 26 MB | 26 MB | 294889 | 73539 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 334 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 473 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 405 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 289 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 294889 | 3455 |
| kafka | the frozen tier | 1 | 222 MB | 222 MB | 294889 | 616489 |
| kube-proxy | the frozen tier | 1 | 3 MB | 3 MB | 294889 | 8184 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 355 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 1231 |
| opensearch | the frozen tier | 1 | 5 MB | 5 MB | 294889 | 14185 |
| opentelemetry-collector | the frozen tier | 1 | 1.3 GB | 361 MB | 294889 | 1003702 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 210 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 667 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 294889 | 3518 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 294889 | 21 |
| recommendation | the frozen tier | 1 | 34 MB | 34 MB | 294889 | 94505 |
| valkey-cart | the frozen tier | 1 | 4 MB | 4 MB | 294889 | 10105 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 294889 | 1227 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
