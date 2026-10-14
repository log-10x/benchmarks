// @loader: tenx

import {TenXEnv, TenXConsole, TenXUnit, TenXMath} from '@tenx/tenx'

export class ParallelizeUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return (!TenXEnv.get("quiet")) && (config.unitName == "parallelize");
    }

    constructor() { 
                
        // https://doc.log10x.com/run/transform/parallelize/#paralleleventthreadpoolsize
        var threadPoolSize = TenXMath.parseDouble(this.parallelEventThreadPoolSize);
        
        var coreUsage = "";

        if (threadPoolSize == 0) {

            coreUsage = "synchronously";

        } else if (threadPoolSize == 1) {

            coreUsage = "asynchronously";

        } else if (threadPoolSize < 1) {

            coreUsage = "using " + TenXMath.round(threadPoolSize * 100) + "% of available cores";

        } else {

            coreUsage = "using " + threadPoolSize + " cores";
        }

        TenXConsole.log("⚙️ Transforming events into TenXObjects " + coreUsage);
    }
}