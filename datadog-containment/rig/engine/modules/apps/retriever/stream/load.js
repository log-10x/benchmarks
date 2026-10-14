// @loader: tenx

import {TenXUnit, TenXEnv, TenXObject, TenXConsole} from '@tenx/tenx'

export class ConfigLoadUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return (!TenXEnv.get("quiet")) && ((config.unitName == "configLoader"));
    }

    constructor() { 
        TenXConsole.log("🚀 Launching 10x Engine: Retriever app (stream results via fluentbit)");
    }
}

export class StreamedObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        // If the search isn't checking index_file, no need perform extraction at construction time.
        return TenXString.includes(TenXEnv.get("queryObjectFilter"), "index_file");
    }

    // Invoked by the engine for each log event read from remote bytes.
    constructor() {
        this.index_file=TenXEnv.get("queryObjectTargetObject");
    }
}
