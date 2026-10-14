// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class UnixSocketOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.outputUnixSocketAddress) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.outputUnixSocketFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.outputUnixSocketFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.outputUnixSocketFields + "'";

            } else if (this.outputUnixSocketWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → " + this.outputUnixSocketAddress);
        }
    }
}