# Elasticsearch store, four ways

Elasticsearch stores logs in less space with logsdb index mode and the `pattern_text` field type, which keeps each message as a template plus its arguments. 10x stores each repeated format string once, as a template, and ships each event as a reference to it plus the values that change. On one Elasticsearch 9.5.5 node with the published OpenTelemetry demo capture, logsdb with `pattern_text`, sorted on its template id, took the least store, 34.7% of a raw index. Compact on logsdb took 53.7% more than that, and 27.2% more when sorted the same way on its own template id.

Per field, the sorted compact index stores about as much message text as `pattern_text` does. The compact form adds the inverted index over the encoded message, with a term for every variable value, including the container, pod and image ids. The `pattern_text` index keeps those values as keyword doc values.

## Primary store of each index

Each figure is the primary store after a force merge to one segment, averaged over two repetitions.

| Index | Index mode | Store | Share of raw | Share of logsdb |
|---|---|---:|---:|---:|
| Raw | standard | 20,107,900 B | 100% | 167.6% |
| Logsdb | logsdb | 12,000,374 B | 59.7% | 100% |
| Logsdb, pattern_text | logsdb, sorted on template id | 6,974,760 B | 34.7% | 58.1% |
| Compact | standard | 14,905,394 B | 74.1% | 124.2% |
| Compact on logsdb | logsdb | 10,720,088 B | 53.3% | 89.3% |
| Compact on logsdb, sorted | logsdb, sorted on template id | 8,874,049 B | 44.1% | 73.9% |

Compact on logsdb is smaller than both raw and logsdb, but in standard mode the compact index is 24.2% larger than logsdb. Every compact figure includes the template dictionary index, 537,262 B in the first repetition.

- With only `index.logsdb.default_sort_on_message_template` set, on documents without a host.name field, segments were sorted on @timestamp alone and the `pattern_text` index took 10,649,904 B ([results-setting-only/](results-setting-only/)). The table sets `index.sort.field` instead, as Elastic's "Custom sorting" example does.

## How the store was read

The sample is the published [OpenTelemetry demo capture](https://github.com/log-10x/config/releases/tag/otel-sample-v1), 215,039,161 B in 197,430 JSON lines as Fluentd ships them. The native indexes store the parsed record, one document per line, and the compact indexes one document per event (157,228, multi-line events folded into one) plus 3,030 templates. The compact form decoded to the sample byte for byte. Each index had one primary shard and best_compression, and its primary store came from the index stats API. Repetitions differed by at most 0.07%, and all 66 checks in [results/results.md](results/results.md) pass.

## Limits

- Query cost, ingest cost and Elastic Cloud pricing were not measured.
- Search-time decoding was not tested, because its plugin is built for Elasticsearch 8.17.0.
- The compact form carries the metadata inside each event, and metadata kept as fields was not measured.
- Every index ran with Elastic's paid features on. On the free basic license, a `pattern_text` index came back with templating off and stored source, which was not measured.

## Run it

```
cd elastic-store-four-ways
./run.sh report   # re-render results/results.md from the committed results/
./run.sh          # full run: encode, decode check, six variants twice, report
```

The report needs Python 3. A full run also needs Docker, curl, about 2 GB of memory and 3 GB of free disk, and takes about 10 minutes.

The full record, with each repetition, the license probe and the compact form's hashes, is in [RECORD.md](RECORD.md), and the plan written before the run in [METHOD.md](METHOD.md).
