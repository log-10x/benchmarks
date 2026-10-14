// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class PrometheusRWOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if ((this.prometheusRWHost)) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to Prometheus RW host: " + this.prometheusRWHost);
        }
    }
}