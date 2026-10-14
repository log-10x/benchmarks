// @loader: tenx

import {TenXInput, TenXEnv, TenXConsole} from '@tenx/tenx'

export class OtelCollectorOtlpInput extends TenXInput {

    // @https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
       return !TenXEnv.get("quiet");
    }

    constructor() {

        if (this.inputName == "otelCollector") {
            TenXConsole.log("📥 Reading events from OpenTelemetry Collector via OTLP/gRPC on tcp://0.0.0.0:" + TenXEnv.get("otelCollectorInputPort"));
        }
    }
}
