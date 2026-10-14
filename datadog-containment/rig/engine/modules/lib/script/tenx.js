

//   This file provides the base classes from which custom 10x scripting classes are derived,
//   and classes containing utility functions for operating on strings, numbers, lookups, etc.
  
//   10x JavaScript allows for filtering, enriching, and aggregating of tenxObjects.
//   The classes and functions below provide a specified subset of javascript functions implemented by the 10x Engine. 
  
//   10x script actions are evaluated during different phases of pipeline execution: input, object, and summary initialization.
//   These allow for the customization of pipeline behavior by deriving and adding logic to classes from 
//   {@link TenXInput}, {@link TenXOutput}, {@link TenXUnit}, {@link TenXObject} and {@link TenXSummary} respectively.
  
//   10x JavaScript does NOT allow for explicit new object allocations, loops, error-throwing in tenxObject constructors
//   and other language constructs that have indeterminate execution times/memory costs. 
  
//   To execute a 10x .js script, pass it alongside other pipeline launch arguments to the 10x Engine: 
//   > tenx @my.js
  
//   or placed in a folder launch argument: 
//   > tenx @~/tenx-js
 
/**
 * @class
 * @classdesc
 * Provide a joint class base for tenxObject, summary and template and instances.
 *
 * **Objects**: provide a structured approach to operating on semi/unstructured events.
 * To learn more see {@link TenXObject}
 *
 * **Templates**:describe the schema/structure of other tenxObject similar to programmatic classes (who are themselves object instances)
 * who describes the structure of other instances. 
 * To learn more see {@link https://doc.log10x.com/run/template|tenxTemplates}.
 *
 * **Summaries**: aggregate the values of other Objects. Summaries are instantiated by an {@link https://doc.log10x.com/run/aggregate|aggregator}
 * after a certain number of tenxObjects have been aggregated or a certain interval has elapsed.
 * They are commonly used with time series outputs (e.g. Prometheus)
 * To learn more see {@link TenXSummary}
 * 
 */
export class TenXBaseObject {

    /**
     * Returns the value of a target intrinsic, extracted or calculated field of the current instance.
     *
     * This function produces and returns a JSON object listing all intrinsic
     * (i.e., built into all objects), extracted (i.e., JSON and Key/Value
     * fields automatically extracted from the object's text field) and
     * encoded (i.e., assigned into the object through an event action) fields.
     *
     * @param  field {string}       Field name to whose value to return
     *
     * @param {number} [index=0]    Index of the element if 'field' is an array
     *
     * @return {number|string|boolean}  Value of 'field' at position 'index'
     * 
     * @example
     * export class MyObject extends TenXObject {
     *   // filter instances for which the value of 'myField'
     *   // is different than the 'myValue' launch argument  
     *   constructor() {
     *     this.drop(this.get(TenXEnv.get("myField") != TenXEnv.get("myValue"));
     *   }
     * }
     *
    */
    get(field, index) {
        return TenXEngine.invoke(field, index);
    }

    /**
     * Set a target value into a calculated field
     *
     * This function is similar to {@link https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Reflect/set|Reflect.set}.
     * 
     * Note that intrinsic fields (i.e., fields declared by this class) cannot be set.
     * 
     * Calls to this function can only be made from within an tenxObject's constructor.
     *
     * @param  field {string}       Field name to set
     *
     * @param {number|string|boolean} value to assign to field
     *
     * @return {boolean}  return true if the value was set
     *
     * @example
     * export class MyGeoObject extends TenXObject {
     *   // Assign a geo-ref lookup value (e.g., country, region) specified by a launch argument to a matching field
     *   constructor() {
     *     this.set(TenXEnv.get("geoField"), TenXLookup.get("geoIP"), this.ipAddress, TenXEnv.get("geoField"));
     *   }
     * }
     *
    */
    set(field, value) {
        return TenXEngine.invoke(field, value);
    }

    /**
     * Returns a new String composed of evaluated tenxObject fields joined together with the specified delimiter
     * or as a JSON object containing the field name/value pairs.
     *
     * @param  delimiter {string}   the delimiter that separates each field value (should be one character long)
     *
     * @param  fields    {string[]} the current tenxObject's intrinsic/extracted/calculated fields to join.
     *
     * @return {string}  a String composed of the evaluated fields separated by the delimiter. If an empty delimiter
     *                   is passed, the field values are formatted and escaped as JSON values of an array.
     *                   If only one argument is passed, the values of the argument are treated as the array of 
     *                   fields to join and the delimiter is assumed to be empty (formatting as JSON).
     */
    joinFields(delimiter, ...fields) {
        return TenXEngine.invoke(delimiter, fields);
    }

    /**
     * Invokes {@link TenXString.length}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {number}
     */
    length() {
        return TenXString.length(this.text);
    }

    /**
     * Invokes {@link TenXString.hash}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {string}
     */
    hash() {
        return TenXString.hash(this.text);
    }

    /**
     * Invokes {@link TenXString.includes}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {boolean}
     */
    includes(...term) {
        return TenXString.includes(this.text, term);
    }

    /**
     * Invokes {@link TenXString.startsWith}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {boolean}
     */
    startsWith(prefix) {
        return TenXString.startsWith(this.text, prefix);
    }

    /**
     * Invokes {@link TenXString.endsWith}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {boolean}
     */
    endsWith(suffix) {
        return TenXString.endsWith(this.text, suffix);
    }

    /**
     * Invokes {@link TenXString.indexOf}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {number}
     */
    indexOf(term, fromIndex) {
        return TenXString.indexOf(this.text, term, fromIndex);
    }

    /**
     * Invokes {@link TenXString.lastIndexOf}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {number}
     */
    lastIndexOf(term, fromIndex) {
        return TenXString.lastIndexOf(this.text, term, fromIndex);
    }

    /**
     * Invokes {@link TenXString.toLowerCase}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {string}
     */
    toLowerCase() {
        return TenXString.toLowerCase(this.text);
    }

    /**
     * Invokes {@link TenXString.toUpperCase}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {string}
     */
    toUpperCase() {
        return TenXString.toUpperCase(this.text);
    }

    /**
     * Invokes {@link TenXString.matchAll}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {string[]}
     */
    matchAll(pattern) {
        return TenXString.matchAll(this.text, pattern);
    }

    /**
     * Invokes {@link TenXString.match}, passing {@link TenXBaseObject#text|text} as the value of 'str'.
     * @return {string}
     */
    match(pattern) {
        return TenXString.match(this.text, pattern);
    }

    /**
     * Invokes {@link TenXString.replace}, passing {@link TenXBaseObject#text|text} as the value of 'str'
     * @return {string}
     */
    replace(target, replacement) {
        return TenXString.replace(this.text, target, replacement);
    }

    /**
       * Returns a JSON representation of the current instance's intrinsic, extracted, and calculated fields.
       *
       * This function  returns a JSON object listing all intrinsic (i.e., built into all tenxObjects),
       * extracted (i.e., JSON/KV entries extracted from {@link TenXBaseObject#text|text}) and
       * calculated (i.e., assigned into the instance within its constructor) fields.
       *
       * This function is useful for examining the state of a specific instance,
       * especially in conjunction with the {@link TenXConsole.log|log()} function.
       * 
       * To print the JSON description of every object whose  {@link TenXBaseObject#text|text} field contains the 'target' variable to console:
       * @example
       * if this.includes(TenXEnv.get("target")) TenXConsole.log(this.toString());
       * 
       * @return {string} the object's JSON representation
       *
       */
    toString() {
        return TenXEngine.invoke();
    }

    /**
     * Returns the value of specific tokens within the current tenxObject.
     *
     * tenxObjects are comprised of `tokens`, which are alpha-numeric values categorized as:
     * - `symbol`: values found in the pipeline's {@link https://doc.log10x.com/compile/link/#symbol-library|symbol library}).
     * - `delimiter`: single length {@link https://doc.log10x.com/run/transform/structure/#delimiters|token delimiters} (e.g. ',;<>.').
     * - `variable`: alpha-numeric values that are neither delimiter nor symbols.
     *
     * This function provides a mechanism for querying the current tenxObject's token structure.
     * 
     * The following call can be made to look for the second {@link https://doc.log10x.com/run/transform/structure/#variabls|variable} in the current tenxObject:
     * @example
     * this.status = this.token(2, "variable");
     *
     * @param {number} [tokenOffset=0] Number of tokens within the object's tokens array to begin searching from.
     *
     * @param {number} [tokenTypes=variable] Comma delimited string containing the token type(s) to search for.
     * 						                 Available values: [symbol, variable, delimiter].
     *
     * @param {number|string} [from=0]   Number: Position within the target string to begin searching for the target token.
     * 						             If positive, the zero-based n character is used. If negative, the (length - n - 1) is used
     * 						             if the index is out of bounds, it is ignored and 0 is used.
     *                                   String: index of value within the current tenxObject's text. 
     *                              
     *
     * @return {string}		Value of the token of type 'tokenTypes',
     * 						having skipped 'tokenOffset' tokens from the 'startIndex' start position
     *
     */
    token(tokenOffset, tokenTypes, startIndex) {
        return TenXEngine.invoke(tokenOffset, tokenTypes, startIndex);
    }

    /**
     * Returns the number of tokens in the current tenxObject's {@link TenXBaseObject#text|text} field.
     * To learn more about tokens, see: {@link https://doc.log10x.com/run/transform/structure/#delimiters|token delimiters}
     *
     * @return {number}	number of tokens in the current object
     *
     */
    tokenSize() {
        return TenXEngine.invoke();
    }

    /**
     * Returns the index of the first token matching the specified type and criteria.
     *
     * Tokens within {@link https://doc.log10x.com/api/js/#TenXObject+timestamp|timestamp} and {@link https://doc.log10x.com/api/js/#TenXObject+ipAddress|IPaddress} values are excluded from the search.
     *
     * @param {string} type Token type to search for: "symbol" ({@link https://doc.log10x.com/run/transform/structure#symbols}) or "variable" ({@link https://doc.log10x.com/run/transform/structure#variables}).
     * @param {number|string|Array.<(number|string)>|Object} valueOrFrom Single value to match, or array/map (generated by {@link https://doc.log10x.com/api/js/#TenXMap.fromEntries}) for inclusion check, or 'from' for range (number/string).
     * @param {number|string} [to] Optional 'to' for range (same type as valueOrFrom).
     * @return {number} Index of the first matching token, or -1 if not found. If valueOrFrom is array/map, returns first token included in array or map keyset.
     */
    findToken(type, valueOrFrom, to) {
        return TenXEngine.invoke(type, valueOrFrom, to);
    }

    /**
     * Returns the index of the first token matching the specified type and value
     * that lies within ±window tokens of the given center token index.
     *
     * Useful for context-sensitive extraction where a candidate value is only
     * meaningful when a confirming keyword appears nearby — for example, requiring
     * an HTTP method or status keyword within 5 tokens of a numeric HTTP code.
     *
     * Tokens within {@link https://doc.log10x.com/api/js/#TenXObject+timestamp|timestamp} and {@link https://doc.log10x.com/api/js/#TenXObject+ipAddress|IPaddress} values are excluded from the search.
     *
     * @param {string} type Token type to search for: "symbol" ({@link https://doc.log10x.com/run/transform/structure#symbols}) or "variable" ({@link https://doc.log10x.com/run/transform/structure#variables}).
     * @param {string|Array.<string>|Object} value Single value to match, or array/map for inclusion check.
     * @param {number} center Token index to search around (typically the index of the candidate token).
     * @param {number} window Number of tokens to search on each side of center (inclusive).
     * @return {number} Index of the first matching token within [center-window, center+window], or -1 if not found.
     */
    findTokenNear(type, value, center, window) {
        return TenXEngine.invoke(type, value, center, window);
    }

    /**
     * Returns the index of within the object's {@link TenXBaseObject#text|text} where
     * the Nth timestamp sequence begins (inclusive).
     *
     * To learn more see {@link https://doc.log10x.com/run/transform/timestamp|timestamp extraction}.
     * 
     * @param   index {number}  Index within the {@link TenXObject#timestamp|timestamp} array to use.
     *                          A negative value can be provided to search from the end of the timestamp array
     *
     * @return {number}	zero-based index of the start position (inclusive), -1 if not found
     *
     */
    timestampStart(index) {
        return TenXEngine.invoke(index);
    }

    /**
     * Returns the index of within the object's {@link TenXBaseObject#text|text} where
     * the Nth timestamp sequence ends (exclusive).
     *
     * To learn more see {@link https://doc.log10x.com/run/transform/timestamp|timestamp extraction}.
     *
     * @param   index {number}  Index within the {@link TenXObject#timestamp|timestamp} array to use.
     *                          A negative value can be provided to search from the end of the timestamp array
     *
     * @return {number}	zero-based index of the end position (exclusive), -1 if not found
     *
     */
    timestampEnd(index) {
        return TenXEngine.invoke(index);
    }

    /**
     * Returns the N value of a 'symbol' token sequence matching a target criteria
     *
     * This function selects a certain set of {@link https://doc.log10x.com/run/transform/structure/#symbols|symbol} and delimiter tokens from the object's
     * Template based on their context within the source code/binary file from which they originated.
     * 
     * To capture the symbol tokens that originated from an enum named "Status" for the following object:
     *  `
     *  17/06/09 20:51:58 INFO spark.CacheManager: Partition rdd_2876_26 not found, computing Status ENABLED
     * `
     * 
     * For this information to be available, symbol files (*.json) must be placed within {@link https://doc.log10x.com/run/symbol|symbol path}.
     * 
     * @example
     * this.status = this.symbol("ENUM", "Status"); //capture the 'ENABLED value above
     * 
     * @param type       {string}	Type of symbol that is being searched for. 
     *                              Supported values: PACKAGE, CLASS, METHOD, LOG, ENUM, CONST, TEXT (case insensitive).
     *                              To select all symbol types, pass an empty string.
     *    
     * @param symbolName {string}   A specific symbol name to look for. For example, look for
     * 						        the values of an enum named "status", that value could be specified
     * 						        to limit results to symbol tokens whose literals are defined in the "status" enum
     *
     * @param {number} [index=0]    index of the selected symbol token matching the type and
     * 						        symbolName parameters. To choose the second symbol sequence, use 1; for last, use -1.
     *
     * @return           {string}   the symbol and delimiter token sequence selected from the object's Template fields
     * 			                    matching the selected criteria. If no matching sequence is found or {@link https://doc.log10x.com/run/symbol|symbol files}.
     * 			                    have not been loaded, an empty value is returned.
     */
    symbol(type, symbolName, index) {
        return TenXEngine.invoke(type, symbolName, index);
    }

    /**
     * Returns a sequence of 'symbol' tokens of a specified type.
     *
     * This function ranks the candidate source code/binary origins of the object's tenxTemplate by coverage, meaning the number of distinct
     * library-known {@link https://doc.log10x.com/run/transform/structure/#symbols|symbol} tokens each origin explains, and emits the symbol and delimiter tokens of the winner
     * (span length is the last tiebreak, and contiguity describes the emitted value rather than the selection).
     * This allows for extracting the 'message' value of a target tenxObject from its {@link TenXBaseObject#text|text} field.
     * 
     * To capture a symbol sequence for the following event:
     * `
     * 17/06/24 20:51:58 INFO spark.CacheManager: Partition rdd_2876_26 not found, computing Status ENABLED
     * `
     * 
     * The following call can be used:
     * 
     * ``` js
     * this.message = symbolSequence("log"); // will assign: 'Partition__not_found_computing_Status'
     * ```
     * 
     * The 'symbolContexts' argument controls which {@link https://doc.log10x.com/run/transform/symbol/#contexts|symbol contexts} participate; the listed contexts are evaluated in a single pass, so list order acts as a filter rather than a precedence chain.
     * Supported values: PACKAGE, CLASS, METHOD, LOG, ENUM, CONST, TEXT, EXEC, ANY (case insensitive).
     * 
     * @param symbolContexts  {string} Comma delimited  symbol types to search for. Supported values: PACKAGE, CLASS, METHOD, LOG, ENUM, CONST, TEXT, EXEC, ANY (case insensitive). Defaults to 'ANY'.
     * @param fieldName       {string} name of {@link https://doc.log10x.com/run/transform/fields|extracted JSON/KV} field name (e.g., 'log') to scan for symbol tokens. If not specified, scans the {@link TenXBaseObject#text|text} field.
     * @param maxLen          {number} Max length of result string, 0 for unlimited.
     *  
     * @return           {string}  The symbol sequence selected from the object's Template fields
     * 			                   matching the selected criteria. If no matching sequence is found or {@link https://doc.log10x.com/run/symbol|symbol path}.
     * 			                   have not been loaded, an empty value is returned.
     */
    symbolSequence(symbolContexts, fieldName, maxLen) {
        return TenXEngine.invoke(symbolContexts, fieldName, maxLen);
    }


    /**
     * Returns a the source code/binary origin of 'symbol' tokens of a specified type.
     *
     * This function returns the origin (i.e. the source code or binary executable which emitted the line) that ranks highest by coverage,
     * meaning the number of distinct library-known {@link https://doc.log10x.com/run/transform/structure/#symbols|symbol} tokens it explains across the object's
     * tenxTemplate; span length is the last tiebreak.
     * 
     * To capture the origin value for the following event:
     * `
     * 17/06/24 20:51:58 INFO spark.CacheManager: Partition rdd_2876_26 not found, computing Status ENABLED
     * `
     * 
     * The following call can be used:
     * 
     * ``` js
     * this.origin = symbolOrigin("log"); // = CacheManager.scala
     * ```
     * 
     * The 'symbolContext' argument controls which {@link https://doc.log10x.com/run/transform/symbol/#contexts|symbol contexts} participate; the listed contexts are evaluated in a single pass, so list order acts as a filter rather than a precedence chain.
     * Supported values: PACKAGE, CLASS, METHOD, LOG, ENUM, CONST, TEXT, EXEC (case insensitive).
     * 
     * A symbol context value may be preceded by [fieldName]: to limit the sequence search
     * to a target extracted field. For example, for: "log:message,class",
     * will search for symbols originating from code log statements (e.g., "log.error("...")" only in the object's "message" field (if it exists). 
     * When searching for "class" symbols, the entire object is searched.
     * 
     * @param symbolContext  {string} Types of symbols to search for. Supported values: PACKAGE, CLASS, METHOD, LOG, ENUM, CONST, TEXT, EXEC (case insensitive).
     *    
     * 
     * @return           {string}  The symbol sequence and/or origin selected from the object's Template fields
     * 			                   matching the selected criteria. If no matching sequence is found or {@link https://doc.log10x.com/run/symbol|symbol path}.
     * 			                   have not been loaded, an empty value is returned.
     */
    symbolOrigin(symbolContext) {
        return TenXEngine.invoke(symbolContext);
    }

    /**
     * The content of the event from which this instance was structured.
     * This value may be read directly from an {@link https://doc.log10x.com/run/input/|input} or calculated on demand for {@link https://doc.log10x.com/run/template/#expand|decoded} instances.
     * @type {string}
     */
    text = "";

        
    /**
     * The byte size of UTF8 encoding of {@link TenXBaseObject#text|text}.
     * @type {number}
     */
    utf8Size = 0

    /**
     * A text value {@link https://doc.log10x.com/run/input/extract/#outer-text|extracted} from the input stream from 
     * which the object originated which encloses its {@link TenXBaseObject#text|text} field.
     * For example, if an object's text reflects a field extracted from a JSON object,
     * The value of 'fullText' will return the text of its entire enclosing JSON object.
     * @type {string}
     */
    fullText = "";

    /**
     * An array of {@link https://doc.log10x.com/run/transform/structure| variable sequences} extracted from the object's {@link TenXBaseObject#text|text}.
     * The {@link TenXArray.length} function can be used to query the number of elements in this array.
     * @type {(string[])} 
     * 
     * @example
     * export class HttpObject extends TenXObject {
     *   // Compute an HTTP error code field from the penultimate entry in vars[]
     *   // according to: https://httpd.apache.org/docs/2.4/logs.html schema.
     *   // For example, this will extract the '200' value into the 'code' field from:
     *   // 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
     *   constructor() {
     *     // Grab the penultimate variable value
     *     var code =  TenXMath.parseInt(this.vars[-2]); 
     *     // Validate it's in the correct range       
     *     this.code = (code >= 200) && (code < 600) ? code : 0;
     *   }
     * }
     */
    vars = null;
    
    /**
     * Returns whether the current object is an tenxTemplate instance.
     * To learn more see {@link https://doc.log10x.com/run/template|tenxTemplates}
     * @type {boolean}
     */
    isTemplate = false;

    /**
     * Returns whether the current instance is an object and not a template or summary instance.
     * @type {boolean}
     */
    isObject = false;

    /**
     * Returns whether the current tenxObject was read from a 10x-encoded input stream.
     * To learn more see {@link https://doc.log10x.com/run/transform/#encoding|Encoding}
     * @type {boolean}
     */
    isEncoded = false;

    /**
     * Returns whether the current object is a summary instance produced by an {@link https://doc.log10x.com/run/aggregate|aggregator}
     * @type {boolean}
     */
    isSummary = false;

     /**
     * A sequence of all symbol and delimiter tokens from the object's {@link TenXBaseObject#text|text} field.
     * To learn more see {@link https://doc.log10x.com/run/template/#structure|tenxTemplates}.
     * @type {string}
     */
     template = null;

    /**
     * An alphanumeric encoded value of a 64bit hash of the current object's {@link TenXBaseObject#template|template} field.
     * @type {string}
     */
    templateHash = null;

    /**
     * Returns the timestamp pattern for the specified timestamp.
     *
     * For example, for an event whose timestamp is equal to: '2021-09-16T02:33:05.289552Z',
     * the return value would be: yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'
     * 
     * To learn more see {@link https://doc.log10x.com/run/transform/timestamp|timestamp extraction}.
     * 
     * @param {number} [timestampIndex=0]    Index of the desired timestamp within the object's timestamp array.
     *
     * @return {string}                      Timestamp pattern if found, otherwise an empty value
     */
    timestampFormat(timestampIndex) {
        return TenXEngine.invoke(timestampIndex);
    }

    /**
     * Return true if length of {@link TenXBaseObject#timestamp|timestamp} is greater than 0
     * @type {boolean}    
     */
    timestamped = false;

    /**
     * The ordered route-state byte for this object (0 = pass). Set via route(name);
     * test via isRoute(name). Negative = left the pipeline (drop).
     * @type {number}
     */
    routeState = 0;

    /**
     * Returns the context in which the current object, template or summary was created.
     *    
     * At run time it may be needed to treat tenxObjects differently
     * based on the {@link https://doc.log10x.com/run/input/stream|input} or {@link https://doc.log10x.com/run/aggregate|aggregator} from which they originated.
     *
     * For example, to check if the current tenxObject was read from the
     * 'Fluentd' input, as configured via its {@link https://doc.log10x.com/run/input/stream/#inputname|inputName}, the following check can be made:
     *
     * @example   
     * class MyObject extends TenXObject {
     *    constructor() {
     * 
     *       if (this.inputName == "Fluentd") {
     *         TenXCounter.inc("Fluentd");
     *         if this.startsWith("DEBUG") this.drop();
     *      } 
     *    }
     * }
     * 
     * @type {string}    
     */
    inputName = "";
}

/**
 * @class
 * @classdesc
 * Serves as a base class to allow for custom {@link https://doc.log10x.com/run/input/stream|input} initialization.
 * 
 * Input constructors allow for the initialization of resources needed for event processing and aggregation
 * such as setting counters, loading lookup tables via {@link TenXLookup.load|load()}
 * or connecting to GeoIP DBs via {@link TenXLookup.loadGeoIPDB|loadGeoIPDB()}.
 *
 * These resources are available by {@link TenXObject} and  {@link TenXSummary} sub-class to enrich and filter instances. 
 *
 * The example below demonstrates initializing [HTTP lookups](https://doc.log10x.com/run/initialize/lookup).
 * @example
 * export class HttpInput extends TenXInput {
 *   constructor() {
 *     // Loads the 'http.csv' lookup table to enrich instances of 'HttpSummary' below.    
 *     TenXLookup.load("data/run/lookup/http.csv", true); 
 *   }
 * }
 * ```
 */
export class TenXInput {

    /**
     * The name of this input (e.g., 'myElastic') as defined by the {@link https://doc.log10x.com/run/input|input configuration}.
     */
    inputName = "";

    /**
     * Get the value of the input field value specified by a key name.
     *  
     * This function gets a specific entry from an input field whose values are 
     * shared between different tenxObjects of the same {@link https://doc.log10x.com/run/input/stream|input}.
     *
     * @param {string}	key	name of the input field entry to get.
     *
     * @return {number|string|boolean}	value of the input field item. Empty string if input field was not previously set.
     */
    static get(key) {
        return TenXEngine.invoke(key);
    }

    /**
     * Set the value of the input field specified by the key name.
     *
     * This function sets a specific entry from an input field whose values are 
     * shared between different tenxObjects of the same {@link https://doc.log10x.com/run/input/stream|input}.
     *
     * @param  {string}	key	                    Name of the input field to set.
     *
     * @param  {number|string|boolean}	value   Value to set in the input input field.
     *
     * @return {number|string|boolean}	        The value of the input field before the new value is set. 
     *                                          Empty string if set for the first time.
     */
    static set(key, value) {
        return TenXEngine.invoke(key, value);
    }
}

/**
 * @class
 * @classdesc
 * Serves as a base class to allow for custom {@link https://doc.log10x.com/run/output/stream|output} initialization.
 * 
 * Output constructors allow for the initialization of resources needed for event processing and aggregation
 * such as setting counters.
 *
 * Each option defined in the output's declaring module is available at runtime as a named member.
 * For example, the {@link https://doc.log10x.com/run/output/event/file/#outputfilepath|outputFilePath} option can be accessed 
 * as a named member of the output instance:
 *
 * ``` js
 * export class FileOutput extends TenXOutput {
 *     constructor() { 
 *         if (this.outputFilePath) {
 *             if (this.outputFileWriteObjects != false) {
 *                 if (this.outputFileWriteTemplates) {
 *                     TenXConsole.log("Writing TenXObjects and TenXTemplates to: " + this.outputFilePath);
 *                 } else {
 *                     TenXConsole.log("Writing TenXObjects to: " + this.outputFilePath);
 *                 }
 *             } else if (this.outputFileWriteTemplates ) {
 *                 TenXConsole.log("Writing TenXTemplates to: " + this.outputFilePath);
 *             }
 *         }
 *     }
 * }
 * ```
 */
export class TenXOutput {

    /**
     * Provides a logical name for the output instance as defined by its {@link https://doc.log10x.com/run/output/#output-modules|declaring module}.
     * @type {string}
     */
    outputName = "";

    /**
     * Provides the type of the output. Possible values: `file`, `stdout`, `event`, `metric`.
     * @type {string}
     */
    outputType = "";
}

/**
 * @class
 * @classdesc
 * Serves as a base class to allow for custom {@link https://doc.log10x.com/engine/pipeline/#units|pipeline unit} initialization and shutdown.
 *
 * Unit constructors allow for the initialization of resources needed for pipeline execution
 * such as setting counters and configuring unit-specific behavior.
 *
 * Unit close() methods allow for cleanup and reporting when a pipeline unit shuts down.
 * Close methods are called before the unit is terminated, while the unit is still fully functional.
 *
 * Each option defined in the unit's declaring module is available at runtime as a named member.
 * For example, unit configuration options can be accessed as named members of the unit instance:
 *
 * ``` js
 * // @loader: tenx
 *
 * import {TenXUnit, TenXEnv, TenXConsole} from '@tenx/tenx'
 *
 * export class ConfigLoadUnit extends TenXUnit {
 *
 *     // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
 *     static shouldLoad(config) {
 *        return !TenXEnv.get("quiet") && (config.unitName == "loadConfig")
 *     }
 *
 *     constructor() {
 *       TenXConsole.log("🛠️ Launching 10x Engine: Dev app (local development & testing environment)");
 *     }
 *
 *     close() {
 *       TenXConsole.log("🛠️ Shutting down: " + this.unitName);
 *     }
 * }
 * ```
 */
export class TenXUnit {

    /**
     * Provides a logical name for the unit instance as defined by its {@link https://doc.log10x.com/engine/pipeline/#units|declaring module}.
     * @type {string}
     */
    unitName = "";

    /**
     * Called when the pipeline unit is shutting down.
     *
     * Override this method to perform cleanup, log shutdown messages, or release resources
     * when a pipeline unit shuts down. The close() method is called while the unit is still
     * fully functional, before the unit's internal shutdown sequence begins.
     *
     * Like constructors, close() methods have access to all unit options as named members
     * (e.g., this.unitName) and can use TenXConsole, TenXEnv, and other TenX utility classes.
     *
     * The {@link TenXEngine.shouldLoad|shouldLoad} method controls whether a class's close()
     * method is invoked for a given unit, using the same filtering logic as the constructor.
     *
     * @example
     * export class SymbolLoaderUnit extends TenXUnit {
     *   static shouldLoad(config) {
     *     return !TenXEnv.get("quiet") && (config.unitName == "symbolLoader");
     *   }
     *
     *   constructor() {
     *     TenXConsole.log("Loading symbol libraries from: " + this.symbolPaths);
     *   }
     *
     *   close() {
     *     TenXConsole.log("Shutting down symbol loader: " + this.unitName);
     *   }
     * }
     */
    close() {
        TenXEngine.invoke();
    }
}

/** 
 * @class
 * @extends {TenXBaseObject}
 * @classdesc
 * 
 * Provide structured, reflective access to log/trace events read from input(s).
 * 
 * The 10x Engine {@link https://doc.log10x.com/run/transform/|transforms} semi/unstructured log and trace events read from input(s)
 * into well-defined, structured and reflectable tenxObjects. Sub-classes of this class can declare constructors and functions that enrich, group and filter instances. 
 * 
 * The 10x Engine can load multiple subclasses, in which case their constructors will be executed 
 * to initialize matching tenxObject instances in their order of loading. 
 * 
 * tenxObject instances provides access to the following capabilities:
 * 
 * ### Variables
 * 
 * The categorizes each value within an instance's {@link TenXBaseObject#text|text} 
 * into high-cardinality (e.g., IP, number, and GUID) and constant/low-cardinality (e.g., class, function, message) values
 * through the {@link TenXBaseObject#vars|vars} and {@link TenXObject#ipAddress|ipAddress} fields and the  {@link TenXBaseObject#token|token()} function. 
 * 
 * ### Timestamps
 * 
 *  Alphanumeric sequences convertible into a Unix Epoch values (e.g., 'Thursday, April 11, 2024 2:51:58 PM' -> 1712847118000)
 *  are {@link https://doc.log10x.com/run/transform/timestamp|extracted} and accessible via the {@link TenXObject#timestamp|timestamp} array.    
 * 
 * ### JSON/KV
 * 
 * {@link https://doc.log10x.com/run/transform/fields|Embedded fields} are accessible as named members. 
 * For example, if {@link TenXBaseObject#text|text} contains the following segments:  
 * `...{"price":1}... {"price":2}...price=3...price:4...'
 * `
 * Price values are accessible as 'this.price' for the first element and 'this.price[N]' for zero-based access.
 * The {@link TenXBaseObject#get|get} function allows the name of the field to be specified dynamically.
 *
 * ### tenxTemplate
 * 
 * The {@link TenXBaseObject#template|template} and {@link TenXBaseObject#templateHash|templateHash} fields return a string representation of 
 * the instance's {@link https://doc.log10x.com/run/template|tenxTemplate}.
 * 
 * ### Metric Name
 * 
 * The {@link TenXObject#metricName|metricName()} function omits delimiters and timestamps from {@link TenXBaseObject#template|template} to provide 
 * each instance with a Prometheus-compliant 'identity' for aggregation and {@link https://doc.log10x.com/run/output/metric|metric output}.
 * 
 * ### Reflection
 * 
 * The source code/binary executable {@link https://doc.log10x.com/run/transform/symbol|origin} of constant and low cardinality values and 
 * context within their origin file (e.g., class, function, printout) are queryable via the {@link  TenXObject#symbol|symbol()} and {@link  TenXObject#symbolSequence|symbolSequence()} functions.
 * 
 * ### Encoding
 * 
 * tenxObjects can be serialized like proto-buffers to reference (vs. repeat) information contained in their templates 
 * to reduce their footprint by > 50% via {@link TenXBaseObject#encodedText|encodedText} 
 * used by {@link https://doc.log10x.com/run/input/forwarder/module.yaml|Receiver compact-mode modules}.
 *  
 * ### Calculated Fields
 * 
 * New fields can be assigned to enrich each instance using any intrinsic/extracted fields, {@link symbolSequence|reflective} functions, {@link TenXEnv|launch arguments}
 * and {@link TenXLookup|text/GeoIP Lookups}. The example below enriches tenxObjects with HTTP code values:
 * ``` js
 * export class HttpObject extends TenXObject {
 *   // Compute an HTTP error code field from the penultimate variable token
 *   // according to: https://httpd.apache.org/docs/2.4/logs.html schema.
 *   // For example, this will extract the '200' value into the 'code' field from:
 *   // 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
 *   constructor() {
 *     // Grab the penultimate variable value
 *     var code =  TenXMath.parseInt(this.vars[-2]); 
 *     // Validate it's in the correct range       
 *     this.code = (code >= 200) && (code < 600) ? code : 0;
 *   }
 * }
 * ```
 * 
 * ### Filtering
 * 
 * An tenxObject instance whose information is not required for {@link https://doc.log10x.com/run/output|output} can be filtered via the {@link TenXObject#drop|drop()} function to save on storage and analytics costs.
 * Information can be extracted from the instance to add to {@link TenXCounter|counters} and set into {@link TenXInput|fields} before dropping it.
 *
 * ### Grouping
 * 
 * tenxObjects can form {@link https://doc.log10x.com/run/transform/group|logical groups} that
 * can be aggregated, filtered and encoded as a single composite object (e.g., stack traces that comprise multiple lines to describe a single error) using the {@link https://doc.log10x.com/run/transform/group/#groupexpressions|groupExpressions} setting.
 * 
 */
export class TenXObject extends TenXBaseObject {

    /**
     * Hard-drops the current instance from the 10x pipeline at construction time,
     * removing it from aggregation and output. To drop conditionally, pass the
     * predicate: `this.drop(this.startsWith("TRACE"))`.
     *
     * **Note**: Instances are structured from log/trace events 'on-demand'; that is if an instance is dropped
     * without first accessing its template members, significant performance gains can be achieved.
     *
     * #### Only the constructor can drop
     *
     * `drop()` removes an event only when called from a constructor. The engine
     * short-circuits at the lexer: a dropped event never reaches the subsequent
     * transform, group, aggregate, encode or output stages, and no further CPU is
     * spent on it. Resolve the drop predicate from intrinsic or extracted fields
     * available at construction time.
     *
     * Called later, from a getter or method invoked by a
     * {@link https://doc.log10x.com/run/transform/group/#groupfilters|groupFilter}
     * or {@link https://doc.log10x.com/run/output/filter|output filter}, `drop()`
     * is a no-op and returns `false`: the event has already been materialized and
     * is past the lexer, so it can no longer be removed. To act on a materialized
     * event, tag it with {@link TenXObject#route|route("name")} and have the stream
     * recipe honor the marker, testing it with {@link TenXObject#isRoute|isRoute("name")}.
     *
     * @example
     * export class FilteredObject extends TenXObject {
     *   constructor() {
     *     // Fast path: drop before structuring, no downstream work performed.
     *     this.drop(this.startsWith("TRACE"));
     *
     *     // Drops after structuring (vars[-2] requires a parsed object), still on the fast path
     *     // because the decision is made in the constructor.
     *     this.drop(this.vars[-2] != 200);
     *    }
     *  }
     *
     * @param {boolean} [condition=true] If truthy, the current object is dropped.
     *
     * @return {boolean}                 whether the instance was dropped: true from a
     *                                   constructor, false if called too late to remove it.
     */
    drop(condition) {
        return TenXEngine.invoke(condition);
    }

    /**
     * Route the current object to a named disposition: "drop", "pass", "compact",
     * "offload", "tier_down" or "sample". Replaces drop() for explicit routing.
     * An unknown name fails at config-load (literal) or per-event (dynamic).
     * @param {string} name the route name
     * @return {boolean} whether the object left the pipeline (routeState < 0)
     */
    route(name) {
        return TenXEngine.invoke(name);
    }

    /**
     * Returns true if the current object's routeState equals the named route.
     * Replaces reads of the old dropped/isDropped flag (use isRoute("drop")).
     * @param {string} name the route name to test
     * @return {boolean}
     */
    isRoute(name) {
        return TenXEngine.invoke(name);
    }

    /**
     * Returns the type of output (e.g. event, metric, stream, file, stdout) the current instance 
     * is currently being emitted to.
     *
     * This call can only be made within an {@link https://doc.log10x.com/run/output/stream|output context}
     * to control whether to serialize the current instance to a target output. 
     * 
     * For example, a {@link https://doc.log10x.com/run/receive|Receiver module} may set the 'printToOutput'
     * function below into the {@link https://doc.log10x.com/run/output/filter|outputStreamsFilter argument} 
     * to write only timestamped tenxObjects to the console output.
     *
     * @example
     * export class MyObject extends TenXObject { 
     *   get printOnlyTimestamped() {
     *     return this.outputType() == "stdout" ? this.timestamped : true;
     *   }
     * }
     * @param {string[]} [types=[]] An array value compared against the current output type.
     *                              If the array does not contain the output's type an empty string is returned 
     * 
     * @return {string} type of the current output (e.g., 'stdout', 'file', 'event', 'metric', 'stream') or an empty string
     *                  if the output type is not contained in the 'types' array.
     *                  
     */
    outputType(types) {
        return TenXEngine.invoke(types);
    }

    /**
     * Returns the 'path' value of an output the current instance is being serialized to.
     *
     * This call can only be made within an {@link https://doc.log10x.com/run/output/stream|output context}
     * to control whether to serialize the current instance to a target output. 
     * 
     * For example, a {@link https://doc.log10x.com/run/receive|Receiver module} may set the
     * {@link https://doc.log10x.com/run/output/filter|outputStreamsFilter argument} to the 'encodeToPrometheus'
     * function below that to only encode tenxObjects extracted from a 'message' JSON field to a Prometheus destination. 
     *
     * @example
     * export class MetricObject extends TenXObject {
     *   get encodeToPrometheus() {
     *     return TenXString.includes(this.outputPath(), "prometheus") ?
     *       this.extractorKey == "message" : false;
     *     }
     *  } 
     * 
     * @return {string} Path of the active output (e.g. file path, log4j appender, micrometer registry,.. )
     */
    outputPath() {
        return TenXEngine.invoke();
    }

    /**
     * Encodes the current object's log event into a compact, template‐based string.
     *
     * This method combines the object's `templateHash`, `timestamp` (in epoch form), and `vars`
     * fields to generate an efficient representation of the object's variable state—that is,
     * the values not contained in its shared `tenxTemplate`. This process effectively compresses
     * log events by referencing a pre-generated dictionary of low‐cardinality values.
     *
     * If the optional parameter `includeEnclosingText` is true, the returned encoded text will
     * be wrapped with the value of `fullText`, which provides context by representing the
     * tenxObject's encoded text within the full event from which it was extracted. This mode is
     * particularly useful for Forwarder inputs that need to ship template‐encoded tenxObjects
     * (for example, to Splunk or Elastic) along with their full associated context (such as
     * container ID and name).
     *
     * @function
     * @name encode
     * @memberof TenXObject
     * @param {boolean} [includeEnclosingText=true] - Indicates whether the returned encoded text
     * should be enclosed with the `fullText` (i.e., include the full event context).
     * @returns {string} A template-encoded representation of this instance.
     *
     * @example
     * 
     * For the following log event:
     * {"log":"[INFO] 127.0.0.1:48899 - 63371 \"HINFO IN 3388893353626257077.643398171450697041. udp 56 false 512\" NXDOMAIN qr,rd,ra 56 0.123504685s\n","stream":"stdout","docker":{"container_id":"4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e"},"kubernetes":{"container_name":"coredns","namespace_name":"kube-system","pod_name":"coredns-7db6d8ff4d-pddxj","container_image":"registry.k8s.io/coredns/coredns:v1.11.1","container_image_id":"docker-pullable://registry.k8s.io/coredns/coredns@sha256:1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1","pod_id":"38b91d65-ba47-4d0f-a689-711056955842","pod_ip":"10.244.0.99","host":"minikube","labels":{"k8s-app":"kube-dns","pod-template-hash":"7db6d8ff4d"}},"tenx_tag":"kubernetes.var.log.containers.coredns-7db6d8ff4d-pddxj_kube-system_coredns-4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e.log"}
     *
     * The following call for an tenxObject extracted from the event's `log` field:
     *
     * TenXConsole.log(this.encode(true));
     *
     * Will print:
     * {"log":"~-Kw0UHgdH_9,127,0,1,48899,63371,3388893353626257077,643398171450697041,56,512,123504685s","stream":"stdout","docker":{"container_id":"4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e"},"kubernetes":{"container_name":"coredns","namespace_name":"kube-system","pod_name":"coredns-7db6d8ff4d-pddxj","container_image":"registry.k8s.io/coredns/coredns:v1.11.1","container_image_id":"docker-pullable://registry.k8s.io/coredns/coredns@sha256:1eeb4c7316bacb1d4c8ead65571cd92dd21e27359f0d4917f1a5822a73b75db1","pod_id":"38b91d65-ba47-4d0f-a689-711056955842","pod_ip":"10.244.0.99","host":"minikube","labels":{"k8s-app":"kube-dns","pod-template-hash":"7db6d8ff4d"}},"tenx_tag":"kubernetes.var.log.containers.coredns-7db6d8ff4d-pddxj_kube-system_coredns-4c195cfdbf7e41f640631629970b9af2d8a1f40f63dcffd15edca84e2e2e497e.log"}
     *
     * Whereas a call to:
     *
     * this.encode(false)
     *
     * Will drop portions of the event not encoded, and return:
     *
     * ~-Kw0UHgdH_9,127,0,1,48899,63371,3388893353626257077,643398171450697041,56,512,123504685s 
     * 
    */
    encode(includeEnclosingText) {
        return TenXEngine.invoke(includeEnclosingText);
    }

   /**
     * Returns whether the object's {@link https://doc.log10x.com/run/template|tenxTemplate} was loaded from disk, 
     * an {@link https://doc.log10x.com/run/input/stream|input stream} or generated at runtime on the fly.
     * 
     * This function is commonly used by {@link https://doc.log10x.com/run/output/stream|output streams} to determine
     * whether to encode the object's {@link TenXBaseObject#template|template} to output, assuming pre-existing templates do not need to be shipped to output.
     *
     * @return {boolean} True if the object's template was generated on the fly.
     */
    isNewTemplate() {
        return TenXEngine.invoke();
    }

    /**
     * If the current instance is a logical group formed via {@link https://doc.log10x.com/run/transform/group/#groupexpressions|groupExpressions} returns the number of tenxObject within the group.
     * @type {number}
    */
    groupSize = 0;


    /**
     * If the current object was extracted from a pattern match or JSON field using an input extractor,
     * returns 'name' property of the extractor; otherwise an empty string.
     * To learn more see {@link https://doc.log10x.com/run/input/extract|input extractors}
     * @type {string}
     */
    extractorName = "";

    /**
     * If the object was extracted from a pattern match or JSON field using an input extractor,
     * returns the 'key' property of the extractor (i.e., the name of the JSON field or regex match group); 
     * otherwise empty string. 
     * To learn more see {@link https://doc.log10x.com/run/input/extract|input extractors}
     * @type {string}
     */
    extractorKey = "";

    /**
     * Returns the source value assigned to this instance by its input {@link https://doc.log10x.com/run/input/stream/#inputsourcepattern|source pattern}
     * @type {string}
     */
    source = "";

    /**
     * An array of UNIX epoch values of timestamps parsed from the object's {@link TenXBaseObject#text|text}.
     * The {@link TenXArray.length} function can be used to query the number of elements in this array.
     * To learn more about how timestamp values are extracted from events, see {@link https://doc.log10x.com/run/transform/timestamp|timestamps}.
     * @type {string[]}
     */
    timestamp = [0];

    /**
     * An array of string values of IPV4 parsed from the object's {@link TenXBaseObject#text|text}.
     * To geo-reference an entry in this array, see {@link TenXLookup.loadGeoIPDB|loadGeoIPDB()}.
     * 
     * @type {string[]}
     */
    ipAddress = [""];
    
    /**
     * An array of symbol source /binary file names from which class tokens within the object's {@link TenXBaseObject#text|text} originated.
     * This value is only available if {@link https://doc.log10x.com/run/symbol|symbol files} have been loaded.
     * To learn more see {@link https://doc.log10x.com/run/transform/symbol|symbol}.
     * @type {string[]}
     */
    classes = [""];
}


/**
 * @class
 * @extends {TenXBaseObject}
 * @classdesc
 * Access aggregate values of tenxObjects which share a target set of field values. 
 * 
 * {@link https://doc.log10x.com/run/aggregate|Aggregators} are defined in a similar way to "GROUP BY" SQL statements
 * which groups table rows based on specific columns. 
 *
 * Once the number of aggregated instances has exceeded a target threshold or interval,
 * the aggregator creates an instance of TenXSummary whose aggregated values are accessible as named members as well as 
 * via the intrinsic fields defined below. 
 * 
 * The example below demonstrates initializing TenXSummary instances using [HTTP lookups](https://doc.log10x.com/run/initialize/lookup).
 * 
 * ``` js
 * export class HttpSummary extends TenXSummary {
 *   // Calculate an HTTP message for TenxSummary instances.
 *   constructor() {
 *    if (this.code) this.message = TenXLookup.get("http", this.code);
 *   }
 * }
 * ```
*/
export class TenXSummary extends TenXBaseObject {

    /**
     * The number of tenxObjects whose values have been aggregated into this summary instance. 
     * @type {number}    
     */
    summaryVolume = 0;

    /**
     * The accumulative number of bytes in the values of {@link TenXBaseObject#text|text} fields
     * of objects whose values have been incorporated into this summary instance. 
     * @type {number}    
     */
    summaryBytes = 0;

    /**
     * Array of values by which tenxObjects have been grouped into this summary instance.
     * @type {string[]}    
     */
    summaryValues = [""];

    /**
     * A hash value of the {@link summaryValues} field used to
     * more concise representation of the values by which objects have been grouped into this summary.
     * @type {string}    
     */
    summaryValuesHash = "";

    /**
     * Sum values of the {@link https://doc.log10x.com/run/aggregate/#aggregatortotalfields|aggregatorTotalFields} value of tenxObjects aggregated into this instance. 
     * This value commonly specifies {@link https://www.baeldung.com/micrometer#2-counter|metric counter} values when writing TenXSummaries to {@link https://doc.log10x.com/run/output/metric/|time-series} outputs.
     * @type {number[]}    
     */
    summaryTotals = [0];    
}

/**
 * @class
 * @extends {TenXBaseObject}
 * @classdesc
 * 
 * The TenXEngine class implements an optimization model inspired by Chrome V8's
 * intelligent design principle (see {@link https://v8.dev/docs/hidden-classes#why-have-hidden-classes%3F|Hidden Classes}).
 * Instead of treating log events as unstructured "bags of properties," it assumes a finite
 * number of object shapes will emerge, following stereotypical usage templates.
 *
 * The engine uses symbol library files (see {@link https://doc.log10x.com/compile/link/#symbol-library|Symbol Library})
 * to assign a shared {@link https://doc.log10x.com/api/js/#TenXTemplate|TenXTemplate} (i.e., hidden class)
 * to input log/trace events with identical structure (see {@link https://doc.log10x.com/run/transform/structure|Structure}).
 * This creates a cached, optimized schema for each event type.
 *
 * By operating on well-defined TenXObjects, the engine enables direct access to symbol
 * and variable values (see {@link https://doc.log10x.com/run/transform/structure/#symbols|Symbols}
 * and {@link https://doc.log10x.com/run/transform/structure/#variables|Variables}) at runtime,
 * avoiding repeated JSON parsing or complex, brittle regular expression evaluations for each event.
 *
 * @example
 *   
 *    export LevelTemplate extends TenXTemplate {
 * 
 *      // Constructs a LevelTemplate instance, assigning a severity level based on symbol values.
 *      constructor() {
 *   
 *       // Check if the template's symbol value starts with any configured 'levelTerms' values.
 *       // Map the symbol value to a severity level.
 *       LevelTemplate.level = TenXString.startsWith(
 *       this.symbolSequence("", "log", 30),          // Capture first 30 characters of symbol values
 *       TenXMap.fromEntries(TenXEnv.get("levelTerms")) // Map symbol value to severity level
 *     );
 *   }
 */
export class TenXTemplate extends TenXBaseObject {

    /**
     * Returns the value of a target field of the current TenXTemplate instance.
     *
     * @method get
     * @static
     * @memberof TenXObject
     * @param {string} field - Field name whose value to return
     * @returns {number|string|boolean} Value of 'field'
     */
    static get(field) {
        return TenXEngine.invoke(field);
    }

    /**
     * Sets a target value into the current template field.
     * Similar to {@link https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Reflect/set|Reflect.set}.
     * Can only be called from within a TenXTemplate's constructor.
     *
     * @method set
     * @static
     * @memberof TenXObject
     * @param {string} field - Field name to set
     * @param {number|string|boolean} value - Value to assign to field
     * @returns {string|number|boolean} returns the value  set
     * @example
     * export class MessageTemplate extends TenXTemplate {
     * 
     *     constructor() {
     * 
     *         if (GroupTemplate.isGroup) {
     * 
     *             TenXTemplate.set(
     *                 TenXEnv.get("symbolMessageField"),
     *                 this.symbolSequence(
     *                     TenXEnv.get("symbolContexts", "log,exec"),
     *                     TenXEnv.get("inputField"),
     *                     TenXEnv.get("symbolMaxLen", 0)
     *                 )
     *             );
     *         }
     *     }
     * }
     */
    static set(field, value) {
        return TenXEngine.invoke(field, value);
    }
}

/// Utility classes

/**
 * 10x utility classes provide a library of string, array, number, and lookup processing functions, as well 
 * as for logging and printing to the console. The static functions provided in the classes below follow similar 
 * semantics to those provided by ECMA javascript standards whenever possible, but are primarily designed
 * to be implemented in the context of a 10x host runtime.
 */

/**
 * @class
 * @classdesc
 * Base class for collection utilities, providing shared methods for length and access.
 */
export class TenXCollection {
    /**
     * Returns the length of a collection (array or map).
     *
     * @param collection {number[]|string[]|Object}    the target collection 
     *
     * @return 	{number}      the number of elements in the collection
     */
    static length(collection) {
        return TenXEngine.invoke(collection);
    }

    /**
     * Returns an element from the collection by key or index.
     *
     * For arrays, 'key' is treated as index (number). For maps, 'key' is the string key.
     *
     * @param collection {number[]|string[]|Object}	    the collection from which to retrieve the target element
     *
     * @param {number|string} key    Key or index in collection. 
     *                              For arrays: positive/negative index (Python-style for negative).
     *                              For maps: string key.
     *
     * @param {*} [defValue]        Optional default value to return if the key/index is out of bounds or not found.
     *                              If not provided, an empty value is returned.
     *
     * @return 	the element at the specified key or index.
     * 			If out of bounds or not found, returns defValue if provided, otherwise an empty value is returned
     */
    static get(collection, key, defValue) {
        return TenXEngine.invoke(collection, key, defValue);
    }

    /**
     * Tests if a target collection contains the specified term.
     *
     * @param {Object|Array.<string>} collection array or map to search in.
     * @param {string|Array.<string>|Object} term Term to search for. If term is a string, checks if str (or any element/key) contains it. If term is an array, returns the first item from term contained in str (or any element/key). If term is a map generated by {@link TenXMap.fromEntries}, returns the value associated with the first key contained in str (or any element/key).
     * @return {boolean|string|*} Returns true if the collection contains the term. If term is an array, returns the first item from term that is contained within str (or any element in str if an array, or any key in str if a map), or undefined if no match. If term is a map generated by {@link TenXMap.fromEntries}, returns the value associated with the first key from term that is contained within the collection, or undefined if no match.
     */
    static includes(collection, term) {
        return TenXEngine.invoke(collection, term);
    }
}

/**
 * @class
 * @extends {TenXCollection}
 * @classdesc
 * Query array elements, length, and search.
 */
export class TenXArray extends TenXCollection {
    /**
     * Returns the index of the first occurrence of 'value' in 'list'.
     *
     * @param list {number[]|string[]}	    the array to search in
     *
     * @param value {number|string}         the value to search for
     *
     * @return {number}                     the index of the first occurrence, or -1 if not found
     */
    static indexOf(list, value) {
        return TenXEngine.invoke(list, value);
    }
}

/**
 * @class
 * @extends {TenXCollection}
 * @classdesc
 * Utilities for map (object) operations.
 */
export class TenXMap extends TenXCollection {
    /**
     * Returns a map object parsed from a list of values.
     * @static
     * @memberof TenXMap
     * @param {string[]} list - The array of values from which to parse the result map (e.g., `a=b,c=d,..`).
     * @param {string} [separator="="] - String to use to separate keys and values in the list. For separator `=`, returns: `{"a":"b","c":"d"}`.
     * @param {string} [keyName=""] - Name of key field name. For example, for keyName = `myKey` and valueName = `myVal`, returns: `[{"myKey":"a","myVal":"b"},{"myKey":"c","myVal":"d"}]`.
     * @param {string} [valueName=""] - Name of value field name (e.g., `myVal`). Required if `keyName` is specified.
     * @returns {Object} A map object parsed from the values array.
     * @example
     * class LevelTemplate extends TenXTemplate {
     *   constructor() {
     *     // Check the template's symbol value starts with any of the configured 'levelTerms' values
     *     // Use the fromEntries function to get the level value associated with a matching term
     *     let levelTerm = TenXString.startsWith(
     *       this.symbolSequence("", TenXEnv.get("inputField"), 30),
     *       TenXMap.fromEntries(TenXEnv.get("levelTerms"))
     *     );
     *     // If no match, try inferring from the template's timestamp pattern using configured 'levelTimestampPatterns' values
     *     if (!levelTerm) {
     *       levelTerm = TenXString.startsWith(
     *         this.timestampFormat(),
     *         TenXMap.fromEntries(TenXEnv.get("levelTimestampPatterns"))
     *       );
     *     }
     *   }
     * }
     */
    static fromEntries(list, separator = "=", keyName = "", valueName = "") {
        return TenXEngine.invoke(list, separator, keyName, valueName);
    }
}

/**
 * @class
 * @classdesc
 * Search, pattern-match and join string values.
 */
export class TenXString {

    /**
    * returns the length of a string value in a local variable or object field
    *
    * @param list {string} the target string
    *
    * @return 	{number}   the number of characters in the string
    */
    static length(list) {
        return TenXEngine.invoke(list);
    }

    /**
     * Returns an alphanumeric string representation of a 64bit hash of the supplied value.
     *
     * The hash is the same one used internally by the engine to populate
     * {@link TenXBaseObject#templateHash|templateHash}, encoded with the
     * JSON-safe alphanumeric encoding used across the platform. Use this when
     * a compact, stable, JSON-friendly identifier is needed for an arbitrary
     * string (e.g. a transaction id, a derived key, a deduplication tag).
     *
     * For a numeric (32bit) hash code see {@link TenXMath.hashCode}.
     *
     * @example
     *  this.transactionHash = TenXString.hash(this.transactionId);
     *
     * @param {string} value Value to hash
     *
     * @return {string}      Alphanumeric encoding of the 64bit hash, or null if value is null
     */
    static hash(value) {
        return TenXEngine.invoke(value);
    }

    /**
     * Splits the 'str' string around matches of delimiter.
     *
     * The array returned by this method contains each substring of this
     * string that is terminated by another substring that matches the given
     * delimiter. The substrings in the array are in the order in which they occur in this string.
     * If the expression does not match any part of the input, then the resulting array
     * has just one element, namely str.
     *
     * The limit parameter controls the number of times the
     * pattern is applied and therefore affects the length of the resulting
     * array.
     *
     * If the limit is positive, then the pattern will be applied
     * at most limit - 1 times, the array's length will be
     * no greater than the limit, and the array's last entry will contain
     * all input beyond the last matched delimiter.
     *
     * If the limit is zero, then the pattern will be applied as
     * many times as possible, the array can have any length and trailing
     * empty strings will be discarded.
     *
     *  If the limit is negative, then the pattern will be applied
     *  as many times as possible, and the array can be any length.
     *
     * @param  {string} str        String to split
     * @param  {string} delimiter  Delimiting string
     * @param  {number} [limit]    Result threshold, as described above
     *  
     * @return  {string[]}         Array of strings computed by splitting string around matches of the delimiter
     */
    static split(str, delimiter, limit) {
        return TenXEngine.invoke(str, delimiter, limit);
    }

    /**
     * Tests if a target string, array of strings, or map contains the specified term.
     * @static
     * @memberof TenXString
     * @param {string|string[]|Object} str - String, array of strings, or map to search in.
     * @param {string|string[]|Object} term - Term to search for. If term is a string, checks if str (or any element/key) contains it. If term is an array, returns the first item from term contained in str (or any element/key). If term is a map generated by {@link TenXMap.fromEntries}, returns the value associated with the first key contained in str (or any element/key).
     * @returns {boolean|string|*} Returns true if term is a string and str (or any element in str if an array, or any key in str if a map) contains it. If term is an array, returns the first item from term that is contained within str (or any element/key), or undefined if no match. If term is a map, returns the value associated with the first key contained in str (or any element/key), or undefined if no match.
     */
    static includes(str, ...term) {
        return TenXEngine.invoke(str, term);
    }

    /**
     * Tests if a target string starts with the specified prefix.
     * @static
     * @memberof TenXString
     * @param {string} str - String to search in.
     * @param {string|string[]|Object} prefix - Prefix to match. If prefix is a string, checks if str starts with it. If prefix is an array, returns the first matching item from the array if str starts with it. If prefix is a map generated by {@link TenXMap.fromEntries}, returns the value from the map corresponding to the key that str starts with.
     * @returns {boolean|string|*} Returns true if prefix is a string and str starts with it, or if prefix is an empty string or equal to str. If prefix is an array, returns the matching item or undefined if no match. If prefix is a map, returns the value corresponding to the matching key or undefined if no match.
     */
    static startsWith(str, prefix) {
        return TenXEngine.invoke(str, prefix);
    }

    /**
     * Tests if a target string ends with the specified postfix.
     * @static
     * @memberof TenXString
     * @param {string} str - String to search in.
     * @param {string|string[]|Object} postfix - Postfix to match. If postfix is a string, checks if str ends with it. If postfix is an array, returns the first matching item from the array if str ends with it. If postfix is a map generated by {@link TenXMap.fromEntries}, returns the value from the map corresponding to the key that str ends with.
     * @returns {boolean|string|*} Returns true if postfix is a string and str ends with it, or if postfix is an empty string or equal to str. If postfix is an array, returns the matching item or undefined if no match. If postfix is a map, returns the value corresponding to the matching key or undefined if no match.
     */
    static endsWith(str, suffix) {
        return TenXEngine.invoke(str, suffix);
    }

    /**
     * Returns the index within the search string of the first occurrence of the
     * specified substring, starting at the specified index.
     *
     * @param   str {string|string[]}        Substring or array to search in.
     *
     * @param   term {string}                Substring to search for.
     *
     * @param   fromIndex {number}           Index from which to start the search if 'str' is a string
     *
     * @return  {number}            the index of the first occurrence of the specified substring or array,
     *                              starting at the specified index,  or -1 if there is no such occurrence.
     */
    static indexOf(searchIn, term, fromIndex) {
        return TenXEngine.invoke(searchIn, term, fromIndex);
    }

    /**
     * Returns the index within str of the last occurrence of the
     * specified substring, searching backward starting at the specified index.
     *
     * @param   str  {string}       String to search in.
     *
     * @param   term {string}       Substring to search for.
     *
     * @param   fromIndex {number}  Index in str to start the search from.
     *
     * @return  {number} the index of the last occurrence of the specified substring,
     *          searching backward from the specified index,
     *          or -1 if there is no such occurrence.
     */
    static lastIndexOf(str, term, fromIndex) {
        return TenXEngine.invoke(str, term, fromIndex);
    }

    /**
     * Converts all of the characters in str to lowercase.
     *
     * @param str {string}    String to convert.
     *
     * @return {string}       String, converted to lowercase.
     *
     */
    static toLowerCase(str) {
        return TenXEngine.invoke(str);
    }

    /**
     * Converts all of the characters in str to uppercase.
     *
     * @param str {string}  String to convert. 
     * 
     * @return {string}     String, converted to uppercase.
     *
     */
    static toUpperCase(str) {
        return TenXEngine.invoke(str);
    }

    /**
     * Returns a list of matches of the specified pattern within str.
     *
     * @param str {string}	    String to search in. 
     *
     * @param pattern {string}	Regex pattern to match
     *
     * @return 	{string[]}        List of matches within str. If no match is found, an empty array is returned
     */
    static matchAll(str, pattern) {
        return TenXEngine.invoke(str, pattern);
    }

    /**
     * Returns the first matches of the specified pattern within str.
     *
     * @param str {string}	    String to search in. 
     *
     * @param pattern {string}	Regex pattern to match
     *
     * @return 	{string}    First string segment matching the pattern.
     * 					    If no match is found, an empty string is returned
     */
    static match(str, pattern) {
        return TenXEngine.invoke(str, pattern);
    }

    /**
     * Replaces each substring in str that matches the literal target
     * sequence with the specified literal replacement sequence. 
     * 
     * The replacement proceeds from the beginning of the string to the end for
     * For example, replacing "aa" with "b" in the string "aaa" will result in
     * "ba" rather than "ab".
     *
     * @param  str {string}     The string to search in.
     *
     * @param  target {string} The sequence of char values to be replaced
     *
     * @param  replacement {string} The replacement sequence of char values
     *
     * @return {string} The resulting string
     */
    static replace(str, target, replacement) {
        return TenXEngine.invoke(str, target, replacement);
    }

    /**
     * Returns a string that is a substring of 'str'.
     * 
     * The substring begins at the specified beginIndex and extends to the character at index endIndex - 1.
     * Thus, the length of the substring is endIndex-beginIndex.
     *
     * @param {string} str   		 String to search in. 
     *
     * @param {number}  beginIndex    Beginning index, inclusive.
     *                                If negative, length(str) + beginIndex is used. If not provided, 0 is used
     *
     * @param {number}  endIndex      Ending index, exclusive.
     *                                If negative, length(str) + endIndex is used. If not provided, length(str) is used
     *
     * @return {string}               Specified substring.
     */
    static substring(str, beginIndex, endIndex) {
        return TenXEngine.invoke(str, beginIndex, endIndex);
    }

    /**
     * Returns a new String composed of elements joined together with the specified delimiter.
     *
     * @param  delimiter {string}   Delimiter that separates each element
     *
     * @param  elements  {string[]} Elements to join together.
     *
     * @return {string}             String composed of the elements separated by the delimiter
     */
    static join(delimiter, ...elements) {
        return TenXEngine.invoke(delimiter, elements);
    }

    /**
     * Returns a new String composed of elements joined together.
     * 
     * @param  elements {string[]}   Elements to join together.
     *
     * @return {string}              String composed of the elements
     */
    static concat(...elements) {
        return TenXEngine.invoke(elements);
    }

    /**
      *	Returns a JSON representation of an array of input values.
      *
      *	If 'values' is provided, this function returns a JSON object of the values passed similar to 
      * {@link https://www.w3schools.com/js/js_json_stringify.asp|JSON.stringify()}
      *	
      * @example
      * this.print(this.stringify(
      *   "now", TenXDate.now(), 
      *   "str", "hello" + " world")
      * );
      * 
      *  will print: {"now": 1661782307673, "str": "hello world"}
      *
      * @param values {Object[]}        Even-numbered array of values to format
  
      * @return {string}			    JSON representation of the 'values' array 
      *
      */
    static stringify(...values) {
        return TenXEngine.invoke(values);
    }

    /**
     * Applies a JsonPath query to a JSON string and returns the result.
     *
     * This function parses the JSON string and applies the JsonPath query expression
     * to extract specific values or data structures from the JSON object.
     * JsonPath is a query language for JSON, similar to XPath for XML.
     *
     * @param {string} json    The JSON string to query
     * @param {string} path    The JsonPath expression to apply
     * 
     * @return {*}             The result of the JsonPath query. Can be a single value, 
     *                         an array of values, or undefined if no match is found.
     *
     * @example
     * // Given JSON: {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
     * // Extract all user names:
     * TenXString.jsonPath(jsonStr, "$.users[*].name")  // returns ["Alice", "Bob"]
     * 
     * // Extract first user's age:
     * TenXString.jsonPath(jsonStr, "$.users[0].age")   // returns 30
     */
    static jsonPath(json, path) {
        return TenXEngine.invoke(json, path);
    }
}

/**
 * @class
 * @classdesc
 * Load and query the values of text lookup tables (.csv, .tsv) and geoIP DB files (.mmdb).
 */
export class TenXLookup {

    /**
    * Load a comma/tab-delimited text lookup table into memory. 
    * 
    * An event may hold a value in a field that may need to be translated
    * to another using a key/value map for a specific action to be taken, or for the event
    * to be correctly encoded for output. 
    * 
    * This function scans a text file containing comma/tab
    * delimited rows to create an efficient in-memory table that can be used
    * to locate specific rows based on a selected column value and
    * retrieve the value of a specified value column. 
    * 
    * For example, the "example.csv" file can be loaded into memory in the following manner:
    * 
    * ``` js
    * TenXLookup.load("example.csv", true, "Model", "Year", "Maker")
    * ```
    *    
    * Column names are extracted from the header of the file, and the file is scanned
    * to index the file positions of the "Model", "Year" and "Maker" column values. 
    * 
    * Indexing allows for random access to column values without having to scan the file
    * each time the lookup table is queried. Queries to the table can be made via subsequent calls
    * to the {@link lookup()} function to locate the maker of the "Focus" model (e.g., "Ford"). 
    * This function supports the loading of text lookup files, which can span GBs of data
    * without having to load them into memory in their raw form or scan them each time the lookup is queried  
    * 
    * @example
    * this.maker = TenXLookup.get("example", this.model,  "Model",  "Maker"); 
    * 
    * @param lookup {string}   the name of the lookup file. If the name is a canonized path name
    * 					       it is used as-is to locate the file. 
    *  
    * @param {boolean} [extractColumns=true] specifies whether the first row of the file should be used 
    * 						to determine the column names. If set to false, access to column names
    * 						with subsequent calls to the {@link lookup} function will need to be made
    * 						using numeric column indexes vs. alphanumeric names.
    * 
    * @param columns {string[]}	an array of up to 5 column names to index in memory. This provides
    * 						    fast access to column values without having to re-scan the file when querying the lookup
    * 
    * 
    * @return	{number}   The lastModified value (UNIX epoch in milliseconds) of the lookup file on disk 
    *                     (similar to the parameterless overload of {@link TenXLookup.lastModified|lastModified()}),
    *                     allowing the calling TenxInput instance to validate the lookup file's freshness. 
    *                     Raises an error if the lookup file could not be loaded.
    */
    static load(lookup, extractColumns, ...columns) {
        return TenXEngine.invoke(lookup, extractColumns, columns);
    }

    /**
    * Load a text lookup table whose file may not exist yet.
    *
    * Same arguments as {@link TenXLookup.load|load()}. A file that is absent loads as an empty
    * table, every lookup misses, and the table loads when the file appears. Use it for a
    * policy file that ships alone, such as an actions file beside a cap file.
    *
    * @param {string} lookup - path of the lookup file (.csv or .tsv)
    * @param {boolean} [extractColumns=true] - read column names from the header row
    * @param {...string} columns - column names to index
    * @returns {number} the file's last-modified time, 0 while the file is absent
    */
    static loadIfExists(lookup, extractColumns, ...columns) {
        return TenXEngine.invoke(lookup, extractColumns, columns);
    }

    /**
    * Loads a GeoIP DB file to allow the geo location of host IP addresses.
    *
    * This function uses the {@link https://www.maxmind.com/en/geoip2-databases|Maxmind}
    * client library to connect to a GeoIP DB file. Once connected, the {@link TenXLookup.get|get()} function
    * can be used to query the location attributes of a target host IP address.
    * 
    * Supported lookup fields provided for an IP address are:
    * - Continent
    * - Country
    * - Subdivision
    * - City
    * - Postal
    * - Latitude
    * - Longitude
    *
    * Field names are case insensitive.
    *
    * The following call will load a MaxMind GeoIP db as part of input initialization:
    * 
    * ``` js
    * export class CountryInput extends TenXInput {
    *   constructor() {
    *     TenXLookup.loadGeoIPDB("GeoLite2-City.mmdb");
    *   }
    * }
    * ```
    *
    * tenxObject constructors can use the calls to {@link TenXLookup.get|get()} can
    * translate the {@link TenXObject#ipAddress|ipAddress} field into its matching country value:
    * ``` js
    * export class CountryObject extends TenXObject {
    *   constructor() {
    *     this.country = TenXLookup.get("GeoLite2-City", this.ipAddress, "country");
    *   }
    * }
    * ```
        *
        * @param 	fileName {string}   Path to the GeoIP DB file. 
        * 
        * @return 	{number}            The lastModified value (UNIX epoch in milliseconds) of the GeoIP DB file on disk
        *                              (similar to the parameterless overload of {@link TenXLookup.lastModified|lastModified()}),
        *                              allowing the calling TenxInput instance to validate the lookup file's freshness. 
        *                              Raises an error if the lookup file could not be loaded.
        *
        */
    static loadGeoIPDB(fileName) {
        return TenXEngine.invoke(fileName);
    }

    /**
    * Query a previously loaded lookup table using a specific key
    * 
    * This function queries a lookup table that has been previously loaded
    * via a call to {@link TenXLookup.load|load()} or {@link TenXLookup.loadGeoIPDB|loadGeoIPDB()} 
    * for a specific column value using a key and value column names.
    * 
    * For example, to calculate the make of a car object using an tenxObject's extracted/calculated 'model' field
    * from the 'examples' lookup table loaded via {@link TenXLookup.load|load()}, use:
    * 
    * @example
    * export class Car extends TenXObject {
    *   constructor() {
    *     this.make = TenXLookup.get("examples", this.model, "model", "make"); 
    *   }
    * }
    *
    * @param lookup {string}    the name of the lookup to access. This name can be that of a 
    * 				            .csv/.tsv text file or geoIP DB previously loaded via {@link TenXLookup.load|load()}
    *                           Lookup table names are case insensitive, and the parent folder and file extension
    *                           can be omitted (e.g., specify 'examples' vs. '/etc/lookups/examples.csv')  
    *
    * @param key {string}		the lookup key value to search for, such as a 
    * 						    a host IP for a GeoIP DB or comma/tab-delimited value to look for within a .csv/.tsv text file.
    * 
    *  @param {string|number} [keyColumn=0] Name of the column containing the key value, or its zero-based numeric index in the lookup table. 
    * 
    *  @param {string|number} [valueColumn=0] Name of the value column from which to retrieve
    * 							              the function's result value or its zero-based numeric index in the lookup table. 
    * 
    * @return	{string}		Value held within the table's 'valueColumn' for the row whose 'keyColumn' is equal to 'key'.
    * 							If the key is not found, an empty string is returned.
    */
    static get(lookup, key, keyColumnName, valueColumnName) {
        return TenXEngine.invoke(lookup, key, keyColumnName, valueColumnName);
    }

   /**
     * Checks whether a specified lookup table has a row matching the current tenxObject equivalent fields.
     *
     * This function scans a lookup table that has been previously loaded
     * via a call to {@link TenXLookup.load|load()} for a row whose values matches those of fields
     * identified by the table's columns within the current object. The lookup table must be loaded
     * with an 'extractColumns' argument set to true for this function to operate correctly.
     *
     * For example, a 'dropPolicy.csv' lookup table containing a 'message' and 'severity' columns may be queried
     * against the current object's (intrinsic/calculated/extracted) fields of the same two names. If the
     * current object's 'message' and 'severity' fields match the values of a target row within the lookup -
     * the call would return true.
     *
     * The lookup table can be further synchronized with a GitHub repository to allow changes to the table
     * to be made and reflected within the lifetime of the current 10x Engine via {@link https://doc.log10x.com/run/reload/}.
     *
     * @example
     * if (TenXLookup.match("dropPolicy.csv") { // check whether 'this.message' and 'this.severity' are found in the table
     *   this.drop();                          // if so - filter out the current object
     * }
     *
     * @param lookup {string}    the name of the lookup to access. This name can be the name  of a
     * 				             .csv/.tsv text file previously loaded via {@link TenXLookup.load|load()}.
     *                           Lookup table names are case insensitive, and the parent folder/file extension
     *                           may be omitted (e.g., specify 'examples' vs. '/etc/lookups/examples.csv')
     *
     *
     * @return	{boolean}		whether the lookup table contains a row whose values match those
     *                           of current object's (intrinsic/calculated/extracted) fields named by the table's columns.
     */
    static lookupMatch(lookup) {
        return TenXEngine.invoke(lookup);
    }

    /**
     * Returns the last modified time of a lookup file as a 64-bit epoch timestamp,
     * or checks if the lookup is fresh based on a specified age threshold.
     *
     * Allows determination of lookup data "freshness" by returning the last modification
     * time of the underlying lookup file on disk. Lookup files can be configured to sync 
     * with GitHub or reload from disk when changes occur.
     *
     * This function helps determine when lookup data was last updated, which is useful
     * for monitoring data currency and triggering refresh operations when needed.
     *
     * @param lookupName {string}    The name of the lookup whose last modified time to retrieve
     *
     * @param {number} [offset]      Optional. Maximum age in milliseconds to consider the lookup "fresh".
     *                               If provided, the function returns true if the lookup is fresh 
     *                               (lastModified > TenXDate.now() - offset), false if stale.
     *                               If not provided, returns the timestamp.
     *
     * @return {number|boolean}      If offset is not provided: 64-bit epoch timestamp of the last modification time.
     *                               If offset is provided: true if lookup is fresh, false if stale.
     *
     * @example
     * // Get the last modified timestamp
     * let lastMod = TenXLookup.lastModified(TenXEnv.get("geoIpLookFile"));
     * let twentyFourHoursAgo = TenXDate.now("-24h");
     *
     * if (TenXDate.isBefore(lastMod, twentyFourHoursAgo)) {
     *   throw new Error("GeoIP lookup data is stale (older than 24h), last modified: " +
     *     TenXDate.format(lastMod, "yyyy-MM-dd HH:mm:ss"));
     * }
     *
     * @example
     * // Check if lookup is fresh (less than 5 minutes old)
     * if (!TenXLookup.lastModified(TenXEnv.get("geoIpLookFile"), 60000 * 5)) {
     *   throw new Error("GeoIP lookup data is stale (older than 5 minutes)");
     * }
     * 
     * // Load the GeoIP database if fresh
     * TenXLookup.loadGeoIPDB(TenXEnv.get("geoIpLookFile"));
     *
     * @see {@link https://doc.log10x.com/run/reload/} - Config reload
     * @see {@link https://doc.log10x.com/config/github/} - GitHub sync
     */
    static lastModified(lookupName, offset) {
        return TenXEngine.invoke(lookupName, offset);
    }
}

/**
 * @class
 * @classdesc
 * Print values to the host process' stdout/stderr output streams.
 */
export class TenXConsole {

    /**
     * Prints a set of values to the stdout device
     *
     * This function prints an array of values into the stdout device.
     * If the _values_ array is empty, the value of {@link TenXObject#joinFields|joinFields}  is used.
     * @param {Object[]} [values=null] the list of values to print.
     *
     * @return{string}	          the actual string printed to the console
     */
    static log(...values) {
        return TenXEngine.invoke(values);
    }

    /**
     * Prints a set of values to the stderr device
     *
     * This function prints an array of values to the stderr device.
     * If the _values_ array is empty, the value of {@link TenXObject#joinFields|joinFields}  is used.
     * @param {Object[]} [values=[]] the list of values to print.
     *
     * @return  {string}	      the actual string printed to the console
     */
    static error(...values) {
        return TenXEngine.invoke(values);
    }
}

/**
 * @class
 * @classdesc
 * Access system time and formatting/parsing date values. 
 */
export class TenXDate {

    /**
     * Returns the current epoch time in milliseconds plus a specified offset
     *
     * @param {string|number} [offset=0]  Offset duration to be added to the current epoch time. 
     *                                    If a string is provided (e.g., "-1h", "30sec"), it is converted into milliseconds.
     *                                    If a number is provided, it is treated as a +/- millisecond numeric offset.
     *
     *
     * @return {number} Difference, measured in milliseconds, between the current time + offset
     *                  and midnight, January 1, 1970 UTC
     */
    static now(offset) {
        return TenXEngine.invoke(offset);
    }

    /**
     * Parses a string value into an epoch value based on a specified pattern
     *
     * @example
     * TenXConsole.log(TenXDate.parse("2021-09-16T02:33:05.289552Z", "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'"));
     *
     * will output: 1631773985289
     *
     * @param str {string}      String to parse
     *
     * @param pattern {string}  Date-time pattern
     *
     * @return 	{number}        Numerical value holding the epoch time resulting
     * 				            from parsing str based on the pattern. If parsing fails, 0 is returned
     */
    static parse(str, pattern) {
        return TenXEngine.invoke(str, pattern);
    }

    /**
     * Formats a numeric epoch value into a string representation based on a specified pattern
     *
     * @example
     * TenXConsole.log(TenXDate.format(1631773985289, "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'"));
     * 
     * will output: 2021-09-16T02:33:05.289552
     *
     * @param epoch	{number}	Epoch value to format
     *
     * @param pattern {string}	Date-time pattern to apply
     *
     * @return {string}		    Numerical value holding the epoch time resulting
     * 				            from formatting epoch based on pattern. If formatting fails, an empty string is returned
     */
    static format(epoch, pattern) {
        return TenXEngine.invoke(epoch, pattern);
    }

    /**
     * Parses a duration string and converts it to milliseconds
     *
     * @example
     * TenXConsole.log(TenXDate.parseDuration("6d"));
     * 
     * will output: 518400000 (6 days in milliseconds)
     * 
     * @example
     * TenXConsole.log(TenXDate.parseDuration("3min"));
     * 
     * will output: 180000 (3 minutes in milliseconds)
     *
     * @param duration {string}  Duration string to parse (e.g., "6d", "3min", "1h", "30sec", "500ms")
     *                          Supported units: ms (milliseconds), sec/s (seconds), min/m (minutes), 
     *                          h (hours), d (days), w (weeks)
     *
     * @return {number}         Numerical value holding the duration in milliseconds.
     *                          If parsing fails, 0 is returned
     */
    static parseDuration(duration) {
        return TenXEngine.invoke(duration);
    }

    /**
     * Checks if the first epoch timestamp is before the second epoch timestamp.
     * Handles both millisecond and nanosecond epoch formats automatically.
     *
     * @example
     * TenXDate.isBefore(1631773985289, 1631773985290); // returns true
     *
     * @example
     * TenXDate.isBefore(this.timestamp, TenXDate.now()); // compare event time to current time
     *
     * @param left {number}   First epoch timestamp to compare (milliseconds or nanoseconds)
     * @param right {number}  Second epoch timestamp to compare (milliseconds or nanoseconds)
     *
     * @return {boolean}      true if left < right, false otherwise
     *
     * @throws {IllegalArgumentException} if either argument is null, not a valid number, or negative
     */
    static isBefore(left, right) {
        return TenXEngine.invoke(left, right);
    }

    /**
     * Checks if the first epoch timestamp is before or equal to the second epoch timestamp.
     * Handles both millisecond and nanosecond epoch formats automatically.
     *
     * @example
     * TenXDate.isBeforeOrEqual(1631773985289, 1631773985289); // returns true
     *
     * @example
     * TenXDate.isBeforeOrEqual(this.timestamp, TenXEnv.get("cutoff_time")); // compare event time to cutoff
     *
     * @param left {number}   First epoch timestamp to compare (milliseconds or nanoseconds)
     * @param right {number}  Second epoch timestamp to compare (milliseconds or nanoseconds)
     *
     * @return {boolean}      true if left <= right, false otherwise
     *
     * @throws {IllegalArgumentException} if either argument is null, not a valid number, or negative
     */
    static isBeforeOrEqual(left, right) {
        return TenXEngine.invoke(left, right);
    }

    /**
     * Checks if the first epoch timestamp is after the second epoch timestamp.
     * Handles both millisecond and nanosecond epoch formats automatically.
     *
     * @example
     * TenXDate.isAfter(1631773985290, 1631773985289); // returns true
     *
     * @example
     * TenXDate.isAfter(this.timestamp, TenXDate.now("-1h")); // check if event is within the last hour
     *
     * @param left {number}   First epoch timestamp to compare (milliseconds or nanoseconds)
     * @param right {number}  Second epoch timestamp to compare (milliseconds or nanoseconds)
     *
     * @return {boolean}      true if left > right, false otherwise
     *
     * @throws {IllegalArgumentException} if either argument is null, not a valid number, or negative
     */
    static isAfter(left, right) {
        return TenXEngine.invoke(left, right);
    }

    /**
     * Checks if the first epoch timestamp is after or equal to the second epoch timestamp.
     * Handles both millisecond and nanosecond epoch formats automatically.
     *
     * @example
     * TenXDate.isAfterOrEqual(1631773985289, 1631773985289); // returns true
     *
     * @example
     * TenXDate.isAfterOrEqual(this.timestamp, TenXEnv.get("start_time")); // check if event is at or after start
     *
     * @param left {number}   First epoch timestamp to compare (milliseconds or nanoseconds)
     * @param right {number}  Second epoch timestamp to compare (milliseconds or nanoseconds)
     *
     * @return {boolean}      true if left >= right, false otherwise
     *
     * @throws {IllegalArgumentException} if either argument is null, not a valid number, or negative
     */
    static isAfterOrEqual(left, right) {
        return TenXEngine.invoke(left, right);
    }
}



/**
 * @class
 * @classdesc
 * Get and set the values of global atomic counters.
 */
export class TenXCounter {

    /**
      * Returns the value of the specified atomic counter. If no counter
      * by this name found it is created.
      *
      * @param {string} [counter=default]   Name of the counter whose value to get.
      *
      * @return {number}		            Value of the counter 
      */
    static get(counter) {
        return TenXEngine.invoke(counter);
    }

    /**
      * Increase and return the value of the selected atomic counter by a specified value.
      * 
      * To add the values of the current object's calculated/extracted 'price' field to a 'purchases' counter:
      * @example
      * TenXCounter.inc("purchases", this.price);
      * 
      * @param {string} [counter=default]	 Name of the counter to get.
      * 
      * @param {number} [value=1]	         Value by which to increase the counter.
      * 
     * @param {string|number} [resetInterval=""]	 Repeating interval after which the counter is reset to 0.
     *                                              Can be a number (milliseconds), string interval (e.g., "10s", "1min"), 
     *                                              ISO-8601 duration format (e.g., "PT10S", "PT1M"), or name of a variable containing it.
     * 						                     This value cannot exceed 255 seconds and is rounded up to the second.
      *
      * 
      * @return 	{number}		        Value of the counter after 'value' has been added to it
      */
    static inc(counter, value, resetInterval) {
        return TenXEngine.invoke(counter, value, resetInterval);
    }

  /**
   * Increase the value of the selected counter by a specified value and return its value before increase.
   * 
   * To add the values of the current object's calculated/extracted 'price' field in a 'purchases' counter:
   * @example
   * TenXCounter.getAndInc("purchases", this.price);
   * 
   * @param {string} [counter=default]   Name of the counter whose value to get.
   * 
   * @param {number} [value=1]           The value by which to increase the counter.
   * 
   * @param {string|number} [resetInterval=""]	 Repeating interval after which the counter is reset to 0.
   *                                            Can be a number (milliseconds), string interval (e.g., "10s", "1min"), 
   *                                            ISO-8601 duration format (e.g., "PT10S", "PT1M"), or name of a variable containing it.
   * 						                   This value cannot exceed 255 seconds and is rounded up to the second.
   *
   * 
   * @return 	{number}		         The value of the counter before 'value' has been added to it
   */
    static getAndInc(counter, value, resetInterval) {
        return TenXEngine.invoke(counter, value, resetInterval);
    }

    /**
     * Set the value of a target 64bit atomic counter to a specified value
     * and optionally reset every target interval.
     *
     * A counter can be used to aggregate the number of events matching a specific condition:
     *
     * ``` js
     * export class MyObject extends TenXObject {
     *
     * 	    MyObject() {
     * 	        if this.startsWith("ERROR")
     *              TenXCounter.inc("errors");
     * 	    }
     * }
     * ```
     *
     * The counter can then be atomically queried and reset into a summary instance:
     *
     *  ``` js
     *  export class ErrorSummary extends TenXSummary {
     *    constructor() {
     *      this.errors = TenXCounter.getAndSet("errors", 0);
     *    }
     *  }
     * ```
     * 
     * An interval counter can be used to limit the rate of tenxObjects
     * based on their {@link TenXObject#metricName|metricName} to a target limit (e.g. 1000) within a
     * specific interval (e.g. "1s"). This prevents a "chatty" event from "hogging" the pipeline's bandwidth:
     *
     * ``` js
     * export class RateLimitObject extends TenXObject {
     *   constructor() {
     * 	   if (TenXCounter.getAndSet(this.metricName, "1s") > 1000) 
     * 		 this.drop();
     *     else 
     *       TenXCounter.inc(this.metricName);      
     *   }
     * }
     * ```
     * 
     * @param {string} [counter=default] name of the counter whose value to get.
     *                            
     * @param {number} [value=1]           Value to set into the counter.
     *
     * @param {string|number} [resetInterval=""]  Repeating interval after which the counter is reset to 0.
     *                                          Can be a number (milliseconds), string interval (e.g., "10s", "1min"), 
     *                                          ISO-8601 duration format (e.g., "PT10S", "PT1M"), or name of a variable containing it.
     * 						                 This value cannot exceed 255 seconds and is rounded up to the second.
     *
     * @return {number}		               Value of the counter before being reset
     */

    static getAndSet(counter, value, resetInterval) {
        return TenXEngine.invoke(counter, value, resetInterval);
    }
}

/**
 * @class
 * @classdesc
 * Mathematical functions such as aggregation, parsing and hashing. 
 */
export class TenXMath {

    /**
      * Returns the average of an array of values
      *
      * This function returns an average of the sum of each of the values
      * in the supplied array. If an element cannot be converted into a number, it is ignored.
      *
      * @param {number[]} values the list of values to average
      *
      * @return {number}  the resulting average value. If no value is found to average, return 0
      */
    static avg(...values) {
        return TenXEngine.invoke(values);
    }

    /**
      * Returns a simple 32bit hashCode for a supplied string
      *
      * This function returns a simple hashing facility for an input string.
      * The hashing algorithm is the same as Java's {@link https://www.baeldung.com/java-objects-hash-vs-objects-hashcode#1-objecthashcode|Object.hashCode} function.
      *
      * An example where this function can be useful in the context of the event
      * sampling. If only 10% of transaction spans that have a DEBUG level severity
      * are to be kept, the value of an alphanumeric field such as "transactionId"
      * which holds a GUID value can be hashed to filter in those values which
      * divide cleanly by 10, thus keeping (assuming a random GUID distribution) 10% of matching objects:
      *
      *  @example
      *  if (this.startsWith("DEBUG") && (TenXMath.hashCode(this.transactionId) % 10) == 0) 
      *     this.drop();
      *
      * @param {string}     value	Value to hash
      *
      * @return {number}    32-bit hashCode
      */
    static hashCode(value) {
        return TenXEngine.invoke(value);
    }

    /**
     * Returns the highest numerical value within the supplied array
     *
     * This function returns the highest numerical value within the supplied array.
     * If an element cannot be converted into a number, it is ignored.
     *
     * @param values {number[]} List of values to search in
     *
     * @return {number}         Resulting max value. If no numerical value is found, return 0.
     */
    static max(...values) {
        return TenXEngine.invoke(values);
    }

    /**
     * Returns the lowest numerical value in the supplied array
     *
     * This function returns the lowest numerical value in the supplied array.
     * If an element cannot be converted into a number, it is ignored.
     *
     * @param values {number[]} List of values to search in
     *
     * @return {number}         Resulting average value. If no minimal value is found, return 0.
     */
    static min(...values) {
        return TenXEngine.invoke(values);
    }

    /**
     * Return a 64bit double representation of a string
     *
     * This function converts the input string into a 64-bit double value.
     * If the value does not represent a floating point value, 0 is returned.
     *
     * @param  str {string}        String to parse
     * 
     * @param {number} [defVal=0]  Value to return if str cannot be parsed
     * 
     * @return {number}            Parsed double value, def (if provided) or 0 in case of failure
     */
    static parseDouble(str) {
        return TenXEngine.invoke(str);
    }

    /**
     * Return a 64bit long representation of a string
     *
     * This function converts the input string into a 64-bit long value.
     * If the value does not represent a numeric point value, 0 is returned.
     *
     * @param str {string}          String to be parsed
     * 
     * @param {number} [defVal=0]   Value to return if str cannot be parsed
     *
     * @return {number}             Parsed long value, defVal (if provided) or 0 in case of failure
     */
    static parseInt(str) {
        return TenXEngine.invoke(str);
    }

    /**
     * Returns a randomly generated number
     *
     * This function randomly generated an int number in the range between min and max. If
     * min and/or max are not supplied, and the function returns a double number between 0 and 1.
     *
     * @param {number} [min=0]  Start of random range
     * @param {number} [max=1]  End of random range
     * 
     * @return {number}         Resulting random number.
     */
    static random(min, max) {
        return TenXEngine.invoke(min, max);
    }

    /**
     * Returns the closest integer to the argument, with ties rounding to positive infinity.
     *
     * This function rounds a number to the nearest integer using Java-style rounding rules.
     * For values exactly halfway between two integers (e.g., 2.5), it rounds up to the larger integer.
     *
     * @param {number} value The number to round
     * 
     * @return {number} The rounded integer value.
     */
    static round(value) {
        return TenXEngine.invoke(value);
    }

    /**
     * Returns the sum of values in the supplied array
     *
     * This function returns the sum of values in the supplied array.
     * If an element cannot be converted into a number, it is ignored.
     *
     * @param values {number[]} List of values to search in
     *
     * @return {number}         Resulting sum value. If no numerical value is found, returns 0.
     */
    static sum(...values) {
        return TenXEngine.invoke(values);
    }
}

/**
 * @class
 * @classdesc
 * Access 10x launch arguments.
 */
export class TenXEnv {

    /**
    * Returns the value of a launch argument or environment variable.
    * 
    * Requests for variable values are resolved in the following order:
    * - Launch arguments passed on the command line or using configuration files.
    * - OS Environment variable.
    * - {@link https://docs.oracle.com/javase/tutorial/essential/environment/sysprop.html|JVM properties}.
    * - Attributes from the authenticated user (when providing a license key)
    *     
    * For example, the decision on whether to drop "TRACE" events may be made configurable.
    * For this, an argument named "dropTrace" can be passed and queried in the following manner:
    * 
    * @example
    * class MyObject extends TenXObject {
    *   constructor() {
    *     this.drop(TenXEnv.get("dropTrace") && this.startsWith("TRACE")); 
    *   }
    * }
    * 
    * @param name {string}	                    Name of the launch arg or environment variable to query
    * 
    * @param defValue {string|number|boolean}	Value to return if a matching variable is not found
    * 
    * @return {string}                          Value of the variable if found, otherwise 'defValue' if provided or empty value if not.
    */
    static get(name, defValue) {
        return TenXEngine.invoke(name, defValue);
    }

    /**
    * Resolves a relative path on disk to a canonical one.
    * 
    * Configuration files utilize this function to resolve a file/folder references relative to:
    * - {@link https://doc.log10x.com/run/bootstrap/#includepaths|includePaths}
    * - Shell variable (e.g.,. MY_FOLDER)
    * - JVM system property (e.g.,. user.dir, temp.dir, tenx.temp.dir)
    * 
    * @example
    * 
    * Resolve a relative config path, if not found - default to pipeline temp dir variable.
    * localFolder: $=path("compile/sources", <tenx.temp.dir>") 
    *
    * # Resolve the 'astpretty.py' relative path
    * launchOptions:
    *   args:
    *     - $=path("pipelines/compile/modules/scan/pythonAST/astpretty.py")
    * 
    * @param paths {string[]}	               relative file/folder paths to attempt to resolve in order
    * @param emptyOnFail {boolean}	           return empty string if path not found, otherwise return last items in paths
 
    * @return {string}                         canonical path value
    */
    static path(value) {
        return TenXEngine.invoke(value);
    }    
}

/**
 * @class
 * @classdesc
 * Write messages to the 10x log.
 */
export class TenXLog {
    
    /**
     * logs a message to the 10x log with a DEBUG level.
     *
     * This function logs a message and an optional list of parameters to the 10x log.
     * The destination to which log messages are written is configured in the 'log4j2.yaml' file.
     * It is recommended to apply the log4j parameter formatting scheme vs. concatenating the message and params manually.
     * To learn more see {@link https://logging.apache.org/log4j/2.x/manual/messages.html|messages}.
     * 
     * @example
     * TenXLog.debug("error parsing value: {} in object of type: {}", this.value, this.metricHash);
     *
     * @param {string}	 message	Message to log
     *
     * @param {string[]} params     Parameters to format into message
     *
     * @return {string}	            Message parameter passed into this function
     */
    static debug(message, ...params) {
        return TenXEngine.invoke(message, params);
    }

    /**
     * logs a message to the 10x log with an INFO level.
     * See {@link  TenXLog.debug} to learn more.
     */
    static info(message, ...params) {
        return TenXEngine.invoke(message, params);
    }

    /**
     * logs a message to the 10x log with an ERROR level.
     * See {@link TenXLog.debug} to learn more.
     */
    static error(message, ...params) {
        return TenXEngine.invoke(message, params);
    }

    /**
     * checks whether debug logging is enabled.
     *
     * This function returns a boolean value indicating whether debug-level logging is currently enabled.
     * The function can be used to conditionally log expensive debug messages only when debugging is active,
     * avoiding unnecessary string formatting or computation when debug logs would be discarded.
     * 
     * @example
     * // Drop if rate is below minimum threshold
     * if (rate < minRate) {
     *     
     *     this.drop();
     * 
     *     if (TenXLog.isDebug()) {
     * 
     *         TenXLog.debug("drop by min rate. preIncrementCount={}, baseRate={}, rate={}, freqPerMin={}, randomValue=undefined, boost={}, baseline={}",
     *         preIncrementCount, baseRate, rate, freqPerMin, boost, baseline);
     *     }
     * }
     *
     * @return {boolean}	        boolean indicating whether debug logging is enabled
     */
    static isDebug() {
        return TenXEngine.invoke();
    }

   /**
    * Throws an error to halt the 10x Engine.
    *
    * This function can be used to validate input/configuration values to ensure they are 
    * present and correct before reading events from input(s).
    * 
    * For example, a 'threshold' startup argument used for processing tenxObjects
    * may need to hold a positive numeric value. For this, an assertion is used to validate that the
    * launch argument is both present and can be converted into a positive number value. 
    * 
    * The threshold launch argument can be defined in a {@link https://doc.log10x.com#Module|module file} as:
    * 
    * ``` yaml
    *   options:      
    *   - names:
    *     - threshold
    *     description: my threshold value
    *     type: number
    *     required: true
    * ```
    *
    * The script below validates a positive number was passed to the 10x Engine:
    * 
    * ``` js
    * export class ThresholdInput extends TenXInput {
    *   constructor() {
    *     if (TenXMath.parseInt(TenXEnv.get("threshold", -1)) <= 0) 
    *       throw new Error("positive 'threshold' not set!");      
    *   }
    * }
    * 
    * //The threshold can be used to tally instances whose 'threshold' field is > 'threshold'
    * export class ThresholdObject extends TenXObject {
    *   constructor() {       
    *     if (this.threshold > TenXEnv.get("threshold")) TenXCounter.inc("overThreshold");
    *   }
    * }
    * 
    * // An aggregator can be configured to generate TenXSummaries to tally the volume of TenXObjects surpassing 'threshold'. 
    * // To learn more see: https://doc.log10x.com/run/aggregate
    * export class ThresholdSummary extends TenXSummary {
    *   constructor() {       
    *     this.overThreshold = TenXCounter.getAndSet("overThreshold", 0);
    *   }
    * }   
    * ```
    * 
    * The module and script files can be passed alongside the threshold value to the 10x Engine: 
    * ``` console
    * $ tenx run @threshold.js @threshold.yaml threshold 1000
    * ```
    * 
    * A 'config.yaml' file can bundle these settings and passed to the runtime via:
    * > tenx @config.yaml: 
    * 
    * ``` yaml
    * tenx: run
    * include:
    *   - threshold.yaml
    *   - threshold.js

    * threshold: 1000   
    * ```
    * @param message {string}    a message to write to stderr if the condition is not 'truthy'.
    * 
    * @return                    halt the engine
    *
    */
    static throwError(message) {
        return TenXEngine.invoke(message);
    }
}

/**
 * @class
 * @classdesc
 * The 10x Engine provides the underlying implementation of all classes and functions in the 'tenx.js' module.
 * 
 * 10x JavaScript files (*.js) are passed to the 10x Engine as startups args in the form of: '> tenx @my.js' or placed
 * within folders passed as: '> tenx @/myApp'. 
 */
class TenXEngine {

    /**
    * The concrete implementation of this method is provided by the 10x Engine.
    */
    static invoke(...args) {
        throw new Error("TenX Javascript functions are implemented by the 10x Engine, received args: " + args.join(","));
    }

    /**
     * Determines whether a custom JavaScript class should be loaded and instantiated by the 10x Engine.
     *
     * This static method is called by the engine during the loading phase to decide which user-defined
     * subclasses should be applied to specific instances. The engine passes a config object containing
     * all configuration values for the relevant module (input, output, unit, etc.).
     *
     * For object, template, and summary subclasses, the config object provides all configuration values
     * from the input module for which these classes are instantiated.
     *
     * Global configuration flags (such as "quiet") are accessed via TenXEnv.get() and are not part of the config object.
     *
     * @param {Object} config - Configuration object with named access to all module options
     * @param {string} config.inputName - For inputs/objects/templates: name of the input (e.g., "CloudWatchLogs")
     * @param {string} config.outputName - For outputs: name of the output (e.g., "FileOutput")
     * @param {string} config.unitName - For units: name of the unit (e.g., "LoadConfig")
     * @returns {boolean} True if the class should be loaded and instantiated, false to skip
     *
     * @example
     * // In a CloudWatch Logs object processor
     * export class CloudwatchLogsObject extends TenXObject {
     *   static shouldLoad(config) {
     *     return TenXString.endsWith(config.inputName, "CloudWatchLogs");
     *   }
     * }
     *
     * @example
     * // In a file output with quiet mode check
     * export class FileOutput extends TenXOutput {
     *   static shouldLoad(config) {
     *     return !TenXEnv.get("quiet") && config.outputName === "FileOutput";
     *   }
     * }
     */
    static shouldLoad(config) {
        return TenXEngine.invoke(config);
    }
}
