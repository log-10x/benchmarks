---
icon: material/table-eye
---

Enrich TenXObjects using CSV [lookup](https://doc.log10x.com/api/js/#TenXLookup) files.

Example: map [HTTP status codes](https://github.com/Mr-Pi/httpStatusCodes/blob/master/priv/http-status-codes-1.csv?plain=1) to human-readable messages.

Lookup files [reload](https://doc.log10x.com/run/reload/) on disk changes. The engine can pull them from a [GitHub repo](https://doc.log10x.com/config/github/) or a [Kubernetes ConfigMap](https://doc.log10x.com/config/k8s/) via the @kubernetes launch macro, which polls the ConfigMap over the Kubernetes API and writes each key atomically into a watched temp folder, so an edit propagates without redeploying the pod. (A ConfigMap mounted as a pod volume is not equivalent: kubelet swaps the underlying symlink and most file watchers miss the change. The default key filter is `*.csv` and `*.json`; TSV requires an explicit keys override on the macro.)