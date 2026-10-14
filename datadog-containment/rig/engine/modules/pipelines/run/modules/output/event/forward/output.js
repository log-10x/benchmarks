// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class ForwardOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        var fieldStr = "";

        var fieldSize = TenXArray.length(this.outputForwardFields);

        if (fieldSize > 1) {

            fieldStr = "TenXObject fields: '" + this.outputForwardFields + "'";

        } else if (fieldSize == 1) {

            fieldStr = "TenXObject field: '" + this.outputForwardFields + "'";

        } else if (this.outputForwardWriteTemplates) {

            fieldStr = "TenXTemplates";
        }

        if (this.outputForwardAddress) {
            TenXConsole.log("📝 Writing " + fieldStr + " → Fluentd: " + this.outputForwardAddress);
        } else if (this.outputForwardHostAddress && this.outputForwardHostPort) {
            TenXConsole.log("📝 Writing " + fieldStr + " → Fluentd: " + this.outputForwardHostAddress + ":" + this.outputForwardHostPort);
        }
    }
}
