---
icon: simple/prometheus
---

Defines a Prometheus Remote-Write output to publish TenXSummary metrics.
    
This output utilizes The [PrometheusRWMetricRegistryFactory](https://github.com/log-10x/pipeline-extensions/blob/main/cloud-extensions/src/main/java/com/log10x/ext/cloud/micrometer/registry/PrometheusRWMetricRegistryFactory.java) class to instantiate a Micrometer registry that uses the Prometheus [Remote-Write protocol](https://github.com/log-10x/pipeline-extensions/blob/main/edge-extensions/src/main/java/com/log10x/ext/edge/prometheus/PrometheusClient.java). 
