---
icon: simple/opentelemetry
---

Writes [TenXObject](https://doc.log10x.com/api/js/#TenXObject) instances and templates to an OpenTelemetry Collector (or any OTLP-compatible receiver) over [OTLP/gRPC](https://opentelemetry.io/docs/specs/otlp/). Each rendered event is parsed back into a JSON envelope and emitted as an OTLP `LogRecord`: the configured body field is lifted into `LogRecord.body`, every other top-level field becomes a log-record attribute.

For an example configuration, see the [OpenTelemetry Collector forwarder output](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/input/forwarder/otel-collector/stream.yaml).
