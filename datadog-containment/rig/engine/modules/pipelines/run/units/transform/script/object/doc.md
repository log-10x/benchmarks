---
icon: material/star-cog-outline
---

Enrich and drop [TenXObjects](https://doc.log10x.com/api/js/#TenXObject) using custom JavaScript constructors.

Load custom .js files via [JavaScript config](https://doc.log10x.com/config/javascript/).

### :material-function-variant: Enrich

[Enrich](https://doc.log10x.com/run/initialize/) instances with calculated fields that combine [JSON/KV](https://doc.log10x.com/run/transform/#jsonkv-fields) field, [reflection](https://doc.log10x.com/run/transform/#reflection),
[launch argument](https://doc.log10x.com/api/js/#TenXInput.get) and [lookup](https://doc.log10x.com/api/js/#TenXLookup) values. 

The example below calculates an HTTP code field:

``` js

// @loader: tenx

import {TenXObject, TenXMath} from '@tenx/tenx'

export class HttpCodeObject extends TenXObject {

   /**
   This constructor computes a calculated HTTP error code field from the penultimate variable token for each 10x Object
   according to: https://httpd.apache.org/docs/2.4/logs.html
   For example, this will extract the '200' value into the 'code' field from:
   127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
   */
  constructor() {
    var code = TenXMath.parseInt(this.var[-2]);
    this.httpCode = (code >= 200) && (code < 600) ? code : 0;
  }
} 
```

### :material-filter-outline: Filter 

Drop unnecessary TenXObjects from the pipeline via the [drop](https://doc.log10x.com/api/js/#TenXObject+drop) function.

``` js

// @loader: tenx

import {TenXObject} from '@tenx/tenx'

export class FilteredObject extends TenXObject {
  constructor() {
    // Does not require the instance to undergo structuring
    this.drop(this.startsWith("TRACE"));

    // Requires the instance to undergo structuring based on the value of the penultimate 'vars' element.
    this.drop(this.vars[-2] != 200);
   }
 }

```

### :material-counter: Increase

Update cyclical [counters](https://doc.log10x.com/api/js/#TenXCounter) and update [dictionaries](https://doc.log10x.com/api/js/#TenXInput).

The example below uses an interval counter can be used to limit the rate of TenXObjects
based on their [symbolSequence](#TenXObject+symbolSequence) to a target limit (e.g. 1000) within a
specific interval (e.g. "1s"). This prevents a "chatty" event from "hogging" the pipeline's bandwidth:

``` js

// @loader: tenx

import {TenXObject, TenXCounter} from '@tenx/tenx'

export class RateLimitObject extends TenXObject {
  constructor() {
    
    var symbolSequence = this.symbolSequence();
    
    if (TenXCounter.getAndSet(symbolSequence, "1s") > 1000) 
         this.drop();
    else 
      TenXCounter.inc(symbolSequence);      
  }
}
```

### :material-forest-outline: Template Members

Template members demonstrated below allow all instances of the same [TenXTemplate](https://doc.log10x.com/run/template/) to share members across all of its instances. 

The example below assigns TenXObjects with a calculated severity level using specific [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values (e.g.,`Debug`, `Traceback most recent call last`).

``` js

// @loader: tenx

import {TenXTemplate, TenXString, TenXEnv} from '@tenx/tenx'

export class LevelTemplate extends TenXTemplate {

    constructor() {
    
        // check the template's symbol value starts with any of the configured 'levelTerms' values
        // use the map function to get the level value associated with a matching term
        
        LevelTemplate.level = TenXString.startsWith(
            this.symbolSequence("", "log"", 30), 
            TenXMap.fromEntries(TenXEnv.get("levelTerms"))
        ));
    }
}

```

### :material-counter: Dynamic Loading

Each class can define a custom [shouldLoad](https://doc.log10x.com/api/js/#TenXEngine.shouldLoad) static function to determine whether to execute code defined in its constructor based on configuration and environment settings.

The engine invokes this function upon initialization. If the function returns a truthy value the class is loaded into memory, otherwise it is not loaded and its enclosed constructor code is not executed to initialize inputs, instances, and summaries.

``` js

// @loader: tenx

import {TenXInput, TenXObject, TenXEnv} from '@tenx/tenx'

export class MyInput extends TenXInput {

    // To learn more see https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
      return config.myProp || TenXEnv.get("myVar");
    }
    
    constructor() {
    
       // init actions
    }
}

export class SplunkObject extends TenXObject {

    // To learn more see https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
      return config.myProp || TenXEnv.get("myVar");
    }
    
    constructor() {
    
       // init actions
    }
}

```