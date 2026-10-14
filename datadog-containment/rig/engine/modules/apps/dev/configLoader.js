// @loader: tenx

import {TenXUnit, TenXEnv, TenXConsole, TenXCounter} from '@tenx/tenx'

export class ConfigLoadUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return (!TenXEnv.get("quiet")) && ((config.unitName == "configLoader"));
    }

    constructor() {
        TenXConsole.log("🚀 Launching 10x Engine: Dev app (local development & testing environment)");
    }

    close() {

        if (!TenXEnv.get("TENX_LICENSE_FILE")) {
            TenXConsole.log("");
            TenXConsole.log("💡 Ready to move forward to production? See https://doc.log10x.com/manage/license/ and point TENX_LICENSE_FILE at your license.");
        }
    }
}
