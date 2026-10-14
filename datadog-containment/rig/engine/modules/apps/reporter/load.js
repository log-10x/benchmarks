// @loader: tenx

import {TenXUnit, TenXEnv, TenXConsole} from '@tenx/tenx'

export class ConfigLoadUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return (!TenXEnv.get("quiet")) && ((config.unitName == "configLoader"));
    }

    constructor() { 
        TenXConsole.log("🚀 Launching 10x Engine: Reporter app");
    }
}
