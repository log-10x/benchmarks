---
icon: material/power-plug-outline
---

Initialize [inputs](https://doc.log10x.com/run/input) using JavaScript constructors to perform the following functions:

:material-check: **Validate** launch [arguments](https://doc.log10x.com/api/js/#TenXEnv) and [halt](https://doc.log10x.com/api/js/#TenXLog.throwError) the pipeline if unnecessary. 

:material-file-table: **Load** .csv/.tsv [lookup](https://doc.log10x.com/api/js/#TenXLookup.load) files to enrich TenXObject and summary instances.

:material-globe-model: **Connect** to [GeoIP DBs](https://doc.log10x.com/api/js/#TenXLookup.loadGeoIPDB) to geo-reference IP addresses.

:material-counter: **Initialize** [counters](https://doc.log10x.com/api/js/#TenXCounter.getAndSet) and [dictionaries](https://doc.log10x.com/api/js/#TenXInput.set).

The example below from [http.js](https://github.com/log-10x/config/blob/main/pipelines/run/config/transform/script/http.js) loads an HTTP message [lookup](https://doc.log10x.com/api/js/#TenXLookup) based on the value of a launch argument.

``` js
/**
 * Input constructors are designed to initialize specific resources at the start of pipeline execution.
 */
export class HttpInput extends TenXInput {

 /**
  * This constructor loads the 'http.csv' lookup table to enrich instances of 'HttpSummary' below. 
  */
  constructor() {

  if !TenXLookup.load("data/run/lookup/http.csv", true)
    throw new Error("could not load HTTP lookup!");
}
```

To load input constructors see [JavaScript configuration](https://doc.log10x.com/config/javascript/).

 