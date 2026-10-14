// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx';

export class FileOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.outputFilePath) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.outputFileFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.outputFileFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.outputFileFields + "'";

            } else if (this.outputFileWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → " + TenXString.match(this.outputFilePath, "[^/\\\\]+\\.[^/\\\\]+$"));
        }
    }
}