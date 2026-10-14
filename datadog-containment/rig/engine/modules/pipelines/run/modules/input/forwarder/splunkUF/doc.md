---
icon: material/greater-than
---

Splunk Universal Forwarder inputs use a **file relay pattern** with [Fluent Bit + 10x](../fluentbit/) to process events _before_ Splunk UF ships them to Splunk indexers. This approach keeps UF as the forwarder (handling buffering, retries, timeouts) while 10x filters and (optionally) compacts events inline.

## Architecture

<div style="text-align: center;">

```mermaid
graph LR
    A["<div style='font-size: 14px;'>📝 App Logs</div><div style='font-size: 10px;'>Folder A</div>"] --> B["<div style='font-size: 14px;'>🔧 Fluent Bit</div><div style='font-size: 10px;'>+ 10x sidecar</div>"]
    B --> C["<div style='font-size: 14px;'>📂 Processed</div><div style='font-size: 10px;'>Folder B</div>"]
    C --> D["<div style='font-size: 14px;'>📤 Splunk UF</div><div style='font-size: 10px;'>monitors B</div>"]
    D --> E["<div style='font-size: 14px;'>🔍 Splunk</div><div style='font-size: 10px;'>Indexers</div>"]

    classDef logs fill:#2563eb,stroke:#1d4ed8,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef fluentbit fill:#ea580c,stroke:#c2410c,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef processed fill:#7c3aed,stroke:#6d28d9,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef uf fill:#0891b2,stroke:#0e7490,color:#ffffff,stroke-width:2px,rx:8,ry:8
    classDef splunk fill:#16a34a,stroke:#15803d,color:#ffffff,stroke-width:2px,rx:8,ry:8

    class A logs
    class B fluentbit
    class C processed
    class D uf
    class E splunk
```

</div>

### Data Flow

- 📝 **App Logs (Folder A)** - Application writes logs to original location
- 🔧 **Fluent Bit + 10x** - Reads from Folder A, filters and (optionally) compacts events
- 📂 **Processed Logs (Folder B)** - 10x writes processed output to new location
- 📤 **Splunk UF** - Monitors Folder B with standard `inputs.conf`, handles forwarding
- 🔍 **Splunk Indexers** - Receives processed events via standard S2S protocol

### Why File Relay?

| Benefit | Description |
|---------|-------------|
| 🔧 **Standard UF** | No protocol changes, no `enableOldS2SProtocol` flag |
| 👤 **App Team Control** | Configure without Splunk admin involvement |
| 🔒 **UF Handles Reliability** | Buffering, retries, and timeouts stay with UF |
| ✅ **Proven Pattern** | Uses existing [Fluent Bit + 10x](../fluentbit/) integration |

### When to Use

This module is recommended for **VM/traditional infrastructure** where Splunk UF is deployed. For Kubernetes environments, Splunk recommends [Splunk Connect for Kubernetes](https://github.com/splunk/splunk-connect-for-kubernetes) (which uses Fluent Bit) - use the [Fluent Bit module](../fluentbit/) directly in that case.

??? tenx-keyfiles "Key Files"

    This module uses the [Fluent Bit forwarder module](../fluentbit/) under the hood:

    | File | Purpose |
    |------|---------|
    | [`fluentbit/conf/tenx-sidecar.conf`](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/input/forwarder/fluentbit/conf/tenx-sidecar.conf) | Reference Fluent Bit config showing the 10x sidecar handoff |
