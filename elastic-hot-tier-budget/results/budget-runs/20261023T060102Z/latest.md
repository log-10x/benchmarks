# Hot-tier run: 2026-10-23T06:01:03.000Z

Hot tier: 51 MB of 45 MB (0.0448 GB set in the policy) on 1 hot node; at these limits it settles at about 51 MB within 6 hours, with 1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 31 MB in 6 indices; its tier_down lines not yet moved: 19 MB in 3.
- A kept line stays on hot 6 hours (ILM policy tenx-keep (rollover max_age 1h + frozen min_age 5h)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 0.93 bytes of store kept, 0.58 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- Hot is above the size now; the allowance is held at 87% until it drains, which takes up to 6 hours as the indices on hot age out.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 45 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| ad | the frozen tier | 1 | 37 MB | 0 MB | 1 | 1 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| cart | the frozen tier | 1 | 78 MB | 0 MB | 1 | 1 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| fluentd-10x | the frozen tier | 1 | 7 MB | 0 MB | 1 | 1 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| frontend | the frozen tier | 1 | 15 MB | 0 MB | 1 | 1 |
| frontend-proxy | the frozen tier | 1 | 1 MB | 0 MB | 1 | 1 |
| grafana | the frozen tier | 1 | 65 MB | 0 MB | 1 | 1 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| hb-inventory | the frozen tier | 1 | 47 MB | 0 MB | 1 | 1 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| jaeger | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| kafka | the frozen tier | 1 | 172 MB | 0 MB | 1 | 1 |
| kube-proxy | the frozen tier | 1 | 1 MB | 0 MB | 1 | 1 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| opensearch | the frozen tier | 1 | 2 MB | 0 MB | 1 | 1 |
| opentelemetry-collector | the frozen tier | 1 | 577 MB | 0 MB | 1 | 1 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| prometheus-server | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1 |
| recommendation | the frozen tier | 1 | 26 MB | 0 MB | 1 | 1 |
| valkey-cart | the frozen tier | 1 | 1 MB | 0 MB | 1 | 1 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 1 | 1 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
