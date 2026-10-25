| case | lines_sent | records | lines_returned | cross_container_records | lines_in_cross_container_records | lines_missing | lines_duplicated | trace_events | trace_events_whole | cross by pause (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| a | 4428 | 1554 | 4428 | 512 | 3386 | 0 | 0 | 512 | 0 | {"0": 500, "1": 2, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2} |
| b | 3072 | 1036 | 3072 | 509 | 2545 | 0 | 0 | 0 | 0 | {"0": 500, "1": 2, "2": 2, "3": 2, "4": 2, "5": 1} |
| c | 6602 | 1024 | 6602 | 512 | 5066 | 0 | 0 | 1024 | 0 | {"0": 500, "1": 2, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2} |
| d | 3781 | 1027 | 3781 | 0 | 0 | 0 | 0 | 512 | 509 | {} |
| e | 4674 | 1194 | 4674 | 0 | 0 | 0 | 0 | 511 | 508 | {} |
| total | 22557 | 5836 | 22557 | 1533 | 10997 | 0 | 0 | 2559 | 1017 | |
{"verdict": "FAIL", "records_in_returned_file": 5836, "fluent_bit_in_records": 22557, "records_without_sent_line": 0, "records_without_log": 1, "nonblank_lines_without_token": 0}
