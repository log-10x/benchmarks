// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class StdOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.stdoutTarget) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.stdoutFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.stdoutFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.stdoutFields + "'";

            } else if (this.stdoutWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → " + this.stdoutTarget);
        }
    }
}