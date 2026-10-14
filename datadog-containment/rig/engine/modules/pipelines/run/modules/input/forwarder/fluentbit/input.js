// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class FluentbitForwardInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        if (this.inputName == "fluentbit") {
            if (TenXEnv.get("fluentbitInputPath")) {
                TenXConsole.log("📥 Reading events from Fluent Bit via Forward protocol on unix://" + TenXEnv.get("fluentbitInputPath"));
            } else {
                TenXConsole.log("📥 Reading events from Fluent Bit via Forward protocol on tcp://0.0.0.0:" + TenXEnv.get("fluentbitInputPort"));
            }
        }
    }
}
