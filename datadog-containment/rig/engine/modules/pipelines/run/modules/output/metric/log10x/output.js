// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class Log10xOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if ((this.log10xMetricsNameField) || (this.log10xMetricsCounterFields)) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to the log10x backend");
        }
    }
}
