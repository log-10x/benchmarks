---
icon: material/launch
---

Launches a subprocess to extract [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values from source code or binary files.

Supports OS utilities like [strings](https://linux.die.net/man/1/strings) for pre-compiled binaries, or custom code for reading from arbitrary files and remote sources (databases, web services).

The subprocess stdout is parsed in one of two modes:

### Unstructured
Splits stdout lines using [token delimiters](https://doc.log10x.com/compile/scan/#tokendelims) and assigns each value an [exec](https://doc.log10x.com/run/transform/symbol/#exec) context. See the [strings](#__tabbed_1_2) configuration example below.

### Structured
Parses JSON objects from stdout containing hierarchical symbol trees with [context](https://doc.log10x.com/run/transform/symbol/#contexts) metadata (class, function, enum names). See [SymbolUnit.java](https://github.com/log-10x/pipeline-extensions/blob/main/cloud-extensions/src/main/java/com/log10x/ext/cloud/compile/symbol/SymbolUnit.java) for an example.

