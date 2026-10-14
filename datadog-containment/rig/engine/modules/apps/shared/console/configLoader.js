// @loader: tenx

import {TenXEnv, TenXConsole, TenXUnit} from '@tenx/tenx'

export class ConfigLoaderUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return (!TenXEnv.get("quiet")) && (config.unitName == "configLoader");
    }

    constructor() {
        if (TenXEnv.get("TENX_LOG_FILE")) {
            TenXConsole.log("🪵 Initializing 10x engine. Logging to: " + TenXEnv.get("TENX_LOG_FILE"));
        } else if (TenXEnv.get("TENX_LOG_APPENDER") == "tenxConsoleAppender") {
            TenXConsole.log("🪵 Initializing 10x engine. Logging to SYS_OUT");
        } else {
            TenXConsole.log("🪵 Initializing 10x engine.");
        }
    }
}
