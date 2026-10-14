---
icon: material/text-search
---

Analyzer inputs retrieve events from log analytics backends via REST APIs to [transform](https://doc.log10x.com/run/transform/) them into typed TenXObjects.  

The [Dev app](https://doc.log10x.com/apps/dev/) app launches analyzer inputs within scheduled tasks (e.g., k8s CronJob) to read a sample amount of events (e.g., 10Mb of events in the last 5min) to identify and report on the app/infra events that incur the highest costs. 

### :material-toy-brick-outline: Extensibility

The [Apache Camel](https://camel.apache.org/) integration framework enables connectivity and event ingestion from 400+ data sources without requiring custom coding, using [YAML Routes](https://camel.apache.org/components/4.4.x/others/yaml-dsl.html).

For a full example of integrating a log analyzer service, see the [Datadog Logs route](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/input/analyzer/datadogLogs/route.yaml).

## :material-bug-outline: Debugging

Each route has an explicit logger that can be enabled for debugging.

| Logger Name | App/Input | Description |
|-------------|-----------|-------------|
| `splunkRoute` | [Splunk Analyzer](/run/input/analyzer/splunk/) | Splunk REST API requests/responses |
| `elasticsearchRoute` | [Elasticsearch Analyzer](/run/input/analyzer/elasticsearch/) | Elasticsearch query requests/responses |
| `cloudwatchLogsRoute` | [CloudWatch Logs Analyzer](/run/input/analyzer/cloudwatchLogs/) | AWS CloudWatch API requests/responses |
| `datadogLogsRoute` | [Datadog Logs Analyzer](/run/input/analyzer/datadogLogs/) | Datadog API requests/responses |

To enable trace-level logging for a specific route, add the logger to your `log4j2.yaml`:

=== "Splunk"

    ```yaml
    loggers:
      logger:
        - name: splunkRoute
          level: trace
    ```

=== "Elasticsearch"

    ```yaml
    loggers:
      logger:
        - name: elasticsearchRoute
          level: trace
    ```

=== "CloudWatch Logs"

    ```yaml
    loggers:
      logger:
        - name: cloudwatchLogsRoute
          level: trace
    ```

=== "Datadog Logs"

    ```yaml
    loggers:
      logger:
        - name: datadogLogsRoute
          level: trace
    ```

### :material-eye-outline: What Debug Logs Show

When trace logging is enabled, the route logs include:

- **Request headers**: Authentication tokens, content types
- **Request body**: Query parameters, search filters
- **Response headers**: Rate limits, pagination info
- **Response body**: Full API response data

### :material-clipboard-check-outline: Example Debug Session

1. **Enable the logger** in `$TENX_CONFIG/log4j2.yaml`:

    ```yaml
    loggers:
      logger:
        - name: splunkRoute
          level: trace

        - name: org.apache.camel
          level: info

      root:
        level: info
    ```

2. **Run the app** and check the log file:

    ```bash
    tail -f /var/log/tenx/tenx.log | grep -i splunk
    ```

3. **Look for error patterns**:

    ```
    # Authentication errors
    [TRACE] splunkRoute - Response: {"messages":[{"type":"ERROR","text":"Unauthorized"}]}

    # Connection errors
    [ERROR] org.apache.camel - Failed to connect to splunk.example.com:8089

    # Query errors
    [TRACE] splunkRoute - Response: {"messages":[{"type":"FATAL","text":"Search query is malformed"}]}
    ```

