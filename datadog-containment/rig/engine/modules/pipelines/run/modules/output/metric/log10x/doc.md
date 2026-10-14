---
icon: material/monitor-dashboard
---

Publish [TenXSummary](https://doc.log10x.com/api/js/#TenXSummary) instance values as metric counters to the log10x-hosted metrics backend.

!!! warning "Internal and evaluation use only"

    This output targets the log10x-hosted backend, which is an opt-in
    evaluation surface, not a production destination. Production metrics
    belong in a store the deployment owns: [Prometheus](https://doc.log10x.com/run/output/metric/prometheus/), [Datadog](https://doc.log10x.com/run/output/metric/datadog/), [AWS CloudWatch](https://doc.log10x.com/run/output/metric/cloudwatch/), or [Elastic](https://doc.log10x.com/run/output/metric/elastic/).
