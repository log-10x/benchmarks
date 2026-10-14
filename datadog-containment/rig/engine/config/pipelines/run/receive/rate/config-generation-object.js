// @loader: tenx

import { TenXInput, TenXObject, TenXEnv, TenXLookup, TenXString } from '@tenx/tenx'

// Config-generation stamp -- the version marker for the cap/budget policy.
//
// RELOCATED here from the initialize/custom sample (my-object.js). It belongs
// in the receiver: configure_engine writes `config-generation.csv` as a SIBLING
// of caps.csv in the cap ConfigMap, and the generation is a hash of that cap
// policy, so the stamp rides next to the budget lookups and reloads in lockstep
// with them (the verifier's stale->live transition is that reload).
//
// Gated on the `rateReceiverConfigGenerationFile` option (declared in
// module.yaml, set via `configGeneration.file` / the `CONFIG_GENERATION_FILE`
// env in config.yaml). OPT-IN and decoupled from caps: set only where the MCP
// writes the file; unset otherwise. Two consequences this fixes vs. the old
// sample placement:
//   1. A bare local 'run' (no receiver, option unset) never loads it -> no crash.
//   2. A receiver running the regulator WITHOUT the MCP closed loop (option
//      unset) simply omits the stamp instead of failing engine init on a
//      missing file.
//
// Input and Object are gated on the SAME option on purpose: the DSL
// parse-validates TenXLookup.get against runtime-registered tables, so an
// Object that reads a table its Input may not have loaded fails init (the same
// reason the regulator uses the (mute,cap) cartesian -- see settings.yaml).

export class configGenerationInput extends TenXInput {

    static shouldLoad(config) {
        return TenXString.length(TenXEnv.get("rateReceiverConfigGenerationFile")) > 0;
    }

    constructor() {
        // key,value CSV with one row: generation,<hash-of-caps>. Reloadable
        // (the `true` registers the file for watch), so a new generation written
        // by configure_engine goes live without an engine restart.
        TenXLookup.load(TenXEnv.get("rateReceiverConfigGenerationFile"), true, "key", "value");
    }
}

export class configGenerationObject extends TenXObject {

    static shouldLoad(config) {
        return TenXString.length(TenXEnv.get("rateReceiverConfigGenerationFile")) > 0;
    }

    constructor() {
        // Stamp the running generation onto every event so it rides the summary
        // metrics as the `tenx_config_version` label (declared in the receiver
        // module settings.yaml). Table is referenced by the option (env-var)
        // name, the same way rate-object-cap.js reads its cap table. "unset"
        // when the row is absent (file present but no generation written yet).
        var g = TenXLookup.get("rateReceiverConfigGenerationFile", "generation", "key", "value");
        this.tenx_config_version = g ? g : "unset";
    }
}
