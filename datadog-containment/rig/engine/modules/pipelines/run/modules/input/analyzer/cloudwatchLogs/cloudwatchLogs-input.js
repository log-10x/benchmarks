// @loader: tenx

import {TenXInput, TenXObject, TenXString, TenXEnv, TenXLog, TenXCounter, TenXMath} from '@tenx/tenx'

/*
 this script updates the AWS CloudWatch Logs 'GetLogEvents' request's 'nextToken'
 value with that of the most recent 'nextToken' value returned by the previous REST call
 to continuously request the next page of results

 The 'GetLogEvents' function formats the body of the 'GetLogEvents' REST request.
 The function is called by the Apache Camel route defined in './route.yaml' 
*/

//Set the initial 'cloudwatchLogsLimit' and 'cloudwatchLogsNextToken" values using an 10x input initializer
export class CloudWatchLogs extends TenXInput {

	// load this class if the input was created by an AWS CloudWatch logs input module
	// To learn more see https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
	static shouldLoad(config) {
        return config.cloudwatchLogsGroupName;
    }

	constructor() {

		if (!TenXEnv.get("quiet")){			
			TenXConsole.log("📥 Reading input events from AWS CloudWatch logs: " + this.cloudwatchLogsGroupName + ":"  + this.cloudwatchLogsStreamName);
		}

		// apply 'cloudwatchLogsLimit' if set, otherwise, default to 500
		// this value is used for retrieval by 'formatGetLogEventsRequest()' below

		var limit = TenXEnv.get("cloudwatchLogsLimit", 500);
		
		TenXLog.info("cloudwatchLogsLimit: {}",  limit);
		this.cloudwatchLogsLimit = limit;
		
		var startTime = TenXMath.parseInt(this.cloudwatchLogsStartTime, 0);
		var endTime = TenXMath.parseInt(this.cloudwatchLogsEndTime, 0);

		if (endTime - startTime <= 0) {
			throw new Error("invalid time range, start " + startTime + ", end: " + endTime);
		}

		TenXLog.info("cloudwatchLogsStartTime: {}", startTime);
		this.cloudwatchLogsStartTime = startTime;

		TenXLog.info("cloudwatchLogsEndTime: {}", endTime);
		this.cloudwatchLogsEndTime = endTime;

		if (this.cloudwatchLogsNextToken) {
			TenXLog.info("GetLogEventsRequest.nextToken: {}", this.cloudwatchLogsNextToken);
		}

		TenXLog.info("Cloudwatch input initialized: {}", this.inputName);
	}

	// This function uses the config defined in: './module.yaml'
	// to format the AWS 'GetLogEvents' REST request body. It is invoked by './route.yaml'
	// To learn more see: https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_GetLogEvents.html

	get formatGetLogEventsRequest() {

		var request = TenXString.stringify(
			"logGroupName",  this.cloudwatchLogsGroupName,
			"logStreamName", this.cloudwatchLogsStreamName,
			"startTime", 	 this.cloudwatchLogsStartTime,
			"endTime", 		 this.cloudwatchLogsEndTime,
			"startFromHead", this.cloudwatchLogsStartFromHead,
			"limit", 		 this.cloudwatchLogsLimit,
			"nextToken", 	 this.cloudwatchLogsNextToken
		);
		
		TenXLog.debug("formatGetLogEventsRequest: {}", request);
		
		return request;
	}

	// verify our query is different than the previous one sent.
	// As processing of the previous query's result is done in other threads,
	// We need to make sure that when the camel route timer fires, we've
	// completed processing the previous batch and know the next token to request from.
	// the 'cloudwatchLogsRetryTimeout' counter is used as a waiting mechanism if no new data is available
	get shouldInvokeGetLogEvents() {

		if (this.currCloudwatchLogsRequest != this.prevCloudwatchLogsRequest) {

			TenXCounter.getAndSet(this.inputName, 0); //we have updated value, reset timeout counter

			TenXLog.info("posting new page request from token: {}", this.cloudwatchLogsNextToken);
			
			TenXLog.debug("request body: {}, prev: {}", 
				this.currCloudwatchLogsRequest, this.prevCloudwatchLogsRequest);

			return true;
		}

		// Calculate retry cycles accounting for queryInterval
		var retryTimeout = TenXEnv.get("cloudwatchLogsRetryTimeout", 10000);
		var queryInterval = TenXEnv.get("cloudwatchLogsQueryInterval", 5000);
		
		var retryCycles = retryTimeout / queryInterval;
		var retryCounter = TenXCounter.inc(this.inputName);

		if ((retryCounter % retryCycles) == 0) {

			TenXLog.info("retrying page request: retryCounter: {}, retryTimeout: {}ms, cycles: {}, from token: {}", 
				retryCounter, retryTimeout, retryCycles, this.cloudwatchLogsNextToken);
			
			TenXLog.debug("request body: {}", this.currCloudwatchLogsRequest);

			return true;
		}
		
		return false;

	}
}

// This class is used to capture and the 'nextToken' value after each result set to request the next page of results
export class CloudwatchLogsObject extends TenXObject {

	// load this class if the input was created by an AWS CloudWatch logs input module
	// To learn more see https://doc.log10x.com/api/js/#TenXEngine.shouldLoad
	static shouldLoad(config) {
        return config.cloudwatchLogsGroupName;
    }

	constructor() {

		// check if the object created by a 'nextToken' JSON extractor defined in './stream.yaml'
		// to capture the 'nextToken' value from the last AWS CloudWatch 'GetLogEvents' result
		
		// If so, set its value into the 'cloudwatchLogsNextToken' input field.
		// This value is used by 'formatGetLogEventsRequest' above called by './route.yaml'
		// to request the next batch of events. Once done, drop this event from the pipeline.
		
		if (this.extractorKey == "nextForwardToken") {

			TenXLog.debug("GetLogEventsRequest.nextForwardToken: {}", this.text);

			if (TenXEnv.get("cloudwatchLogsStartFromHead")) {

				TenXInput.set("cloudwatchLogsNextToken", this.text);
			}
			
			// no need to send this metadata object into the pipeline
			this.drop();
			
		} else if (this.extractorKey == "nextBackwardToken") {

			TenXLog.debug("GetLogEventsRequest.nextBackwardToken: {}", this.text);

			if (!TenXEnv.get("cloudwatchLogsStartFromHead")) {
				TenXInput.set("cloudwatchLogsNextToken", this.text);
			}
			
			// no need to send this metadata object into the pipeline
			this.drop();
		}		
	}
}
