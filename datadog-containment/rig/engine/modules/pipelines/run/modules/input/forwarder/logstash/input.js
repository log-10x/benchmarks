// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class LogstashSocketInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        if (this.inputName == "logstash") {
            if (TenXEnv.get("logstashInputPath")) {
                TenXConsole.log("📥 Reading events from Logstash unix output on unix://" + TenXEnv.get("logstashInputPath"));
            } else {
                TenXConsole.log("📥 Reading events from Logstash tcp output on tcp://0.0.0.0:" + TenXEnv.get("logstashInputPort"));
            }
        }
    }
}
