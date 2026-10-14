---
icon: material/select-group
---

Group [TenXObjects](https://doc.log10x.com/api/js/#TenXObject) to filter, aggregate and output as a single
logical unit. 

Log events read from an input stream can serve as a part of a larger logical group. A typical
example of events spanning multiple sub-events are [stack traces](https://stackoverflow.com/questions/3988788/what-is-a-stack-trace-and-how-can-i-use-it-to-debug-my-application-errors) where each
line within the stack trace may be logged as a separate line. 

TenXObjects can be composed into logical group to:

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

## :material-cogs: Grouping Logic

The group module calculates two static fields for each TenXTemplate:

### isGroup

TenXObjects qualify as group heads (`isGroup = true`) when they meet one of these conditions:

1. **Timestamp** - Presence of a timestamp marks them as heads.
2. **Severity level** - Assignment of a severity level designates them as heads.
3. **Group indicator** - Starting with any configured [groupIndicators](#groupindicators) pattern confirms them as heads.

Subsequent TenXObjects attach to the active group until encountering another head, exceeding the maximum group size, or hitting the flush timeout.


### Default Configuration

Default [groupIndicators](#groupindicators) encompass patterns like private IP addresses (e.g., '192.', '10.'), HTTP methods (e.g., 'GET ', 'POST '), system logs (e.g., 'kernel:', 'sshd['), and stack trace starters (e.g., 'Traceback ', 'Exception in thread ').


Users can customize these patterns in their configuration to suit specific log formats.

