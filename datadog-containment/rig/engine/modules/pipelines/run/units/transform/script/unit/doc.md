---
icon: material/power-plug-outline
---

Initialize and shut down [pipeline units](https://doc.log10x.com/engine/pipeline/#units) using JavaScript.

## Unit Initialization

Unit `constructor()` methods run when a pipeline unit starts, allowing for resource initialization, logging, and configuration.

``` js
export class FileOutput extends TenXOutput {
    constructor() {
        if (this.outputFilePath) {
            if (this.outputFileWriteObjects != false) {
                if (this.outputFileWriteTemplates) {
                    TenXConsole.log("Writing TenXObjects and TenXTemplates to: " + this.outputFilePath);
                } else {
                    TenXConsole.log("Writing TenXObjects to: " + this.outputFilePath);
                }
            } else if (this.outputFileWriteTemplates ) {
                TenXConsole.log("Writing TenXTemplates to: " + this.outputFilePath);
            }
        }
    }
}
```
