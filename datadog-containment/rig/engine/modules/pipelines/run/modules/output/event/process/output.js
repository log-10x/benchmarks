// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class ProcessOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.procOutCommand) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.procOutFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.procOutFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.procOutFields + "'";

            } else if (this.procOutWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → process: " + this.procOutCommand);
        }
    }
}