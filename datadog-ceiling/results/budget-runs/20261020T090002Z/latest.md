# Budget run: 2026-10-20T09:00:03.000Z

Standard held at $11 a month: $0.28 so far this month. Moved this month: 156,268 events to Flex, about $0.01 a month of Flex storage at $0.05 per million (Flex compute is unpriced and left out), $0.27 at the Standard rate.

- Standard indexing this month: $0.28 of $11 (164,330 events through 2026-10-20 09:00 UTC), 279 hours left.
- Lines that do not pass the Receiver, outside the services with their own number: 380 events in Standard this month, about $0 by the month's end at this rate. The Receiver's other services get the rest of $10.
- The Receiver's other services may send 20,579 events an hour to Standard against 35,945 now: each statement keeps up to 983 an hour, and the noisiest move to Flex first. A service the run has not seen gets the same level and the median service's 766 an hour until the next run, which takes any overshoot back from the rest of the month.
- Node counts from nodes_by_container in policy.yaml; 1 Receiver. The `*` row is divided by 1 node, the median known service's count. The division assumes a DaemonSet Receiver, one per node, each holding its node's share.
- frontend is held to its own $0.88 a month: $0.03 spent so far by Datadog's usage count for service:frontend, 1,792 events an hour for the rest of the month, a limit of 73 per statement and a total of 119 per window per node.
- Warning: No node count for inventory: its limits are written for one Receiver.

| Service | Destination | Nodes | Events an hour now | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | Flex | 1 | 4 | 4 | 65 | 1 |
| ad | Flex | 1 | 822 | 822 | 65 | 54 |
| astronomy-db | Flex | 1 | 916 | 916 | 65 | 61 |
| cart | Flex | 1 | 5,175 | 2,470 | 65 | 164 |
| email | Flex | 1 | 716 | 716 | 65 | 47 |
| flagd | Flex | 1 | 18 | 18 | 65 | 1 |
| flagd-ui | Flex | 1 | 3 | 3 | 65 | 1 |
| fraud-detection | Flex | 1 | 498 | 498 | 65 | 33 |
| frontend (own $0.88 a month) | Flex | 1 | 9,651 | 1,792 | 73 | 119 |
| frontend-proxy | Flex | 1 | 55 | 55 | 65 | 3 |
| image-provider | Flex | 1 | 41 | 41 | 65 | 2 |
| inventory | Flex | 1 | 3,488 | 983 | 65 | 65 |
| kafka | Flex | 1 | 4,912 | 4,912 | 65 | 327 |
| otel-collector | Flex | 1 | 12,631 | 3,105 | 65 | 207 |
| payment | Flex | 1 | 2,690 | 2,058 | 65 | 137 |
| product-catalog | Flex | 1 | 1 | 1 | 65 | 1 |
| quote | Flex | 1 | 543 | 543 | 65 | 36 |
| recommendation | Flex | 1 | 816 | 816 | 65 | 54 |
| shipping | Flex | 1 | 1,646 | 1,646 | 65 | 109 |
| telemetry-docs | Flex | 1 | 891 | 891 | 65 | 59 |
| valkey-cart | Flex | 1 | 80 | 80 | 65 | 5 |
| `*` (any other service) | Flex | 1 | | 766 | 65 | 51 |

Limits and totals are events per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window.
