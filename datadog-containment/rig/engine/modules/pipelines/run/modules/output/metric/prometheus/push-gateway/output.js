// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class PrometheusPGOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if ((this.prometheusPGHost)) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to Prometheus Push-gateway: " + this.prometheusPGHost);
        }
    }
}