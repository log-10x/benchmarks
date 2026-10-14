## Fleet default

Quiet run 2026-10-14 12:54:22 to 2026-10-14 13:16:29 UTC, 5 full windows of 240 s, 7108 events, 15 containers, 48 (container, pattern) pairs, 197 cells.

| Cell statistic (bytes per pattern per container per 4-minute window) | Value |
|---|---|
| max | 123368 |
| p99 | 123362 |
| p90 | 24127 |
| median | 5316 |
| **cap = 2 x max** | **246736** |

Largest cells in the quiet run:

| container | pattern | window | events | bytes | sample |
|---|---|---|---|---|---|
| otel-collector | KG8Fq0QFuoY | 4 | 240 | 123368 | `2026-10-14T12:54:22.346Z	info	Logs	{"resource": {"service.instance.id": "fede5d45-b052-4f3` |
| otel-collector | KG8Fq0QFuoY | 1 | 240 | 123363 | `2026-10-14T12:54:22.346Z	info	Logs	{"resource": {"service.instance.id": "fede5d45-b052-4f3` |
| otel-collector | KG8Fq0QFuoY | 0 | 240 | 123362 | `2026-10-14T12:54:22.346Z	info	Logs	{"resource": {"service.instance.id": "fede5d45-b052-4f3` |
| otel-collector | Gl3Gtr_SH5w | 4 | 238 | 122156 | `2026-10-14T12:54:24.721Z	info	Traces	{"resource": {"service.instance.id": "fede5d45-b052-4` |
| otel-collector | Gl3Gtr_SH5w | 0 | 236 | 121135 | `2026-10-14T12:54:24.721Z	info	Traces	{"resource": {"service.instance.id": "fede5d45-b052-4` |
| otel-collector | Gl3Gtr_SH5w | 1 | 235 | 120602 | `2026-10-14T12:54:24.721Z	info	Traces	{"resource": {"service.instance.id": "fede5d45-b052-4` |
| otel-collector | Gl3Gtr_SH5w | 3 | 233 | 119561 | `2026-10-14T12:54:24.721Z	info	Traces	{"resource": {"service.instance.id": "fede5d45-b052-4` |
| otel-collector | KG8Fq0QFuoY | 2 | 230 | 118223 | `2026-10-14T12:54:22.346Z	info	Logs	{"resource": {"service.instance.id": "fede5d45-b052-4f3` |
| otel-collector | KG8Fq0QFuoY | 3 | 230 | 118222 | `2026-10-14T12:54:22.346Z	info	Logs	{"resource": {"service.instance.id": "fede5d45-b052-4f3` |
| otel-collector | Gl3Gtr_SH5w | 2 | 226 | 115951 | `2026-10-14T12:54:24.721Z	info	Traces	{"resource": {"service.instance.id": "fede5d45-b052-4` |

## Incidents

| # | flag | variant | on (UTC) | off (UTC) | container | first noisy minute | first held | noisy to held (min) | events held | events kept | bytes never sent | patterns held |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Held patterns per incident (samples)

## False holds (offload while no flag was active)

None.

## Delivery check (raw records received by Fluent Bit vs records returned by the Receiver)

| container | raw lines | returned records | lines covered | covered % |
|---|---|---|---|---|
| accounting | 237 | 131 | 233 | 98.31 |
| ad | 241 | 162 | 239 | 99.17 |
| astronomy-db | 590 | 517 | 589 | 99.83 |
| cart | 1638 | 817 | 1634 | 99.76 |
| currency | 1 | 1 | 1 | 100.0 |
| email | 214 | 116 | 213 | 99.53 |
| flagd | 36 | 35 | 35 | 97.22 |
| flagd-ui | 9 | 8 | 8 | 88.89 |
| fraud-detection | 98 | 90 | 96 | 97.96 |
| frontend | 1489 | 1477 | 1487 | 99.87 |
| frontend-proxy | 269 | 254 | 268 | 99.63 |
| image-provider | 82 | 81 | 81 | 98.78 |
| kafka | 5260 | 2859 | 5257 | 99.94 |
| otel-collector | 9901 | 7003 | 9895 | 99.94 |
| payment | 172 | 168 | 170 | 98.84 |
| product-catalog | 19 | 18 | 18 | 94.74 |
| quote | 85 | 82 | 82 | 96.47 |
| recommendation | 143 | 140 | 140 | 97.9 |
| shipping | 272 | 83 | 83 | 30.51 |
| telemetry-docs | 456 | 453 | 453 | 99.34 |
| valkey-cart | 39 | 38 | 38 | 97.44 |
