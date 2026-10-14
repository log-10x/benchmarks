---
icon: material/tune-variant
---

Compact specific patterns' events into a template+values tuple, without redeploying the engine.

The compact receiver makes a per-event decision whether to emit via `encode()` (the pattern's template hash plus extracted variable values, smaller where the destination supports it) or preserve `fullText`. The decision is keyed by pattern identity (the same `message_pattern` value the Reporter attributes cost to), so an operator targets compaction at the same patterns surfaced in cost analysis.

Entries live in a CSV cap-file, typically committed to a git repo and edited by PR. The file is hot-reloaded on in-place writes; a merged PR takes effect within ~10 seconds, no pod restart.

## :material-clipboard-list-outline: Per-pattern caps

A cap-file declares, for each pattern, whether its events are compacted or preserved. Patterns not listed fall back to `compactReceiverDefault`.

**File format**, CSV with a header row, keyed by the fields named in `compactReceiverFieldNames` joined with `_` (the shipped configuration uses the pattern field, `message_pattern`):

```csv
fieldSet,value
<fieldSet>,<true|false>[:<untilEpochSec>][:<reason>]
```

- `fieldSet`, the event fields named by `compactReceiverFieldNames` joined with `_`. With the shipped configuration this is the pattern's `message_pattern` value.
- `value`, `true` compacts via `encode()`; `false` explicitly preserves `fullText` for this pattern (beats the default).
- `untilEpochSec`, optional Unix-epoch (seconds) expiry. Past it the entry self-heals and the pattern falls back to `compactReceiverDefault`.
- `reason`, optional free-text for audit. Must not contain commas (would break CSV parsing).

**Example** (with `compactReceiverDefault: false`):

```csv
fieldSet,value
payment_retry_gateway_timeout,true:1745856000:OPS-5123 spike
auth_audit_trail,false:1745856000:compliance keep verbose
```

The engine hot-reloads on in-place file writes (the gitops pattern); Kubernetes `ConfigMap` mounts don't reload because the CM swap is a symlink rename, not an in-place write.

## :material-swap-horizontal: Default policy

`compactReceiverDefault` sets the fallback decision when no cap-file entry matches:

- **`false`** (default), preserve `fullText`. Cap-file entries opt specific patterns *into* compaction. Right when most traffic is already high-signal.
- **`true`**, compact via `encode()`. Cap-file entries opt specific patterns *out* of compaction (e.g. audit/compliance patterns that must stay verbose). Right when most traffic is low-signal machinery and only some patterns need full-text fidelity.

Flipping the default is a policy decision that affects every event and requires a pod rollout. Cap-file edits handle per-pattern exceptions without restart.

## :material-cog-box: Wiring

```yaml
compactReceiver:
  fieldNames: [message_pattern]      # fields joined to form the lookup key
  default: false                     # fallback when no entry matches
  lookup:
    file: $=path("data/caps") + "/compact-cap.csv"
    retain: $=parseDuration("10m")
```

- Setting `lookup.file` enables the per-pattern compaction path; leaving it unset preserves the pre-compact behavior (receive-only emits `fullText`; `receiverOptimize=true` compacts every event).

Tune these values in this config block, not via container environment variables. Any `compactReceiver:` key set here resolves to a launch argument at engine init and shadows a same-named env var, so env-only overrides are silently ignored. Edit the config (via a gitops PR) to change a value at runtime.
