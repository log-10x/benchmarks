# Elasticsearch store, four ways

On Elasticsearch 9.5.5, does the 10x engine's compact form take less index store than Elasticsearch's own log features? Against plain logsdb it does, but against logsdb with the message field mapped as `pattern_text` it does not. That native setup, sorted on its template id, took the least store of all. Compact on logsdb took 53.7% more, and 27.2% more with the same sort on its own template id.

Per-field disk usage shows why. The stored text in the sorted compact index is about the size of what `pattern_text` stores. The extra is an inverted index over the encoded message, with every variable value as a term, including the container, pod and image ids in each event. With `pattern_text` those values sit in keyword doc values.

## Result

Primary store after a force merge to one segment, as the mean of two repetitions:

| Variant | Index mode | Store | Of raw | Of logsdb |
|---|---|---:|---:|---:|
| Raw | standard | 20,107,900 B | 100.0% | 167.6% |
| Logsdb | logsdb | 12,000,374 B | 59.7% | 100.0% |
| Logsdb + pattern_text | logsdb, sorted on template id | 6,974,760 B | 34.7% | 58.1% |
| Compact | standard | 14,905,394 B | 74.1% | 124.2% |
| Compact on logsdb | logsdb | 10,720,088 B | 53.3% | 89.3% |
| Compact on logsdb, sorted | logsdb, sorted on template id | 8,874,049 B | 44.1% | 73.9% |

Compact on logsdb is smaller than raw and plain logsdb, and every compact variant is larger than `pattern_text`. The compact figures include the template dictionary index (537,262 B).

- The template sort took effect only when set with `index.sort.field`. With `index.logsdb.default_sort_on_message_template` alone, on documents with no host.name field, the segments were sorted on @timestamp only and the `pattern_text` index took 10,649,904 B ([results-setting-only/](results-setting-only/)).

## How it was measured

The sample is the published OpenTelemetry demo capture, 215,039,161 B in 197,430 JSON lines as Fluentd ships them. The native indexes store the parsed record, one document per line. The compact indexes store one document per event (157,228, with multi-line events folded into one) plus 3,030 templates. The compact form decoded back to the sample byte for byte.

Everything ran on one Elasticsearch 9.5.5 node in Docker on a trial license, with one shard and best_compression per index. The repetitions differed by at most 0.07%, and all 66 checks in [results/results.md](results/results.md) pass.

## Limits

- The test measures store on one sample and one node, and not query cost, ingest cost or Elastic Cloud pricing.
- Search-time decoding was not tested, because the decoding plugin is built for Elasticsearch 8.17.0, not 9.x.
- Every compact variant carries the metadata inside the encoded event. Keeping the metadata as separate fields was not measured.
- `pattern_text` is a subscription feature and was measured on a trial license. The basic license accepted it with templating off, and that case was not measured.

## Run it

```
cd elastic-store-four-ways
./run.sh report   # re-render results/results.md from the committed results/
./run.sh          # full run: encode, decode check, six variants twice, report
```

The report needs only Python 3. A full run also needs Docker, curl, about 2 GB of memory and 3 GB of free disk, and takes about 10 minutes.

[METHOD.md](METHOD.md) is the plan written before the run, and [RECORD.md](RECORD.md) is the full record with per-field bytes, the license probe and hashes.
