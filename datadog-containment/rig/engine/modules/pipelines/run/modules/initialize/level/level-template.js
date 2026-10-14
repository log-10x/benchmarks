// @loader: tenx

import {TenXEnv, TenXString, TenXTemplate, TenXMap, TenXUnit, TenXConsole} from '@tenx/tenx'

export class LevelUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return (config.unitName == "transform") && (TenXEnv.get("levelField")) && (!TenXEnv.get("quiet"));
    }
    
     constructor() { 
        TenXConsole.log("ℹ️ Enriching TenXObjects with severity field: '" + TenXEnv.get("levelField") + "'");
     }
}

export class LevelTemplate extends TenXTemplate {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("levelField");
    }

    constructor() {
    
        if (this.groupSize == 1) {
            // check the template's symbol value starts with any of the configured 'levelTerms' values
            // use the map function to get the level value associated with a matching term (e.g., PHP_Fatal_error => CRITICAL)
            
            var levelTerm = TenXString.includes(
                this.symbolSequence("", TenXEnv.get("inputField"), 256), 
                TenXMap.fromEntries(TenXEnv.get("levelTerms"))
            );
            
            // if no match, try inferring from the template's timestamp pattern using configured 'levelTimestampPatterns' values
            if (!levelTerm) {

                levelTerm = TenXString.startsWith(
                    this.timestampFormat(), 
                    TenXMap.fromEntries(TenXEnv.get("levelTimestampPatterns"))
                );
            }
            
            if (levelTerm) {
                
                // apply the result to the target 'levelField' template static field for use by all its instances
                TenXTemplate.setStatic(TenXEnv.get("levelField"), levelTerm);
            }
        } else {

            TenXTemplate.setStatic(
                TenXEnv.get("levelField"), 
                TenXTemplate.getStatic(TenXEnv.get("levelField"))
            );
        }
    }
}
