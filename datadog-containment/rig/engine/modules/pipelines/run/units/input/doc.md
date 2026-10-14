---
icon: material/set-merge
---

Reads log/trace events from local and remote sources, transforming them into [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).

Inputs comprise two core components: _streams_ and _extractors_ to construct [modules](https://doc.log10x.com/engine/module/) which read events from edge/cloud sources such as log analyzers, forwarders and object storage.

Multiple input streams can execute in conjunction, where each stream provides [backpressure](https://doc.log10x.com/run/input/stream/#backpressure) controls to ensure the pipeline can process the information received. 