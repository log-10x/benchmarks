// @loader: tenx

import {TenXTemplate, TenXEnv} from '@tenx/tenx'
import {GroupTemplate} from '../group/group-template'

export class OriginTemplate extends TenXTemplate {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("symbolOriginField");
    }

    constructor() {

        if ((this.groupSize == 1) && (GroupTemplate.isGroup)) {

            // use the setStatic reflection function as the target `symbolOriginField` is dynamic
            TenXTemplate.setStatic(
                TenXEnv.get("symbolOriginField"),
                this.symbolOrigin(
                    TenXEnv.get("symbolContexts", "log,exec"),
                    TenXEnv.get("inputField"),
                    TenXEnv.get("symbolMaxLen", 0)
                )
            );
        }

        // A group whose head is all envelope is named from a later member
        // and takes its origin from that member. When the head leads, this
        // assigns nothing and the group reads its members' own origins.
        if (this.groupSize > 1) {

            TenXTemplate.setStatic(
                TenXEnv.get("symbolOriginField"),
                this.symbolOrigin(
                    TenXEnv.get("symbolContexts", "log,exec"),
                    TenXEnv.get("inputField"),
                    TenXEnv.get("symbolMaxLen", 0)
                )
            );
        }
    }
}
