// @loader: tenx

import {TenXEnv, TenXConsole, TenXUnit} from '@tenx/tenx'

export class SymbolLoaderUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet") && (config.unitName == "symbolLoader");
    }

    constructor() {

        // https://doc.log10x.com/run/symbol/#symbolpaths
        TenXConsole.log("📚 Loading symbol libraries from: " + this.symbolPaths);

        if (this.loadedSymbolFiles) {
            TenXConsole.log("📂 Loaded symbol files: " + this.loadedSymbolFiles);
        }
    }
}
