// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class AWSCloudWatchOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.cloudwatchNamespace) {
            TenXConsole.log("📈 Publishing TenXSummary metrics to AWS CloudWatch: " + this.cloudwatchNamespace);
        }
    }
}