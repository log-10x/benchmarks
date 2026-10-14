// @loader: tenx

import {TenXInput, TenXEnv, TenXLog} from '@tenx/tenx'

/*
 This script initializes the S3 Logs analyzer input.

 The S3 Logs input fetches a single S3 object by key using the GetObject API.
 The Camel route handles the actual fetching - this class just logs initialization.
*/

export class S3LogsInput extends TenXInput {

	// Load this class if the input was created by an AWS S3 Logs input module
	static shouldLoad(config) {
		return config.s3LogsBucket && config.s3LogsKey;
	}

	constructor() {
		var bucket = TenXEnv.get("s3LogsBucket");
		var objectKey = TenXEnv.get("s3LogsKey");

		if (!bucket) {
			throw new Error("s3LogsBucket is required");
		}

		if (!objectKey) {
			throw new Error("s3LogsKey is required - specify the S3 object key to fetch");
		}

		if (!TenXEnv.get("quiet")) {
			TenXConsole.log("Reading input events from AWS S3: s3://" + bucket + "/" + objectKey);
		}

		TenXLog.info("S3 Logs input initialized - bucket: {}, key: {}", bucket, objectKey);
	}
}
