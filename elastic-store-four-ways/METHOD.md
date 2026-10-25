# Elasticsearch store, four ways: method (written before the run, 2026-10-25)

One question: on Elasticsearch 9.5.5, how much index store does the engine's compact form save over
(a) a raw index, (b) logsdb index mode and (c) logsdb with `message` mapped as `pattern_text`, on
the same sample?

The earlier figure this replaces as the Elastic comparison: on 8.17.0 the compact form (encoded
index plus template index, 13.8 MB) took 51.7% less store than a raw index holding each whole line
in one `message` text field (28.6 MB). That raw index had neither logsdb nor `pattern_text`;
`pattern_text`'s doc page marks it preview in 9.2 and generally available since 9.3.

## Sample

`otel-sample-200mb.log` from release `otel-sample-v1` of `log-10x/config` (byte-identical to the raw
asset of `otel-sample-v2`): 215,039,161 bytes, 197,430 lines, sha256
`aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432`. Container output of the
OpenTelemetry demo as Fluentd ships it: every line is a JSON record with the message under `log`
and `stream`, `docker.container_id`, `kubernetes.*` (16 label keys, one host) and `tenx_tag`
around it. The records carry no timestamp field.

## The compact form

Engine `ghcr.io/log-10x/edge-10x:1.1.150` by digest, in file mode, with the published round-trip
configs `../drain3-vs-log10x/tenx-encode.config.yaml` and `tenx-decode.config.yaml` unchanged
(the configs `otel-denominators/` and `loghub-compaction/` measure the compact form with). The
encode reads each whole line and writes `encoded.log` (one encoded event per line; multi-line
events become one) and `templates.json` (one template per line). Run twice; both outputs are
hashed and the two runs compared. The template dictionary followed by the encoded events is decoded
and compared with the sample byte for byte. The first run's output is what is indexed.

## Elasticsearch

One node, `docker.elastic.co/elasticsearch/elasticsearch:9.5.5` by digest, `discovery.type:
single-node`, security and ML off, heap 1 GB, container limit 2 GB, the disk allocation threshold
off (the measurement is not about watermarks). Before the trial, a logsdb index with a
`pattern_text` field is created on the default licence and the response recorded. Then
`POST /_license/start_trial?acknowledge=true`; the run stops unless `GET /_license` reads type
`trial`, status `active`.

Elastic's docs, read 2026-10-25:

- `pattern_text` (https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/pattern-text):
  "Elastic Stack: Generally available since 9.3"; "This feature requires a [subscription]";
  "The `pattern_text` field type is a variant of `text` with improved space efficiency for log
  data."; "The compression provided by `pattern_text` can be significantly improved if the index
  is sorted by the `template_id` field."; "This index sorting is not applied by default, but can
  be enabled for the `message` field of LogsDB indices (assuming it is of type `pattern_text`) by
  setting the index setting `index.logsdb.default_sort_on_message_template` to `true`. This will
  cause the index to be sorted by `host.name` (if present), then `message.template_id`, and
  finally by `@timestamp`."; the mapping in the doc's example is `"notice": { "type":
  "pattern_text" }`; `index_options` "Defaults to `docs`".
- Subscriptions (https://www.elastic.co/subscriptions): "Pattern text field type for logsdb
  indices" and "Synthetic _source" are ticked under Enterprise only.
- Start trial API: "Start a 30-day trial, which gives access to all subscription features."
- Logsdb (https://www.elastic.co/docs/manage-data/data-store/data-streams/logs-data-stream-configure):
  "If you have the required subscription, logsdb index mode uses synthetic `_source`"; "In logsdb
  index mode, indices are sorted by the fields `host.name` and `@timestamp` by default"; "By
  default, logsdb index mode uses the `best_compression` codec".

## The four variants

Every index: one primary shard, no replica, `index.codec: best_compression` set explicitly,
refresh off while loading, documents sent in file order in bulk requests of 2,000 with
generated `_id`s, from one client.

(a), (b) and (c) index the same document per line: the record as captured with `log` renamed
`message`, plus `@timestamp` (line i at 2025-10-02T00:00:00Z + i/7 s, the pace the Elastic rigs
replay this capture at). All three map every other string as `keyword` (`ignore_above: 1024`) by
one dynamic template. Each step changes one thing:

| | Index | Index settings beyond the common ones | `message` |
|---|---|---|---|
| (a) raw | `es4-raw` | none (standard mode) | `text` |
| (b) logsdb | `es4-logsdb` | `index.mode: logsdb` | `text` |
| (c) logsdb + `pattern_text` | `es4-pattern` | `index.mode: logsdb`, `index.logsdb.default_sort_on_message_template: true` | `pattern_text`, defaults |
| (d) compact | `es4-compact` + `es4-compact-dict` | none (standard mode) | the encoded event, `text` |

(d) is the shape the compact form was measured in on 8.17.0 and that the l1es plugin documents:
`es4-compact` holds one document per encoded event, `{"@timestamp", "message": <encoded line>,
"l1x_tid": <template hash>}`, mapped `text`, `keyword` (`dynamic: strict`), with `@timestamp`
spread over the same span as the lines'; `es4-compact-dict` holds the template dictionary as the
plugin's own `l1es_dml` index does, `_id` = template hash, `{"pattern": <template>}`, mapping
`{"dynamic": false, "properties": {"pattern": {"type": "text"}}}`. Its store is the two indexes
added together. The metadata is inside each encoded event, not in fields.

`run.sh` also knows `compact_logsdb` (the same documents in logsdb mode, same dictionary); it is not
in the default run.

## Measurement

Per repetition: delete and create the indexes, load all of them, `_refresh` and `_flush` each, wait
(up to 180 s) until every shard's retention leases have moved past its last operation (so a merge
keeps no `_recovery_source` for them), then per index `POST _forcemerge?max_num_segments=1`,
`_refresh`, and `GET _stats/store,docs` read twice 5 s apart; the second read's
`primaries.store.size_in_bytes` is the figure. Recorded beside it: segment count, the effective
index settings (`index.mode`, `index.codec`, `index.mapping.source.mode`, `index.sort.*`), the
mapping, and `_disk_usage?run_expensive_tasks=true` per field. Two repetitions; the figure is
their mean.

## Checks, fixed before the run

A failed check is reported in `results/results.md`, not hidden.

1. The trial licence is active.
2. Every index's document count equals its input: 197,430 for (a), (b) and (c); the encoded
   event count for `es4-compact`; the distinct template hashes for `es4-compact-dict`. The same
   in both repetitions.
3. One segment per index after the merge.
4. `best_compression` on every index.
5. On the logsdb indexes, `_disk_usage` shows no stored `_source` (synthetic source is on) and no
   stored `_recovery_source`.
6. The two encodes are byte-identical, and the compact form decodes to the sample byte for byte.
7. The two repetitions agree within 1% per variant.

## Reading, fixed before the run

The headline is (d)'s saving over (c), 1 - (d)/(c), on the mean of the repetitions, with its
savings over (a) and (b) beside it. Whether the native pair alone already takes 51.7% off a raw
index is (c)/(a): at or under 0.483 it does. The 8.17.0 raw index held each whole line in one
field and (a) here holds the parsed record, so the two raws are not the same index; both
figures are stated with that difference.

## Not claimed

Query or ingest cost; search-time decoding (the l1es plugin is built for 8.17.0, not 9.x); Elastic
Cloud Hosted pricing; replicas, several shards, data streams, routing on sort fields; `match_only_text`;
`logsdb_columnar` (preview in 9.5); `pattern_text` with `index_options: positions`; a compact form
of the message text alone with the metadata kept as fields.
