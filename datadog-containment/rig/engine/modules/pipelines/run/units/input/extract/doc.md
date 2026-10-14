---
icon: material/select-all
---

Extractors filter, redact and select text to transform into [TenXObjects](https://doc.log10x.com/api/js/#TenXObject) from a stream of input events.
   
Configured extractors scan an input event for specified JSON fields or regex
[capture groups](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Regular_expressions/Named_capturing_group) values on which to perform specified actions.

An extractor can be applied to an input via its [targetInput](#extractortargetinput) member or by adding the extractor to a target input's [extractors](https://doc.log10x.com/run/input/stream/#inputextractors) list.

For example, the [k8s enrichment](https://doc.log10x.com/run/initialize/k8s/) module uses JSON extractors to add pod and container context to TenXObjects for filtering and aggregation.

## Actions

Extractors can perform the following actions on input events:

### :material-select-all: Capture
 
Capture actions control which segments of a log/trace event's text to transform into TenXObjects. 

JSON extractors select field values to transform into TenXObjects. 
Regex extractors select values using defined by the [extractorPattern](#extractorPattern).

For example, to capture the `message` value of the following simple event: 
``` json
{
   "event": {
     "origin": "localhost",
     "message": "some event"
   }
}
```

A JSON extractor can specify the `message` field, while a Regex extractor can specify a capture group (see [example](https://regex101.com/r/WmGjnZ/1)).

Each capture action specifies which instances of the JSON field/Regex groups within an event to transform:  

#### **`All`**

Transform all matching JSON field/capture group values in an event into TenXObjects.

#### **`First`**

Transform the first matching JSON field/capture group value in an event into an TenXObject.

#### **`Last`**

Transform the last matching JSON field/capture group value in an event into an TenXObject.

#### **`Default`**

Serves as a sink for selecting events that fail to match the [extractorFilter](#extractorfilter) pattern
or do not contain JSON field names/regex capture groups specified by [extractorActions](#extractoractions).

This action captures the entire text of an event to transform into an TenXObject and 
set its [extractorKey](https://doc.log10x.com/api/js/#TenXObject+extractorKey) value to the current action's name.

Only one default capture action is allowed.

#### **`Field`**

Capture a JSON field value and attach it to every TenXObject produced by the extractor, under the alias name. Unlike the other capture actions, `captureField` does not emit its own TenXObject.

For example, the [k8s enrichment](https://doc.log10x.com/run/initialize/k8s/) module declares `captureField:kubernetes.namespace_name:namespace_name` to attach pod namespace as a context [field](https://doc.log10x.com/run/initialize/#enrichmentFields) on every extracted TenXObject.

Only the first matching value per field is captured.

### :material-filter-outline: Filter

Filter actions allow for filtering an entire event or redacting some of its values. These actions serve a dual purpose of providing a fast mechanism for filtering out unnecessary events to save on the CPU resources as well as redacting sensitive information (i.e., HIPAA, PII).

#### **`Drop`**

Deletes a matched JSON field and its value(s) from the event entirely. Available only for JSON extractors.

#### **`Redact`**

For JSON extractors resets matching field values:

| JSON Field Type | Redacted Value         |
|-----------------|------------------------|
| object          | {}                     |
| array           | []                     |
| number          | 0                      |
| string          | ""                     |
| boolean         | true                   |

For regex extractors deletes all instances of matching capture groups from an event.

### :material-brain: Advanced

Advanced actions allow more granular control over how events are captured:

#### **`No Transform`** 

Select events without transforming them into typed [TenXObjects](https://doc.log10x.com/api/js/#TenXObject). This action enables writing raw events that do not require any structure to output. Only one `noTransform` action is allowed.

#### **`Outer Text`**

Sets a JSON field/capture group as the `outer text` value for TenXObjects extracted by `captureAll`, `captureFirst`, or `captureLast` actions.

For example, if a JSON extractor action specifies `captureFirst:message`, 
a `setOuterText:event` action can set the [fullText](https://doc.log10x.com/api/js/#TenXBaseObject+fullText) value of an TenXObject to the JSON `message` field's enclosing `event` object.

In the [example event](#capture), `some event` is set as the TenXObject's [text](https://doc.log10x.com/api/js/#TenXBaseObject+text) value and its [fullText](https://doc.log10x.com/api/js/#TenXBaseObject+fullText) value is the entire enclosing JSON object.  

The [encode](https://doc.log10x.com/api/js/#TenXObject+encode) function returns a compact representation of an TenXObject's text value enclosed within the outer text region. 

If no `setOuterText` selector is specified, an TenXObject's [fullText](https://doc.log10x.com/api/js/#TenXBaseObject+fullText) and [text](https://doc.log10x.com/api/js/#TenXBaseObject+text) fields return the same value. 
 
If `outerText` actions are defined but not matched, the extractor applies the `default` capture action (if defined), otherwise, it drops the event.