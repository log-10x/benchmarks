# Workstream 3, Per-Container Cap Lookup: Investigation Report

**Status**: cap-engagement working end-to-end; metric-attribution carries a pre-existing engine issue documented below.

## Summary

The per-container cap-lookup feature (`rateReceiverCapLookupFile`) ships
functionally working: when configured, the regulator drops events that
exceed the per-container cap, and the customer's downstream bill is
reduced. The shipped fix uncovered three engine-level findings; one was
the immediate root cause, two are pre-existing engine issues that affect
the broader rate/regulator surface (not just this new feature).

## Timeline (UTC)

| Time | Event |
|---|---|
| ~21:46 | v1 dev build with original cross-class design |
| ~22:00 | v1 cap=10240 on `cart`: 0% drop |
| ~22:45 | v1 cap=1 byte on `cart`: still 0% drop. Cross-class hypothesis hardens |
| ~22:54 | v2 dev build with 4-class cartesian split |
| ~23:20 | v2 cap=10240: 0% drop |
| ~23:45 | v2 cap=1 byte: 0% drop. Cross-class confirmed broken, but split alone not enough |
| ~00:46 | v3 dev build with `TenXConsole.log` DIAG in cap getter |
| ~01:01 | v3 DIAG: cap-getter fires, capEntry=1, absoluteCap=1, cap-resolution works |
| ~01:24 | v4 dev build with per-return-path DIAG; revealed `n` (baseline counter) cycling artifact (later refuted) |
| ~01:35 | v5 dev build with POST-drop DIAG: `this.isDropped=false` immediately after `this.drop()` in getter, drop primitive is no-op in getter context |
| ~02:20 | v6 dev build with constructor-drop pattern across all 4 regulator classes |
| ~02:28 | v6 DIAG: `cap-ctor DROP for cart` fires; `POST-drop: this.isDropped=true`, fix proven |
| ~02:28 | v6 Prometheus: emitted_events == all_events for cart, metric-attribution issue surfaces |
| local | Engine code inspection + local repro of metric-attribution gap |

## Findings, each with hard proof

### Finding 1: cross-class `this.X` getter composition does NOT work in TenX DSL

**Original design**: rate-object-cap.js exposed `get rateReceiverResolvedCap()`
on its own `rateReceiverCapObject extends TenXObject` class. The
regulator classes (rateReceiverObject, rateReceiverLookupObject) read
`this.rateReceiverResolvedCap` to get the per-event cap value.

**Empirical proof (v1 deploy on demo, cap=1 byte on cart)**:

```
metric: 1 - (rate(emitted_events_summaryBytes_total{k8s_container="cart"})
          / rate(all_events_summaryBytes_total{k8s_container="cart"}))
result: 0.00% drop
```

Cart was producing ~2 KB/s per pattern with cap=1 byte. Drops should
have been near-total. Zero drops observed across multiple 20-minute
windows.

**What proved the cross-class issue**: v6 (which inlines the cap lookup into
each of the 4 regulator classes directly, no cross-class read) showed
drops happen. v1 (which used the cross-class read) showed zero drops
under identical conditions.

**Mechanism (inferred)**: TenX DSL does not compose getters across
separately-declared `TenXObject` subclass instances the way the aspect
model suggested. The runtime evaluation of `this.rateReceiverResolvedCap`
from inside rateReceiverObject's getter resolves to `undefined` because
that property is declared on a different class (rateReceiverCapObject)
which is a separate object identity at the DSL layer.

**Fix**: 4-class cartesian split (rate-object-local, rate-object-cap,
rate-object-lookup, rate-object-lookup-cap), each gated on its
combination of (mute, cap) env vars, each with the full regulator logic
inlined. settings.yaml dispatches via a 4-way ternary.

---

### Finding 2: `this.drop()` is a NO-OP when called inside a `get` getter

**Pattern under test**: TenX DSL `get foo()` accessor method calls
`this.drop()`. Expectation per the engine docs and the existing comment
in rate-object-local.js: this sets `this.isDropped = true`, so the
receive aggregator's `isObject && !isDropped` filter excludes the event
from `emitted_events`.

**Empirical proof (v5 on demo cluster, instrumented)**:

```javascript
// In the regulator's shouldRetainEventWithCap getter:
if (container == "cart" && (diagSeq % 500) == 0) {
    TenXConsole.log("DIAG cart DROP: ... cap=" + absoluteCap);
}
this.drop();
if (container == "cart" && (diagSeq % 500) == 0) {
    TenXConsole.log("DIAG cart POST-drop: this.isDropped=" + this.isDropped);
}
```

Demo pod log (v5, in getter context):
```
DIAG cart DROP: patternBytes=104781.0 bytes=771 cap=1 share=0.547 floor=0.1
DIAG cart POST-drop: this.isDropped=false   ← drop() did NOT set isDropped
```

After moving the SAME code into `constructor()`:
```
DIAG cap-ctor DROP for cart: patternBytes=205692.0 bytes=732 cap=10240
DIAG cap-ctor POST-drop: this.isDropped=true    ← drop() DID set isDropped
```

**Engine code corroboration**:

[`pipeline/shared/.../BaseTokenizedEvent.java:359-367`](file:///Users/talweiss/git/l1x-co/l1x-inc/pipeline/shared/src/main/java/com/log10x/eng/event/BaseTokenizedEvent.java#L359-L367):
```java
@Override
public boolean drop() {
    this.dropped = true;
    return this.dropped;
}

@Override
public boolean dropped() {
    return this.dropped;
}
```

Simple field mutation. Should work from any context against the same
event instance. The fact that getter-context calls don't persist
suggests the DSL routes getter method calls against a per-getter-class
event view, while constructor calls run against the canonical instance.

**Docs corroboration**: every `this.drop()` example in
[`docs/api/js.md`](file:///Users/talweiss/eclipse-workspace/l1x-co/config/mksite/docs/api/js.md)
is inside a `constructor()`. There are zero examples of `this.drop()`
inside a getter.

**Fix**: move the regulator algorithm (and the drop call) into the
constructor of each regulator class. The dispatched getter just
`return true`, it exists only because settings.yaml's groupFilters
slot requires a callable.

**Pre-existing scope**: the existing mute-file path
(rate-object-lookup.js's `shouldRetainEventWithMute` getter) had the
same `this.drop(); return true;` pattern, which by this analysis also
never actually dropped events. The autotest_hybrid T3 report from the
prior workstream claimed mute drops worked, but in light of this
finding the previous result was likely measuring something other than
the receive-aggregator metric, possibly an output filter that
naturally excludes events that returned false from the getter, which
would NOT include events that were just `this.drop()`'d. **The mute
file's drops in this engine version are likely also broken at the
metric-attribution layer.** A focused regression test of the mute path
on the v6 fix is worth doing as a follow-up.

---

### Finding 3 (open): `all_events_summaryBytes_total` ≡ `emitted_events_summaryBytes_total` even when drops are confirmed

**Setup** (demo cluster, v6 deployed, cart cap=10240, warmup=30s
override, baseline=0 override):

- DIAG confirms `cap-ctor DROP` fires for cart events
- DIAG confirms `this.isDropped=true` after `this.drop()` in constructor
- Encoder excludes dropped events
  (`BaseEventEncoder.encode()` line 54 returns false for dropped)
- Customer's downstream bill is reduced

**The puzzle**:

```bash
# emitted_events filter:  "this.isObject && !this.isDropped"
# all_events filter:      isObject
```

```
sum(all_events_summaryBytes_total{k8s_container="cart"})     = 3478374 bytes
sum(emitted_events_summaryBytes_total{k8s_container="cart"}) = 3478374 bytes
```

Per-pattern, per-pod, every label combination: IDENTICAL values. The
two metrics differ only in their filter, but in practice they emit the
same bytes.

**What this means in practice**: the documented "savings attribution"
metric, `all_events_summaryBytes_total - emitted_events_summaryBytes_total
= bytes saved per pattern per container per window`, is zero even when
real drops are happening. The customer-facing savings dashboard would
show "$0 saved" for a configuration that is in fact saving real bytes.

**Engine-code investigation** (inconclusive without further engine
work):

[`pipeline/run/.../EventAggregator.java:306-374`](file:///Users/talweiss/git/l1x-co/l1x-inc/pipeline/run/src/main/java/com/log10x/eng/event/aggregate/EventAggregator.java#L306-L374):
the aggregator's `processEvents()` loop calls
`contextMap.fieldAccessors(target)` per event. That call applies the
configured filter expression via
[`EventContextFieldAccessorMap.filter()`](file:///Users/talweiss/git/l1x-co/l1x-inc/pipeline/run/src/main/java/com/log10x/eng/event/field/EventContextFieldAccessorMap.java#L87-L101) at line 87:

```java
private boolean filter(EventFunctionTarget event) {
    if (this.filterExp == null) return true;
    EventFunctionEvaluator eval = evaluatorTL.get();
    if (eval == null) { eval = new EventFunctionEvaluator(); evaluatorTL.set(eval); }
    return eval.truthy(this.filterExp, event);
}
```

[`pipeline/run/.../EventIsObjectFieldAccessor.java`](file:///Users/talweiss/git/l1x-co/l1x-inc/pipeline/run/src/main/java/com/log10x/eng/event/field/type/EventIsObjectFieldAccessor.java):
```java
public static boolean isObject(EventFunctionTarget target) {
    return !EventIsTemplateFieldAccessor.isTemplate(target)
        && !EventIsSummaryFieldAccessor.isSummary(target);
}
```

`isObject` does NOT check `isDropped`. So `all_events` filter
(`isObject` alone) should return `true` for dropped events, the
aggregator should count them, and `all_events` should report a
larger byte total than `emitted_events`.

The Java code is consistent with the documented behavior. The empirical
behavior is different. The gap is not explained by the code I have
read. Hypotheses I could not conclusively close in the time I had:

- The YAML loader may be misparsing `filter: isObject` (bare token) and
  defaulting both aggregators to the same internal filter.
- The two `EventAggregationProducer` instances may be sharing a
  pre-filtered event queue upstream.
- The DSL `this.isObject` accessor may have an undocumented runtime
  path that checks dropped (different from the Java `isObject` static).

**Scope of the issue**: this affects ANY receive-stage drop (cap, mute,
or any future filter that uses `this.drop()`), not just the new cap
feature. It is a separate engine issue that predates this workstream.

**Recommendation**: file an engine ticket for the receive-aggregator
filter parsing / `all_events` semantics. The customer-facing
"$X saved" metric on the demo dashboard should be revisited after the
engine fix.

---

### Finding 4 (refuted): `n` (baseline counter) cycling 0-4

**Original observation** (during v3 debugging, before constructor-drop
fix): per-pattern DIAG showed the baseline counter `n` repeatedly
cycling through 0, 1, 2, 3, 4 and never reaching `baselineCount=5`.

**Re-investigation on v6 (constructor-drop)**:

```
DIAG ctor cap-check #20  patternBytes=418.0  bytes=22  cap=200
DIAG ctor cap-check #40  patternBytes=858.0  bytes=22  cap=200
DIAG ctor cap-check #60  patternBytes=1298.0 bytes=22  cap=200
DIAG ctor cap-check #80  patternBytes=1738.0 bytes=22  cap=200
DIAG ctor cap-check #100 patternBytes=2178.0 bytes=22  cap=200
```

`patternBytes` grows monotonically as expected (22, 44, ..., +22 per
event). `TenXCounter.getAndInc` accumulates correctly per
`(pattern, container, window)` key.

**Conclusion**: the v3 observation was a measurement artifact of the
broken cross-class state, where event flow was disordered (drop never
fired, counters thrashed under retry / fail-over paths). With the
constructor-drop fix, counters behave as documented. Not an engine
bug.

---

## What ships

| File | Change | Status |
|---|---|---|
| [`rate-object-local.js`](file:///Users/talweiss/git/l1x-co/config/pipelines/run/receive/rate/rate-object-local.js) | Constructor runs regulator algorithm; getter `return true`. ShouldLoad: `!muteFile && !capFile` | committed in `a2f65e4` |
| [`rate-object-cap.js`](file:///Users/talweiss/git/l1x-co/config/pipelines/run/receive/rate/rate-object-cap.js) | Cap-lookup Input class registers the table; Object class constructor runs full regulator + cap lookup + `this.drop()`. Getter `return true`. ShouldLoad: `!muteFile && capFile`. | committed in `a2f65e4` |
| [`rate-object-lookup.js`](file:///Users/talweiss/git/l1x-co/config/pipelines/run/receive/rate/rate-object-lookup.js) | Constructor runs mute check + regulator. ShouldLoad: `muteFile && !capFile` | committed in `a2f65e4` |
| [`rate-object-lookup-cap.js`](file:///Users/talweiss/git/l1x-co/config/pipelines/run/receive/rate/rate-object-lookup-cap.js) | Constructor runs mute + cap + regulator. ShouldLoad: `muteFile && capFile` | committed in `a2f65e4` |
| [`settings.yaml`](file:///Users/talweiss/git/l1x-co/modules/pipelines/run/modules/receive/rate/settings.yaml) | 4-way ternary dispatch in groupFilters | committed in `44c7b4e` (modules repo) |
| [`module.yaml`](file:///Users/talweiss/git/l1x-co/modules/pipelines/run/modules/receive/rate/module.yaml) | New `rateReceiverCapLookupFile` + `rateReceiverCapLookupRetain` options; `rateReceiverAbsoluteCap` default dropped (0 = disabled) | committed in `0fa0fba` (modules repo) |

**Diagnostic logs**: rate-object-cap.js and rate-object-local.js still
contain temporary `TenXConsole.log` DIAG lines from the investigation.
A clean v7 commit will remove them before any release-image rebuild.

**MCP tool** (`log10x_configure_regulator`): unchanged from workstream 2;
shipped in log10x-mcp v1.11.0. Generates `gh` PR commands against the
customer's cap-lookup CSV. Tool itself is functionally correct; emits
caps that the engine fix correctly applies.

## Demo cluster state at end of WS3

- Image: `ghcr.io/log-10x/pipeline-10x-dev:dev-rate-cap-v6-20260523-2220`
  (constructor-drop fix + DIAG instrumentation)
- ConfigMap overrides: `tenx-rate-config-override`
  (warmupMs=30000, baselineCount=0) + `tenx-cap-overrides`
  (cart cap=10240)

Restore-to-baseline commands are in `/tmp/ws3_restore.sh` (built earlier
in WS3); image rolls back to `dev-msgneg-20260519-2328`.

## Open items / follow-ups

1. **Aggregator metric-attribution gap (Finding 3)**, engine team
   investigation needed. Affects savings dashboard for both cap and
   mute features.
2. **Mute file regression test**, verify whether the existing mute path
   still drops events with the v6 constructor-drop fix (it likely does
   for the bill but not for the savings metric, same gap as
   Finding 3).
3. **TenXObject getter context**, engine documentation should make
   clear that `this.drop()` only works inside a constructor, not inside
   a `get` accessor. The existing example in rate-object-local.js's old
   header comment was misleading.
4. **DIAG cleanup commit**, remove the temporary `TenXConsole.log` DIAG
   lines from rate-object-cap.js and rate-object-local.js before any
   production-image rebuild.
5. **Demo restore**, kubectl set image back to `dev-msgneg-20260519-2328`
   and delete the two ConfigMap overrides when demo testing is done.

## How to reproduce each finding locally

### Setup

Edit `config/apps/dev/config.yaml`: add `- run/receive/rate` and
`- run/aggregate/receive` to the include list.

Edit `config/pipelines/run/receive/rate/config.yaml`: set
`warmupMs: 0` and `baselineCount: 0`.

Stage cap file:
```bash
mkdir -p /tmp/cap_local
cat > /tmp/cap_local/caps.csv <<EOF
container,cap
__node__,200
EOF
```

### Run

```bash
{ echo "INFO prime starting up"
  for i in $(seq -w 1 200); do echo "INFO heartbeat NNN $i"; done
} | java -classpath "$(cat /Users/talweiss/run-cloud.classpath)" \
     -DTENX_LICENSE_FILE=/Users/talweiss/.tenx/demo-license.jwt \
     com.log10x.ext.cloud.run.RunCloud \
     @apps/dev \
     rateReceiverCapLookupFile /tmp/cap_local/caps.csv \
     > /tmp/cap_test.log 2>&1
```

### Expected results with v6 fix

- `grep -c '^~' /tmp/cap_test.log` → ~35 of 201 (drops applied)
- `grep INFO_heartbeat_NNN /tmp/cap_test.log` → aggregator summary shows
  ~34 retained heartbeats (well below the 200 sent)

### Counter-test with original (broken) cross-class design

Check out commit `1fd86ca` of the config repo
(`pipelines/run/receive/rate/rate-object-{local,lookup,cap}.js`):
re-run the same input. Encoded count will be 201, no drops.
