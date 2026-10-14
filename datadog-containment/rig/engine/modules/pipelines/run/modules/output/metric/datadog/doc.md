---
icon: simple/datadog
---

Publishes [TenXSummary](https://doc.log10x.com/api/js/#TenXSummary) values to [Datadog Micrometer](https://docs.micrometer.io/micrometer/reference/implementations/datadog.html).

!!! tenx-cloud "Availability"

    This implementation is only available by default in the 10x Engine [Compiler](https://doc.log10x.com/engine/flavors/#compiler) flavor to reduce the footprint of the [Runtime](https://doc.log10x.com/engine/flavors/#runtime) flavor.

## :material-tag-outline: What Datadog counts

Datadog bills a custom metric for each distinct metric name and tag set. The shipped output tags each series with the pattern and where it ran (`message_pattern`, `tenx_hash`, `tenx_user_service`, `severity_level`, `routeState`, `k8s_container`, `k8s_namespace`) and with the runtime attributes, and with nothing that names one node or one process, so the same series comes from every node. It publishes the 200 tag sets with the most bytes (`topSeries`), 800 custom metrics with the two shipped aggregators, inside a Pro plan's allotment from ten hosts up. A pattern outside the top is published once it costs more than the smallest one inside.
