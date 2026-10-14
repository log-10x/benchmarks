// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class FluentdForwardInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        if (this.inputName == "fluentd") {
            if (TenXEnv.get("fluentdInputPath")) {
                TenXConsole.log("📥 Reading events from Fluentd via Forward protocol on unix://" + TenXEnv.get("fluentdInputPath"));
            } else {
                TenXConsole.log("📥 Reading events from Fluentd via Forward protocol on tcp://0.0.0.0:" + TenXEnv.get("fluentdInputPort"));
            }
        }
    }
}
