---
icon: material/pipe-valve
---

Filters noisy telemetry before shipping to output (Splunk, Elastic) using [per-node budget sampling or a declarative field-set mute file](https://doc.log10x.com/run/receive/rate/) to control costs.

### :material-pipe-valve: Output Filters

Filters provides a JavaScript-based mechanism for controlling which TenXObjects to write to output stream(s): 

- Custom constructors provide a programmatic method for [dropping](https://doc.log10x.com/run/transform/script/object/#filter) instances.

- The [outputFilters](https://doc.log10x.com/run/output/receive/#outputfilters) option provides a global hook into which receiver [modules](https://doc.log10x.com/engine/module/#run) can install logic (e.g., thresholds, anomaly detection). 

- Each output stream provides an individual [outputFilter](https://doc.log10x.com/run/output/stream/#outputfilter) setting to allow for granular control over which instances it should emit.

### :material-language-javascript: Filter Expressions

JavaScript expressions can be set inline  within the [YAML config](https://doc.log10x.com/config/yaml/#javascript-expressions) to control which TenXObject instances to encode. For example:

``` yaml
outputFile:
  path: encoded.log
  filter: isObject # encode TenXObject instances only (exclude TenXSummaries and templates)
  ...
```

The following expressions provide examples for different types of filters:

| Expression                                                                             | Description                                                                                           |
|----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| [isObject](https://doc.log10x.com/api/js/#TenXBaseObject+isObject)                      | Checks if the instance TenXObject (exclude templates and summaries).                                  |
| [isEncoded](https://doc.log10x.com/api/js/#TenXBaseObject+isEncoded)                    | Checks if the instance has been encoded.                                                              |
| [isTemplate](https://doc.log10x.com/api/js/#TenXBaseObject+isTemplate)                  | Checks if the instance is a TenXTemplate instance.                                                    |
| [isSummary](https://doc.log10x.com/api/js/#TenXBaseObject+isSummary)                    | Identifies if the object is a TenXSummary instances.                                                  |
| [timestamped](https://doc.log10x.com/api/js/#TenXBaseObject+timestamped)                | Checks if the instance has timestamps.                                                                |
| [ipAddress == TenXEnv.get("host")](https://doc.log10x.com/api/js/#TenXObject+ipAddress) | Matches the object's IP address with a host [env variable](https://doc.log10x.com/api/js/#TenXEnv.get) |
| [inputName == "myElastic"](https://doc.log10x.com/api/js/#TenXObject+inputName)         | Filters objects with the input name "myElastic".                                                      |
| [startsWith("ERROR")](https://doc.log10x.com/api/js/#TenXBaseObject+startsWith)         | Filters objects starting with "ERROR".                                                                |
| [myFilter()](https://doc.log10x.com/config/javascript)                                  | Applies a custom filter function.                                                                     |