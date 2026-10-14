// @loader: tenx

import { TenXObject, TenXEnv, TenXCounter, TenXMap, TenXMath, TenXLog, TenXConsole, TenXDate } from '@tenx/tenx'

// Per-container noise regulator -- NO-MUTE, NO-CAP-FILE variant.
//
// This is one of FOUR regulator-decision classes split across the (mute,
// cap) cartesian. Each variant has its own getter name dispatched by
// settings.yaml's groupFilters 4-way ternary, because TenXLookup.get is
// parse-validated against runtime-registered tables -- a class that
// references a lookup table that may not be loaded fails engine init.
//
//   shouldLoad gates:                           Getter:
//   - rateReceiverObject:             !mute && !cap   shouldRetainEvent
//   - rateReceiverCapObject:          !mute &&  cap   shouldRetainEventWithCap
//   - rateReceiverLookupObject:        mute && !cap   shouldRetainEventWithMute
//   - rateReceiverLookupCapObject:     mute &&  cap   shouldRetainEventWithMuteAndCap
//
// This file is the NO-MUTE NO-CAP-FILE variant: no lookups at all, cap
// comes from the fleet-wide `rateReceiverAbsoluteCap` env var only. If the
// env var is 0 (default), the regulator does nothing.
//
// Cross-class composition was attempted first (a per-event getter
// `rateReceiverResolvedCap` on a separate cap-class read via
// `this.rateReceiverResolvedCap`) and verified BROKEN on the demo cluster:
// the getter never fired from this class's regulator. TenX DSL does not
// compose property-style getters across separately-declared TenXObject
// classes the way the aspect model suggested. Inlining the lookup didn't
// work either: parse-validation walks every loaded class and rejects
// TenXLookup.get when the table is not registered, regardless of runtime
// if-guards. The 4-class cartesian is the structurally honest answer.
//
// WHAT THE CAP DOES (the cap variants): once a log pattern has spent its
// resolved cap bytes in a container within the `rateReceiverResetIntervalMs`
// window, the regulator engages for that pattern. The cap is NOT a hard
// bound: step 5 below runs after step 3, so above the cap a flood still
// passes at the floor rate (ERROR and CRITICAL half, WARN three tenths,
// everything else a tenth), and the worst case for one pattern in one
// container per window is the cap plus the floor share of everything above
// it. Cap resolution priority:
//   1. `rateReceiverCapLookupFile` (cap-file variants only)
//   2. `rateReceiverAbsoluteCap` env var (this variant)
//   3. No cap: the over-cap branch is skipped, event retained, no counter
//      state accumulated. Protection is strictly opt-in.
//
// Decision order per event (only runs when a cap IS resolved):
//   1. Warmup: container left unregulated for `warmupMs` after this regulator
//      instance first sees its events (per-instance, not per container birth --
//      a regulator restart restarts the window). Default 5 min.
//   2. Baseline: first `baselineCount` events of each pattern kept per
//      window for forensic visibility.
//   3. ABSOLUTE CAP (primary trigger): under cap -> keep.
//   4. SHARE GUARD: pattern is small share of a chatty container -> keep.
//   5. Severity floor wins over cap: keep with probability = floor.
//
// ENGINE NOTES:
//   - Counter keyspace is bounded by AtomicCounterRegistry (~262K LRU);
//     evicted counters re-baseline gracefully.
//   - Counter increments only happen when a cap is resolved, so unprotected
//     containers accumulate zero counter cardinality.
//   - Fail-open: an exception in a receive-stage filter must result in
//     retain. Engine-wide policy.

export class rateReceiverInput extends TenXInput {

    // Validation runs whenever there is no mute file; this Input is shared by
    // both the no-cap (rate-object-local.js) and with-cap (rate-object-cap.js)
    // regulator-object classes -- we don't want to validate twice or split
    // the validation across files.
    static shouldLoad(config) {
        return !TenXEnv.get("rateReceiverLookupFile");
    }

    constructor() {

        if (!TenXEnv.get("quiet")) {
            TenXConsole.log("🚦 Applying rate regulator to: " + this.inputName);
        }

        if (!TenXEnv.get("levelField")) {
            throw new Error("the rate receiver module requires 'level' enrichment: https://doc.log10x.com/run/initialize/level/");
        }

        var resetIntervalMs = TenXEnv.get("rateReceiverResetIntervalMs", 240000);

        if (!(resetIntervalMs >= 60000)) {
            throw new Error("the 'rateReceiverResetIntervalMs' argument must be at least 60000 (1 minute), received: " + resetIntervalMs);
        }

        var warmupMs = TenXEnv.get("rateReceiverWarmupMs", 300000);

        if (!(warmupMs >= 0)) {
            throw new Error("the 'rateReceiverWarmupMs' argument must be >= 0, received: " + warmupMs);
        }

        var maxShare = TenXEnv.get("rateReceiverMaxSharePerFieldSet", 0.2);

        if (!((maxShare > 0) && (maxShare <= 1))) {
            throw new Error("the 'rateReceiverMaxSharePerFieldSet' argument must be in (0, 1], received: " + maxShare);
        }
    }
}

export class rateReceiverObject extends TenXObject {

    // No mute file AND no cap file: pure env-var cap path.
    static shouldLoad(config) {
        return !TenXEnv.get("rateReceiverLookupFile") && !TenXEnv.get("rateReceiverCapLookupFile");
    }

    // The regulator algorithm runs in the groupFilter getter (the correct
    // pipeline phase: post-grouping, on the whole event), dispatched by
    // settings.yaml's groupFilters slot. `this.route("drop")` here MARKS the event
    // routeState="drop"; the marked event keeps flowing. The encoder no longer filters
    // marked events out of output (engine change), so each output stream's
    // filter decides: isObject = emit (soft-drop), isObject && !this.isRoute("drop")
    // = suppress (hard-drop). The getter always returns true so the engine
    // does not remove the event at the group stage -- the mark is the signal.
    get shouldRetainEvent() {

        if ((!this.isObject) || (this.isRoute("drop"))) return true;

        var fieldSetKey = this.joinFields("_", TenXEnv.get("rateReceiverFieldNames"));
        if (!fieldSetKey) return true;

        // Inline the env lookup; a local var passed to this.get() is treated as an event field.
        var container = this.get(TenXEnv.get("rateReceiverContainerField"));
        if (!container) container = "__node__";

        // No cap-file path here -- fleet-wide env var only.
        var absoluteCap = TenXEnv.get("rateReceiverAbsoluteCap", 0);
        if (absoluteCap == 0) return true;

        var key = fieldSetKey + "@" + container;
        var bytes = this.utf8Size();

        var level = this.get(TenXEnv.get("levelField"));
        var floorMap = TenXMap.fromEntries(TenXEnv.get("rateReceiverSeverityFloors"));
        var floorRaw = TenXMap.get(floorMap, level, "");
        var floor = floorRaw ? TenXMath.parseDouble(floorRaw) : TenXEnv.get("rateReceiverMinRetentionThreshold", 0.1);

        var windowMs = TenXEnv.get("rateReceiverResetIntervalMs", 240000);
        var patternBytes = TenXCounter.getAndInc("rg_num_" + key, bytes, windowMs);
        var containerBytes = TenXCounter.getAndInc("rg_den_" + container, bytes, windowMs);
        var n = TenXCounter.getAndInc("rg_cnt_" + key, 1, windowMs);

        var now = TenXDate.now();
        var firstSeen = TenXCounter.getAndInc("rg_seen_" + container, 0);
        if (firstSeen == 0) {
            TenXCounter.getAndSet("rg_seen_" + container, now);
            return true;
        }
        if ((now - firstSeen) < TenXEnv.get("rateReceiverWarmupMs", 300000)) return true;
        if (n < TenXEnv.get("rateReceiverBaselineCount", 5)) return true;
        if ((patternBytes + bytes) <= absoluteCap) return true;
        var minSharePercent = TenXEnv.get("rateReceiverMinSharePercent", 0.05);
        var share = (patternBytes + bytes) / (containerBytes + bytes);
        if (share < minSharePercent) return true;
        if (TenXMath.random() < floor) return true;

        this.route("drop");
        return true;
    }
}
