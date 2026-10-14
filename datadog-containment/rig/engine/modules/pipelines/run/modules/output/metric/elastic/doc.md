---
icon: simple/elastic
---

Publish [TenXSummary](https://doc.log10x.com/api/js/#TenXSummary) instance values as metric counters to an [ElasticSearch Micrometer](https://docs.micrometer.io/micrometer/reference/implementations/elastic.html) registry.

!!! tenx-cloud "Availability"

    This implementation is only available by default in the 10x Engine [Compiler](https://doc.log10x.com/engine/flavors/#compiler) flavor to reduce the footprint of the [Runtime](https://doc.log10x.com/engine/flavors/#runtime) flavor.

!!! info "Querying Metrics"

    The Micrometer ElasticMeterRegistry disables `_source` storage for metrics documents to optimize storage. This means individual metric documents cannot be retrieved directly. Use Elasticsearch aggregation queries to analyze the metrics:

    ```json
    GET tenx-metrics-*/_search
    {
      "size": 0,
      "aggs": {
        "by_severity": {
          "terms": { "field": "severity_level.keyword", "size": 10 }
        }
      }
    }
    ```
