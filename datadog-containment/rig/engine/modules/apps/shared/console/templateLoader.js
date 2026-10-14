// @loader: tenx

import {TenXEnv, TenXConsole, TenXUnit} from '@tenx/tenx'

export class TemplateLoaderUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet") && config.unitName == "templateLoader" && this.templateFiles;
    }

    constructor() { 
                
        // https://doc.log10x.com/run/template/#templatefiles
        TenXConsole.log("📂 Loading TenXTemplates from: " + this.templateFiles);
    }
}