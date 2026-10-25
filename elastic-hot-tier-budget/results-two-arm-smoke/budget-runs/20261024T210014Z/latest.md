# Hot-tier run: 2026-10-24T21:00:15.000Z

Hot tier: 12 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 98 MB within 2 hours, with 1.4 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 2 indices; its tier_down lines not yet moved: 9 MB in 2.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.20 bytes of store kept, 0.67 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.6 GB a day; 0 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 190 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 190 MB a day on hot, more than the 0 MB a day that fits, so hot settles above 74 MB at about 98 MB. Raise the size, move the noisiest services to offload, or lower the sample.
- Warning: Lines outside the Receiver and the tier_down lines waiting to move already fill 74 MB, so the Receiver's services keep nothing beyond the always-pass sample of 5 lines a statement a window.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4742 |
| ad | the frozen tier | 1 | 51 MB | 2 MB | 1 | 5632 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 105 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 1 | 286 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 1 | 517 |
| cart | the frozen tier | 1 | 119 MB | 1 MB | 1 | 3692 |
| coredns | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3259 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 122 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 1 | 460 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 1 | 600 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 203 |
| fluentd-10x | the frozen tier | 1 | 13 MB | 4 MB | 1 | 11580 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 1 | 523 |
| frontend | the frozen tier | 1 | 28 MB | 12 MB | 1 | 33566 |
| frontend-proxy | the frozen tier | 1 | 5 MB | 5 MB | 1 | 13380 |
| grafana | the frozen tier | 1 | 59 MB | 55 MB | 1 | 152860 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 1 | 889 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1257 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1077 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 1 | 768 |
| jaeger | the frozen tier | 1 | 3 MB | 3 MB | 1 | 9174 |
| kafka | the frozen tier | 1 | 248 MB | 22 MB | 1 | 60209 |
| kube-proxy | the frozen tier | 1 | 7 MB | 4 MB | 1 | 12112 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 1 | 943 |
| metrics-server | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3270 |
| opensearch | the frozen tier | 1 | 10 MB | 10 MB | 1 | 27774 |
| opentelemetry-collector | the frozen tier | 1 | 1 GB | 59 MB | 1 | 163799 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 1 | 559 |
| postgresql | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1772 |
| prometheus-server | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4249 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 1 | 56 |
| recommendation | the frozen tier | 1 | 36 MB | 1 MB | 1 | 2717 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 1 | 6975 |
| `*` (any other service) | the frozen tier | 1 | | 1 MB | 1 | 2717 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
