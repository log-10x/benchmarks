---
icon: material/power-plug-outline
---

Initializes [outputs](https://doc.log10x.com/run/output) via JavaScript constructors.

The class demonstrates how `TenXOutput` subclasses can access module-specific configuration options (like [outputFilePath](https://doc.log10x.com/run/output/event/file/#outputfilepath), [outputFileWriteObjects](https://doc.log10x.com/run/output/event/file/#outputfilewriteobjects), and [outputFileWriteTemplates](https://doc.log10x.com/run/output/event/file/#outputfilewritetemplates)) as instance properties and customize their initialization behavior accordingly.

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

To load input constructors see [JavaScript configuration](https://doc.log10x.com/config/javascript/).

 