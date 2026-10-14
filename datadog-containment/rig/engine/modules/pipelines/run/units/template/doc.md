---
icon: material/forest-outline
---

The 10x Engine employs an optimization model inspired by Chrome V8’s [_intelligent design_](https://v8.dev/docs/hidden-classes#why-have-hidden-classes%3F) principle. Rather than treating each log event as a "bag of properties," the 10x Engine assumes only a finite number of object shapes will emerge and that these shapes will follow stereotypical usage `templates`.

The 10x Engine utilizes [symbol library](https://doc.log10x.com/compile/link/#symbol-library) files to assign a shared [TenXTemplate](https://doc.log10x.com/api/js/#TenXTemplate) (i.e., _hidden class_) to input log/trace events with the same [structure](https://doc.log10x.com/run/transform/structure), creating a cached optimized schema for each event type.

Operating on typed TenXObjects enables direct access to [symbol](https://doc.log10x.com/run/transform/structure/#symbols) and [variable](https://doc.log10x.com/run/transform/structure/#variables) values at runtime without repeatedly parsing JSON structures or evaluating complex, brittle regular expressions for each event.

## :material-code-json: Template Files

Template files describes the structure of [TenXTemplates](https://doc.log10x.com/engine/design/#optimization-model) generated during previous execution cycles, similar to a `.proto` file which describes the structure of serialized records. 

Each template instance is read as a single line JSON object which contains a `templateHash` and `template` fields into an in-memory map to enable [expanding](https://doc.log10x.com/run/transform/#expand) of previously compact instances read from [inputs](https://doc.log10x.com/run/input/). 

For example, a template .json file or data read from an input stream may contain the following template objects:

``` json
{"templateHash":"7C9 /a$3Lv","template":"{\"log\":\".:$\\n\",\"stream\":\"stdout\",\"docker\":{\"container_id\":\"$\"},\"kubernetes\":{\"container_name\":\"coredns\",\"namespace_name\":\"kube-system\",\"pod_name\":\"coredns-$-$\",\"container_image\":\"registry.k8s.io//coredns//coredns:v1.$.$\",\"container_image_id\":\"docker-$:////registry.k8s.io//coredns//coredns@sha256:$\",\"pod_id\":\"$-$-$-$$\",\"pod_ip\":\"$.$.$.$\",\"host\":\"minikube\",\"labels\":{\"k8s-app\":\"kube-dns\",\"pod-template-hash\":\"$\"}},\"$_tag\":\"kubernetes.var.log.containers.coredns-$-$_kube-system_coredns-$.log\"}"}
{"templateHash":"-EqO[AdeT!#","template":"{\"log\":\"[INFO] plugin//reload: Running configuration SHA512 = $\\n\",\"stream\":\"stdout\",\"docker\":{\"container_id\":\"$\"},\"kubernetes\":{\"container_name\":\"coredns\",\"namespace_name\":\"kube-system\",\"pod_name\":\"coredns-$-$\",\"container_image\":\"registry.k8s.io//coredns//coredns:v1.$.$\",\"container_image_id\":\"docker-$:////registry.k8s.io//coredns//coredns@sha256:$\",\"pod_id\":\"$-$-$-$$\",\"pod_ip\":\"$.$.$.$\",\"host\":\"minikube\",\"labels\":{\"k8s-app\":\"kube-dns\",\"pod-template-hash\":\"$\"}},\"$_tag\":\"kubernetes.var.log.containers.coredns-$-$_kube-system_coredns-$.log\"}"}
{"templateHash":"-*pAW5IsbiJ","template":"{\"log\":\"[INFO] $.$.$.$:$ - $ \\\"AAAA IN github.com.default.svc.cluster.local. udp $ false $\\\" NXDOMAIN qr,aa,rd $ $7.$\\n\",\"stream\":\"stdout\",\"docker\":{\"container_id\":\"$\"},\"kubernetes\":{\"container_name\":\"coredns\",\"namespace_name\":\"kube-system\",\"pod_name\":\"coredns-$-$\",\"container_image\":\"registry.k8s.io//coredns//coredns:v1.$.$\",\"container_image_id\":\"docker-pullable:////registry.k8s.io//coredns//coredns@sha256:$\",\"pod_id\":\"$-$-$-$$\",\"pod_ip\":\"$.$.$.$\",\"host\":\"minikube\",\"labels\":{\"k8s-app\":\"kube-dns\",\"pod-template-hash\":\"$\"}},\"$_tag\":\"kubernetes.var.log.containers.coredns-$-$_kube-system_coredns-$.log\"}"}
```

The last template in this example whose hash is `-*pAW5IsbiJ` can be used to expand the contents of the following [compact event](https://doc.log10x.com/run/transform/#compact) from an input stream:

```
~-*pAW5IsbiJ,10,244,0,102,45981,64767,77,1232,147,000221854s,4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e,7db6d8ff4d,pddxj,11,1,1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1,38b91d65,ba47,4d0f,a689,-711056955842,10,244,0,99,7db6d8ff4d,10x,7db6d8ff4d,pddxj,4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e
```

Given both template and compact event information, the 10x Engine will automatically expand the event to its original full-text form:

``` json
{"log":"[INFO] 10.244.0.102:45981 - 64767 \"AAAA IN github.com.default.svc.cluster.local. udp 77 false 1232\" NXDOMAIN qr,aa,rd 147 0.000221854s\n","stream":"stdout","docker":{"container_id":"4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e"},"kubernetes":{"container_name":"coredns","namespace_name":"kube-system","pod_name":"coredns-7db6d8ff4d-pddxj","container_image":"registry.k8s.io/coredns/coredns:v1.11.1","container_image_id":"docker-pullable://registry.k8s.io/coredns/coredns@sha256:1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1","pod_id":"38b91d65-ba47-4d0f-a689-711056955842","pod_ip":"10.244.0.99","host":"minikube","labels":{"k8s-app":"kube-dns","pod-template-hash":"7db6d8ff4d"}},"tenx_tag":"kubernetes.var.log.containers.coredns-7db6d8ff4d-pddxj_kube-system_coredns-4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e.log"}
```

At runtime, matching TenXTemplate JSON objects from pipeline [inputs](https://doc.log10x.com/run/input/) are automatically added to the available templates for expanding. This allows compact files and streams to include template definitions followed by their compact instances.
