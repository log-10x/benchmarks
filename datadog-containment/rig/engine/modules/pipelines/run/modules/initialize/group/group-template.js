// @loader: tenx

import {TenXEnv, TenXString, TenXTemplate, TenXConsole, TenXUnit} from '@tenx/tenx'
import {LevelTemplate} from '../level/level-template'

export class GroupUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return !TenXEnv.get("quiet") && (config.unitName == "transform");
    }
    
     constructor() { 
        TenXConsole.log("🔲 Consolidating multi-line events into logical TenXObject groups");
     }
}

// this class applies a heuristic to calculate the static isGroup indicating whether instances of this template
// represent the first event in a logical event group (e.g., stack trace)
export class GroupTemplate extends TenXTemplate {

    // this constructor is invoked once per tenXTemplate instance
    constructor() {

        if (this.groupSize == 1) {

            var event = this.get(TenXEnv.get("inputField"));
            var groupHead = false;

            // timestamped templates are assumed to be a group head
            if (this.timestamped) {

                groupHead = true;

            } else if (TenXString.startsWith(event, TenXEnv.get("messageNegators"))) {

                // a continuation-shaped line is not a group head, whatever
                // severity-shaped tokens it carries: an own timestamp (above)
                // is head evidence, a continuation indent or prefix is not,
                // and a severity word in the text (below) is weak evidence
                // that a line about severities ("  severityText: 'info',")
                // defeats, so dump lines weld into their parent event
                groupHead = false;

            } else if (TenXTemplate.getStatic(TenXEnv.get("levelField"))) {

                // templates with an assigned severity level are assumed to be a group head
                groupHead = true;

            } else if (TenXString.startsWith(event, TenXEnv.get("groupIndicators"))) {

                // instances starting with a group indicator term are assumed to be a group head
                // https://doc.log10x.com/run/transform/group/#groupindicators
                groupHead = true;

            }

            GroupTemplate.isGroup = groupHead;

        }
    }  
}
