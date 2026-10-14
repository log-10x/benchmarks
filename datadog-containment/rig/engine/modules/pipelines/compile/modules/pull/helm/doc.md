---
icon: simple/helm
---

Scan Helm [chart](https://helm.sh/docs/topics/charts/), [template](https://helm.sh/docs/helm/helm_template/), and [values](https://helm.sh/docs/chart_template_guide/values_files/) files
for Docker container [image](https://doc.log10x.com/compile/pull/docker/) and [GitHub](https://doc.log10x.com/compile/pull/github/) repositories to pull and [scan](https://doc.log10x.com/compile/scan/) for symbols. 

!!! tenx-helm "Helm CLI"

    The scanner uses the Helm CLI to connect and [show charts](https://helm.sh/docs/helm/helm_show_chart/), so ensure the CLI is installed on your local machine or use the compiler [Docker image](https://doc.log10x.com/install/docker/).
