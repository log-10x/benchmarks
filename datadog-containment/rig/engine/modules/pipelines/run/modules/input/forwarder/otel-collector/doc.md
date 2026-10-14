---
icon: simple/opentelemetry
---

Runs 10x Engine as a [sidecar](https://doc.log10x.com/engine/launcher/sidecar) to the [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) for reporting, receiving, and optimizing events before they ship to their destination (Elasticsearch, Splunk, S3, Kafka, …). The Collector and Log10x run as peer processes. On Kubernetes, the Helm chart connects the two containers over unix domain sockets on a shared `/tmp` emptyDir: the Collector sends events to Log10x via syslog on `/tmp/tenx-otel-in.sock` and receives processed events back via fluentforward on `/tmp/tenx-otel-out.sock`. The Architecture and Quickstart below show the VM/CLI recipe instead, where the Collector sends events via its native [OTLP/gRPC exporter](https://github.com/open-telemetry/opentelemetry-collector/tree/main/exporter/otlpexporter) and receives them back via its OTLP/gRPC receiver. Every value on the OTLP wire survives the round trip: resource attributes, scope info, log-record attributes, severity, timestamp, and body, so k8s metadata (`k8s.pod.name`, `k8s.namespace.name`, `k8s.container.name`, labels, …) reaches your destinations with its name and value unchanged. Where an attribute sits does change. Everything comes back as a log-record attribute, so the resource-versus-log-record split is not preserved. See [What an event looks like on the way back](#what-an-event-looks-like-on-the-way-back).

!!! note "Distribution"
    Both the OTLP receiver and OTLP exporter ship in the core `otelcol` distribution, no `otelcol-contrib` build is required. Tested against `otelcol` v0.151.0+.

## Architecture

<div style="text-align: center;">

```mermaid
graph LR
    A["<div style='font-size: 14px;'>📂 Receivers</div><div style='font-size: 10px;'>filelog, otlp, journald</div>"] --> F["<div style='font-size: 14px;'>🧪 logs/to-tenx</div><div style='font-size: 10px;'>k8sattributes, resource, transform</div>"]
    F --> B["<div style='font-size: 14px;'>📤 otlp exporter</div><div style='font-size: 10px;'>OTLP/gRPC → :4317</div>"]
    B --> E["<div style='font-size: 14px;'>⚡ 10x Engine</div><div style='font-size: 10px;'>Receive/Optimize</div>"]
    E --> C["<div style='font-size: 14px;'>📥 otlp receiver</div><div style='font-size: 10px;'>:24225 (no processors)</div>"]
    C --> D["<div style='font-size: 14px;'>📤 Destinations</div><div style='font-size: 10px;'>ES, Splunk, S3, Kafka</div>"]

    classDef input fill:#2563eb,stroke:#1d4ed8,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef filter fill:#ea580c,stroke:#c2410c,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef engine fill:#7c3aed,stroke:#6d28d9,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef output fill:#16a34a,stroke:#15803d,color:#ffffff,stroke-width:2px,rx:8,ry:8

    class A input
    class B filter
    class C filter
    class D output
    class E engine
    class F filter
```

</div>

### Data Flow

- 📂 **Receivers**, Your existing OTel receivers (`filelog`, `otlp`, `journald`, `kafka`, …) feed events into the `logs/to-tenx` pipeline.
- 🧪 **`logs/to-tenx`**, Your enrichment processors (`k8sattributes`, `resource`, `attributes`, `transform`, `filter`, …) run here exactly once before the event is handed off to Log10x. The processors live on this pipeline only; the return-path pipeline never sees them.
- 📤 **OTLP exporter** → Log10x, The Collector forwards the enriched event to the Log10x sidecar over OTLP/gRPC on TCP `:4317`. Resource attributes, scope info, log-record attributes, and the body all travel on the wire.
- ⚡ **10x Engine**, The Receiver app applies rate/policy-based filtering and optionally compacts events for volume reduction.
- 📥 **`logs/from-tenx`**, Processed events come back to the Collector on `:24225` via its OTLP/gRPC receiver. Keep this pipeline processor-free; the destination exporters consume events directly so enrichment never re-fires on the return path.
- 📤 **Destinations**, Your OTel destination exporters (`elasticsearch`, `splunkhec`, `kafka`, `awss3`, …) consume the return pipeline and ship to the real destinations.

### What an event looks like on the way back

Values survive the round trip. Where a value sits does not. Both sentences are
true, and the second one is the one to check your destination configuration
against.

**Every value comes back.** Resource attributes, scope info, log-record
attributes, severity, timestamp and body all return to the Collector, each with
the same key and the same value. The `LogRecord.body` carries the message
verbatim in its original `AnyValue` shape, so a `body.stringValue` is
byte-for-byte unchanged. Nothing is dropped and nothing is rewritten.

**The resource-versus-log-record split does not.** Log10x reads the incoming
record as one flat set of top-level fields and the
[OTLP output](https://doc.log10x.com/run/output/event/otlp/) writes it back the
same way: the configured body field is lifted into `LogRecord.body` and every
other top-level field becomes a log-record attribute. An attribute that arrived
under `Resource` therefore comes back under `LogRecord.attributes`, with its
key and value intact but no longer marked as a resource attribute.

That matters on the return path for anything that reads the two apart: a
`resource` or `transform` processor keyed on `resource.attributes[...]`, a
`groupbyattrs` processor, or a destination exporter that maps resource
attributes to its own resource-level fields. Keep the return pipeline
processor-free, as the Data Flow section above says, and check the destination
exporter's own attribute mapping before relying on it.

What else changes between in and out depends on the Receiver app mode:

| Mode | Difference vs the event the Collector sent in |
|------|------------------------------------------------|
| Receive (default) | No field added, none removed, no value changed. Every attribute returns as a log-record attribute, as described above. |
| Receive + `symbolMessageHashField <name>` | As above, plus one new field named `<name>` carrying the symbol-pattern hash (a stable identifier for the message pattern, usable as a dedup key, metric dimension, or correlation ID). |
| `receiverOptimize true` | The value of the field captured by `otelCollectorInputMessageField` (default `body`) is replaced with a compact encoded form. Each new template is sent once as its own LogRecord, with no body and the attributes `templateHash`, `template` and `tenx_tag` = `tenx-template`; route on `tenx_tag` to send templates to their own destination. All other fields stay verbatim. |
| `receiverOptimize true` + `symbolMessageHashField <name>` | Both of the above. |

`symbolMessageHashField` is unset by default, which is what makes the first row true: the receive path adds nothing of its own to the record. The pattern hash is still computed and still rides the event inside the engine as `tenx_hash` for metrics and aggregation, it just does not reach the wire. Naming a field opts in, either as a launch argument (`tenx @run/input/forwarder/otel-collector @apps/receiver symbolMessageHashField my_custom_hash`) or as an environment variable of the same name.

Log10x reads the log line text via the JSON field configured by `otelCollectorInputMessageField` (default `body`); the `tag` field stamped by the input (from `service.name`, falling back to `k8s.pod.name`, then to the literal `"otel"`) becomes the event's source. All other resource and log-record attributes (`k8s.pod.name`, `k8s.namespace.name`, `service.name`, …) come through as flat top-level fields on the record, available for message-pattern and rate filtering. That flattening is also why they leave as log-record attributes.

??? tenx-keyfiles "Key Files"

    | File | Purpose |
    |------|---------|
    | [`stream.yaml`](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/input/forwarder/otel-collector/stream.yaml) | OTel Collector OTLP/gRPC input + output stream definitions |
    | [`conf/tenx-sidecar.yaml`](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/input/forwarder/otel-collector/conf/tenx-sidecar.yaml) | Reference Collector config showing the two-pipeline split with no return-path processors |

## Quickstart

**1. Run Log10x:**

```bash
tenx @run/input/forwarder/otel-collector @apps/receiver
```

**2. Wire up your Collector config**, start from the sidecar recipe and add your real receivers + destination exporters. The `logs/to-tenx` pipeline carries everything from sources through enrichment to the `otlp/tenx` exporter; the `logs/from-tenx` pipeline carries the returning events directly to your destination exporters:

```yaml title="otelcol.yaml"
receivers:
  filelog:
    include: [/var/log/app.log]

  # Receive processed events back from Log10x over OTLP/gRPC
  otlp/tenx:
    protocols:
      grpc:
        endpoint: 0.0.0.0:24225

processors:
  batch: {}

exporters:
  # Hand off to the Log10x sidecar over OTLP/gRPC
  otlp/tenx:
    endpoint: 127.0.0.1:4317
    tls:
      insecure: true
    # One sender keeps records in the order they were read; the engine
    # groups multi-line events from consecutive records.
    sending_queue:
      num_consumers: 1

  debug:
    verbosity: detailed

service:
  pipelines:
    logs/to-tenx:
      receivers: [filelog]
      processors: [batch]
      exporters: [otlp/tenx]
    logs/from-tenx:
      receivers: [otlp/tenx]
      exporters: [debug]
```

For Splunk integration see the [Log10x App](https://doc.log10x.com/apps/receiver/compact/splunk/) documentation. For Kubernetes deployment via the official OpenTelemetry Collector Helm chart see the [Helm sidecar overlay](https://doc.log10x.com/apps/receiver/deploy/#otel-collector).
