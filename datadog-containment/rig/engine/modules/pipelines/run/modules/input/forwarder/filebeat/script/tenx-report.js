var console = require('console');

// This function is called by the Filebeat 'script' processor
function process(event) {

	// No need to process the 10x internal logs if they're being consumed by Filebeat
	if (event.Get("fields.log_type") == "tenx_internal") {
		return;
	}

	// Mark the event as an 10x event and write it to stdout.
	event.Put("tenx", true);
	console.info(JSON.stringify(event.fields));

	// Remove marker before continuing with event
	event.Delete("tenx");
}
