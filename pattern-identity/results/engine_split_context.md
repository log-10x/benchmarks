# A template hash and the history before it

Written by `bench/engine_split_context.py`. The first probe record of `results/engine_split_raw.json` that both engine instances grouped into the same event and named with the same pattern hash, but gave different template hashes:

- trial 2, probe position 771, an event of 2 records, pattern `notify_retry_canceled_due_unrecoverable_error_after_attempts_SMTP_not_configured_check_your_grafana_ini_config_file_s_section`
- instance A (its half, then the probes): pattern hash `udYJnEDiCao`, template hash `-7m1gMJe0&&`
- instance B: pattern hash `udYJnEDiCao`, template hash `<+Ddt8HFAn`
- image: `log10x/pipeline-10x:1.1.142@sha256:22ae67148bd7f6cbdf171c1b8da1c9c6c801290d43488693dfd8527e27138d05`

The same event, at the end of shorter stretches of instance A's feed. Each input runs 2 times in a fresh container.

| input | records | pattern hash | template hash | records in the event |
|---|---:|---|---|---:|
| the event alone | 2 | `udYJnEDiCao` | `<+Ddt8HFAn` | 2 |
| the event alone | 2 | `udYJnEDiCao` | `<+Ddt8HFAn` | 2 |
| last 2,000 records of A's feed | 2,000 | `udYJnEDiCao` | `<+Ddt8HFAn` | 2 |
| last 2,000 records of A's feed | 2,000 | `udYJnEDiCao` | `<+Ddt8HFAn` | 2 |
| last 20,000 records of A's feed | 20,000 | `udYJnEDiCao` | `-7m1gMJe0&&` | 2 |
| last 20,000 records of A's feed | 20,000 | `udYJnEDiCao` | `-7m1gMJe0&&` | 2 |
| last 60,000 records of A's feed | 60,000 | `udYJnEDiCao` | `<+Ddt8HFAn` | 2 |
| last 60,000 records of A's feed | 60,000 | `udYJnEDiCao` | `<+Ddt8HFAn` | 2 |

Each input gave the same answer on every run: yes. Template hashes seen for this one event: `-7m1gMJe0&&`, `<+Ddt8HFAn`. Pattern hashes seen: `udYJnEDiCao`.
