# Hot-tier run: 2026-10-23T12:35:42.000Z

Hot tier: 36 MB of 57 MB (0.0567 GB set in the policy) on 1 hot node; at these limits it settles at about 57 MB within 2 hours, with 1.1 GB a day of counted lines moved to the frozen tier.

- Outside the Receiver: 1 MB on hot. The Receiver's kept lines: 32 MB in 7 indices; its tier_down lines not yet moved: 3 MB in 3.
- A kept line stays on hot 2 hours (ILM policy tenx-keep (rollover max_age 10m + frozen min_age 110m)); a tier_down index 0.2 hours (rollover max_age 3m + a median 7 minutes from rollover to mount over 16 moved indices).
- Each counted byte takes 0.91 bytes of store kept, 0.46 as tier_down (measured on the indices on hot).
- The Receiver's statements send 1.8 GB a day; 690 MB a day fits the size, so each statement keeps up to 60 MB a day and the noisiest give way first.
- The always-pass sample (5 lines a statement a window on every node, 50 more for an error statement over its limit) keeps about 107 MB a day on hot whatever the limits; the size holds down to that floor.
- Warning: 1 documents on hot carry no utf8Size, so their statements count as 0 bytes. The Receiver writes it when installed for the hot-tier run.

| Service | Destination | Nodes | Sent a day | Kept a day | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 1068 |
| ad | the frozen tier | 1 | 42 MB | 42 MB | 167330 | 117262 |
| aws-eks-nodeagent | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 43 |
| aws-node | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 116 |
| aws-vpc-cni-init | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 211 |
| cart | the frozen tier | 1 | 114 MB | 102 MB | 167330 | 283123 |
| coredns | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 1070 |
| currency | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 50 |
| email | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 191 |
| flagd | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 246 |
| flagd-ui | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 82 |
| fluentd-10x | the frozen tier | 1 | 12 MB | 12 MB | 167330 | 33833 |
| fraud-detection | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 219 |
| frontend | the frozen tier | 1 | 28 MB | 28 MB | 167330 | 78223 |
| frontend-proxy | the frozen tier | 1 | 2 MB | 2 MB | 167330 | 5536 |
| grafana | the frozen tier | 1 | 29 MB | 29 MB | 167330 | 79612 |
| grafana-sc-alerts | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 364 |
| grafana-sc-dashboard | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 515 |
| grafana-sc-datasources | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 444 |
| init-config | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 324 |
| jaeger | the frozen tier | 1 | 1 MB | 1 MB | 167330 | 3775 |
| kafka | the frozen tier | 1 | 202 MB | 202 MB | 167330 | 561176 |
| kube-proxy | the frozen tier | 1 | 2 MB | 2 MB | 167330 | 6723 |
| load-generator | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 393 |
| metrics-server | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 1341 |
| opensearch | the frozen tier | 1 | 5 MB | 5 MB | 167330 | 14422 |
| opentelemetry-collector | the frozen tier | 1 | 1.3 GB | 225 MB | 167330 | 626200 |
| payment | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 235 |
| postgresql | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 725 |
| prometheus-server | the frozen tier | 1 | 1 MB | 1 MB | 167330 | 3547 |
| quote | the frozen tier | 1 | 0 MB | 0 MB | 167330 | 22 |
| recommendation | the frozen tier | 1 | 31 MB | 31 MB | 167330 | 87176 |
| valkey-cart | the frozen tier | 1 | 3 MB | 3 MB | 167330 | 8851 |
| `*` (any other service) | the frozen tier | 1 | | 0 MB | 167330 | 1068 |

Limits and totals are bytes per 4-minute window per node, counted the way the Receiver counts them (utf8Size). Error lines pass 50 over a limit per statement per node per window.
