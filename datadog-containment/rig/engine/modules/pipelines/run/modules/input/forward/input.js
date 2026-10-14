// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class ForwardInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        if (this.inputName == "forward") {
            if (TenXEnv.get("forwardInputPath")) {
                TenXConsole.log("📥 Reading events via Forward protocol on unix://" + TenXEnv.get("forwardInputPath"));
            } else {
                TenXConsole.log("📥 Reading events via Forward protocol on tcp://0.0.0.0:" + TenXEnv.get("forwardInputPort"));
            }
        }
    }
}
