Reads events via the [Fluent Forward protocol](https://github.com/fluent/fluentd/wiki/Forward-Protocol-Specification-v1) on a Unix domain socket.

Supports all standard Forward protocol modes:

- **Message**: `[tag, time, record]`
- **Forward**: `[tag, [[time, record], ...]]`
- **PackedForward**: `[tag, packed_entries_bin]`

Each record is decoded from msgpack and emitted as a JSON line with the Forward tag injected as a `"tag"` field.
