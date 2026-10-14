// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class HTTPOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.outputHttpUrl) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.outputHttpFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.outputHttpFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.outputHttpFields + "'";

            } else if (this.outputHttpWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → " + this.outputHttpUrl);
        }
    }
}