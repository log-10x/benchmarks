---
icon: material/source-commit
---

Push symbol unit and library files to GitHub for use by subsequent run and compile pipeline execution. 

The pushed files are consumed by two downstream readers.

### :material-cogs: Compile

Compile pipelines [pull](https://doc.log10x.com/compile/sources/) prior outputs to skip unchanged files, reducing compilation time and keeping [apps](https://doc.log10x.com/apps/) current.

### :material-play: Run

Run pipelines [pull](https://doc.log10x.com/config/github/) symbol libraries from GitHub at startup or periodically to [transform](https://doc.log10x.com/run/transform/) events via [GitOps](https://doc.log10x.com/engine/gitops/) configuration. Kubernetes deployments can instead source action-intent CSV and JSON keys from a [ConfigMap](https://doc.log10x.com/config/k8s/) mounted by the @kubernetes launch macro, which reloads on atomic rename.
