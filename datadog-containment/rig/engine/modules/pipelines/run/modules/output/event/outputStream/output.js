// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class OutputStreamOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.outputStreamClass) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.outputStreamFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.outputStreamFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.outputStreamFields + "'";

            } else if (this.outputStreamWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → " + TenXString.match(this.outputStreamClass, "[^.]+$"));
        }
    }
}