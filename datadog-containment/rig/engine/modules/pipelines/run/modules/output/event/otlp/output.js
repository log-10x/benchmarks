// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray} from '@tenx/tenx'

export class OtlpOutput extends TenXOutput {

    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        var fieldStr = "";

        var fieldSize = TenXArray.length(this.outputOtlpFields);

        if (fieldSize > 1) {
            fieldStr = "TenXObject fields: '" + this.outputOtlpFields + "'";
        } else if (fieldSize == 1) {
            fieldStr = "TenXObject field: '" + this.outputOtlpFields + "'";
        } else if (this.outputOtlpWriteTemplates) {
            fieldStr = "TenXTemplates";
        }

        // Do NOT invent a destination. These are bound after the constructor
        // runs, so a fallback here prints the module default rather than where
        // events actually go: it reported 127.0.0.1:4317 while writing to the
        // configured port, and 4317 is the Collector's own otlp receiver, which
        // is exactly the port the sidecar must NOT be on. The forward output
        // takes the same approach: name the destination only when it is known.
        var host = this.outputOtlpHost;
        var port = this.outputOtlpPort;

        if (host && port) {
            TenXConsole.log("📝 Writing " + fieldStr + " → OTLP/gRPC: " + host + ":" + port);
        } else {
            TenXConsole.log("📝 Writing " + fieldStr + " → OTLP/gRPC");
        }
    }
}
