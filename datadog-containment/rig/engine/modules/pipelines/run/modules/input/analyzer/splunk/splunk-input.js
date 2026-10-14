// @loader: tenx

import {TenXCounter, TenXEnv, TenXInput, TenXLog, TenXString} from '@tenx/tenx'

// the functions in this class are called by: /.route.yaml
export class SplunkInput extends TenXInput {

	// load this class if the input was created by a Splunk input module
	// https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
    static shouldLoad(config) {
        return config.splunkHost;
    }

	constructor() {

		if (!TenXEnv.get("quiet")){			
			TenXConsole.log("📥 Reading input events from Splunk: " + this.splunkHost);
		}

		TenXLog.info("Splunk input initialized: {}, formatSplunkBaseJobURL: {} ",
			this.inputName, formatSplunkBaseJobURL()
		);

		if (!this.splunkHost) {
			throw new Error("no 'splunkHost' set");
		}

		if (!this.splunkUsername) {
			throw new Error("no 'splunkUsername' set");
		}

		if (!this.splunkPassword) {
			throw new Error("no 'splunkPassword' set");
		}
	}

	get formatSplunkBaseJobURL() {

		var host = this.splunkPort ?
			TenXString.join(":", this.splunkHost, this.splunkPort) :
			this.splunkHost;

		var protocol = TenXEnv.get("splunkProtocol", "https");

		var result = TenXString.concat(protocol, "://", host, "/services/search/v2/jobs");

		TenXLog.debug("jobs endpoint: {}", result);

		return result;
	}

	// Returns the SSL query parameters for netty-http
	// If SSL is enabled and verification is disabled, returns params for insecure context
	// Otherwise returns minimal SSL params or empty string
	get formatSslParams() {
		var protocol = TenXEnv.get("splunkProtocol", "https");

		if (protocol != "https") {
			return "";
		}

		var verifySSL = this.splunkVerifySSL;

		if (verifySSL == false) {
			TenXLog.warn("splunkVerifySSL == false, using insecure ssl context");

			return "ssl=true&sslContextParameters=#insecureSslContext";
		}

		return "ssl=true";
	}

	get formatSplunkSearchURL() {

		var host = this.splunkPort ?
			TenXString.join(":", this.splunkHost, this.splunkPort) :
			this.splunkHost;

		var protocol = TenXEnv.get("splunkProtocol", "https");

		var result = TenXString.concat(protocol, "://", host, "/services/search/v2/jobs/", this.splunkSid);

		TenXLog.debug("search url: {}", result);

		return result;
	}

	get formatSplunkResultURL() {

		var host = this.splunkPort ?
			TenXString.join(":", this.splunkHost, this.splunkPort) :
			this.splunkHost;

		var protocol = TenXEnv.get("splunkProtocol", "https");

		var result = TenXString.concat(protocol, "://", host, "/services/search/v2/jobs/", this.splunkSid, "/results");

		TenXLog.debug("search result url: {}", result);

		return result;
	}

	get isWaitingForSplunkJob() {
		return this.splunkSid && !this.splunkIsReady;
	}

	get formatSplunkQuery() {

		var result = TenXString.concat("",
			"&output_mode=json&search=",
			this.splunkQuery
		);

		TenXLog.info("query: {}", result);

		return result;
	}

	// only perform this step if the job is ready and we have more results to scroll through.
	// the value of the 'splunkEventOffset' counter is compared against the 'splunkEventCount' counter
	get shouldFetchNextSplunkPage() {

		var eventOffset = TenXCounter.get(this.inputName);

		TenXLog.debug("isReady: {}, eventOffset: {}, eventCount: {} ",
			this.splunkIsReady, eventOffset, this.splunkEventCount);

		return (this.splunkIsReady) && (eventOffset < this.splunkEventCount);
	}

	get formatSplunkPageQuery() {

		var pageSize = TenXEnv.get("splunkPageSize", 500);

		var result = TenXString.concat("",
			"output_mode=raw&count=",
			pageSize,
			"&offset=",
			TenXCounter.getAndInc(this.inputName, pageSize)
		);

		TenXLog.info("query: {}", result);

		return result;
	}

	get fetchedAllSplunkPages() {

		var eventOffset = TenXCounter.get(this.inputName);

		var result =  (this.splunkIsReady) && (eventOffset >= this.splunkEventCount);

		if (result) {

			TenXLog.info("isReady: {}, eventOffset: {}, eventCount: {}, result: {} ",
				this.splunkIsReady, eventOffset, this.splunkEventCount, result);

		} else {
			
			TenXLog.debug("isReady: {}, eventOffset: {}, eventCount: {}, result: {} ",
				this.splunkIsReady, eventOffset, this.splunkEventCount, result);
		}

		return result;
	}
}
