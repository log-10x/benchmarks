---
icon: material/code-tags
---

Scan input source code/binary files to produces symbol files from a variety of programming languages, text and binary formats
using configurable scanner [modules](https://doc.log10x.com/engine/module/).

Scanner modules parse the contents of a target input file to generate an 
[AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree) from which to
capture [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values and the 
[context](https://doc.log10x.com/run/transform/symbol/#contexts) in which they appear (e.g., class, function, printout).

The run pipeline utilizes symbol files to [transform](https://doc.log10x.com/run/transform/)
input log/trace events into typed [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).

Once scanner modules complete, the compile pipeline [links](https://doc.log10x.com/compile/link/) symbol files into a single [symbol library](https://doc.log10x.com/run/symbol/#libraries) file for use at run time.

### :material-file-tree: Output

Scanners emit information captured from each input into a respective symbol unit (.json) file.
The path of each output symbol unit within [outputSymbolFolder](https://doc.log10x.com/compile/scan/#outputsymbolfolder) matches its 
folder structure within [inputPaths](https://doc.log10x.com/compile/scan/#inputpaths)

For example, when launching a compile pipeline with the following [config](https://doc.log10x.com/config/yaml/):

``` yaml
tenx: compile
inputPaths:
  - ~/dev 
outputSymbolFolder: ~/symbols 
```

For a foo.js file located in:

`~/dev/app/foo.js`

The respective output symbol unit output file is: 

`~/symbols/app/foo.js.10x.json`

### :material-card-multiple-outline: Parallel Processing

The compile pipeline supports running multiple instances of the [compiler app](https://doc.log10x.com/apps/compiler/) in parallel by using shared file locks to safely reuse existing symbol unit files residing in the [output path](#outputsymbolfolder). The underlying storage system must support [advisory locks](https://www.baeldung.com/linux/file-locking#1-advisory-locking) for parallel execution to be enabled.

A separate scheduled task periodically can link symbol unit files into a single [symbol library](https://doc.log10x.com/compile/link/#symbol-library) artifact used by edge/cloud apps at runtime.
