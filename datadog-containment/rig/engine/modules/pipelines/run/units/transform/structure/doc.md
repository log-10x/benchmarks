---
icon: material/shape-plus-outline
---

Structure events read from [input](https://doc.log10x.com/run/input/stream/) using [Symbol libraries](https://doc.log10x.com/run/symbol) into typed [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).
 
The structuring process breaks down each input event into its discrete values and classifies each value as either a [variable](#variables), [symbols](#symbol) or [delimiter](#delimiters) using information from the symbol library. An event's _structure_ is defined by its sequence of symbols and delimiter values (excluding variables).

Events sharing the same structure are assigned an `TenXTemplate` (i.e. _hidden class_) as a joint schema, similar to a programmatic class that defines the structure of its instances. 

## :material-butterfly-outline: Process

The transform process executes the following steps for each [input](https://doc.log10x.com/run/input/) event:

1. Identify the event's matching TenXTemplate type (i.e., _hidden class_) using loaded [symbol libraries](https://doc.log10x.com/compile/link/#symbol-library).

2. If a new cached TenXTemplate is generated on-the-fly for the event:
    - Parse [timestamp](https://doc.log10x.com/run/transform/timestamp/) structures.
    - Extract [KV/JSON field](https://doc.log10x.com/run/transform/fields/) structures.
    - Calculate [symbol information](https://doc.log10x.com/run/transform/symbol/) (lazy).

3. [Initialize](https://doc.log10x.com/run/transform/script/object/) the instance using custom JavaScript constructors.

4. [Enrich](https://doc.log10x.com/run/initialize/) with calculated fields (e.g., GeoIP) using configured modules.

5. [Group](https://doc.log10x.com/run/transform/group/) instances together into composite units (e.g., stack traces, multi-line JSON) for aggregation and encoding as a single logical unit.

## :material-format-list-group: Members

Each TenXObject instance contains variables unique to its instance as members and a reference to its TenXTemplate (i.e., [_hidden class_](https://v8.dev/docs/hidden-classes)). Symbol values serve as _static_ class members shared across all instances of a logical app/infra event. 

Each symbol links to its source code/binary [origin](https://doc.log10x.com/run/transform/symbol/) and its [context](https://doc.log10x.com/run/transform/symbol/#contexts) within the file (e.g., class, field, enum, printout).

### :material-variable: **`Variables`**
Values the symbol library does not hold, and every number or digit-led token. These include:
- Alphanumeric values (e.g., EDC8116I)  
- Formatted/epoch timestamps (e.g., 2022-04-29T18:52:58.114201Z, 1719928783) 
- Host addresses (e.g., 10.10.34.11:9000)
- Span IDs (e.g., 0x051581bf3cb55c13) 

### :material-alphabetical-variant: **`Symbols`**
Values extracted from source code and binary artifacts at compile-time and stored in a target [Symbol library](https://doc.log10x.com/run/symbol), plus configured literals. A token is a symbol when the library holds it and it is not a number or a digit-led token; no other test applies. These include:
- Class names (e.g., MyClient, MyServer)
- Function/method names (e.g., info, warn) 
- Enum literals (e.g., STATUS, ERROR, OK)
- String formats (e.g., "could not connect to {}")
- JSON/XML field names (e.g. attributes, trace_id)
- Win/Nix executable strings (e.g., 'sudo, 'connection refused'). 

### :material-comma: **`Delimiters`**
Single character values specified via the [tokenDelims](#tokendelims) argument.

