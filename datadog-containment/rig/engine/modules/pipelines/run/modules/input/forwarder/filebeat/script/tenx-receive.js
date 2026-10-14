var console = require('console');

// This function is called by the Filebeat 'script' processor
function process(event) {

	// If the event has been processed, remove the 'tenx' field and return
	if (event.Delete("tenx") == true) {
		return;
	}

	// No need to process the 10x internal logs if they're being consumed by Filebeat
	if (event.Get("fields.log_type") == "tenx_internal") {
		return;
	}

	// Mark the event as a 10x event and write it to stdout.
	event.Put("tenx", true);
	console.info(JSON.stringify(event.fields));

	// Cancel the non-received event
	event.Cancel();
}
