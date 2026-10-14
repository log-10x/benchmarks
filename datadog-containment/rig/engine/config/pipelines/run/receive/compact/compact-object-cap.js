// @loader: tenx

import { TenXObject, TenXEnv, TenXLookup, TenXConsole, TenXDate, TenXString, TenXMath, TenXLog } from '@tenx/tenx'

// Per-pattern compaction predicate.
//
// Reads a cap-file keyed by `fieldSetKey` (joined from
// `compactReceiverFieldNames`, the pattern field `symbolMessageField` names).
// Listed patterns get the entry's `true|false` decision; unlisted patterns
// fall back to `compactReceiverDefault`.
//
// CSV format: pattern_hash,<true|false>[:<untilEpochSec>[:<reason>]]
//   e.g.  payment_retry_timeout,true:1745856000:OPS-5123
//
// The env var `compactReceiverLookupFile` is the gate the engine recognises.
// Do not rename it without an engine change.

export class CompactInput extends TenXInput {

    static shouldLoad(config) {
        return TenXEnv.get("compactReceiverLookupFile");
    }

    constructor() {

        if (!TenXEnv.get("quiet")) {
            TenXConsole.log("🗜️ Loading compact cap file: " + TenXEnv.get("compactReceiverLookupFile"));
        }

        var compactLastModified = TenXLookup.load(TenXEnv.get("compactReceiverLookupFile"), true);
        var compactRetain = TenXEnv.get("compactReceiverLookupRetain", 300000);

        if (TenXDate.now() - compactLastModified > compactRetain) {
            if (!TenXEnv.get("quiet")) {
                TenXConsole.log("⚠️ compact receiver cap file is stale, lastModified: {}, retainInterval: {}",
                    compactLastModified, compactRetain);
            }
            TenXLog.info("compact receiver cap file is stale, lastModified: {}, retainInterval: {}",
                compactLastModified, compactRetain);
        }
    }
}

export class CompactObject extends TenXObject {

    static shouldLoad(config) {
        return TenXEnv.get("compactReceiverLookupFile");
    }

    // Per-event compact decision. Pure -- returns the bool, doesn't mutate
    // the event. Called by the forwarder output stream's field expression
    // `encoded=shouldEncode() ? encode() : fullText`, which is substituted
    // into each forwarder's output by run/input/forwarder/config.yaml when
    // compactReceiverLookupFile is set.
    get shouldEncode() {

        if ((!this.isObject) || (this.isRoute("drop"))) return false;

        var defaultEncodeRaw = TenXEnv.get("compactReceiverDefault", false);
        var defaultEncode = (defaultEncodeRaw == true) || (defaultEncodeRaw == "true");

        // Key on the pattern identity (the symbolMessageField field), matching the
        // rate receiver's rateReceiverFieldNames key so MCP-authored entries
        // address the same pattern_hash the Reporter attributes cost to.
        var fieldSetKey = this.joinFields("_", TenXEnv.get("compactReceiverFieldNames"));
        if (!fieldSetKey) return defaultEncode;

        var entry = TenXLookup.get("compactReceiverLookupFile", fieldSetKey);
        if (!entry) return defaultEncode;

        // Entry shape: `<true|false>[:<untilEpochSec>][:<reason>]`.
        var c1 = TenXString.indexOf(entry, ":", 0);
        var valueEnd = (c1 < 0) ? TenXString.length(entry) : c1;
        var entryValue = TenXString.substring(entry, 0, valueEnd);

        if (c1 >= 0) {
            var c2 = TenXString.indexOf(entry, ":", c1 + 1);
            var untilEnd = (c2 < 0) ? TenXString.length(entry) : c2;
            var untilEpochSec = TenXMath.parseDouble(TenXString.substring(entry, c1 + 1, untilEnd));
            if (untilEpochSec > 0 && (TenXDate.now() / 1000) > untilEpochSec) {
                // TTL expired -- fall back to the default like the entry was never there.
                return defaultEncode;
            }
        }

        return TenXString.startsWith(entryValue, "true");
    }
}
