---
icon: simple/fluentbit
---

Defines a Fluent Bit process that spawns and writes [TenXObject](https://doc.log10x.com/api/js/#TenXObject) instances and template field values.

This output integrates a lightweight, customizable [Fluent Bit](https://fluentbit.io/) pipeline for shipping processed events to destinations such as [Datadog](https://docs.fluentbit.io/manual/pipeline/outputs/datadog), [Splunk](https://docs.fluentbit.io/manual/pipeline/outputs/splunk), [Elasticsearch](https://docs.fluentbit.io/manual/pipeline/outputs/elasticsearch), and [CloudWatch](https://docs.fluentbit.io/manual/pipeline/outputs/cloudwatch).

**Use cases:**

- **[Lambda launcher](https://doc.log10x.com/engine/launcher/lambda/)**: Ships optimized CloudWatch Logs events to analytics platforms. The Python handler pipes expanded events to the 10x Engine via stdin; Fluent Bit handles output shipping to the configured destination.
- **[Retriever](https://doc.log10x.com/apps/retriever/#query)**: Ships query results from cloud storage (e.g., S3) to log analyzers and time-series databases.

