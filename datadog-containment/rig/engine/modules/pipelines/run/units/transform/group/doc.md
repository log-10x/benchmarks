---
icon: material/select-group
---

Groups [TenXObjects](https://doc.log10x.com/api/js/#TenXObject) for filtering, aggregation, and output as single units.

Log events read from an input stream can serve as a part of a larger logical group. A typical
example of events spanning multiple sub-events are [stack traces](https://stackoverflow.com/questions/3988788/what-is-a-stack-trace-and-how-can-i-use-it-to-debug-my-application-errors) where each
line within the stack trace may be logged as a separate line. 

Grouping enables:

- **Identify** groups consuming the most storage and analytics resources 
using [aggregators](https://doc.log10x.com/run/aggregate/). 
This is especially valuable when storing stack traces than span 100s of lines and consume a significant amount of resources.
- **Filter** unnecessary groups such as 'noisy' stack traces via [group filters](#groupfilters) and output [receivers](https://doc.log10x.com/run/output/receive). 
- **Optimize** storage of multi-line events by [losslessly compacting](https://doc.log10x.com/run/transform/#compact) them as a composite instances to reduce storage footprint by >  **75%** when compared to storing individual events.

## :material-group: Group Heads

tenXObjects which evaluate as truthy against [groupExpressions](https://doc.log10x.com/run/transform/group/#groupexpressions) are marked as starting of a new group (i.e. a _group head_). 

All subsequent TenXObjects read from the same input will join the current group until either:
- Another group is started marked by a subsequent instance which evaluates as truthy against `groupExpressions`.
- The number of TenXObjects in the current group exceeds [groupMaxSize](#groupmaxsize).
- The [groupFlushTimeout](#groupflushtimeout) elapses. 

At that point the group is sealed as new composite TenXObject and flushed forward for aggregation and output.
Each composite TenXObject returns the number of instances grouped within it via the [groupSize](https://doc.log10x.com/api/js/#TenXObject+groupSize) member.

**` Example #1 - timestamps + negators (default)`**

The TenXObject [constructor](https://doc.log10x.com/run/transform/script/object/) below marks an instance as the head of a group if:
- its [text](https://doc.log10x.com/api/js/#text-string) field [starts with](https://doc.log10x.com/api/js/#TenXString.startsWith) an [indicator](#groupindicators) value.
- its [timestamped](https://doc.log10x.com/api/js/#timestamped-boolean) field is true.
     
``` js
export class GroupTemplate extends TenXTemplate {

    static get isGroup() {

        // https://doc.log10x.com/run/initialize/group/#groupindicators
        if (this.startsWith(TenXEnv.get("groupIndicators"))) {
            return true;
        }

        return this.timestamped;
    }

    // This constructor is invoked by the engine once for each unique TenXTemplate discovered
    // at runtime based on log event structures
    constructor() {
        GroupTemplate.isGroup = this.isGroup();
     }
}
```
**` Example #2 - Group ISO_8601 events`**

The TenXObject below marks an instance as the head of a group if it 
has an [ISO_8601](https://stackoverflow.com/questions/3914404/how-to-get-current-moment-in-iso-8601-format-with-date-hour-and-minute) timestamp:
     
``` js
export class IsoTemplate extends TenXTemplate {

  constructor() {
    IsoTemplate.isGroup = this.timestampFormat() == "yyyy-MM-dd'T'HH:mm'Z'";
  }
}
```

**` Example #3 - Group Linux Call Traces`**

The constructor below groups Linux Call Traces (see [example](https://syzkaller.appspot.com/text?tag=CrashLog&x=17f5743fe00000)) 
by folding lines that are part of a trace (e.g., an <IRQ> interrupt marker, or end with
a memory address) into a logical group. 

``` js
class NixTemplate extends TenXTemplate {

  constructor() {  

   // is event is call trace interrupt marker
    if (this.contains("<IRQ>")) {
        NixTemplate.isGroup = false;
    } else 
 
    // does event end in a '/'' + hex memory address (e.g., 0x16d0) ?
    // use the token() function to access the last + penultimate instance values
    if (this.token(-2) == "/") && (startsWith(this.token(-1), "0x")) {
        NixTemplate.isGroup = false;
    }
  }
}
``` 

## :material-filter-multiple-outline: Group Filters

The [groupFilters](#groupfilters) option provides a mechanism for filtering TenXObject groups
based on conditions that relate to the entire group (e.g., filter entire stack traces vs. individual lines).
        
The [YAML](https://doc.log10x.com/config/yaml/) config below places a limit of a maximum of 'SocketException' 1000 groups per minute
using a [cyclical counter](https://doc.log10x.com/api/js/#TenXCounter.inc): 
        
``` yaml
group:
  filters: 'this.includes("SocketException") && (this.groupSize > 1) ? (TenXCounter.incAndGet("socketException", 1, "1m") > 1000) : true'
```

A filter may also be set to a function loaded from a [JavaScript config](https://doc.log10x.com/config/javascript/) file. For example:

``` yaml
group:
  filters: socketExceptionFilter()
```

Where the JavaScript file would contain:

``` js

// @loader: tenx

public class MyFilter extends TenXObject {

  function socketExceptionFilter() {

    return this.includes("SocketException") && (this.groupSize > 1) ?
      (TenXCounter.incAndGet("socketException", 1, "1m") > 1000) : 
      true
  }

}

```
## :material-regex: Event Source

Input streams that read data from multiple locations (e.g., log files, pods, hosts) 
can utilize source [patterns](https://doc.log10x.com/run/input/stream/#inputsourcepattern) and 
[fields](https://doc.log10x.com/run/input/stream/#inputsourcefields) to assign each event 
a logical origin (e.g., log file, host address). 

This value ensure each TenXObject is grouped alongside instances 
from the same source and is accessible via the [source](https://doc.log10x.com/api/js/#TenXObject+source) member.
