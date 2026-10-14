---
icon: material/progress-check
---

Stop any single log pattern from dominating its container's volume, on the forwarder, before that volume is billed downstream. Errors and warnings keep flowing, and a pattern an operator lists in the mute file follows its own entry instead of the cap.

The rate regulator watches each container's recent volume and acts on any one [pattern](https://doc.log10x.com/run/initialize/message/ "the message symbol sequence that identifies a log type") that spends more bytes than the cap set for that container. That pattern is the same value, in the field `symbolMessageField` names (`message_pattern` in the shipped configuration), that a Reporter attributes cost to, so a top spender maps straight to what gets regulated. No cap ships by default, so nothing is regulated until an operator sets one.

## :material-percent-outline: The cap

The cap is a byte budget for one pattern in one container over one window. It resolves per event: the container's row in the cap file first, then the fleet-wide `absoluteCap`. Both default to none, and a resolved cap of `0` means keep everything, so protection is opt-in. Set `absoluteCap`, a cap file, or both.

At or below the cap every event is kept. Above it the regulator engages, and the event takes one of three exits, in this order: kept by the share guard, kept by the severity floor, or routed by the container's action.

The share guard is a sanity check on the cap. A pattern over its cap but below `minSharePercent` (default 5%) of its container's volume is left alone, so a busy container whose traffic is spread thin does not trip the regulator. Share is measured per container over a rolling window (`resetIntervalMs`, default 4 minutes): `(pattern bytes + event) / (container bytes + event)`. The window is recent rather than all-time, so a pattern that spikes during a deploy and then goes quiet stops being trimmed on its own.

Nothing targets the excess back down to the cap line. The cap decides when the regulator engages, the floor decides what fraction of the excess survives, and the action decides what happens to the rest.

The cap is not a hard bound. The floor check runs after the cap check, so above the cap a flood still passes at the floor rate, and the worst case for one pattern in one container per window is the cap plus the floor share of everything above it.

## :material-shield-alert-outline: Severity floors

The cap never silences high-severity logs. `severityFloors` sets a minimum retention per level that beats the cap: even a pattern over its cap keeps at least Error 50%, Warn 30%, Info 10%. Critical and Fatal sit with Error, and any level with no entry of its own falls to `minRetentionThreshold` (10%). That floor share of the excess is what makes the cap a trigger rather than a bound. The floor reads the [severity](https://doc.log10x.com/run/initialize/level/) the level enrichment produced, so it applies whatever field the original log used.

## :material-timer-sand: Warmup

A container is left unregulated for `warmupMs` (default 5 minutes) after this regulator instance first sees its events. Lower for fast-starting apps that should be capped sooner after a restart, raise for slow-ramping JVMs or workloads with long init phases.

The warmup exists because the regulator's per-pattern sample counts start empty. Without a few minutes of accumulation, a low-volume pattern can look dominant purely because of ordering. Five minutes gives enough samples for typical Kubernetes traffic to tell a noisy pattern from a quiet one.

"First sees" is per regulator instance, not per container birth. A container that has been running for hours but whose events have only just started flowing through this regulator, after a regulator restart or a forwarder reconnect, restarts the warmup window. On a daemonset rolling restart the cap is therefore disabled for `warmupMs` per node as it cycles.

The first `baselineCount` events (default 5) of every pattern are also kept each window, so even a heavily-trimmed pattern leaves a sample to inspect.

## :material-file-document-edit-outline: Protection list

An optional mute file overrides the regulator for patterns an operator has declared. A listed, active pattern is decided by its entry, so the human declaration wins and the regulator is skipped for it; every other pattern is handled by the cap. The two run together rather than as separate modes.

**File format**, CSV with a header row, keyed by the joined `fieldNames`:

```
fieldSet,value
<fieldSetKey>,<sampleRate>:<untilEpochSec>[:<reason>]
```

- `sampleRate` retains that fraction: `1` is never sampled, `0` is a full mute.
- `untilEpochSec` expires the entry, which then self-heals to a no-op.
- `reason` is free text for audit.

The severity floor still applies, so a `0` mute never silences ERROR or FATAL. The file is typically committed to a repo and pulled via [gitops](https://doc.log10x.com/config/github/#config), or read directly from a Kubernetes ConfigMap via the [`@kubernetes` launch macro](https://doc.log10x.com/config/k8s/), so each change carries a diff, a review, and a merge. Both lanes hot-reload via atomic rename; a plain volume-mounted `ConfigMap` does not, because the swap is a symlink rename.

## :material-clipboard-list-outline: Per-container caps

An optional cap file sets a byte cap for a specific container in priority over the fleet-wide `absoluteCap`. Listed containers get the file's cap; unlisted containers fall back to `absoluteCap` (or to no cap, when `absoluteCap` is 0).

**File format**, CSV with a header row, keyed by the `containerField` value (k8s container name by default):

```
container,cap
<container>,<bytes>[:<untilEpochSec>][:<reason>]
```

- `bytes` is the per-pattern per-window cap for the container. `0` exempts the container from the absolute cap.
- `untilEpochSec` expires the entry, which then self-heals to a no-op.
- `reason` is free text for audit. Must not contain commas (would break CSV parsing).

The cap value changes; the share guard and severity floor still apply. Intended use is via the `log10x_configure_engine` MCP tool, which derives per-container caps from a target percent or a monthly dollar budget and opens a PR against the file.

Same hot-reload rule as the mute file: both launch-macro lanes reload, a plain volume-mounted `ConfigMap` does not.

## :material-arrow-decision: Actions

An optional action file decides what happens to the events a pattern spends above its cap. Without it, or for a container with no row, the excess passes: a cap alone never loses a line.

**File format**, CSV with a header row, keyed by the same `containerField` value as the cap file:

```
container,action
<container>,<action>[:<untilEpochSec>][:<reason>]
```

- `action` is one of `pass`, `offload`, `tier_down`, `compact`, `sample`, or `drop`. Unlisted containers get `pass`.
- `untilEpochSec` expires the entry, which then self-heals to a no-op.
- `reason` is free text for audit. Must not contain commas (would break CSV parsing).

The action is set per service and applies to every pattern over its cap in that service. Here a service is a container. Per-pattern thinning comes from the mute file, not from this file.

The event keeps flowing either way. The action lands on the event as its `routeState`, and the output streams and the forwarder recipe act on that, so `offload` and `tier_down` reach their destinations instead of being discarded at the regulator. The cap stays the backstop that decides how much excess there is; the action only decides where it goes.

The action file is a sibling of the cap file in the same ConfigMap, and hot-reloads on the same rule.

## :material-kubernetes: Containers

Share is scoped per container, named by `containerField` (default the k8s container name). That name is stable across replicas, so scaling from one pod to ten does not bypass the cap, and a sidecar never spends the application container's share. Use `container`, never `pod`.

Outside Kubernetes, or when no container field is present, the regulator falls back to a single node-wide bucket and caps each pattern across the node.

## :material-cash-multiple: Savings

Drops are measured, not estimated. The receive-stage aggregators tally every event by pattern and container both before and after regulation, so the saving for a pattern is the volume seen minus the volume emitted. A dropped event still counts as seen, so the figure reflects exactly what the regulator removed.

## :material-tag-check-outline: Config-version stamp

When the receiver runs the MCP closed loop, the control plane (`log10x_configure_engine`) writes a `config-generation.csv` next to the cap file in the same ConfigMap, a one-row `key,value` CSV whose `generation` is a hash of the cap policy. Point `configGeneration.file` at it (or set the `CONFIG_GENERATION_FILE` env) and the receiver stamps that value on every event as the `tenx_config_version` metric label, so the running engine advertises which config generation it loaded. The MCP then confirms the policy it wrote is actually live by comparing the label to the hash of the current caps, the config-generation closed loop.

It is opt-in and decoupled from caps: unset by default, so a regulator managed by GitOps without the MCP emits no `tenx_config_version` label and never depends on the file existing. Hot-reloaded like the cap file, so a new generation goes live without an engine restart (this is the stale → live transition the verifier observes).

## :material-cog-box: Wiring

```yaml
rateReceiver:
  fieldNames:
    - message_pattern        # the pattern identity, the field symbolMessageField names
  containerField: container  # scopes the cap denominator
  absoluteCap: 10485760      # 10 MB per pattern per container per window (optional; 0 = no fleet-wide cap)
  minSharePercent: 0.05      # share guard (sanity)
  severityFloors:
    - INFO=0.1
    - WARN=0.3
    - ERROR=0.5
  warmupMs: 300000           # 5m per-instance grace; raise for slow-ramping apps
  baselineCount: 5
  capLookup:
    # file: $=path("data/caps") + "/caps.csv"   # optional per-container overrides
    retain: $=parseDuration("10m")
  actionLookup:
    # file: $=path("data/caps") + "/actions.csv"  # optional per-container action for the excess; default pass
  configGeneration:
    # file: $=TenXEnv.get("CONFIG_GENERATION_FILE", "")   # MCP config-version stamp; opt-in, sibling of caps.csv
```

Tune these values in this config block, not via container environment variables. Any `rateReceiver:` key set here resolves to a launch argument at engine init and shadows a same-named env var, so env-only overrides are silently ignored. Edit the config (via a gitops PR) to change a value at runtime.
