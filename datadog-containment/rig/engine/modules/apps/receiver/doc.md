---
icon: material/play-circle-outline
---

The Receiver runs alongside your log forwarder and acts on events as they flow through. The rate regulator finds which patterns are over the byte cap set for their service, and an action decides what happens to that excess: pass, sample, compact, tier_down, offload, or drop. An AI agent picks the action per service through the log10x MCP (the `configure_engine` tool); the engine enforces it, and the decision travels as a config change through the GitOps repo.

The actions:

- **pass**: forward unchanged.
- **sample**: forward a rate-limited share against a per-pattern budget.
- **compact**: replace repeated lines with an encoded form the destination expands (lossless only where the destination supports it: Splunk up to 256 KB per event, self-hosted Elasticsearch; a no-op elsewhere). Requires the expand plugin installed in [Splunk](compact/splunk.md) or [Elasticsearch](compact/elasticsearch.md). On ClickHouse the lever is offload, not compact: the per-pattern cap sends overflow to the customer's own bucket.
- **tier_down**: tag the pattern for a cheaper storage tier the destination enforces (Datadog Flex, CloudWatch IA, Azure Monitor Basic/Auxiliary).
- **offload**: route the pattern to customer-owned object storage (S3 or any S3-compatible store) instead of the destination.
- **drop**: stop forwarding the pattern.

The Receiver also runs in **read-only** mode (observation): receive events from the forwarder, run aggregators, and publish pattern-identity metrics with the event stream untouched. Use it for visibility into per-pattern volume and cost before any action is applied. **Read-write** mode (default) applies the actions above.

Log10x is normally driven by an AI agent (Claude, or a model the customer brings) through the log10x MCP server, which installs, configures, and queries via MCP tools. The agent's `configure_engine` tool turns a target percent or budget into a per-pattern action set, carried as a cap/action CSV that lands in the config repo through a GitOps PR and hot-reloads on the next pull. The hand-authored cap YAML and CSV shown below are the same representation an agent produces.

<h3 id="compact">Compact action</h3>

The compact action replaces repeated lines with an encoded form the destination expands at query time, operating on stable pattern identity. It is lossless only on Splunk (up to 256 KB per event) and self-hosted Elasticsearch, and a no-op on managed/SaaS destinations (there the levers are offload or drop). For SIEM-side plugin install, see the [Splunk](compact/splunk.md) and [Elasticsearch](compact/elasticsearch.md) pages.

## :material-clipboard-play-outline: Setup Guide

Follow the steps below. Steps that require customization link to the relevant [Config Files](#config-files) section where you can edit on github.dev or locally.

???+ tenx-bootstrap "Step 1: Install"

    Install the engine on the same machine as your log forwarder. The script installs the [`Runtime`](https://doc.log10x.com/engine/flavors/#runtime) native binary; the DEB and RPM packages carry either the [`Compiler`](https://doc.log10x.com/engine/flavors/#compiler) or [`Runtime (JVM)`](https://doc.log10x.com/engine/flavors/#runtime-jvm). Windows has no native build, so the PowerShell script installs `Runtime (JVM)`:

    - :simple-linux: [Single line script](https://doc.log10x.com/install/singleline/ "curl https://raw.githubusercontent.com/log-10x/pipeline-releases/main/install.sh | bash -s -- --flavor runtime"){data-copy="curl https://raw.githubusercontent.com/log-10x/pipeline-releases/main/install.sh | bash -s -- --flavor runtime"} | [DEB](https://doc.log10x.com/install/linux/#ubuntu-debian) | [RPM](https://doc.log10x.com/install/linux/#red-hat-centos-7)
    - :simple-macos: [Homebrew](https://doc.log10x.com/install/macos/ "brew install log-10x/tap/log10x"){data-copy="brew install log-10x/tap/log10x"}
    - :material-microsoft-windows: [PowerShell script](https://doc.log10x.com/install/win/)
    - :simple-docker: [Docker image](https://doc.log10x.com/install/docker/)

??? tenx-config "Step 2: Set Environment Variables"

    Set these environment variables before running. See [path configuration](https://doc.log10x.com/install/paths/) for details.

    | Variable | Description |
    |----------|-------------|
    | `TENX_MODULES` | Path to your [modules directory](https://doc.log10x.com/install/paths/#modules) |
    | `TENX_CONFIG` | Path to your [configuration directory](https://doc.log10x.com/install/paths/#config) |
    | `TENX_LICENSE_KEY` | Your Log10x license JWT ([licensing](https://doc.log10x.com/manage/license/)); unset, the engine runs on the built-in evaluation license |

    ```bash
    export TENX_MODULES=/etc/tenx/modules
    export TENX_CONFIG=/etc/tenx/config
    export TENX_LICENSE_KEY="$(cat license.jwt)"
    ```

    For production deployments, mount the license as a file and set `TENX_LICENSE_FILE` instead. See [deploy](https://doc.log10x.com/apps/receiver/deploy/).

??? tenx-forwarderinputs "Step 3: Configure Your Forwarder"

    === ":simple-fluentd: Fluentd"

        **Step 1**: Include the 10x receiver configuration:

        ```toml title="my-fluentd.conf"
        # Nix/OSX
        @include "#{ENV['TENX_MODULES']}/pipelines/run/modules/input/forwarder/fluentd/conf/tenx-receive-unix.conf"

        # Windows
        # @include "#{ENV['TENX_MODULES']}/pipelines/run/modules/input/forwarder/fluentd/conf/tenx-receive-stdio.conf"
        ```

        **Step 2**: Apply the `@TENX` label to route events through the receiver:

        === "Route Start"

            Process events directly after reading from input (simplest setup):

            ```xml title="my-fluentd.conf"
            <source>
              @type tail
              path /path/to/file
              tag my_tag
              @label @TENX
            </source>
            ```

            Received events are marked with `@TENX-PROCESSED`. To re-apply `@ROOT`:

            ```toml
            @include "#{ENV['TENX_MODULES']}/pipelines/run/modules/forwarder/fluentd/conf/auxiliary/root.conf"
            ```

        === "Route End"

            Process events after all filters have been applied:

            ```xml title="my-fluentd.conf"
            <source>
              @type tail
              tag my_logs
            </source>

            <filter my_logs>
              @type filter1
            </filter>

            <filter my_logs>
              @type filter2
            </filter>

            <match my_logs>
              @type relabel
              @label @TENX
            </match>

            <label @TENX-PROCESSED>
              <match my_logs>
                @type stdout
              </match>
            </label>
            ```

        === "Mid-Route"

            Insert the receiver between specific plugins:

            ```xml title="my-fluentd.conf"
            <source>
              @type tail
              tag my_logs
            </source>

            <filter my_logs>
              @type filter1
            </filter>

            <match my_logs>
              @type relabel
              @label @TENX
            </match>

            <label @TENX-PROCESSED>
              <filter my_logs>
                @type filter2
              </filter>

              <match my_logs>
                @type stdout
              </match>
            </label>
            ```

        !!! note
            For large files or volume surges, set [XMX](https://www.baeldung.com/jvm-parameters#explicit-heap-memory---xms-and-xmx-options) or use [read_bytes_limit_per_second](https://docs.fluentd.org/input/tail#read_bytes_limit_per_second).

    === ":simple-fluentbit: Fluent-bit"

        !!! note "Sidecar topology"
            Fluent Bit and Log10x run as **peer processes** that exchange events over the Fluent Forward protocol in both directions. No Lua filter, no `io.popen()` subprocess. The bypass (preventing the ingest filters from re-firing and the ingest `[OUTPUT] forward` from looping events) is **tag-prefix namespacing**. Fluent Bit has no labels like Fluentd, so the egress `[INPUT] forward` uses `Tag_Prefix tenx.` to put returning events on a tag namespace that the ingest pipeline doesn't match.

        **Step 1**: Copy the Fluent Bit sidecar recipe:

        ```bash
        cp $TENX_MODULES/pipelines/run/modules/input/forwarder/fluentbit/conf/tenx-sidecar.conf /etc/fluent-bit/
        ```

        **Step 2**: Update sources, filters and destination outputs to match your environment. The recipe wires the ingest `[OUTPUT] forward` to log10x:24224 (matching your source tags) and the egress `[INPUT] forward` listening on :24225 with `Tag_Prefix tenx.`, your destinations match `tenx.*`:

        ```toml title="tenx-sidecar.conf"
        [SERVICE]
            Flush        1
            Log_Level    info

        # Replace with your real sources, tag with anything NOT starting
        # with `tenx.` so the bypass works.
        [INPUT]
            Name         tail
            Path         /var/log/app.log
            Tag          app.logs
            Parser       json

        # Enrichment filters Match the user-tag scheme only (NOT `*`).
        [FILTER]
            Name         modify
            Match        app.*
            Add          cluster ${CLUSTER_NAME}

        # Ingest: hand off to the Log10x sidecar.
        [OUTPUT]
            Name         forward
            Match        app.*
            Host         127.0.0.1
            Port         24224
            Retry_Limit  False

        # Egress: receive processed events back from Log10x. `Tag_Prefix
        # tenx.` is the bypass, `app.logs` returns as `tenx.app.logs`,
        # which filters and the ingest forward output don't match.
        [INPUT]
            Name         forward
            Listen       0.0.0.0
            Port         24225
            Tag_Prefix   tenx.

        # Destinations Match `tenx.*`, replace stdout with your real
        # destination (es, splunk, kafka, s3, …).
        [OUTPUT]
            Name         stdout
            Match        tenx.*
            Format       json_lines
        ```

        **Step 3**: Start Log10x first so the Forward port is listening, then Fluent Bit:

        ```bash
        tenx run @run/input/forwarder/fluentbit @apps/receiver
        fluent-bit -c /etc/fluent-bit/tenx-sidecar.conf
        ```

        Two structurally separate stages prevent loops and double-enrichment: ingest filters/output match `app.*` only, destination outputs match `tenx.*` only. The original tag survives the round trip as the suffix of the prefixed tag (`tenx.app.logs`), so destinations that route on the suffix behave the same as without Log10x in the path.

    === ":simple-beats: Filebeat"

        **Step 1**: Add the 10x input for receiving filtered events:

        ```yaml title="my-filebeat.yml"
        filebeat.config.inputs:
          enabled: true
          # Nix/OSX
          path: ${TENX_MODULES}/pipelines/run/modules/input/forwarder/filebeat/conf/tenxNix.yml
          # Windows
          # path: ${TENX_MODULES}/pipelines/run/modules/input/forwarder/filebeat/conf/tenxWin.yml
        ```

        **Step 2**: Add the receiver processor:

        ```yaml title="my-filebeat.yml"
        filebeat.inputs:
          - type: filestream
            id: my-filestream-id
            paths:
              - /path/to/log

            processors:
              - script:
                  lang: javascript
                  file: ${TENX_MODULES}/pipelines/run/modules/input/forwarder/filebeat/script/tenx-receive.js
        ```

    === ":simple-logstash: Logstash"

        Set up [multiple pipelines](https://www.elastic.co/guide/en/logstash/current/multiple-pipelines.html) in `pipelines.yml`:

        ```yaml title="pipelines.yml"
        - pipeline.id: raw_input
          path.config: "/path/to/conf/upstream.conf"
        - pipeline.id: tenx_pipeline
          path.config: "${TENX_CONFIG}/pipelines/run/input/forwarder/logstash/receive/tenx-pipe-out.conf"
        - pipeline.id: tenx_unix_pipeline
          path.config: "${TENX_CONFIG}/pipelines/run/input/forwarder/logstash/receive/tenx-pipe-in-unix.conf"
        - pipeline.id: processed
          path.config: "/path/to/conf/downstream.conf"
        ```

        ```ruby title="upstream.conf"
        input {
          file { path => /path/to/log }
        }
        output {
          pipeline { send_to => tenx_input_pipeline }
        }
        ```

        ```ruby title="downstream.conf"
        input {
          pipeline { address => user_output_pipeline }
        }
        output {
          stdout { codec => json }
        }
        ```

    === ":simple-opentelemetry: OTel Collector"

        !!! note "Distribution"
            Both directions use OTLP/gRPC (Collector → Log10x and Log10x → Collector), so the core `otelcol` distribution is sufficient. No `otelcol-contrib` build is required. Tested against `otelcol` v0.151.0+.

        **Step 1**: Copy the Collector sidecar recipe:

        ```bash
        cp $TENX_MODULES/pipelines/run/modules/input/forwarder/otel-collector/conf/tenx-sidecar.yaml /etc/otelcol/
        ```

        **Step 2**: Update receivers and destination exporters to match your environment. The `logs/to-tenx` pipeline carries your receivers and enrichment processors through the `otlp/tenx` exporter; the `logs/from-tenx` pipeline carries returning events directly to your destination exporters:

        ```yaml title="tenx-sidecar.yaml"
        receivers:
          # Replace with your real Collector receivers
          filelog:
            include:
              - /var/log/**/*.log
            start_at: end

        exporters:
          # Replace `debug` with your real destinations, elasticsearch, splunk_hec, kafka, awss3, etc.
          debug:
            verbosity: detailed

        service:
          pipelines:
            logs/to-tenx:
              receivers: [filelog]
              processors: [batch]
              exporters: [otlp/tenx]
            logs/from-tenx:
              receivers: [otlp/tenx]
              exporters: [debug]
        ```

        **Step 3**: Start Log10x first so the OTLP/gRPC port is listening, then the Collector:

        ```bash
        tenx run @run/input/forwarder/otel-collector @apps/receiver
        otelcol --config=/etc/otelcol/tenx-sidecar.yaml
        ```

        Keep the egress pipeline (`logs/from-tenx`) processor-free, it carries returning events directly to your destination exporters so enrichment runs exactly once.

    === ":simple-vector: Vector"

        !!! note "Requires Vector v0.34+"
            For the `fluent` source and `socket` sink with `mode: unix`. Vector communicates with the 10x sidecar over Unix domain sockets, newline-delimited text outbound, Fluent Forward inbound.

        **Step 1**: Copy the Vector configuration:

        ```bash
        cp $TENX_MODULES/pipelines/run/modules/input/forwarder/vector/receive/tenxNix.yaml /etc/vector/
        ```

        **Step 2**: Update sources and final sinks to match your environment:

        ```yaml title="tenxNix.yaml"
        sources:
          # Replace with your real Vector sources
          app_logs:
            type: file
            include:
              - /var/log/**/*.log
            read_from: end

        sinks:
          # Replace `console` with your real destination(s), elasticsearch, splunk_hec, kafka, s3, etc.
          final:
            type: console
            inputs:
              - tenx_out
            encoding:
              codec: json
        ```

        **Step 3**: Start Log10x first, then Vector:

        ```bash
        tenx run @run/input/forwarder/vector/receive @apps/receiver
        vector --config /etc/vector/tenxNix.yaml
        ```

        Two disconnected component chains in Vector's graph prevent loops: `app_logs → tenx_in` (events out to 10x) and `tenx_out → final` (received events in from 10x) never wire together.

    === ":simple-splunk: Splunk UF"

        !!! note "File Relay Pattern"
            This integration uses a **file relay pattern**: Fluent Bit + 10x reads from Folder A, receives events, and writes to Folder B. Splunk UF monitors Folder B and handles forwarding to Splunk indexers.

        **Step 1**: Set up folder paths:

        ```bash
        export FOLDER_A=/var/log/app        # App writes here
        export FOLDER_B=/var/log/processed  # UF reads from here
        mkdir -p ${FOLDER_B}
        ```

        **Step 2**: Configure Fluent Bit to read from Folder A, hand off to log10x, and write the processed events back out to Folder B. The egress `[INPUT] forward Tag_Prefix tenx.` is the bypass, only events that have round-tripped through log10x (and thus carry the `tenx.` prefix) hit the `file` output.

        ```toml title="fluent-bit-splunk.conf"
        [SERVICE]
            Flush        1
            Log_Level    info

        [INPUT]
            Name         tail
            Path         ${FOLDER_A}/*.log
            Tag          app.logs

        # Ingest: hand off to the Log10x sidecar.
        [OUTPUT]
            Name         forward
            Match        app.*
            Host         127.0.0.1
            Port         24224
            Retry_Limit  False

        # Egress: receive processed events back from Log10x with Tag_Prefix
        # bypass. `app.logs` returns as `tenx.app.logs`.
        [INPUT]
            Name         forward
            Listen       0.0.0.0
            Port         24225
            Tag_Prefix   tenx.

        # Write processed events (those with the tenx. prefix only) to Folder B.
        [OUTPUT]
            Name         file
            Match        tenx.*
            Path         ${FOLDER_B}
            Format       plain
        ```

        Start log10x first, then fluent-bit: `tenx run @run/input/forwarder/fluentbit @apps/receiver && fluent-bit -c fluent-bit-splunk.conf`.

        **Step 3**: Configure Splunk UF to monitor Folder B:

        ```ini title="inputs.conf"
        [monitor://${FOLDER_B}]
        index = main
        sourcetype = app_logs
        ```

        This keeps Splunk UF as the forwarder (handling buffering, retries, timeouts) while 10x receives events inline. See the [Splunk UF module](https://doc.log10x.com/run/input/forwarder/splunkUF/) for details.

    === ":simple-datadog: Datadog Agent"

        !!! note "File Relay Pattern"
            This integration uses a **file relay pattern**: Fluent Bit + 10x reads from Folder A, receives events, and writes to Folder B. Datadog Agent monitors Folder B and handles forwarding to Datadog.

        **Step 1**: Set up folder paths:

        ```bash
        export FOLDER_A=/var/log/app        # App writes here
        export FOLDER_B=/var/log/processed  # DD Agent reads from here
        mkdir -p ${FOLDER_B}
        ```

        **Step 2**: Configure Fluent Bit to read from Folder A, hand off to log10x, and write the processed events back out to Folder B. The egress `[INPUT] forward Tag_Prefix tenx.` is the bypass, only events that have round-tripped through log10x (and thus carry the `tenx.` prefix) hit the `file` output.

        ```toml title="fluent-bit-datadog.conf"
        [SERVICE]
            Flush        1
            Log_Level    info

        [INPUT]
            Name         tail
            Path         ${FOLDER_A}/*.log
            Tag          app.logs

        # Ingest: hand off to the Log10x sidecar.
        [OUTPUT]
            Name         forward
            Match        app.*
            Host         127.0.0.1
            Port         24224
            Retry_Limit  False

        # Egress: receive processed events back from Log10x with Tag_Prefix
        # bypass. `app.logs` returns as `tenx.app.logs`.
        [INPUT]
            Name         forward
            Listen       0.0.0.0
            Port         24225
            Tag_Prefix   tenx.

        # Write processed events (those with the tenx. prefix only) to Folder B.
        [OUTPUT]
            Name         file
            Match        tenx.*
            Path         ${FOLDER_B}
            Format       plain
        ```

        Start log10x first, then fluent-bit: `tenx run @run/input/forwarder/fluentbit @apps/receiver && fluent-bit -c fluent-bit-datadog.conf`.

        **Step 3**: Configure Datadog Agent to monitor Folder B:

        ```yaml title="conf.d/tenx.d/conf.yaml"
        logs:
          - type: file
            path: ${FOLDER_B}/*.log
            service: myapp
            source: myapp
        ```

        This keeps Datadog Agent as the forwarder (handling buffering, retries, metadata enrichment) while 10x receives events inline. See the [Datadog Agent module](https://doc.log10x.com/run/input/forwarder/datadogAgent/) for details.

    === ":material-test-tube: Test (no forwarder)"

        Test the receiver without setting up a forwarder using the [Dev CLI](https://doc.log10x.com/apps/dev/).

        The dev app uses the [file input module](https://doc.log10x.com/run/input/file/) to read sample log files and writes output to a file, allowing you to verify receiving behavior before integrating with your forwarder.

        **No forwarder configuration required** - provide sample log files to the file input module and skip to [Step 9](#__tabbed_6_5) to run the test.

??? tenx-symbols "Step 4: Symbol Library (optional)"

    Load custom [Symbol library](https://doc.log10x.com/compile/) files to transform events into typed TenXObjects.

    Place symbol files in the `symbolPaths` folders specified in the [symbol config](#symbols).

<span id="pair-with-retriever"></span>
??? tenx-integration "Step 5: Pair with Retriever (optional)"

    Archive all events to S3 before receiving for full retention alongside cost control. The receiver filters what reaches your SIEM; filtered events remain in S3, queryable via [Retriever](https://doc.log10x.com/apps/retriever/) for incident investigation, compliance, and auditing.

    Configure your forwarder to duplicate the event stream, one copy to S3 (all events), one through the receiver (filtered events to SIEM):

    === ":simple-fluentbit: Fluent-bit"

        Use the `rewrite_tag` filter to duplicate events onto an `s3.*` tag before they hit the ingest `[OUTPUT] forward` to the 10x sidecar:

        ```ini
        [FILTER]
            Name         rewrite_tag
            Match        app.*
            Rule         $log .+ s3.$TAG true

        # S3 archive: gets every event (`app.*` originals AND their `s3.app.*` copies
        # adjust the rule above if you want only the copies).
        [OUTPUT]
            Name         s3
            Match        s3.*
            bucket       your-archive-bucket
            region       us-east-1
            total_file_size 50M
            upload_timeout 60s

        # Ingest: hand off to the Log10x sidecar (processed path).
        [OUTPUT]
            Name         forward
            Match        app.*
            Host         127.0.0.1
            Port         24224
            Retry_Limit  False
        ```

        Events tagged `s3.*` go to S3 (every event for full retention); events tagged `app.*` continue through the sidecar (processed). The egress `[INPUT] forward Tag_Prefix tenx.` and destinations matching `tenx.*` are unchanged from the main recipe.

    === ":simple-fluentd: Fluentd"

        Use the `copy` output plugin to send events to both S3 and the 10x sidecar:

        ```xml
        <match app.**>
          @type copy
          <store>
            @type s3
            s3_bucket your-archive-bucket
            s3_region us-east-1
            path logs/
            <buffer time>
              timekey 3600
              timekey_wait 10m
            </buffer>
          </store>
          <store>
            @type forward
            # → 10x sidecar
          </store>
        </match>
        ```

    === ":simple-opentelemetry: OTel Collector"

        Fan out to the Retriever destination from the **ingest** pipeline (before 10x receives), so the archive sees full-volume events. The destinations that consume the **egress** pipeline (`logs/from-tenx`) get the receiver-processed stream:

        ```yaml
        exporters:
          awss3:
            s3uploader:
              region: us-east-1
              s3_bucket: your-archive-bucket
          # → 10x sidecar processes and receives, results land on logs/from-tenx
          otlp/tenx:
            endpoint: 127.0.0.1:4317
            tls:
              insecure: true
            # One sender keeps records in the order they were read; the engine
            # groups multi-line events from consecutive records.
            sending_queue:
              num_consumers: 1

        service:
          pipelines:
            logs/to-tenx:
              receivers: [filelog]
              processors: [batch]
              # Full-volume fanout: archive + 10x sidecar
              exporters: [awss3, otlp/tenx]
            logs/from-tenx:
              receivers: [otlp/tenx]
              exporters: [otlp/siem]   # receiver-processed stream
        ```

    === ":simple-logstash: Logstash"

        Use multiple outputs. Logstash natively sends to all configured outputs:

        ```ruby
        output {
          s3 {
            bucket => "your-archive-bucket"
            region => "us-east-1"
            size_file => 52428800
            time_file => 60
          }
          pipe {
            command => "/opt/tenx-edge/bin/tenx run ..."
            # → 10x sidecar processes and receives these events
          }
        }
        ```

    === ":simple-splunk: Splunk UF"

        Splunk UF uses a [file relay pattern](https://doc.log10x.com/run/input/forwarder/splunkUF/). Fluent Bit + 10x reads from Folder A, processes events, and writes to Folder B. Splunk UF monitors Folder B and forwards to indexers.

        Add the S3 output to the Fluent Bit configuration alongside the file output:

        ```ini
        [FILTER]
            Name         rewrite_tag
            Match        app.*
            Rule         $log .+ s3.$TAG true

        [OUTPUT]
            Name         s3
            Match        s3.*
            bucket       your-archive-bucket
            region       us-east-1
            total_file_size 50M
            upload_timeout 60s

        # Received events written to Folder B for Splunk UF
        [OUTPUT]
            Name         file
            Match        *
            Path         ${FOLDER_B}
            Format       plain
        ```

        Splunk UF continues to monitor Folder B via `inputs.conf`. No changes to the UF configuration.

    === ":simple-datadog: Datadog Agent"

        Datadog Agent uses a [file relay pattern](https://doc.log10x.com/run/input/forwarder/datadogAgent/). Fluent Bit + 10x reads from Folder A, processes events, and writes to Folder B. The Datadog Agent monitors Folder B and forwards to Datadog.

        Add the S3 output to the Fluent Bit configuration alongside the file output:

        ```ini
        [FILTER]
            Name         rewrite_tag
            Match        app.*
            Rule         $log .+ s3.$TAG true

        [OUTPUT]
            Name         s3
            Match        s3.*
            bucket       your-archive-bucket
            region       us-east-1
            total_file_size 50M
            upload_timeout 60s

        # Received events written to Folder B for Datadog Agent
        [OUTPUT]
            Name         file
            Match        *
            Path         ${FOLDER_B}
            Format       plain
        ```

        The Datadog Agent continues to monitor Folder B via `conf.d`. No changes to the Agent configuration.

<span id="receivers2"></span>
??? tenx-receivers "Step 6: Configure Receivers (optional)"

    Configure [rate receivers](https://doc.log10x.com/run/receive/rate/) for common scenarios. Edit these settings in your receiver [config.yaml](#receivers).

    === ":material-percent: Per-Pattern Cap"

        Set a 10 MB budget for any single log pattern per container per window. No cap is set by default, so this block is what turns the regulator on. The [Level Classifier](https://doc.log10x.com/run/initialize/level/) enriches events with severity, so the floor keeps ERROR events flowing even when a pattern is over its cap.

        ```yaml
        rateReceiver:
          fieldNames:
            - message_pattern            # the pattern identity
          containerField: container      # scopes the cap to one service
          absoluteCap: 10485760          # 10 MB per pattern per container per window
          minSharePercent: 0.05          # leave patterns under 5% of their container alone
          severityFloors:
            - INFO=0.1
            - WARN=0.3
            - ERROR=0.5
        ```

        The floor beats the cap: a pattern over 10 MB still keeps Error 50%, Warn 30%, Info 10%. At or below the cap every event passes through untouched. Whatever the floor does not keep is dropped, unless an action file gives that container a different action.

        The cap is therefore not a hard bound. The floor check runs after the cap check, so above the cap a flood still passes at the floor rate, and the worst case for one pattern in one container per window is the cap plus the floor share of everything above it.

    === ":material-kubernetes: Multi-App Kubernetes"

        Cap each pattern per app, scoped by container so all of an app's replicas share one cap. The [container name](https://doc.log10x.com/run/initialize/k8s/) stays constant across pods.

        ```yaml
        rateReceiver:
          fieldNames:
            - message_pattern
          containerField: container      # same name across all pod replicas
          absoluteCap: 10485760          # 10 MB per pattern per container per window
        ```

        Each (pattern, container) pair gets its own 10 MB cap. Scaling from 1 to 10 pods does not bypass it because the container name is stable across replicas. To give one app a different cap, list it in a cap file, which wins over `absoluteCap` for that container.

        The severity floors apply here too, so the cap is where the regulator engages rather than a bound on what a pattern can spend.

    === ":material-file-document-edit-outline: Mute File (GitOps)"

        Layer a declarative mute file over the rate receiver, pulled from a git repo. Entries are keyed by the same `fieldNames` values the rate receiver uses (e.g. `message_pattern`), so mutes target the same patterns a Reporter attributes cost to. A listed, active pattern is decided by its entry; every other pattern stays on the cap. Each entry has an explicit sample rate and epoch expiry, so mutes are diff-reviewed, audited, and self-healing.

        ```yaml
        rateReceiver:
          fieldNames:
            - message_pattern
          lookup:
            file: /etc/log10x/config/data/sample/mutes/mutes.csv
            retain: 300000                 # mark stale after 5 minutes
        ```

        The first line of `mutes.csv` is a header row (`fieldSet,value`) — the lookup reads line 1 as column names, so a file without it silently loses its first entry. Entries below it look like `Error_syncing_pod,0.10:1744848000:pod error spam OPS-4821`. See [protection list](https://doc.log10x.com/run/receive/rate/#protection-list) for the format and workflow.

??? tenx-initializers "Step 7: Enrichments (optional)"

    Enrichments add context (severity, HTTP codes) for richer aggregation and filtering.

    **To enable:**

    1. In the [app config](#mainConfig), uncomment the desired enrichment `include` entries
    2. In the [initializers](#initializers) section below, configure each enrichment's settings

??? tenx-metricoutputs "Step 8: Metrics Output (optional)"

    Publish [aggregated](https://doc.log10x.com/run/aggregate/) metrics to time-series databases (Prometheus, Datadog).

    **To enable:**

    1. In the [app config](#mainConfig), uncomment the desired metric output `include` entry
    2. In the [metric outputs](#metricOutputs) section below, configure connection details

??? tenx-mainconfig "Step 9: Run"

    Start your forwarder with the updated configuration:

    === ":simple-fluentd: Fluentd"

        ```console
        $ fluentd -c my-fluentd.conf
        ```

    === ":simple-fluentbit: Fluent-bit"

        Start Log10x first so its Forward port is listening when Fluent Bit starts, then start Fluent Bit:

        ```console
        $ tenx run @run/input/forwarder/fluentbit @apps/receiver
        $ fluent-bit -c /etc/fluent-bit/tenx-sidecar.conf
        ```

    === ":simple-beats: Filebeat"

        ```console title="Nix/OSX"
        $ filebeat -c my-filebeat.yml -e 2>&1 | /opt/tenx-edge/bin/tenx run @run/input/forwarder/filebeat @apps/receiver
        ```

        ```console title="Windows"
        $ filebeat -c my-filebeat.yml -e 2>&1 | "c:\program files\tenx-edge\tenx" run @run/input/forwarder/filebeat @apps/receiver
        ```

    === ":simple-logstash: Logstash"

        ```console
        $ logstash -f my-logstash.conf
        ```

    === ":simple-opentelemetry: OTel Collector"

        Start Log10x first so its OTLP/gRPC port is listening when the Collector starts, then start the Collector:

        ```console
        $ tenx run @run/input/forwarder/otel-collector @apps/receiver
        $ otelcol --config=/etc/otelcol/tenx-sidecar.yaml
        ```

    === ":simple-splunk: Splunk UF"

        **Step 1**: Start Log10x first, then Fluent Bit:

        ```console
        $ tenx run @run/input/forwarder/fluentbit @apps/receiver
        $ fluent-bit -c fluent-bit-splunk.conf
        ```

        **Step 2**: Start (or restart) Splunk UF to pick up Folder B:

        ```console
        $ splunk restart
        ```

        Fluent Bit reads from Folder A, hands off to the Log10x sidecar, and writes processed events back out to Folder B. Splunk UF monitors Folder B and forwards to indexers.

    === ":simple-datadog: Datadog Agent"

        **Step 1**: Start Log10x first, then Fluent Bit:

        ```console
        $ tenx run @run/input/forwarder/fluentbit @apps/receiver
        $ fluent-bit -c fluent-bit-datadog.conf
        ```

        **Step 2**: Start (or restart) the Datadog Agent to pick up Folder B:

        ```console
        $ sudo systemctl restart datadog-agent
        ```

        Fluent Bit reads from Folder A, hands off to the Log10x sidecar, and writes processed events back out to Folder B. Datadog Agent monitors Folder B and forwards to Datadog.

    === ":material-test-tube: Test (no forwarder)"

        Use the [Dev CLI](https://doc.log10x.com/apps/dev/) to test event processing with sample log files.

        **Step 1**: Provide sample log files to the [file input module](https://doc.log10x.com/run/input/file/):

        ```console
        $ cp /path/to/sample.log $TENX_CONFIG/data/sample/input/
        ```

        **Step 2**: Run the dev app:

        ```console
        $ tenx run @apps/dev
        ```

        The dev app reads events from `data/sample/input/*.log` via the file input module, processes them through the receiving pipeline, and writes results to the configured [file output](https://doc.log10x.com/run/output/event/file/).

        **Verify output:**

        ```console
        $ wc -l $TENX_CONFIG/data/sample/output/encoded.log
        ```

        Compare input vs output line counts to verify event processing.

??? tenx-checklist "Step 10: Verify"

    Verify no errors appear in the [log file](https://doc.log10x.com/manage/logging/#log-file-location). For debugging techniques including enabling verbose logging, see [Engine Logging](https://doc.log10x.com/manage/logging/).

    **View results in the dashboard:**

    Once running, view your cost analytics in the [Receiver Dashboard](https://doc.log10x.com/roi-analytics/#edge-receiver).

??? tenx-delete "Step 11: Teardown"

    Nothing runs in the background. Uninstall removes only what was installed.

    === ":simple-macos: Homebrew"

        ```bash
        brew uninstall log10x
        ```

    === ":simple-linux: Linux"

        ```bash
        sudo rm -rf /opt/tenx-edge /etc/tenx /etc/profile.d/tenx-edge.sh
        ```

        If installed via DEB: `sudo apt-get remove tenx-edge`
        If installed via RPM: `sudo yum remove tenx-edge`

    === ":material-microsoft-windows: Windows"

        Uninstall from **Settings > Apps > Installed apps**.

    === ":simple-docker: Docker"

        ```bash
        docker rmi log10x/pipeline-10x:1.1.39
        ```
