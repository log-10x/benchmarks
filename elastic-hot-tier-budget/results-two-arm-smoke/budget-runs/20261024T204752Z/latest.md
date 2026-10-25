# Hot-tier run: 2026-10-24T20:47:52.000Z

Hot tier: 3 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 157 MB within 2 hours, with 240 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 3 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 1.98 bytes of store kept, 1.98 as tier_down (measured on the indices on hot).
- The Receiver's statements send 949 MB a day; 209 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 709 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 709 MB a day on hot, more than the 209 MB a day that fits, so hot settles above 74 MB at about 157 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 11 MB | 9 MB | 1 | 24041 |
| ad | the frozen tier | 1 | 13 MB | 3 MB | 1 | 7584 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 660 |
| aws-node | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1791 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3238 |
| cart | the frozen tier | 1 | 25 MB | 2 MB | 1 | 6924 |
| coredns | the frozen tier | 1 | 7 MB | 3 MB | 1 | 9167 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 764 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2882 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3755 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1272 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3276 |
| frontend | the frozen tier | 1 | 6 MB | 6 MB | 1 | 15800 |
| frontend-proxy | the frozen tier | 1 | 30 MB | 30 MB | 1 | 83210 |
| grafana | the frozen tier | 1 | 324 MB | 320 MB | 1 | 888108 |
| grafana-sc-alerts | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5565 |
| grafana-sc-dashboard | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7870 |
| grafana-sc-datasources | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6745 |
| init-config | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4811 |
| jaeger | the frozen tier | 1 | 18 MB | 18 MB | 1 | 49246 |
| kafka | the frozen tier | 1 | 161 MB | 59 MB | 1 | 162876 |
| kube-proxy | the frozen tier | 1 | 42 MB | 18 MB | 1 | 50175 |
| load-generator | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5901 |
| metrics-server | the frozen tier | 1 | 7 MB | 7 MB | 1 | 20467 |
| opensearch | the frozen tier | 1 | 55 MB | 49 MB | 1 | 135115 |
| opentelemetry-collector | the frozen tier | 1 | 234 MB | 169 MB | 1 | 469319 |
| `*` (any other service) | the frozen tier | 1 | | 3 MB | 1 | 7254 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
