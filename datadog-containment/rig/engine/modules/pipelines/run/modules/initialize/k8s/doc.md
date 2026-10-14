---
icon: material/kubernetes
---

Enrich TenXObjects with Kubernetes context by extracting container, pod, and namespace [k8s names](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/) from their enclosing text. 

### :material-math-log: Example

For the event below, the `log` field contains raw text that is [structured](https://doc.log10x.com/run/transform/structure/) into a typed TenXObject. 

This module extracts underlying event Kubernetes context such including container name, pod name, and namespace as named fields from a TenXObject's surrounding [fullText](https://doc.log10x.com/api/js/#TenXBaseObject+fullText) for further processing and aggregation.

For example, for the event below this module will extract the following field values:

``` yaml
container_name: coredns
pod_name: coredns-7db6d8ff4d-pddxj
namespace_name: kube-system
```

```json
{
  "log": "[INFO] plugin/reload: Running configuration SHA512 = f869070685748660180df1b7a47d58cdafcf2f368266578c062d1151dc2c900964aecc5975e8882e6de6fdfb6460463e30ebfaad2ec8f0c3c6436f80225b3b5b\n",
  "stream": "stdout",
  "docker": {
    "container_id": "4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e"
  },
  "kubernetes": {
    "container_name": "coredns",
    "namespace_name": "kube-system",
    "pod_name": "coredns-7db6d8ff4d-pddxj",
    "container_image": "registry.k8s.io/coredns/coredns:v1.11.1",
    "container_image_id": "docker-pullable://registry.k8s.io/coredns/coredns@sha256:1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1",
    "pod_id": "38b91d65-ba47-4d0f-a689-711056955842",
    "pod_ip": "10.244.0.99",
    "host": "minikube",
    "labels": {
      "k8s-app": "kube-dns",
      "pod-template-hash": "7db6d8ff4d"
    }
  },
  "tenx_tag": "kubernetes.var.log.containers.coredns-7db6d8ff4d-pddxj_kube-system_coredns-4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e.log"
}