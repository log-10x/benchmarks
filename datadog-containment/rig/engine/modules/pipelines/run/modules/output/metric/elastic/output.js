// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class ElasticOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.elasticHost) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to Elastic: " + this.elasticHost);
        }
    }
}