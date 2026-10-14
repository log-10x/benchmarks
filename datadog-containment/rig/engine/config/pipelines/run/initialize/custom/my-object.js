// @loader: tenx

import {TenXInput, TenXLookup, TenXObject, TenXSummary, TenXCounter, TenXEnv, TenXLog, TenXConsole} from '@tenx/tenx'

/** 
 * The 10x JavaScript library provides a programmatic interface to the 10x Engine.
 * The MyInput, MyObject and MySummary classes below provide a sandbox for writing custom 10x scripts
 * that are loaded by the 10x 'run' pipeline by default. 
 * 
 */

/**
 * Input constructors are designed to initialize specific resources at the start of 
 * pipeline execution. These include functions for loading.csv/.tsv lookup tables via {@link TenXLookup.load},
 * connecting to GeoIP DB files {@link TenXLookup.loadGeoIPDB()} to allow for geo-referencing,
 * validating startups args via {@link TenXLog.throwError} and more. 
 * 
 * To learn more see {@link TenXInput}.
 *  
 */

export class MyInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {

        // customize result to control whether to load this class 
        return true;
    }

    constructor() {
        // your code here
    }
}

/**
 *  Object constructors initialize tenxObjects structured from input events.
 *  This can be used to enrich instances with calculated fields that combine intrinsic, extracted and reflected fields
 *  with configuration values using {@link TenXEnv.get()}, increase atomic counters {@link TenXCounter.inc()},
 *  or filter instances from the pipeline using {@link TenXObject.drop()}.
 * 
 *  To learn more see {@link TenXObject}
 */

export class MyObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        
        // customize result to control whether to load this class 
        return true;
    }

    constructor() {
        // your code here to enrich/filter TenXObject instances
     }
}

/** 
 *  Summary constructors initialize instances produced by an aggregator (https://doc.log10x.com/run/aggregate)
 *  This can be used to enrich instances with calculated fields using lookup tables {@link TenXLookup.get()},
 *  or tally values via counters using {@link TenXCounter.getAndSet()}.
 * 
 *   To learn more see {@link TenXSummary}
 */
export class MySummary extends TenXSummary {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        // customize result to control whether to load this class 
        return true;
    }

    constructor() {
        // your code here to enrich summary instances
    }
}

