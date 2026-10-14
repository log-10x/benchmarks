// @loader: tenx

import {TenXOutput, TenXEnv, TenXConsole, TenXArray, TenXString} from '@tenx/tenx'

export class GitHubOutput extends TenXOutput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() { 
                
        if (this.githubOutputRepo) {

            var fieldStr = "";

            var fieldSize = TenXArray.length(this.githubOutputFields);
            
            if (fieldSize > 1) {

                fieldStr = "TenXObject fields: '" + this.githubOutputFields + "'";

            } else if (fieldSize == 1) {

                fieldStr = "TenXObject field: '" + this.githubOutputFields + "'";

            } else {

                fieldStr = "TenXTemplates";
            }

            TenXConsole.log("📝 Pushing " + fieldStr + " → GitHub: " + this.githubOutputRepo);
        }
    }
}