---
icon: material/equal
---

Extracts JSON objects and KV structures from [TenXTemplates](https://doc.log10x.com/run/template) as named fields.

This process enables [TenXObjects](https://doc.log10x.com/api/js/#TenXObject) to access nested JSON/KV values at runtime as named members.

For an hybrid JSON/plain event whose [text](https://doc.log10x.com/api/js/#TenXBaseObject+text) value is:

``` json 
17/06/24 17:38:00 INFO ExecutorRunnable: Prepared Local resources Map(__spark__.jar -> resource 
{ scheme: "hdfs" host: "10.10.34.11" port: 9000 
file: "/user/curi/.sparkStaging/application_1485248649253_0144/spark-assembly-1.6.0-hadoop2.2.0.jar" } 
size: 109525492 timestamp: 1497001131801 type: FILE visibility: PRIVATE)
```

To increase a [counter](https://doc.log10x.com/api/js/#TenXCounter) identified by a JSON field (scheme) value with that of a KV entry (size):

``` js
TenXCounter.inc(this.scheme, this.size);
```

To [drop](https://doc.log10x.com/api/js/#TenXObject+drop) the instance if either a KV entry (e.g., _visibility_) or JSON field (e.g., _port_) match a specified value:

``` js 
this.drop((this.visibility == "PRIVATE") || (this.port == 9000));
```

### :material-code-array: Arrays

If a JSON/KV field appears more than once within an TenXObject's text, it can be accessed as an array field to access individual entries (e.g., `this.myField[i]`).      
