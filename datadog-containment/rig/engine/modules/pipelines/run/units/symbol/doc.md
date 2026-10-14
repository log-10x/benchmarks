---
icon: material/library-outline
---

Load [symbol library](https://doc.log10x.com/compile/link/#symbol-library) files which enable the run pipeline to [transform](https://doc.log10x.com/run/transform/) input log/trace events into typed [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).

The pipeline can [pull](https://doc.log10x.com/config/github/) up-to-date symbol library files from GitHub, or [reload them from a Kubernetes ConfigMap](https://doc.log10x.com/config/k8s/), at start-up/periodically as part of a centralized GitOps configuration management approach.

