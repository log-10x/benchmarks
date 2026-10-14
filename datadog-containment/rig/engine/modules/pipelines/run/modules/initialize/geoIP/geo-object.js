// @loader: tenx

import {TenXInput, TenXLookup, TenXObject, TenXUnit, TenXEnv, TenXConsole} from '@tenx/tenx'

export class GeoIPUnit extends TenXUnit {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return (config.unitName == "transform") && (TenXEnv.get("geoIPFile")) && (!TenXEnv.get("quiet"));
    }
    
     constructor() { 
        TenXConsole.log("🌎 Enriching TenXObjects with GeoIP info using:" + TenXEnv.get("geoIPFile"));
     }
}

/**
 * Input constructors are designed to initialize specific resources at the start of 
 * pipeline execution. These include functions for loading.csv/.tsv lookup tables via {@link TenXLookup.load},
 * connecting to GeoIP DB files {@link TenXLookup.loadGeoIPDB()} to allow for geo-referencing,
 * validating startups args via {@link TenXInput.test} and more. 
 * If the 'geoIPEnabled' argument is set, apply to all input names (.* = match all), otherwise to none (a^ = match none).
 */
export class GeoRefInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPFile", true);
    }

    /**
    *  This constructor loads the GeoIP DB file (.mmdb) specified by the 'geoIPFile' argument.
    */
    constructor() {
        
        TenXLookup.loadGeoIPDB(TenXEnv.get("geoIPFile"));
    }
}

/**
 * Object constructors initialize tenxObjects structured from input events.
 * This can be used to enrich instances with calculated fields that combine intrinsic, extracted and reflected fields
 * with configuration values using {@link TenXEnv.get()}, increase atomic counters {@link TenXCounter.inc()},
 * or filter instances from the pipeline using {@link TenXObject.drop()}.
 */

export class GeoRefCityObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPCityField");
    }

    /**
    * This constructor assigns a geo-ref field (e.g., city) specified by the 'geoIPCityField' argument
    * using the GeoIP DB specified by the 'geoIPFile' argument.
    */
    constructor() {

        this.set(TenXEnv.get("geoIPCityField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "city")
        );
    }
}

export class GeoRefContinentObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPContinentField");
    }

    /**
     * This constructor assigns a geo-ref field (e.g., continent) specified by the 'geoIPContinentField' argument
     * using the GeoIP DB specified by the 'geoIPFile' argument.
     */
    constructor() {
        this.set(TenXEnv.get("geoIPContinentField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "continent")
        );
    }
}

export class GeoRefCountryObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPCountryField");
    }

    /**
     * This constructor assigns a geo-ref field (e.g., country) specified by the 'geoIPCountryField' argument
     * using the GeoIP DB specified by the 'geoIPFile' argument.
     */
    constructor() {
        this.set(TenXEnv.get("geoIPCountryField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "country")
        );
    }
}

export class GeoRefSubdivisionObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPSubdivisionField");
    }
    
    /**
     * This constructor assigns a geo-ref field (e.g., subdivision) specified by the 'geoIPSubdivisionField' argument
     * using the GeoIP DB specified by the 'geoIPFile' argument.
     */
    constructor() {
        this.set(TenXEnv.get("geoIPSubdivisionField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "subdivision")
        );
    }
}

export class GeoRefPostalObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPPostalField");
    }

    /**
     * This constructor assigns a geo-ref field (e.g., postal) specified by the 'geoIPPostalField' argument
     * using the GeoIP DB specified by the 'geoIPFile' argument.
     */
    constructor() {
        this.set(TenXEnv.get("geoIPPostalField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "postal")
        );
    }
}

export class GeoRefLatitudeObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPLatitudeField");
    }

    /**
     * This constructor assigns a geo-ref field (e.g., latitude) specified by the 'geoIPLatitudeField' argument
     * using the GeoIP DB specified by the 'geoIPFile' argument.
     */
    constructor() {
        this.set(TenXEnv.get("geoIPLatitudeField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "latitude")
        );
    }
}

export class GeoRefLongitudeObject extends TenXObject {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return TenXEnv.get("geoIPLongitudeField");
    }

    /**
     * This constructor assigns a geo-ref field (e.g., longitude) specified by the 'geoIPLongitudeField' argument
     * using the GeoIP DB specified by the 'geoIPFile' argument.
     */
    constructor() {
        this.set(TenXEnv.get("geoIPLongitudeField"), 
            TenXLookup.get(TenXEnv.get("geoIPFile"), this.ipAddress, "longitude")
        );
    }
}
