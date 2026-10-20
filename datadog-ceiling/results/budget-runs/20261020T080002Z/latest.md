# Budget run: 2026-10-20T08:00:02.000Z

Standard held at $11 a month: $0.24 so far this month. Moved this month: 118,670 events to Flex, about $0.01 a month of Flex storage at $0.05 per million (Flex compute is unpriced and left out), $0.2 at the Standard rate.

- Standard indexing this month: $0.24 of $11 (143,238 events through 2026-10-20 08:00 UTC), 280 hours left.
- Lines that do not pass the Receiver, outside the services with their own number: 415 events in Standard this month, about $0 by the month's end at this rate. The Receiver's other services get the rest of $10.
- The Receiver's other services may send 20,574 events an hour to Standard against 33,836 now: each statement keeps up to 1,117 an hour, and the noisiest move to Flex first. A service the run has not seen gets the same level and the median service's 699 an hour until the next run, which takes any overshoot back from the rest of the month.
- Node counts from nodes_by_container in policy.yaml; 1 Receiver. The `*` row is divided by 1 node, the median known service's count. The division assumes a DaemonSet Receiver, one per node, each holding its node's share.
- frontend is held to its own $0.88 a month: $0.03 spent so far by Datadog's usage count for service:frontend, 1,791 events an hour for the rest of the month, a limit of 77 per statement and a total of 119 per window per node.
- Warning: No node count for inventory: its limits are written for one Receiver.

| Service | Destination | Nodes | Events an hour now | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | Flex | 1 | 4 | 4 | 74 | 1 |
| ad | Flex | 1 | 757 | 757 | 74 | 50 |
| astronomy-db | Flex | 1 | 862 | 862 | 74 | 57 |
| cart | Flex | 1 | 4,731 | 2,684 | 74 | 178 |
| email | Flex | 1 | 650 | 650 | 74 | 43 |
| flagd | Flex | 1 | 18 | 18 | 74 | 1 |
| flagd-ui | Flex | 1 | 3 | 3 | 74 | 1 |
| fraud-detection | Flex | 1 | 444 | 444 | 74 | 29 |
| frontend (own $0.88 a month) | Flex | 1 | 8,867 | 1,791 | 77 | 119 |
| frontend-proxy | Flex | 1 | 55 | 55 | 74 | 3 |
| image-provider | Flex | 1 | 41 | 41 | 74 | 2 |
| inventory | Flex | 1 | 3,488 | 1,117 | 74 | 74 |
| kafka | Flex | 1 | 4,699 | 4,699 | 74 | 313 |
| otel-collector | Flex | 1 | 11,848 | 3,502 | 74 | 233 |
| payment | Flex | 1 | 2,591 | 2,092 | 74 | 139 |
| product-catalog | Flex | 1 | 1 | 1 | 74 | 1 |
| quote | Flex | 1 | 496 | 496 | 74 | 33 |
| recommendation | Flex | 1 | 748 | 748 | 74 | 49 |
| shipping | Flex | 1 | 1,490 | 1,490 | 74 | 99 |
| telemetry-docs | Flex | 1 | 836 | 836 | 74 | 55 |
| valkey-cart | Flex | 1 | 75 | 75 | 74 | 5 |
| `*` (any other service) | Flex | 1 | | 699 | 74 | 46 |

Limits and totals are events per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window.
