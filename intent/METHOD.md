# How the labels were made

Every event of two captures of the OpenTelemetry demo carries a label: the
source statement that wrote it, located in that program's own source at the
version that ran. The labels come from source code alone. No tool's pattern
names were read until the labels were validated and frozen (2026-10-05 16:43
UTC); the freeze record is `labels/FROZEN.json`.

## The captures

| capture | what it is | records | events | demo version | forwarder |
|---|---|---:|---:|---|---|
| `otel215` | 215 MB of Kubernetes container output from a cluster running the OpenTelemetry demo, as Fluentd shipped it. Public: [`otel-sample-v1`](https://github.com/log-10x/config/releases/tag/otel-sample-v1), `otel-sample-200mb.log.gz`. The same file the [pattern-identity](../pattern-identity) and [otel-denominators](../otel-denominators) benchmarks use. | 197,430 | 157,228 | 2.1.3 | Fluentd |
| `rec1155` | A two-hour recording (2026-08-08) of a cluster running the unmodified public demo images, as Fluent Bit shipped it. Public: [`intent-data-v1`](https://github.com/log-10x/benchmarks/releases/tag/intent-data-v1), `rec1155.log.gz`. | 41,713 | 41,573 | 2.2.0 | Fluent Bit |

Each record is one Docker JSON line: the program's output in `log`, plus the
container metadata. The recording was published as captured, except that a
`tenx_hash` key added by a sidecar was removed and a `tenx_tag` key (the
Kubernetes log file name, as Fluentd writes it) was added, so both captures
carry the same keys.

An **event** is one record, or a run of records the engine groups into one
event: a stack trace, or the .NET console logger's header line followed by its
message line. `labels/labels_<capture>.jsonl.gz` records how many records each
event spans (`records`), so the capture can be cut into the same events without
running the engine. `bench/score.py` checks that a tool's events are exactly
these, by text hash, before scoring anything.

## How a label is made

1. **Key line.** The first non-blank line of the event's `log` text, with two
   exceptions that keep one call together: the .NET console header
   (`info: Category[0]`) is joined with the message line under it, and a Node
   `util.inspect` dump of an OpenTelemetry log record is keyed by its `body`.
2. **Shape.** The key line with timestamps, UUIDs, IP addresses, hex, product
   ids, numbers and quoted values masked (JSON keys, logfmt `msg` and klog
   messages kept). The shape is in the labels file for anyone auditing a label.
3. **Statement.** Each statement is a repository, a ref and a path, plus a
   needle: a literal substring of the source line. The line number is found by
   searching the fetched file for the needle, never typed by hand. Each
   statement has a match rule over the key line, applied per container. An
   event that matches two statements is a conflict; there are none.
4. **Where the constant text lives.** When a call logs a constant or a helper's
   result defined elsewhere, the label points at the literal, and the
   statement's note names the call site. Examples:
   - `component.go:159` (logged by `builders/extension.go:50`);
   - `KafkaBroker.scala:71` (by `KafkaRaftServer.scala:101`);
   - opentelemetry-go `exporter.go:80` (printed by the default error handler in `internal/global/handler.go`).

   For a call written over several lines, the line is the one holding the format literal.
5. **Checked against printed locations.** Where a program prints its own
   source location, the located line was compared with it:
   - the collector's zap caller: 33 statements agree within one line;
   - Python `[file.py:lineno]`: every product-reviews, recommendation, httpx and opentelemetry-api statement agrees, and the printed lines pin the library versions;
   - klog: all 26 kube-proxy statements agree with v1.32.6.
6. **Validation.** Every labelled code event was checked two ways: the
   statement's constant fragments appear in order in the raw key line, and in
   the masked key line. Result: 0 failures for rec1155's 40,488 code events and
   for otel215's 153,882. Every pseudo-statement event (below) was checked
   against its structural rule, with 0 failures.

   During labelling the check caught three real errors, all fixed before the freeze:
   - C length modifiers (`%zu`) were not split, affecting 143 valkey events;
   - a generated kube-proxy rule picked a value literal, affecting 3 events;
   - a postgres-receiver format had its URL inlined.

## Versions

Versions come from what the programs print or pin:

| Program | rec1155 | otel215 | How the version is known |
|---|---|---|---|
| OpenTelemetry demo | 2.2.0 | 2.1.3 | |
| Collector contrib | 0.142.0 | 0.135.0 | |
| Kafka | 3.9.1 | 3.9.1 | the broker's printed commit is the tag |
| Valkey | 9.0.1 | 8.1.3 | |
| Grafana | | v12.1.1 | the binary's commit is the tag |
| fluentd, with fluent-plugin-kubernetes_metadata_filter 3.5.1 | | 1.17.1 | the startup gem list |
| OpenSearch, plugins 3.2.0.0 | | 3.2.0 | |
| Kubernetes | | v1.32.6 | |
| OpenTelemetry Java agent | 2.23.0 | 2.20.1 | |
| ZooKeeper | 3.8.4 | 3.8.4 | |
| librdkafka | 2.12.0 | 2.12.0 | |
| httpx | 0.28.1 | 0.28.1 | printed locations (step 5) |
| opentelemetry-api | 1.39.1 / 1.37.0 | 1.39.1 / 1.37.0 | printed locations (step 5) |
| opentelemetry-go otlpmetrichttp | | v1.37.0 | inferred, not printed: required by the collector's `go.mod` at v0.135.0 |

## Coverage and what is excluded

The target was 95% of events per capture, labelling containers in descending
volume. Labelling then continued through every container with at least 250
events.

| capture | events | labelled | unlabelled, excluded from every score | statements | code / pseudo |
|---|---:|---:|---:|---:|---|
| rec1155 | 41,573 | 41,333 (99.42%) | 240 (0.58%) | 213 | 207 / 6 |
| otel215 | 157,228 | 156,563 (99.58%) | 665 (0.42%) | 299 | 289 / 10 |

Unlabelled events, by container:
- **rec1155:** frontend-proxy 115, postgresql 83, flagd 14, image-provider 9, flagd-ui 5, init-config 2, and single events in cart, accounting and email.
- **otel215:** prometheus-server 152, frontend-proxy 114, opensearch 102 (single events outside its 20 labelled statements), jaeger 87, coredns 43, metrics-server 35, Grafana sidecars 34, postgresql 33, init-config 14, and 13 smaller containers.

Labelled events and statements, by container:
- **rec1155:**
  - opentelemetry-collector 19,068 (8 statements)
  - kafka 6,226 (140)
  - product-reviews 4,931 (14)
  - cart 3,755 (6)
  - llm 2,477 (9)
  - ad 1,240 (7)
  - accounting 948 (4)
  - payment 781 (3)
  - recommendation 604 (3)
  - fraud-detection 393 (3)
  - quote 392 (2)
  - email 391 (1)
  - valkey-cart 126 (15)
  - frontend 1
- **otel215:**
  - opentelemetry-collector 89,739 (34 statements)
  - kafka 29,039 (92)
  - cart 19,639 (3)
  - ad 7,114 (7)
  - recommendation 3,432 (3)
  - grafana 2,474 (77)
  - frontend 2,317 (3)
  - fluentd-10x 1,427 (17)
  - valkey-cart 607 (12)
  - opensearch 414 (20)
  - kube-proxy 287 (26)
  - accounting 69 (3)
  - fraud-detection 3
  - payment 1
  - quote 1

## Pseudo statements

Some events hold no single statement's text. They carry a pseudo statement,
`<container>:<kind>`:
- `email:access_log`, `llm:access_log`
- `frontend:stack_frame`, `frontend:object_body`, `frontend:banner`
- `kafka:object_body`, `kafka:other`
- `ad:other`, `fraud-detection:other`
- `fluentd-10x:object_body`, `fluentd-10x:other`
- `opensearch:other`

They count in grouping scores, not in attribution or name scores.

## Notes by container

- **opentelemetry-collector.**
  - The debug exporter's `Traces`, `Logs` and `Metrics` lines (core `exporter/debugexporter/exporter.go`) are 19,054 events in rec1155 and 85,739 in otel215. Every other collector line is a zap line with its caller.
  - `failed to upload metrics` is printed by the default OpenTelemetry Go error handler, with its text in opentelemetry-go `otlpmetrichttp/exporter.go:80`.
  - grpc-go's `[core] [Channel #n SubChannel #m]` prefix comes from grpclog, not the statement.
- **kafka.**
  - Shapes were assigned against an index of the 3,364 log calls in the 3.9.1 sources. A shape goes to the call whose format, read as a pattern, fully matches the message, preferring files that declare the logger class. Every assignment was reviewed against its logger class.
  - The thread lifecycle lines (`Starting`, `Stopped`, `Shutting down`, `Shutdown completed`) are `ShutdownableThread.java`, logged under each subclass's name: one statement each.
  - `Rolled new log segment` is `LocalLog.scala:524`; the identical line 488 runs only after a `Trying to roll` warning that never occurs.
  - In otel215 the `KafkaConfig values:` dump arrives as about 250 one-line events: `kafka:object_body`.
- **Demo services.**
  - Python services print `[file:lineno]`, and every line matches.
  - Cart: the .NET console logger writes `info: cart.cartstore.ValkeyCartStore[0]` and the message as two lines, one record in rec1155 and two records grouped into one event in otel215. The label is the call identified by the message line.
  - Payment: each event is a `util.inspect` dump of an OpenTelemetry log record, labelled by the `logger.info` call its `body` identifies.
  - Quote echoes its own request line (`index.php:78`), so it is code.
  - Email and llm request lines are access logs.
- **grafana.**
  - Each `msg` literal was found in the v12.1.1 sources. Duplicates were resolved by the logger name the package creates, as with `Update check succeeded` for the plugin and grafana update checkers.
  - The migrator's statements are logged under both `migrator` and `resource-migrator`: one statement each.
  - Outside Grafana's own tree: `Notify for alerts failed` (grafana/prometheus-alertmanager), `Adding GroupVersion` (k8s.io/apiserver v0.33.2), and the `GF_INSTALL_PLUGINS` echo in `packaging/docker/run.sh`.
- **fluentd-10x.**
  - fluentd 1.17.1 core and the kubernetes_metadata_filter plugin.
  - Configuration lines that arrive one per event are `fluentd-10x:object_body`.
  - The `tenx-stdout:` records come from an `out_stdout` match in the pipeline configuration: `fluentd-10x:other`.
- **valkey-cart.** `server.c`, `rdb.c` and `childinfo.c`. `DB saved on disk` is one statement printed by both the child and the parent.
- **opensearch.** The 20 statements covering 80% of its events: core `PluginsService` and `MetadataMappingService`, job-scheduler, sql, anomaly-detection and security-analytics.
- **kube-proxy.** Rules keyed on the printed `file.go:line`, resolved against v1.32.6. `flags.go:64` (`FLAG: --%s=%q`) is one statement over 59 lines.

**One statement, several shapes (word values):**
- product review lines, one shape per review;
- `Targeted ad request received for [category]`;
- Kafka `Deleted {} {}.` (`log`, `offset index`, `time index`);
- the thread lifecycle lines;
- llm summaries;
- Grafana migration ids;
- `FLAG:` lines;
- OpenSearch `loaded module [x]`;
- fluentd `gem 'x' version 'y'`.

**One shape, two statements (told apart by other text):**
- Grafana `Update check succeeded` and `Installing plugin`, by logger name;
- payment bodies;
- the cart message lines under one header.

## The library column

`statements.tsv` column `library_1_1_89` names the entry of the default symbol
library (the 1.1.89 library, shipped inside engine images 1.1.132 and
1.1.133) that lists the statement's repository, or the image that runs it.
- **Listed:** the OpenTelemetry demo, Kafka (trunk), the collector and contrib, httpx, grpc-go, and the Valkey 9.0.1 image.
- **Not listed:** Grafana, fluentd, OpenSearch, Kubernetes, librdkafka, ZooKeeper, opentelemetry-go, opentelemetry-python and the Java agent.

A listed repository was compiled at its own pin, which can differ from the
version that ran. The column says the source was available to the engine; it
does not check that the statement's text is unchanged at that pin.

## Files

- `labels/labels_<capture>.jsonl.gz`: one line per event, with `i`, `records`, `container`, `statement` (empty when unlabelled), `multiline` and `shape`.
- `labels/statements.tsv`: the 423 statement ids across both captures, with repository, ref, path, line, format, kind, per-capture event counts, `library_1_1_89` and notes.
- `labels/texthash_<capture>.txt.gz`: the first 16 hex digits of the SHA-1 of each event's text, for the alignment check.
- `labels/repo_basenames.json.gz`: the file names in each statement's repository at its ref, for the attribution score.
- `labels/FROZEN.json`: hashes of the published label files.
