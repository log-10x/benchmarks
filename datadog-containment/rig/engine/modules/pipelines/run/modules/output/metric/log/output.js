// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class LoggerOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.simpleLoggerName) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to logger: " + this.simpleLoggerName);
        }
    }
}