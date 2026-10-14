---
icon: material/language-javascript
---

The [JavaScript API](https://doc.log10x.com/api/js/) controls initialization, enrichment, filtering, and serialization of TenXObjects.

Custom code executes in these contexts:


| Context                                                       | Description                                                                                                                                    | Example                                                                                                                 |
|---------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [Input](https://doc.log10x.com/run/transform/script/input/)    | Validate launch arguments and initialize text/GeoIP lookups                                                                                    | [HttpInput](https://github.com/log-10x/config/blob/main/pipelines/run/config/transform/script/http.js#L9)                |
| [Object](https://doc.log10x.com/run/transform/script/object)   | Enrich TenXObjects, update counters/dictionaries, filter unnecessary instances                                                                   | [HttpObject](https://github.com/log-10x/config/blob/main/pipelines/run/config/transform/script/http.js#L30)              |
| [Summary](https://doc.log10x.com/run/transform/script/summary) | Enrich TenXSummaries produced by an [aggregator](https://doc.log10x.com/run/aggregate) using text/GeoIP lookups, counters and dictionaries       | [HttpSummary](https://github.com/log-10x/config/blob/main/pipelines/run/config/transform/script/http.js#L50)             |
| [Unit](https://doc.log10x.com/run/transform/script/unit)       | Initialize pipeline units at startup via `constructor()` and perform cleanup at shutdown via `close()`                                          | [SymbolLoader](https://github.com/log-10x/modules/blob/main/apps/shared/console/symbolLoader.js)                        |
| [Receiver](https://doc.log10x.com/run/output/receive)        | Filter 'noisy' telemetry via per-node budget sampling or a declarative field-set mute file to prevent over-billing.                      | [Rate](https://github.com/log-10x/config/blob/main/pipelines/run/receive/rate/rate-object-global.js)                         |
| [Output](https://doc.log10x.com/run/output/stream)             | Customize encoding of TenXObjects/Summaries to stream (e.g., stdout) and time-series (e.g., Prometheus) outputs.                                | [Fluent Bit](https://github.com/log-10x/config/blob/main/pipelines/run/config/output/event/process/config.yaml#L63)   |
| [Log4j](https://doc.log10x.com/run/output/event/process)      | Customize encoding of TenXObjects to log4j [appenders](https://logging.apache.org/log4j/2.x/manual/appenders.html).                             | [Filebeat](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/input/forwarder/filebeat/log4j2.yaml) |
