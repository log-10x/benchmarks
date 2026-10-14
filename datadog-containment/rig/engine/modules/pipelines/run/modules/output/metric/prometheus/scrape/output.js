// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class PrometheusScrapeOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if ((this.prometheusPort)) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to Prometheus scrape on port: " + this.prometheusPort);
        }
    }
}