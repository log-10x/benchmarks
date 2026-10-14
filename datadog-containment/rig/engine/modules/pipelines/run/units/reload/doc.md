---
icon: material/file-refresh-outline
---

Watches the local filesystem for in-place change events on configuration and symbol files, and notifies/restarts affected pipeline [units](https://doc.log10x.com/engine/pipeline/#units) or the entire pipeline.

This mechanism works in tandem with [GitHub-Sync](https://doc.log10x.com/config/github) or the [@kubernetes](https://doc.log10x.com/config/k8s/) launch macro, which pulls named ConfigMap keys via the Kubernetes API and writes them to a local folder via atomic file replace, so the reload watcher sees a real change event and refreshes symbol, lookup, and configuration files at run time. A raw ConfigMap volume mount uses symlink swap and is NOT detected by the reload watcher, so use the @kubernetes macro instead.

For a real-world example see the [rate receiver](https://doc.log10x.com/run/receive/rate/), which reloads its field-set mute file on disk changes. A GitOps-synced commit propagates to every pod on its next sync tick (default 30s for @kubernetes), and each pipeline reloads when the new file lands on disk.
