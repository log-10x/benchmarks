// @loader: tenx

import { TenXEnv, TenXMath, TenXString, TenXTemplate, TenXObject, TenXUnit } from '@tenx/tenx'
import { GroupTemplate } from '../group/group-template'

export class HttpCodeUnit extends TenXUnit {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return (config.unitName == "transform") && (TenXEnv.get("httpCodeField")) && (!TenXEnv.get("quiet"));
    }
    
     constructor() { 
        TenXConsole.log("🌐 Enriching TenXObjects with HTTP code field: '" + TenXEnv.get("httpCodeField") + "'");
     }
}

export class HttpCodeTemplate extends TenXTemplate {

    // only load this class if the 'httpCodeField' env var is set
    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("httpCodeField");
    }

    // This constructor is invoked by the engine once for each unique tenXTemplate discovered
    // at runtime based on log event structures
    constructor() {

        // only extract HTTP codes from standalone events (e.g., do not look for HTTP codes in stack trace lines)
        // To learn more see https://doc.log10x.com/run/initialize/group
        if ((!GroupTemplate.isGroup) || (this.groupSize > 1)) {
            return;
        }

        // make sure the template contains HTTP status code indicators (e.g., GET, HTTP)
        // To learn more see https://doc.log10x.com/run/transform/structure/#members
        if (!TenXString.includes(this.template, TenXEnv.get("httpCodeKeywords"))) {
            return;
        }

        // search for a token contained in the list of allowed HTTP codes  (e.g., 200, 404)
        var token = this.findToken("variable", TenXEnv.get("httpCodeValidValues"));

        if (!token) {
            return;
        }

        // check if the subsequent token does not preclude the candidate (e.g., preclude '404#')
        if (TenXString.includes(TenXEnv.get("httpCodePrecludersAfter"), this.token(token + 1))) {
            return;
        }

        // check if the preceding token does not preclude the candidate (e.g., preclude '?404')

        // Retrieve the previous token for precluder checks, improving code readability and reuse.
        var prevToken = this.token(token - 1); 
        
        // Compute if the previous token is a precluder, used in conditional logic below.
        var precluderBefore = TenXString.includes(TenXEnv.get("httpCodePrecludersBefore"), prevToken); 

        // explicitly make sure that we preclude candidates preceded by ':' or ' :',
        // UNLESS they are preceeded by a keyword or by '":" or '": ' to accommodate JSON fields (e.g., "code":200 or "code": 200).
        var isColonPattern = false;
        var checkOffset = 0;

        if (prevToken == ":") { // Check if previous token is exactly ":", setting up for colon pattern handling.
            
            isColonPattern = true;
            checkOffset = 2; // Offset for check in "key":code (check at token-2).
       
        } else if (prevToken == " " && this.token(token - 2) == ":") { // Check for space followed by colon, handling "key": code.
            
            isColonPattern = true;
            checkOffset = 3; // Offset for check in "key": code (check at token-3).
        }

        if (isColonPattern) { // If colon pattern detected, perform check.

            var suspect = this.token(token - checkOffset);

            if (suspect != "\"") {
                if (!TenXString.includes(TenXEnv.get("httpCodeKeywords"), suspect)) {
                    return; // Exit if failed the check
                }
            }

        } else if (precluderBefore) { // Else, if not colon pattern but still a precluder, preclude the candidate.
            return; // Exit for other precluders.
        }

        // Structural adjacency guard. The full-template keyword check at the
        // top of this constructor is only a cheap pre-filter — it proves
        // SOMEWHERE in the template body there's an HTTP-ish word, not that
        // THIS specific candidate is an HTTP code. Any numeric variable whose
        // first observed value lands in 100..599 (e.g. kafka `max.request.size
        // = 200`, JVM `-Dclk.tck=100`) would otherwise get bound as httpToken
        // and subsequent events at the same position would carry through
        // arbitrary non-HTTP values as http_code.
        //
        // Require a strict HTTP marker (status, HTTP/, code, GET, Completed,
        // ...) within ±5 tokens of the candidate. Real HTTP status codes
        // always appear adjacent to such a marker; config values and metric
        // counts generally do not.
        var nearbyKeyword = this.findTokenNear(
            "symbol",
            TenXEnv.get("httpCodeStrictKeywords"),
            token,
            5);

        if (nearbyKeyword < 0) {
            return;
        }

        // assign the token to a static variable for all instances of this template
        HttpCodeTemplate.httpToken = token;
    }
}

export class HttpCodeObject extends TenXObject {

    // only load this class if the 'httpCodeField' env var is set
    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("httpCodeField");
    }

    // Invoked by the engine for each log event matching the template,
    // using shared state (e.g., token position) set by HttpCodeTemplate
    // to extract and assign the HTTP status code to the target 'httpCodeField' field.
    //
    // NOTE: HttpCodeTemplate records `httpToken` as the token *position* where
    // findToken located a valid HTTP code on the template-initializing event.
    // Within a single template the token position is stable — but the VALUE
    // at a variable position varies by definition. A kafka config-dump line
    // like `max.request.size = 200` initializes the template with a valid HTTP
    // code at the size-variable position; subsequent events (`size = 3`,
    // `size = 2000`) carry non-HTTP values at the same position, and a raw
    // parseInt emits them as http_code garbage. Re-validate against the
    // configured valid-codes set at event time so only events whose current
    // token value is actually a valid HTTP code get the enrichment.
    constructor() {

        var httpToken = HttpCodeTemplate.httpToken;

        if (httpToken) {
            var tokenValue = this.token(httpToken);

            if (tokenValue) {
                var httpCodeNum = TenXMath.parseInt(tokenValue);

                // Range-check the parsed integer against the valid HTTP status code
                // window. Every code in the configured httpCodeValidValues list is a
                // 3-digit 1xx–5xx value, so (100..599) is the exact admissible range.
                // A substring check against the validValues list would let "3" slip
                // through because "3" is a substring of "300"/"403"/"503"; the
                // explicit numeric bound is the simplest correct check.
                if ((httpCodeNum >= 100) && (httpCodeNum <= 599)) {
                    this.set(TenXEnv.get("httpCodeField"), httpCodeNum);
                }
            }
        }
    }
}
