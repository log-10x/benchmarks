---
icon: material/shape-plus-outline
---

Defines shared static members accessible by all instances of a [template](https://doc.log10x.com/run/template/).

Example: calculating severity from [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values (`Debug`, `Traceback most recent call last`):

``` js

export class LevelTemplate extends TenXTemplate {

    constructor() {
    
        // check the template's symbol value starts with any of the configured 'levelTerms' values
        // use the map function to get the level value associated with a matching term
        
        LevelTemplate.level = TenXString.startsWith(
            this.symbolSequence("", "log", 30), 
            TenXMap.fromEntries(TenXEnv.get("levelTerms"))
        );
    }
}