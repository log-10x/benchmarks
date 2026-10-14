---
icon: material/star-cog-outline
---

Enrich [TenXSummary](https://doc.log10x.com/api/js/#TenXSummary) instances produced by an [aggregator](https://doc.log10x.com/run/aggregate) 
using custom JavaScript constructors.

Enriching summary instances with calculated fields provides a method for creating dynamic [tag dimensions](https://www.baeldung.com/micrometer#1-tags) 
when publishing to [metric](https://doc.log10x.com/run/output/metric/) outputs (e.g., [Prometheus](https://doc.log10x.com/run/output/metric/prometheus/#prometheustagfields)).

Calculated summary fields can combine data from:

1. The [aggregated values](https://doc.log10x.com/run/aggregate/#aggregatorfields) extracted from TenXObjects grouped into the current summary instance.

2. [:material-file-table: TSV/CSV](https://doc.log10x.com/api/js/#TenXLookup.load) lookup files.

3. [:material-globe-model: GeoIP](https://doc.log10x.com/api/js/#TenXLookup.loadGeoIPDB)  to geo-reference instances based on their [ipAddress](https://doc.log10x.com/api/js/#TenXObject+ipAddress).

4. [:material-counter: Counter](https://doc.log10x.com/api/js/#TenXCounter) and [input](https://doc.log10x.com/api/js/#TenXInput) values.
  
To load custom summary .js files at run time see [JavaScript](https://doc.log10x.com/config/javascript/) configuration.
  
The example below enriches summary instances with HTTP message lookup value:
 
``` js 

// Extend the TenXSummary class to define a custom ctor

export default tenx.

/**
 * Input constructors can initialize specific resources at the start of pipeline execution.
 */
export class HttpInput extends TenXInput {

 /**
  * This constructor loads the 'http.csv' lookup table to enrich instances of 'HttpSummary' below. 
  */
  constructor() {

  if !TenXLookup.load("data/run/lookup/http.csv", true)
    throw new Error("could not load HTTP lookup!");
}

export class HttpSummary extends TenXSummary {

    /** 
     *  This constructor calculates an HTTP message for TenXSummaries by translating the numeric 'code' 
     *  value into a human-readable 'reason' message which can be used as a metric dimension
     */
    constructor() {
      
      if (this.code) this.reason = TenXLookup.get("http", this.code);
    }
}
```

