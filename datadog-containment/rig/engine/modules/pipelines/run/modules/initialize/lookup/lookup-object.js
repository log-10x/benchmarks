// @loader: tenx

import {TenXInput, TenXLookup, TenXObject, TenXEnv, TenXUnit} from '@tenx/tenx'

export class LookupUnit extends TenXUnit {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return (config.unitName == "transform") && (TenXEnv.get("lookupFile")) && (!TenXEnv.get("quiet"));
    }
    
     constructor() { 
        TenXConsole.log("📋 Enriching TenXObjects with lookup field: '" + TenXEnv.get("lookupValueField") + "'" + " from file: " + TenXEnv.get("lookupFile"));
     }
}

/**
 * Input constructors are designed to initialize specific resources at the start of 
 * pipeline execution. These include functions for loading.csv/.tsv lookup tables via {@link TenXLookup.load},
 * connecting to GeoIP DB files {@link TenXLookup.loadGeoIPDB()} to allow for geo-referencing,
 * validating startups args via {@link TenXInput.test} and more. 
 * the 'lookupEnabled' argument is set, apply to all inputs, otherwise to none.
 */
export class LookupInput extends TenXInput {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("lookupFile");
    }

    constructor() {
        TenXLookup.load(TenXEnv.get("lookupFile"), true); 
    }
}

/**
 * Object constructors initialize tenxObjects structured from input events.
 * This can be used to enrich instances with calculated fields that combine intrinsic, extracted and reflected fields
 * with configuration values using {@link TenXEnv.get()}, increase atomic counters {@link TenXCounter.inc()},
 * or filter instances from the pipeline using {@link TenXObject.drop()}.
 */
export class LookupSummary extends TenXSummary {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    //
    // Gated so this and LookupColumnSummary are mutually exclusive: this one
    // handles the default columns, the other handles an explicit value column.
    static shouldLoad(config) {
        return TenXEnv.get("lookupFile") && (!TenXEnv.get("lookupValueColumn"));
    }

    /**
     *  This constructor dynamically assigns the lookupValueField with the result of a {@link TenXLookup.get()} for the value of LookupKeyField.
    */
    constructor() {

        // Two args on purpose. The engine can only DEFER lookup resolution for
        // the 2-arg form (EventLookupGetFunction: `canDefer = args.size() == 2`),
        // and the check is on arg COUNT, so passing a blank third arg forced
        // eager parse-time resolution. That threw "could not resolve lookup
        // name" in any unit whose script context had no lookup registered yet --
        // e.g. an aggregator in a pipeline with no input unit ahead of it, which
        // is exactly how @apps/receiver ships (all forwarder inputs commented
        // out). Deferring binds the table on first invocation instead, which is
        // always after input init has registered it.
        this.set(
            TenXEnv.get("lookupValueField"),             // set the target 'lookupValueField' field into this
            TenXLookup.get(                              // query the 'lookupFile' table
                TenXEnv.get("lookupFile"),
                this.get(TenXEnv.get("lookupKeyField"))  // get the 'lookupKeyField' from this to use as the key
            )
        );
    }
}

/**
 * Variant used when 'lookupValueColumn' names an explicit value column.
 *
 * Kept separate because explicit column names must be validated against the
 * table at parse time, so this form cannot defer.
 */
export class LookupColumnSummary extends TenXSummary {

    // https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("lookupFile") && TenXEnv.get("lookupValueColumn");
    }

    constructor() {

        // TenXLookup.get(lookup, key, keyColumnName, valueColumnName)
        this.set(
            TenXEnv.get("lookupValueField"),
            TenXLookup.get(
                TenXEnv.get("lookupFile"),
                this.get(TenXEnv.get("lookupKeyField")),
                0,                                       // key column: first column
                TenXEnv.get("lookupValueColumn")         // value column, in the correct slot
            )
        );
    }
}
