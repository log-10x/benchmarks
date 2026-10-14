// @loader: tenx

import {TenXUnit, TenXEnv, TenXConsole, TenXCounter} from '@tenx/tenx'

export class ReadFileUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return (!TenXEnv.get("quiet")) && ((config.unitName == "readFile"));
    }

    constructor() {

    }

    close() {

        var configFolder = TenXEnv.get("TENX_CONFIG") ?
            TenXEnv.get("TENX_CONFIG") :
            TenXEnv.get("TENX_HOME") + "/config";

        if (!TenXCounter.get("fileObjects")) {

            TenXConsole.log("⚠️ No events read from input. Place your log files in " +
                 configFolder + "/data/sample/input, or name one with inputFilePath. " +
                 "To run on the bundled sample: tenx @apps/dev inputFilePath " +
                 configFolder + "/data/sample/otel-sample.log");
        }
    }
}
