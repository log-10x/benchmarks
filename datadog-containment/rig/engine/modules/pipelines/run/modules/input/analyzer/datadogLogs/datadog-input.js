// @loader: tenx

// The functions in this class are invoked by './route.yaml' and ./query.txt' to format the Datadog Logs
// fetch cursor page to request the next page of results

import {TenXInput, TenXString, TenXLog, TenXString, TenXConsole, TenXCounter} from '@tenx/tenx'

export class DatadogInput extends TenXInput {

	// load this class if the input was created by a Datadog logs input module
	// https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return config.datadogLogsHost;
	}

	constructor() {

		if (!TenXEnv.get("quiet")){
			TenXConsole.log("📥 Reading input events from Datadog logs: " + this.datadogLogsHost);
		}
		
		TenXLog.info("Datadog input initialized: {}", this.inputName);
	}

	// called by route.yaml:
	// verify our query is different than the previous one.
	// Since a different thread processed the previous query,
	// we need to make sure that when the camel route timer fires, we've
	// completed processing the previous batch and know the next token to request from.
	// the retryTimeout counter is used as a waiting mechanism if no new data is available
	get shouldInvokeDatadogLogsRequest() {

		if (this.currDatadogLogsRequest != this.prevDatadogLogsRequest) {

			TenXLog.info("posting new request from page: {}", this.datadogPageAfter);

			TenXLog.debug("currDatadogLogsRequest: {}, prevDatadogLogsRequest: {} ", 
				this.currDatadogLogsRequest, this.prevDatadogLogsRequest);
		
			TenXCounter.getAndSet(this.inputName, 0); // we have updated request, reset timeout counter

			return true;
		}

		// Calculate retry cycles accounting for queryInterval		
		var retryTimeout = TenXEnv.get("datadogRetryTimeout", 10000);
		var queryInterval = TenXEnv.get("datadogLogsQueryInterval", 5000);
		
		var retryCycles = retryTimeout / queryInterval;
		
		var retryCounter = TenXCounter.inc(this.inputName);

		if ((retryCounter % retryCycles) == 0) {

			TenXLog.info("retrying page request: retryCounter: {}, retryTimeout: {}ms, cycles: {}, from page: {}", 
				retryCounter, retryTimeout, retryCycles, this.datadogPageAfter);
			
			TenXLog.debug("request body: {}", this.currDatadogLogsRequest);
				
			return true;
		}

		return false;
	}

	// called by query.txt to format the pagination cursor
    get formatDatadogCursor() {

        TenXLog.debug("datadogPageAfter: {}", this.datadogPageAfter);

        return (this.datadogPageAfter) ?
            TenXString.concat("\"cursor\":\"", this.datadogPageAfter, "\",") :
            "";
	}

	// called by route.yaml to decided whether to close the route on EOF:
	get noNextDatadogLogsPage() {

		var page = TenXString.jsonPath(this.datadogLogsMeta, "page");
	
		if (!page) {

			TenXLog.info("closing route! datadogLogsMeta: {}, page: {}", this.datadogLogsMeta, page);
			return true;
		}

		var pageAfter = TenXString.jsonPath(page, "after");
		
		TenXLog.debug("datadogLogsMeta.pageAfter: {}", this.pageAfter);

		if (!pageAfter) {
			TenXLog.info("closing route! datadogLogsMeta: {}, pageAfter: {}", this.datadogLogsMeta, pageAfter);
			return true;
		}

		this.datadogPageAfter = pageAfter;

		return false;
	}
}
