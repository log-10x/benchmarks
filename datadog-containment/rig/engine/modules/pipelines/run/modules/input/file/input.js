// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class FileInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
           
        if (this.inputFilePath) {
            TenXConsole.log("📥 Reading input events from: " + this.inputFilePath);
        }

    }
}