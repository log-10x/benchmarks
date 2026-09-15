
## Variant `resource`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 25 |
| carrying no attribute at all | 30 |
| carrying `routeState` | 25 |
| carrying `tenx_hash` | 25 |
| carrying `message_pattern` | 25 |
| `timeUnixNano` set | 30 |
| `timeUnixNano` zero or absent | 25 |
| `observedTimeUnixNano` set | 55 |
| a resource attribute present | 15 |
| `service.name` as a log attribute | 10 |

Attribute names nothing configured:

| Name | Records | Shift of the drop range that produces it |
|---|---:|---:|
| `_keys` | 2 | 16 |
| `_teys` | 2 | 18 |
| `ttenx_resource_keys` | 1 | 3 |
| `taenx_resource_keys` | 1 | 4 |
| `tagnx_resource_keys` | 1 | 5 |
| `_tens` | 1 | 20 |
| `_tenx` | 1 | 21 |

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 1 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 2 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 3 | 3 | yes | parsed, key `ttenx_resource_keys` | 12 |
| 4 | 4 | yes | parsed, key `taenx_resource_keys` | 12 |
| 5 | 5 | yes | parsed, key `tagnx_resource_keys` | 12 |
| 6 | 6 | yes | not parsed, whole record in the body | 0 |
| 7 | 7 | yes | not parsed, whole record in the body | 0 |
| 8 | 8 | yes | not parsed, whole record in the body | 0 |
| 9 | 9 | yes | not parsed, whole record in the body | 0 |
| 10 | 10 | yes | not parsed, whole record in the body | 0 |
| 11 | 11 | yes | not parsed, whole record in the body | 0 |
| 12 | 12 | yes | not parsed, whole record in the body | 0 |
| 13 | 13 | yes | not parsed, whole record in the body | 0 |
| 14 | 14 | yes | not parsed, whole record in the body | 0 |
| 15 | 15 | yes | not parsed, whole record in the body | 0 |
| 16 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 17 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 18 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 19 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 20 | 20 | yes | parsed, key `_tens` | 12 |
| 21 | 21 | yes | parsed, key `_tenx` | 12 |
| 22 | 22 | yes | not parsed, whole record in the body | 0 |
| 23 | 23 | yes | not parsed, whole record in the body | 0 |
| 24 | 24 | yes | not parsed, whole record in the body | 0 |
| 25 | 25 | yes | not parsed, whole record in the body | 0 |
| 26 | 26 | yes | not parsed, whole record in the body | 0 |
| 27 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 28 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 29 | 29 | yes | not parsed, whole record in the body | 0 |
| 30 | 30 | yes | not parsed, whole record in the body | 0 |
| 31 | 31 | yes | not parsed, whole record in the body | 0 |
| 32 | 32 | yes | not parsed, whole record in the body | 0 |
| 33 | 33 | yes | not parsed, whole record in the body | 0 |
| 34 | 34 | yes | not parsed, whole record in the body | 0 |
| 35 | 35 | yes | not parsed, whole record in the body | 0 |
| 36 | 36 | yes | not parsed, whole record in the body | 0 |
| 37 | 37 | yes | not parsed, whole record in the body | 0 |
| 38 | not distinguishable | yes | parsed, damage inside the `_tenx_` markers the appender strips | 11 |
| 39 | 39 | yes | not parsed, whole record in the body | 0 |
| 40 | 40 | yes | not parsed, whole record in the body | 0 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 0 | 1789439384004741834 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\` |
| CASE_D | 30 | 0 | 1789439384004798284 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_D \"f0\" \"f1\" \"f2\" \"f3\" \"f4\` |
| CASE_E | 1 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |


## Variant `noresource`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 35 |
| carrying no attribute at all | 20 |
| carrying `routeState` | 35 |
| carrying `tenx_hash` | 35 |
| carrying `message_pattern` | 35 |
| `timeUnixNano` set | 29 |
| `timeUnixNano` zero or absent | 26 |
| `observedTimeUnixNano` set | 47 |
| a resource attribute present | 0 |
| `service.name` as a log attribute | 0 |

Attribute names nothing configured:

| Name | Records | Shift of the drop range that produces it |
|---|---:|---:|
| `d_time` | 2 | 30 |
| `ttenx_time` | 1 | 3 |
| `taenx_time` | 1 | 4 |
| `tagnx_time` | 1 | 5 |
| `_t_tenx_observed_time` | 1 | 17 |
| `_tetenx_observed_time` | 1 | 18 |
| `_tenenx_observed_time` | 1 | 19 |
| `_tenxnx_observed_time` | 1 | 20 |
| `__time` | 1 | 31 |
| `_ttime` | 1 | 32 |
| `_teime` | 1 | 33 |
| `_tenme` | 1 | 34 |
| `_tenxe` | 1 | 35 |

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 1 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 2 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 3 | 3 | yes | parsed, key `ttenx_time` | 11 |
| 4 | 4 | yes | parsed, key `taenx_time` | 11 |
| 5 | 5 | yes | parsed, key `tagnx_time` | 11 |
| 6 | 6 | yes | not parsed, whole record in the body | 0 |
| 7 | 7 | yes | not parsed, whole record in the body | 0 |
| 8 | 8 | yes | not parsed, whole record in the body | 0 |
| 9 | 9 | yes | not parsed, whole record in the body | 0 |
| 10 | 10 | yes | not parsed, whole record in the body | 0 |
| 11 | 11 | yes | not parsed, whole record in the body | 0 |
| 12 | 12 to 13 | yes | not parsed, whole record in the body | 0 |
| 13 | 12 to 13 | yes | not parsed, whole record in the body | 0 |
| 14 | 14 | yes | not parsed, whole record in the body | 0 |
| 15 | 15 | yes | not parsed, whole record in the body | 0 |
| 16 | 16 | yes | not parsed, whole record in the body | 0 |
| 17 | 17 | yes | parsed, key `_t_tenx_observed_time` | 11 |
| 18 | 18 | yes | parsed, key `_tetenx_observed_time` | 11 |
| 19 | 19 | yes | parsed, key `_tenenx_observed_time` | 11 |
| 20 | 20 | yes | parsed, key `_tenxnx_observed_time` | 11 |
| 21 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 22 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 23 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 24 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 25 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 26 | 26 | yes | not parsed, whole record in the body | 0 |
| 27 | 27 | yes | not parsed, whole record in the body | 0 |
| 28 | 28 | yes | not parsed, whole record in the body | 0 |
| 29 | 29 | yes | not parsed, whole record in the body | 0 |
| 30 | 30 | yes | parsed, key `d_time` | 11 |
| 31 | 31 | yes | parsed, key `__time` | 11 |
| 32 | 32 | yes | parsed, key `_ttime` | 11 |
| 33 | 33 | yes | parsed, key `_teime` | 11 |
| 34 | 34 | yes | parsed, key `_tenme` | 11 |
| 35 | 35 | yes | parsed, key `_tenxe` | 11 |
| 36 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 37 | 37 | yes | not parsed, whole record in the body | 0 |
| 38 | none | no | not parsed, whole record in the body | 0 |
| 39 | none | no | not parsed, whole record in the body | 0 |
| 40 | none | no | not parsed, whole record in the body | 0 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 0 | 1789439415629420099 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\` |
| CASE_D | 30 | 11 | absent | `d_time` | `[2025-10-01 20:34:05,556] INFO CASE_D "f0" "f1" "f2" "f3" "f4" "f5" "f6" "f7" "f` |
| CASE_E | 1 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |


## Variant `nodrop`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 55 |
| carrying no attribute at all | 0 |
| carrying `routeState` | 55 |
| carrying `tenx_hash` | 55 |
| carrying `message_pattern` | 55 |
| `timeUnixNano` set | 0 |
| `timeUnixNano` zero or absent | 55 |
| `observedTimeUnixNano` set | 55 |
| a resource attribute present | 55 |
| `service.name` as a log attribute | 0 |

No attribute name outside the configured set.

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 1 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 2 | not distinguishable | yes | parsed, nothing visibly wrong | 10 |
| 3 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 4 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 5 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 6 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 7 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 8 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 9 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 10 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 11 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 12 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 13 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 14 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 15 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 16 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 17 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 18 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 19 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 20 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 21 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 22 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 23 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 24 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 25 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 26 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 27 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 28 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 29 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 30 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 31 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 32 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 33 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 34 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 35 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 36 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 37 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 38 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 39 | not distinguishable | no | parsed, nothing visibly wrong | 10 |
| 40 | not distinguishable | no | parsed, nothing visibly wrong | 10 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_C keys "a" "b" "c" "d" "e" settled.` |
| CASE_D | 30 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_D "f0" "f1" "f2" "f3" "f4" "f5" "f6" "f7" "f` |
| CASE_E | 1 | 10 | absent | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | absent | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |


## Variant `withtime`

Records returned: **55**.

| Measure | Records |
|---|---:|
| carrying attributes | 25 |
| carrying no attribute at all | 30 |
| carrying `routeState` | 25 |
| carrying `tenx_hash` | 25 |
| carrying `message_pattern` | 25 |
| `timeUnixNano` set | 55 |
| `timeUnixNano` zero or absent | 0 |
| `observedTimeUnixNano` set | 55 |
| a resource attribute present | 15 |
| `service.name` as a log attribute | 10 |

Attribute names nothing configured:

| Name | Records | Shift of the drop range that produces it |
|---|---:|---:|
| `_keys` | 2 | 16 |
| `_teys` | 2 | 18 |
| `ttenx_resource_keys` | 1 | 3 |
| `taenx_resource_keys` | 1 | 4 |
| `tagnx_resource_keys` | 1 | 5 |
| `_tens` | 1 | 20 |
| `_tenx` | 1 | 21 |

Escape count against the shift of the drop range:

| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |
|---:|---:|---|---|---:|
| 0 | 0 to 2 | yes | parsed, nothing visibly wrong | 10 |
| 1 | 0 to 2 | yes | parsed, nothing visibly wrong | 10 |
| 2 | 0 to 2 | yes | parsed, nothing visibly wrong | 10 |
| 3 | 3 | yes | parsed, key `ttenx_resource_keys` | 12 |
| 4 | 4 | yes | parsed, key `taenx_resource_keys` | 12 |
| 5 | 5 | yes | parsed, key `tagnx_resource_keys` | 12 |
| 6 | 6 | yes | not parsed, whole record in the body | 0 |
| 7 | 7 | yes | not parsed, whole record in the body | 0 |
| 8 | 8 | yes | not parsed, whole record in the body | 0 |
| 9 | 9 | yes | not parsed, whole record in the body | 0 |
| 10 | 10 | yes | not parsed, whole record in the body | 0 |
| 11 | 11 | yes | not parsed, whole record in the body | 0 |
| 12 | 12 | yes | not parsed, whole record in the body | 0 |
| 13 | 13 | yes | not parsed, whole record in the body | 0 |
| 14 | 14 | yes | not parsed, whole record in the body | 0 |
| 15 | 15 | yes | not parsed, whole record in the body | 0 |
| 16 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 17 | 16 to 17 | yes | parsed, key `_keys` | 12 |
| 18 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 19 | 18 to 19 | yes | parsed, key `_teys` | 12 |
| 20 | 20 | yes | parsed, key `_tens` | 12 |
| 21 | 21 | yes | parsed, key `_tenx` | 12 |
| 22 | 22 | yes | not parsed, whole record in the body | 0 |
| 23 | 23 | yes | not parsed, whole record in the body | 0 |
| 24 | 24 | yes | not parsed, whole record in the body | 0 |
| 25 | 25 | yes | not parsed, whole record in the body | 0 |
| 26 | 26 | yes | not parsed, whole record in the body | 0 |
| 27 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 28 | 27 to 28 | yes | not parsed, whole record in the body | 0 |
| 29 | 29 | yes | not parsed, whole record in the body | 0 |
| 30 | 30 | yes | not parsed, whole record in the body | 0 |
| 31 | 31 | yes | not parsed, whole record in the body | 0 |
| 32 | 32 | yes | not parsed, whole record in the body | 0 |
| 33 | 33 | yes | not parsed, whole record in the body | 0 |
| 34 | 34 | yes | not parsed, whole record in the body | 0 |
| 35 | 35 | yes | not parsed, whole record in the body | 0 |
| 36 | 36 | yes | not parsed, whole record in the body | 0 |
| 37 | 37 | yes | not parsed, whole record in the body | 0 |
| 38 | not distinguishable | yes | parsed, damage inside the `_tenx_` markers the appender strips | 11 |
| 39 | 39 | yes | not parsed, whole record in the body | 0 |
| 40 | 40 | yes | not parsed, whole record in the body | 0 |

The six shapes, and the escapes-elsewhere control:

| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |
|---|---:|---:|---|---|---|
| CASE_A | 0 | 10 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO CASE_A ProducerStateManager wrote a snapshot at o` |
| CASE_B | 2 | 10 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO CASE_B consumer group "alpha" rebalanced in 0 ms.` |
| CASE_C | 10 | 0 | 1789439478478160376 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\` |
| CASE_D | 30 | 0 | 1789439478478214984 | none | `{"body":"[2025-10-01 20:34:05,556] INFO CASE_D \"f0\" \"f1\" \"f2\" \"f3\" \"f4\` |
| CASE_E | 1 | 10 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO CASE_E\tcolumnar field separated by a tab.\n{"body"` |
| NOISE_00 | 0 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_00 plain message, no escapes.` |
| NOISE_03 | 3 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_03 plain message, no escapes.` |
| NOISE_04 | 4 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_04 plain message, no escapes.` |
| NOISE_05 | 5 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_05 plain message, no escapes.` |
| NOISE_06 | 6 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_06 plain message, no escapes.` |
| NOISE_10 | 10 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_10 plain message, no escapes.` |
| NOISE_16 | 16 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_16 plain message, no escapes.` |
| NOISE_20 | 20 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_20 plain message, no escapes.` |
| NOISE_30 | 30 | 11 | 1759350845556000000 | none | `[2025-10-01 20:34:05,556] INFO NOISE_30 plain message, no escapes.` |
