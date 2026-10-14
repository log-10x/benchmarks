// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class VectorSocketInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        if (this.inputName == "vector") {
            if (TenXEnv.get("vectorInputPath")) {
                TenXConsole.log("📥 Reading events from Vector via socket sink on unix://" + TenXEnv.get("vectorInputPath"));
            } else {
                TenXConsole.log("📥 Reading events from Vector via socket sink on tcp://0.0.0.0:" + TenXEnv.get("vectorInputPort"));
            }
        }
    }
}
