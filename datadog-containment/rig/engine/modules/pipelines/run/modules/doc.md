Reusable packages of configuration, JavaScript, extensions, and documentation that read, receive, and output [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).

Multiple modules combine within a 10x Engine to form [apps](https://doc.log10x.com/apps/).

- **Input modules** read events from local/remote sources for transformation
- **Receiver modules** filter and sample _before_ shipping to output
- **Output modules** write to log analyzers (Splunk, Elastic), forwarders (Fluentd/Bit), and time-series DBs (Prometheus, Datadog) 
  