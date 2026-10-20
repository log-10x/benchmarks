# Budget run: 2026-10-20T05:00:02.000Z

Standard held at $11 a month: $0.13 so far this month. Moved this month: 16,377 events to Flex, about $0 a month of Flex storage at $0.05 per million (Flex compute is unpriced and left out), $0.03 at the Standard rate.

- Standard indexing this month: $0.13 of $11 (78,369 events through 2026-10-20 05:00 UTC), 283 hours left.
- Lines that do not pass the Receiver, outside the services with their own number: 323 events in Standard this month, about $0 by the month's end at this rate. The Receiver's other services get the rest of $10.
- The Receiver's other services send 20,269 events an hour, under the 20,567 the budget leaves, and each keeps room to grow 1.01x. A service the run has not seen gets the larger of the 0 an hour left over and the median service's limits, 407 an hour in all, until the next run, which takes any overshoot back from the rest of the month.
- Node counts from nodes_by_container in policy.yaml; 1 Receiver. The `*` row is divided by 1 node, the median known service's count. The division assumes a DaemonSet Receiver, one per node, each holding its node's share.
- frontend is held to its own $0.88 a month: $0.02 spent so far by Datadog's usage count for service:frontend, 1,791 events an hour for the rest of the month, a limit of 101 per statement and a total of 119 per window per node.

| Service | Destination | Nodes | Events an hour now | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | Flex | 1 | 4 | 4 | 1 | 1 |
| ad | Flex | 1 | 405 | 411 | 22 | 27 |
| astronomy-db | Flex | 1 | 663 | 673 | 42 | 44 |
| cart | Flex | 1 | 2,622 | 2,660 | 102 | 177 |
| email | Flex | 1 | 455 | 461 | 18 | 30 |
| flagd | Flex | 1 | 18 | 18 | 1 | 1 |
| flagd-ui | Flex | 1 | 3 | 3 | 1 | 1 |
| fraud-detection | Flex | 1 | 277 | 281 | 18 | 18 |
| frontend (own $0.88 a month) | Flex | 1 | 4,703 | 1,791 | 101 | 119 |
| frontend-proxy | Flex | 1 | 55 | 56 | 1 | 3 |
| image-provider | Flex | 1 | 41 | 42 | 1 | 2 |
| kafka | Flex | 1 | 3,916 | 3,973 | 16 | 264 |
| otel-collector | Flex | 1 | 9,022 | 9,155 | 218 | 610 |
| payment | Flex | 1 | 554 | 562 | 18 | 37 |
| product-catalog | Flex | 1 | 6 | 6 | 1 | 1 |
| quote | Flex | 1 | 276 | 280 | 18 | 18 |
| recommendation | Flex | 1 | 402 | 407 | 27 | 27 |
| shipping | Flex | 1 | 862 | 874 | 18 | 58 |
| telemetry-docs | Flex | 1 | 634 | 644 | 42 | 42 |
| valkey-cart | Flex | 1 | 57 | 57 | 1 | 3 |
| `*` (any other service) | Flex | 1 | | 407 | 18 | 27 |

Limits and totals are events per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window.
