# Budget run: 2026-10-20T06:00:04.000Z

Standard held at $11 a month: $0.17 so far this month. Moved this month: 38,465 events to Flex, about $0 a month of Flex storage at $0.05 per million (Flex compute is unpriced and left out), $0.07 at the Standard rate.

- Standard indexing this month: $0.17 of $11 (99,500 events through 2026-10-20 06:00 UTC), 282 hours left.
- Lines that do not pass the Receiver, outside the services with their own number: 371 events in Standard this month, about $0 by the month's end at this rate. The Receiver's other services get the rest of $10.
- The Receiver's other services may send 20,571 events an hour to Standard against 23,661 now: each statement keeps up to 2,072 an hour, and the noisiest move to Flex first. A service the run has not seen gets the same level and the median service's 473 an hour until the next run, which takes any overshoot back from the rest of the month.
- Node counts from nodes_by_container in policy.yaml; 1 Receiver. The `*` row is divided by 1 node, the median known service's count. The division assumes a DaemonSet Receiver, one per node, each holding its node's share.
- frontend is held to its own $0.88 a month: $0.02 spent so far by Datadog's usage count for service:frontend, 1,791 events an hour for the rest of the month, a limit of 77 per statement and a total of 119 per window per node.

| Service | Destination | Nodes | Events an hour now | Kept an hour | Limit per statement | Total |
|---|---|---|---|---|---|---|
| accounting | Flex | 1 | 4 | 4 | 138 | 1 |
| ad | Flex | 1 | 545 | 545 | 138 | 36 |
| astronomy-db | Flex | 1 | 692 | 692 | 138 | 46 |
| cart | Flex | 1 | 3,410 | 3,410 | 138 | 227 |
| email | Flex | 1 | 473 | 473 | 138 | 31 |
| flagd | Flex | 1 | 18 | 18 | 138 | 1 |
| flagd-ui | Flex | 1 | 3 | 3 | 138 | 1 |
| fraud-detection | Flex | 1 | 298 | 298 | 138 | 19 |
| frontend (own $0.88 a month) | Flex | 1 | 6,590 | 1,791 | 77 | 119 |
| frontend-proxy | Flex | 1 | 55 | 55 | 138 | 3 |
| image-provider | Flex | 1 | 41 | 41 | 138 | 2 |
| kafka | Flex | 1 | 4,037 | 4,037 | 138 | 269 |
| otel-collector | Flex | 1 | 9,448 | 6,358 | 138 | 423 |
| payment | Flex | 1 | 1,933 | 1,933 | 138 | 128 |
| product-catalog | Flex | 1 | 1 | 1 | 138 | 1 |
| quote | Flex | 1 | 364 | 364 | 138 | 24 |
| recommendation | Flex | 1 | 549 | 549 | 138 | 36 |
| shipping | Flex | 1 | 1,063 | 1,063 | 138 | 70 |
| telemetry-docs | Flex | 1 | 665 | 665 | 138 | 44 |
| valkey-cart | Flex | 1 | 61 | 61 | 138 | 4 |
| `*` (any other service) | Flex | 1 | | 473 | 138 | 31 |

Limits and totals are events per 4-minute window per node. Error lines pass 50 over a limit per statement per node per window.
