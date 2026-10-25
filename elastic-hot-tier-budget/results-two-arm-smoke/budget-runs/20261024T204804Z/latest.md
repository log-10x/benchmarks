# Hot-tier run: 2026-10-24T20:48:05.000Z

Hot tier: 4 MB of 74 MB (0.0742 GB set in the policy) on 1 hot node; at these limits it settles at about 182 MB within 2 hours, with 256 MB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 0 MB on hot. The Receiver's kept lines: 4 MB in 1 indices; its tier_down lines not yet moved: 0 MB in 1.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 2 hours (default (no tier_down index has been moved yet)).
- Each counted byte takes 2.38 bytes of store kept, 2.38 as tier_down (measured on the indices on hot).
- The Receiver's statements send 921 MB a day; 119 MB a day fits the size, so each statement keeps up to 0 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 665 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.
- Warning: The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) alone keeps about 665 MB a day on hot, more than the 119 MB a day that fits, so hot settles above 74 MB at about 182 MB. Raise the size, move the noisiest services to offload, or lower the sample.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 10 MB | 8 MB | 1 | 22409 |
| ad | the frozen tier | 1 | 12 MB | 3 MB | 1 | 7386 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 1 | 605 |
| aws-node | the frozen tier | 1 | 1 MB | 1 MB | 1 | 1640 |
| aws-vpc-cni-init | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2965 |
| cart | the frozen tier | 1 | 23 MB | 2 MB | 1 | 6602 |
| coredns | the frozen tier | 1 | 7 MB | 3 MB | 1 | 8780 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 1 | 699 |
| email | the frozen tier | 1 | 1 MB | 1 MB | 1 | 2639 |
| flagd | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3438 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 1 | 1164 |
| fraud-detection | the frozen tier | 1 | 1 MB | 1 MB | 1 | 3000 |
| frontend | the frozen tier | 1 | 5 MB | 5 MB | 1 | 14468 |
| frontend-proxy | the frozen tier | 1 | 27 MB | 27 MB | 1 | 76200 |
| grafana | the frozen tier | 1 | 296 MB | 294 MB | 1 | 815438 |
| grafana-sc-alerts | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5096 |
| grafana-sc-dashboard | the frozen tier | 1 | 3 MB | 3 MB | 1 | 7207 |
| grafana-sc-datasources | the frozen tier | 1 | 2 MB | 2 MB | 1 | 6177 |
| init-config | the frozen tier | 1 | 2 MB | 2 MB | 1 | 4406 |
| jaeger | the frozen tier | 1 | 16 MB | 16 MB | 1 | 45274 |
| kafka | the frozen tier | 1 | 147 MB | 55 MB | 1 | 153140 |
| kube-proxy | the frozen tier | 1 | 38 MB | 17 MB | 1 | 46516 |
| load-generator | the frozen tier | 1 | 2 MB | 2 MB | 1 | 5404 |
| metrics-server | the frozen tier | 1 | 7 MB | 7 MB | 1 | 18742 |
| opensearch | the frozen tier | 1 | 50 MB | 45 MB | 1 | 124943 |
| opentelemetry-collector | the frozen tier | 1 | 266 MB | 167 MB | 1 | 463717 |
| `*` (any other service) | the frozen tier | 1 | | 2 MB | 1 | 6904 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
