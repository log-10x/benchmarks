---
icon: material/power-plug-off-outline
---

Execute JavaScript when [pipeline units](https://doc.log10x.com/engine/pipeline/#units) shut down.

Unit `close()` methods are the shutdown counterpart to `constructor()` methods.
They execute while the unit is still fully functional, before its internal shutdown sequence begins.

``` js
// @loader: tenx

import {TenXUnit, TenXEnv, TenXConsole} from '@tenx/tenx'

export class SymbolLoaderUnit extends TenXUnit {

    static shouldLoad(config) {
       return !TenXEnv.get("quiet") && (config.unitName == "symbolLoader");
    }

    constructor() {
        TenXConsole.log("Loading symbol libraries from: " + this.symbolPaths);
    }

    close() {
        TenXConsole.log("Shutting down symbol loader: " + this.unitName);
    }
}
```

Both `constructor()` and `close()` are defined in the same TenXUnit subclass.
The `shouldLoad(config)` method applies to both, if a class is not loaded for a given unit, neither its constructor nor its close method will execute.

To load unit scripts see [JavaScript configuration](https://doc.log10x.com/config/javascript/).
