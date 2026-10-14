---
icon: material/waves-arrow-right
---

Defines output destinations for [TenXObjects](https://doc.log10x.com/api/js/#TenXObject), specifying location and [compact](https://doc.log10x.com/run/transform/#compact) format. Pipelines support multiple streams.

### :octicons-package-dependents-24: Extensions

Most users work with [output modules](https://doc.log10x.com/engine/module/) rather than raw streams. Modules provide higher-level constructs for serialization via Java [streams](https://www.baeldung.com/java-outputstream) and log4j2 [appenders](https://logging.apache.org/log4j/2.x/manual/appenders.html).

See [output extensions](https://doc.log10x.com/api/output/).

### :octicons-package-24: Output Modules

Output [Modules](https://doc.log10x.com/engine/module/) package stream configuration, JavaScript and documentation files for writing TenXObjects to edge and cloud data destinations which include:  

- [:simple-fluentd: Forwarders](https://doc.log10x.com/run/input/forwarder/) (Fluentd/Bit) - receive and optimize before shipping
- [:simple-prometheus: Time-series](https://doc.log10x.com/run/output/metric/) (Prometheus, Datadog) - publish [TenXSummary](https://doc.log10x.com/api/js/#TenXSummary) metrics
- [:material-bucket-outline: Object Storage](https://doc.log10x.com/run/input/objectStorage/index) (S3, Azure Blobs) - index for in-place querying
  
