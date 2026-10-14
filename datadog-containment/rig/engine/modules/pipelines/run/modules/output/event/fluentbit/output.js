// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray} from '@tenx/tenx'

export class FluentBitOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.fluentbitOutCommand) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.fluentbitOutFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.fluentbitOutFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.fluentbitOutFields + "'";

            } else if (this.fluentbitOutWriteTemplates) {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Writing " + fieldStr + " → Fluent Bit: " + this.fluentbitOutCommand);
        }
    }
}