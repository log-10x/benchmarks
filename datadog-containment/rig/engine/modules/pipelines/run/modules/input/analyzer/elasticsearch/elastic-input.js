// @loader: tenx

import {TenXCounter, TenXEnv, TenXInput, TenXLog, TenXMath, TenXObject, TenXString} from '@tenx/tenx'

/*
 this script updates the elastic query 'search_after' value with
 that of the most recent 'sort' value returned by the elastic 'search' endpoint
 to continuously request the next page of results
*/

export class ElasticSearchInput extends TenXInput {

	// load this class if the input was created by an ElasticSearch input module
	// https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return config.elasticSearchHost;
    }

	constructor() {

		if (!TenXEnv.get("quiet")) {			
			TenXConsole.log("📥 Reading input events from ElasticSearch: {}", this.elasticSearchHost);
		}

		if (this.elasticSearchInitialSearchAfter) {
			TenXLog.debug("elasticSearchInitialSearchAfter: {}", this.elasticSearchInitialSearchAfter);
			this. elasticSearchAfter = this.elasticSearchInitialSearchAfter;
		}

		// set the search start time
		var startTime = TenXEnv.get("elasticSearchStartTime", "now-5m");
		TenXLog.debug("elasticSearchStartTime: {}", startTime);
		this.elasticSearchStartTime = startTime;

		// set the search end time
		var endTime = TenXEnv.get("elasticSearchEndTime", "now");
		TenXLog.debug("elasticSearchEndTime: {}", endTime);
		this.elasticSearchEndTime = endTime;

		// set the timestamp field
		var timestampField = TenXEnv.get("elasticSearchTimestampField", "@timestamp");
		TenXLog.debug("elasticSearchTimestampField: {}", timestampField);
		this.elasticSearchTimestampField = timestampField;

		TenXLog.info("Elastic input initialized: {} to {}", this.inputName, this.formatElasticURL());
	}

	// called by route.yaml
	// Verify that our query is different from the previous one sent.
	// As processing of the previous query's result is done in a different thread,
	// we need to make sure that when the camel route timer fires, we've
	// completed processing the previous batch and know the next token to request from.
	// the 'elasticSearchRetryTimeout' counter is used as a waiting mechanism if no new data is available
	get shouldInvokeElasticQuery() {

		if (this.prevElasticRequest != this.currElasticRequest) {

			TenXLog.info("posting new request from timestamp: {}", this.elasticSearchAfter);

			TenXLog.debug("currElasticRequest: {}, prevElasticRequest: {} ", 
				this.currElasticRequest, this.prevElasticRequest);

			TenXCounter.getAndSet(this.inputName, 0); //we have updated value, reset timeout counter
			
			return true;
		}

		// Calculate retry cycles accounting for queryInterval
		var retryTimeout = TenXEnv.get("elasticSearchRetryTimeout", 10000);
		var queryInterval = TenXEnv.get("elasticSearchQueryInterval", 5000);
		
		var retryCycles = retryTimeout / queryInterval;

		var retryCounter = TenXCounter.inc(this.inputName);

		if ((retryCounter % retryCycles) == 0) {

			TenXLog.info("retrying page request: retryCounter: {}, retryTimeout: {}ms, cycles: {}, from timestamp: {}", 
				retryCounter, retryTimeout, retryCycles, this.elasticSearchAfter);

			TenXLog.debug("request body: {}", this.currElasticRequest);

			return true;
		}

		return false;
	}

	// called by ./route.yaml
	get formatElasticURL() {

		var host = this.elasticSearchPort ?
			TenXString.join(":", this.elasticSearchHost, this.elasticSearchPort) :
			this.elasticSearchHost;

		var targets = TenXString.join(",", TenXEnv.get("elasticSearchTargets", "*"));

		var endpoint = TenXEnv.get("elasticSearchEndpoint", "_search");

		var protocol = TenXEnv.get("elasticSearchProtocol", "https");

		var baseUrl = TenXString.join("/", host, targets, endpoint);

		var result = TenXString.join("://", protocol, baseUrl);

		TenXLog.debug("elastic endpoint: {}", result);

		return result;
	}

	// called by ./route.yaml
	get formatElasticAuthHeader() {

		var prefix = TenXEnv.get("elasticSearchAuthorizationKeyName", "ApiKey");

		var result = TenXString.join(" ", prefix, this.elasticSearchToken);

		return result;
	}

	// called by ./query.txt
	get elasticSearchAfter() {

		if (!this.elasticSearchAfter) {
			return "";
		}

		var searchAfterClause = TenXString.concat(",\"search_after\":", this.elasticSearchAfter);

		TenXLog.debug("elastic search_after: {}", searchAfterClause);

		return searchAfterClause;
	}
}

// update the 'sort' value after each result set
export class ElasticSearchSortObject extends TenXObject {

	// https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return config.elasticSearchHost;
    }

	constructor() {

		// check if the object created by a 'sort' JSON extractor defined in './stream.yaml'
		// to capture the 'sort' value from the last elastic search result
		if (this.extractorKey == "sort") {

			var prevElasticSearchAfter = TenXInput.get("elasticSearchAfter");

			// jump one millisecond forward
			var currElasticSearchAfter = (this.text == prevElasticSearchAfter) ?
				TenXMath.parseInt(prevElasticSearchAfter) + 1 :
				this.text;

			// set its value into the 'elasticSearchAfter' input field.
			// This value is used by the default search query set in './route.yaml'
			// to request the next batch of events.
			// The elastic camel route queries the value via its 'tenx' bean
			TenXInput.set("elasticSearchAfter", currElasticSearchAfter);

			TenXLog.info("next elastic search_after: {}", currElasticSearchAfter);

			// we don't need this value anymore, so drop it from pipeline

			this.drop();
		}
	}
}
