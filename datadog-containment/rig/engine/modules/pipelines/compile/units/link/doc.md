---
icon: material/merge
---

Combine symbol units into a single output symbol library file 
used by the 10x [run](https://doc.log10x.com/run/) pipeline to generate shared [TenXTemplates](https://doc.log10x.com/run/transform/) schemas for input log/trace events. 

This phase is analogous to a [linker](https://en.wikipedia.org/wiki/Linker_(computing)) that 
takes one or more object files (i.e., symbol units) generated during a compilation process and combines them into a single library file for use at run time.

### :material-zip-box-outline: Symbol Library

To dynamically create class and metadata information at run time, the 10x [compile](https://doc.log10x.com/compile/) pipeline scans GitHub and container repos ahead-of-time to generate [symbol libraries](https://doc.log10x.com/run/symbol/), similar to package artifacts (e.g., npm, .jar, .NET assembly).

The 10x [run](https://doc.log10x.com/run/) pipeline utilizes symbol library files to assign a shared [TenXTemplate](https://doc.log10x.com/run/template/) (i.e., _hidden class_) to input log/trace events with the same [structure](https://doc.log10x.com/run/transform/structure), creating a cached optimized schema for each event type.

Operating on typed TenXObjects enables direct access to [symbol](https://doc.log10x.com/run/transform/structure/#symbols) and [variable](https://doc.log10x.com/run/transform/structure/#variables) values at runtime without repeatedly parsing JSON structures or evaluating complex, brittle regular expressions for each event.

### :material-file-tree: File Structure 

Each symbol library `.10x.tar` archive file contains:
- A `.10x.json` file combining the symbol unit files generated during the [scan](https://doc.log10x.com/compile/scan/) phase.
- A manifest `.10x.json` file listing each source with the commit or digest it was built from.
- A `.10x.pb` Protocol Buffer file which provides a reverse in-mem index of the symbols values contained within the JSON for fast loading and random access. To learn more see the [.proto IDL](https://github.com/log-10x/pipeline-extensions/blob/main/api-extensions/src/main/proto/FsSymbolUnitsIndex.proto).
