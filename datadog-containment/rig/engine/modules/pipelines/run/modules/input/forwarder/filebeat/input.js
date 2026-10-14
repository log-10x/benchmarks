// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'


export class FilebeatInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
        
        if (this.inputName == "filebeat") {
            TenXConsole.log("📥 Reading events from Filebeat via stdin");
        }
    }
}