// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class SocketOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.outputSocketHost) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.outputSocketFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.outputSocketFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.outputSocketFields + "'";

            } else if (this.outputSocketWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            var destination = this.outputSocketHost;

            if (this.outputSocketPort) {
                destination = destination + ":" + this.outputSocketPort;
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → " + destination);
        }
    }
}
