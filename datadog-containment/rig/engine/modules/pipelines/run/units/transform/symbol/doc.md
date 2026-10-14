---
icon: material/origin
---

Identify the source code/binary executable origin of [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values within [TenXTemplate](https://doc.log10x.com/engine/design/#optimization-model) hidden classes.

Identifying where each symbol value originated from within TenXTemplates enables [reflective programming](https://en.wikipedia.org/wiki/Reflective_programming) wherein [TenXObjects](https://doc.log10x.com/api/js/#TenXObject)
can inspect their structure and member types and source code/executable file origin.

Each symbol lists its file of origin (e.g., foo.js, sudo, acme.dll) and the 
[context](#contexts) in which it appears in it (e.g., class/func/enum name, string format..).

Source code/executable origin information is accessible at run time via the [symbol](https://doc.log10x.com/api/js/#TenXObject+symbol),
[symbolSequence](https://doc.log10x.com/api/js/#TenXObject+symbolSequence), and [symbolOrigin](https://doc.log10x.com/api/js/#TenXObject+symbolOrigin) functions.

``` js
this.class = this.symbol("class");
this.sequence = this.symbolSequence("log,exec"); 
this.origin = this.symbolOrigin("log,exec");
```

For the following Apache Spark [log event](https://github.com/logpai/loghub/blob/20168f0fc076be8a75d22c01896076090d4a3c6e/Spark/Spark_2k.log#L14):

> 17/06/09 20:10:42 INFO executor.CoarseGrainedExecutorBackend: Connecting to driver: spark://CoarseGrainedScheduler@10.10.34.11:48069

| Field    | Value                                                                                                                                                               |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| class    | CoarseGrainedExecutorBackend                                                                                                                                        |
| sequence | Connecting to driver                                                                                                                                                |
| origin   | [CoarseGrainedExecutorBackend.scala](https://github.com/apache/spark/blob/master/core/src/main/scala/org/apache/spark/executor/CoarseGrainedExecutorBackend.scala)  |

For the following Unix [log event](https://github.com/logpai/loghub/blob/20168f0fc076be8a75d22c01896076090d4a3c6e/Linux/Linux_2k.log#L3):

> Jun 14 15:16:02 combo sshd(pam_unix)[19937]: authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=218.188.2.4

| Field    | Value                                                                                                                            |
|----------|----------------------------------------------------------------------------------------------------------------------------------|
| class    | ""                                                                                                                               |
| sequence | authentication failure                                                                                                           |
| origin   | [sshd](https://linux.die.net/man/8/sshd)                                                                                         |

## Contexts

Compile [scanners](https://doc.log10x.com/compile/scan/) assigns each extracted [symbol](https://doc.log10x.com/run/transform/structure/#symbols) 
value within a target source code/binary file a _context_ which describes its meaning and position within the file.

Supported contexts include:

### **`package`**

Source code package/namespace name. For example:

``` java
package com.acme.client.core;

  public class AcmeLogic {
  ...  
  }
```

``` c#
namespace MyCompany.Proj1
{
    class MyClass1
    {
      ...
    }
}
```

### **`class`**

Source code class/interface definition. For example:
``` python 
class AcmeClient:
...
```

``` java 
public interface AcmeServer {...}
```

The scanner will capture _AcmeServer_, _AcmeClient_ as **class** symbols.

The scanner will capture _com.acme.client.core_, _MyCompany.Proj1_ as **package** symbols.

### **`method`**

Source code method/function name. For example:

``` js 
function hostError(host) {...}
```

``` cpp
void Person::get_name() {
```

The scanner will capture _hostError_, _get_name_ as **method** symbols


### **`enum`**
Source code enum literal value. For example:

``` py
from enum import Enum

class STATUS(Enum):
OK = 1
FAIL = 2
RETRY = 3
```  

The scanner will capture:
- _OK_, _FAIL_, _RETRY_  as **enum** symbols 
- _STATUS_  as a **class** symbol
 
### **`log`**
   
Source code constant arg within a [logging](https://doc.log10x.com/compile/scan/logMethods/) method. For example: 
  
``` js
function hostError(host) {
  //The "error connecting" symbol passes as an indirect arg to the logger
  var msg = fmtError("error connecting", host);
  console.error(msg); 
} 
```   

The scanner will capture _error connecting_ as a **log** symbol. 

### **`const`**

Source code  constant value assigned to a variable, parameter or code annotation. For example:
``` java
@JsonElement(key = "price")
public String price;
```

``` js
report("state: " + state);
```

``` js
this.key = "key";
```

The scanner will capture _price_, _state_, _key_  as a **const** symbol, unless the enclosing method logs or throws, in which case its literals are captured as **log** symbols. Const symbols are not linked into the library by default.

### **`exec`**

Symbol captured from a custom program or OS command via the [executable](https://doc.log10x.com/compile/scanner/executable) symbol scanner
(e.g., [strings](https://linux.die.net/man/1/strings)).

For example:
``` console
strings -a /usr/bin/sudo
```

The scanner will capture _Authentication failure message %s_  as an **exec** symbol.


### **`text`**

Config field name/value captured from file (e.g., .xml, .json) via the [text](https://doc.log10x.com/compile/scanner/text/) symbol scanner.

For example:
``` yaml
spring:
  name: test
  environment: testing
```

The scanner will capture the field names _spring_, _name_, and _environment_  as **text** symbols.

 The _test_ and _testing_ field values are only captured as text if the [textScanFieldValues](https://doc.log10x.com/compile/scanner/text/#textscanfieldvalues) is set to true.

