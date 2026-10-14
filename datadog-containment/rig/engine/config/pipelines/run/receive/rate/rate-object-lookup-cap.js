// @loader: tenx

import { TenXObject, TenXEnv, TenXCounter, TenXMap, TenXMath, TenXLog, TenXLookup, TenXConsole, TenXDate, TenXString } from '@tenx/tenx'

// Per-container noise regulator -- WITH-MUTE, WITH-CAP-FILE variant.
//
// One of FOUR regulator-decision classes split across the (mute, cap)
// cartesian. See rate-object-local.js's header for the full overview.
// This file is the WITH-MUTE WITH-CAP-FILE variant: per-event cap is
// resolved from `rateReceiverCapLookupFile` first, then the
// `rateReceiverAbsoluteCap` env var as fallback; mute-file decisions win
// over the regulator path entirely.
//
// One class only: rateReceiverLookupCapObject (regulator + mute-lookup +
// cap-lookup). Input classes for the two lookup tables live in
// rate-object-lookup.js (mute) and rate-object-cap.js (cap), both gated
// on their respective env vars independently of cap/mute state -- so when
// both files are set, both tables are loaded by their respective Input
// classes, and this Object class can call TenXLookup.get on both.
//
// Dispatched via `shouldRetainEventWithMuteAndCap()` from settings.yaml's
// groupFilters 4-way ternary.

export class rateReceiverLookupCapObject extends TenXObject {

    // BOTH mute file AND cap file set.
    static shouldLoad(config) {
        return TenXEnv.get("rateReceiverLookupFile") && TenXEnv.get("rateReceiverCapLookupFile");
    }

    // The regulator algorithm runs in the groupFilter getter (post-grouping,
    // on the whole event). `this.route("drop")` MARKS the event routeState="drop"; the marked
    // event keeps flowing (getter returns true). The encoder no longer filters
    // marked events out of output, so each output stream's filter decides:
    // isObject = emit (soft-drop), isObject && !this.isRoute("drop") = suppress.
    get shouldRetainEventWithMuteAndCap() {

        if ((!this.isObject) || (this.isRoute("drop"))) return true;

        var fieldSetKey = this.joinFields("_", TenXEnv.get("rateReceiverFieldNames"));
        if (!fieldSetKey) return true;

        var level = this.get(TenXEnv.get("levelField"));
        var floorMap = TenXMap.fromEntries(TenXEnv.get("rateReceiverSeverityFloors"));
        var floorRaw = TenXMap.get(floorMap, level, "");
        var floor = floorRaw ? TenXMath.parseDouble(floorRaw) : TenXEnv.get("rateReceiverMinRetentionThreshold", 0.1);

        // ---- 1. mute file (FILE WINS) ----
        var hasActiveMute = false;
        var muteThreshold = 0;
        var entry = TenXLookup.get("rateReceiverLookupFile", fieldSetKey);
        if (entry) {
            var c1 = TenXString.indexOf(entry, ":", 0);
            if (c1 >= 0) {
                var c2 = TenXString.indexOf(entry, ":", c1 + 1);
                var untilEnd = (c2 < 0) ? TenXString.length(entry) : c2;
                var sampleRate = TenXMath.parseDouble(TenXString.substring(entry, 0, c1));
                var untilEpochSec = TenXMath.parseDouble(TenXString.substring(entry, c1 + 1, untilEnd));
                if ((TenXDate.now() / 1000) < untilEpochSec) {
                    hasActiveMute = true;
                    muteThreshold = TenXMath.max(sampleRate, floor);
                }
            }
        }
        if (hasActiveMute) {
            if (TenXMath.random() > muteThreshold) this.route("drop");
            return true; // mute decision is terminal (marked if over threshold)
        }

        // ---- regulator path (cap-file + env-var fallback) ----

        // Inline the env lookup; a local var passed to this.get() is treated as an event field.
        var container = this.get(TenXEnv.get("rateReceiverContainerField"));
        if (!container) container = "__node__";

        var absoluteCap = 0;
        var capEntry = TenXLookup.get("rateReceiverCapLookupFile", container);
        if (capEntry) {
            var capC1 = TenXString.indexOf(capEntry, ":", 0);
            var capBytesEnd = (capC1 < 0) ? TenXString.length(capEntry) : capC1;
            var capCandidate = TenXMath.parseDouble(TenXString.substring(capEntry, 0, capBytesEnd));
            var capActive = true;
            if (capC1 >= 0) {
                var capC2 = TenXString.indexOf(capEntry, ":", capC1 + 1);
                var capUntilEnd = (capC2 < 0) ? TenXString.length(capEntry) : capC2;
                var capUntilEpochSec = TenXMath.parseDouble(TenXString.substring(capEntry, capC1 + 1, capUntilEnd));
                if (capUntilEpochSec > 0 && (TenXDate.now() / 1000) > capUntilEpochSec) {
                    capActive = false;
                }
            }
            if (capActive) absoluteCap = capCandidate;
        }
        if (absoluteCap == 0) {
            absoluteCap = TenXEnv.get("rateReceiverAbsoluteCap", 0);
        }
        if (absoluteCap == 0) return true;

        var key = fieldSetKey + "@" + container;
        var bytes = this.utf8Size();

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

        // Over-budget: the per-service action lookup (keyed by the same
        // container as the cap) decides the disposition of the excess. A
        // capped service with no action row passes: the cap alone never
        // loses a line. The forwarder recipe + the output encodeField honor
        // offload/tier_down/compact/sample/drop.
        // Entry shape (mirrors the cap entry): <action>[:<untilEpochSec>[:<reason>]].
        var action = TenXEnv.get("rateReceiverDefaultAction", "pass");
        if (TenXString.length(TenXEnv.get("rateReceiverActionLookupFile")) > 0) {
            var actionEntry = TenXLookup.get("rateReceiverActionLookupFile", container);
            if (actionEntry) {
                var aC1 = TenXString.indexOf(actionEntry, ":", 0);
                var actionEnd = (aC1 < 0) ? TenXString.length(actionEntry) : aC1;
                var actionActive = true;
                if (aC1 >= 0) {
                    var aC2 = TenXString.indexOf(actionEntry, ":", aC1 + 1);
                    var aUntilEnd = (aC2 < 0) ? TenXString.length(actionEntry) : aC2;
                    var aUntil = TenXMath.parseDouble(TenXString.substring(actionEntry, aC1 + 1, aUntilEnd));
                    if (aUntil > 0 && (TenXDate.now() / 1000) > aUntil) actionActive = false;
                }
                if (actionActive) action = TenXString.substring(actionEntry, 0, actionEnd);
            }
        }

        this.route(action);
        return true;
    }
}
