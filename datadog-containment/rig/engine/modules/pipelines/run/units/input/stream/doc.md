---
icon: material/waves-arrow-right
---

Defines network, disk, and IPC locations for reading events into [TenXObjects](https://doc.log10x.com/api/js/#TenXObject). Pipelines support multiple concurrent streams.

Input [modules](https://doc.log10x.com/engine/module/#run) read from log analyzers, forwarders, and other sources.

Each stream provides:
- [:material-select-all: Extractors](#inputextractors): Select and redact input data before transformation
- [:material-tag-outline: Source patterns](#inputsourcepattern): Associate events with their origin (log file, network resource)
- [:material-pipe-valve: Backpressure](#backpressure): Throttle data volume

### :octicons-package-dependents-24: Extensions
The [input extensions](https://doc.log10x.com/api/input/) API reads events from custom local and remote sources.