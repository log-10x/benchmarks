# Hot-tier run: 2026-10-24T20:49:18.000Z

Hot tier: 3 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 78 MB within 2 hours, with 572 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.19 bytes of store kept, 0.50 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.1 GB a day; 504 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 541 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 541 MB a day on hot, more than the 504 MB a day that fits, so hot settles above 74 MB at about 78 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 7 MB | 6 MB | 1 | 16711 |
| ad | the frozen tier | 1 | 17 MB | 2 MB | 1 | 6710 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 410 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1113 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2013 |
| cart | the frozen tier | 1 | 38 MB | 2 MB | 1 | 5466 |
| coredns | the frozen tier | 1 | 5 MB | 3 MB | 1 | 7432 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 475 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1791 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2334 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 790 |
| fluentd-10x | the frozen tier | 1 | 17 MB | 10 MB | 1 | 26607 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2036 |
| frontend | the frozen tier | 1 | 8 MB | 8 MB | 1 | 23192 |
| frontend-proxy | the frozen tier | 1 | 19 MB | 19 MB | 1 | 51728 |
| grafana | the frozen tier | 1 | 203 MB | 202 MB | 1 | 559786 |
| grafana-sc-alerts | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3459 |
| grafana-sc-dashboard | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4892 |
| grafana-sc-datasources | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4193 |
| init-config | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2991 |
| jaeger | the frozen tier | 1 | 11 MB | 11 MB | 1 | 30734 |
| kafka | the frozen tier | 1 | 143 MB | 43 MB | 1 | 119607 |
| kube-proxy | the frozen tier | 1 | 26 MB | 12 MB | 1 | 33379 |
| load-generator | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3668 |
| metrics-server | the frozen tier | 1 | 5 MB | 5 MB | 1 | 12723 |
| opensearch | the frozen tier | 1 | 34 MB | 32 MB | 1 | 88993 |
| opentelemetry-collector | the frozen tier | 1 | 548 MB | 166 MB | 1 | 461134 |
| payment | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2174 |
| postgresql | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6896 |
| prometheus-server | the frozen tier | 1 | 4 MB | 4 MB | 1 | 9917 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 220 |
| recommendation | the frozen tier | 1 | 14 MB | 1 MB | 1 | 3344 |
| valkey-cart | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4751 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 1 | 4892 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
