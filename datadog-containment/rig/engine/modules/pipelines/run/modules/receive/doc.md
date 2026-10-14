---
icon: material/pipe-valve
---

Filters TenXObjects based on dynamic policies to reduce noisy telemetry and prevent over-billing.

Receiver [modules](https://doc.log10x.com/engine/module/) commonly execute in conjunction with [forwarder inputs](https://doc.log10x.com/run/input/forwarder)
to filter 'noisy' telemetry from shipping to output (e.g., Splunk, Elastic) to prevent over-billing.

Receiver modules package stream configuration, JavaScript and documentation files to 
filter TenXObjects based on both [local](https://doc.log10x.com/run/output/receive) and
[centralized](https://doc.log10x.com/run/output/receive) rate thresholds.

Threshold values can be updated from GitHub at runtime to allow receivers to dynamically adjust their criteria based on environment-wide conditions.
