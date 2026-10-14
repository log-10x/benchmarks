// @loader: tenx

import {TenXEnv, TenXUnit, TenXConsole} from '@tenx/tenx'

export class K8sUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return (config.unitName == "transform") && (TenXEnv.get("k8sExtractorName")) && (!TenXEnv.get("quiet"));
    }
    
     constructor() { 
        TenXConsole.log("☸️ Enriching TenXObjects with k8s container context using " + TenXEnv.get("k8sExtractorName"));
     }
}

export class K8sFluentObject extends TenXObject {

    static shouldLoad(config) {
        return TenXEnv.get("k8sExtractorName") == "fluentK8s";
    }

    // Assigns namespace + container + user-service enrichments. Always runs when
    // the fluentK8s extractor is enabled.
    constructor() {

        var namespace_name = this.namespace_name;
        if (namespace_name) {
            this.set(TenXEnv.get("k8sNamespaceNameField"), namespace_name);
        }

        var container_name = this.container_name;
        if (container_name) {
            this.set(TenXEnv.get("k8sContainerNameField"), container_name);
            this.tenx_user_service = container_name;
        }
    }
}

// Separate class for the pod-name enrichment. Gated on k8sPodNameField being
// truthy via `shouldLoad`. The class only loads when the operator has opted in,
// and the constructor (and its `set(TenXEnv.get("k8sPodNameField"), ...)` call)
// is only parsed when the field name is non-empty.
//
// Why two classes: the engine parse-validates `set()` at init regardless of
// runtime guards. If we inline `if (TenXEnv.get("k8sPodNameField")) { set(..., ...) }`
// in K8sFluentObject's constructor, the engine still validates set()'s shape
// against an empty field name when k8sPodNameField="" and refuses to load.
// shouldLoad is plain JS, runs at class-load time before the constructor body
// gets transpiled to DSL, so gating there avoids the parse pass entirely.
export class K8sFluentPodObject extends TenXObject {

    static shouldLoad(config) {
        return TenXEnv.get("k8sExtractorName") == "fluentK8s" && TenXEnv.get("k8sPodNameField");
    }

    constructor() {

        var pod_name = this.pod_name;
        if (pod_name) {
            this.set(TenXEnv.get("k8sPodNameField"), pod_name);

            var container_name = this.container_name;
            if (container_name) {
                this.tenx_user_process = pod_name + "/" + container_name;
            }
        }
    }
}
