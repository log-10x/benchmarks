---
icon: material/play-circle-outline
---

Test the Retriever locally using [minikube](https://minikube.sigs.k8s.io/) with either [LocalStack](https://localstack.cloud/) (local AWS emulation) or real AWS services. Each step below provides tabs for both backends. For production deployment via Helm, see the [deployment guide](https://doc.log10x.com/apps/retriever/deploy/).

## :material-clipboard-play-outline: Setup

???+ tenx-bootstrap "Step 1: Prerequisites"

    | Requirement | Description |
    |-------------|-------------|
    | Log10x License | Optional: [MCP sign-in](https://doc.log10x.com/apps/mcp/) mints an API key for full functionality. |
    | minikube | Local Kubernetes cluster ([install guide](https://minikube.sigs.k8s.io/docs/start/)) |
    | kubectl | Kubernetes CLI ([install guide](https://kubernetes.io/docs/tasks/tools/)) |
    | Helm | Kubernetes package manager ([install guide](https://helm.sh/docs/intro/install/)) |
    | Terraform | Infrastructure as code tool ([install guide](https://developer.hashicorp.com/terraform/install)) |
    | AWS CLI | For testing S3/SQS operations ([install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)) |
    | AWS Account | **Required only for the AWS backend tab.** An AWS account with permissions to create S3 buckets, SQS queues, and S3 event notifications. Not needed when using LocalStack. |

??? tenx-minikube "Step 2: Start minikube"

    Start your local Kubernetes cluster:

    ```bash
    minikube start --cpus=4 --memory=8192
    ```

    Verify the cluster is running:

    ```bash
    kubectl cluster-info
    ```

??? tenx-cloud "Step 3: Configure Storage Backend"

    === ":fontawesome-brands-aws: AWS"

        Use real AWS S3 and SQS services. Terraform creates the infrastructure using your AWS credentials, and the pods in minikube access AWS via access keys passed as environment variables.

        **Export your AWS credentials as environment variables.** These are required, Terraform passes them to the retriever pods in minikube so they can reach S3 and SQS.

        If you already have credentials configured via `aws configure` (stored in `~/.aws/credentials`), export them:

        ```bash
        export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
        export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
        export AWS_DEFAULT_REGION=$(aws configure get region || echo "us-east-1")
        ```

        Otherwise, set them directly:

        ```bash
        export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
        export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
        export AWS_DEFAULT_REGION=us-east-1
        ```

        Verify the environment variables are set and valid:

        ```bash
        echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
        aws sts get-caller-identity
        ```

        !!! warning "Environment variables are required"

            Running `aws sts get-caller-identity` alone is not enough, the AWS CLI can authenticate via `~/.aws/credentials` even when the environment variables are empty. The environment variables must be set because they are passed to the retriever pods in Step 7.

        The same credentials are passed to the retriever pods in minikube (via `extraEnv` in the Helm chart) so they can reach S3 and SQS. This is appropriate for local testing. For production, use [IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html).

    === ":material-server: LocalStack"

        [LocalStack](https://localstack.cloud/) provides local AWS service emulation (S3, SQS) running inside your Kubernetes cluster. No AWS account required.

        **Add the LocalStack Helm repository:**

        ```bash
        helm repo add localstack https://localstack.github.io/helm-charts
        helm repo update
        ```

        **Create namespace and install LocalStack:**

        ```bash
        kubectl create namespace localstack

        helm upgrade --install localstack localstack/localstack \
          --namespace localstack \
          --set service.type=ClusterIP \
          --set "extraEnvVars[0].name=SERVICES" \
          --set "extraEnvVars[0].value=s3\,sqs" \
          --wait --timeout 180s
        ```

        **Start port-forward to LocalStack** (keep this running in a separate terminal):

        ```bash
        kubectl port-forward -n localstack svc/localstack 4566:4566
        ```

        **Verify LocalStack is running:**

        ```bash
        curl http://localhost:4566/_localstack/health
        ```

        !!! warning "No query event tracking with LocalStack"
            LocalStack does not emulate CloudWatch Logs, so real-time query progress tracking is not available. To track query execution as it happens, use the **AWS** tab instead.

??? tenx-config "Step 4: Clone and Mount Config Repository (Optional)"

    Clone and mount [github.com/log-10x/config](https://github.com/log-10x/config) to customize metric outputs, symbol files, and engine settings. Without this, you can only modify Fluent Bit via Terraform.

    ```bash
    cd ~
    git clone https://github.com/log-10x/config.git my-tenx-config
    ```

    Start the mount and let it run persistently in the background:

    === ":fontawesome-brands-linux: Linux / macOS"

        ```bash
        nohup minikube mount ~/my-tenx-config:/mnt/tenx-config > /tmp/minikube-mount.log 2>&1 &
        ```

    === ":fontawesome-brands-windows: Windows"

        ```bash
        minikube mount "C:/path/to/my-tenx-config":/mnt/tenx-config
        ```
        (Windows users: run this in a dedicated command prompt that you keep open)

    The mount process will continue running even if your terminal closes. To verify it's running:

    ```bash
    ps aux | grep "minikube mount" | grep -v grep
    ```

    If you made changes to your local config folder and have already deployed via Step 7, restart the pods to pick them up:

    ```bash
    kubectl rollout restart deployment -n log10x-retriever -l app=retriever-10x
    ```
??? tenx-eventoutputs "Step 5: Configure Event Outputs (Optional)"

    Matched events are shipped to your log analyzer via a built-in [Fluent Bit](https://doc.log10x.com/run/output/event/fluentbit/) sidecar that runs alongside each retriever pod. By default, it outputs to `stdout` for debugging. To send events to a real destination, modify the `fluentBit.output` section in your Terraform `main.tf`:

    === ":material-console: stdout"

        Default for local testing. Events print to container logs.

        ```hcl
        fluentBit = {
          output = { type = "stdout" }
        }
        ```

        View output: `kubectl logs -n log10x-retriever -l app=retriever-10x -c fluent-bit`

    === ":simple-elasticsearch: Elasticsearch"

        ```hcl
        fluentBit = {
          output = {
            type = "elasticsearch"
            config = {
              elasticsearch = {
                host  = "elasticsearch.example.com"
                port  = 9200
                index = "logs"
                # httpUser = "elastic"        # Optional auth
                # httpPassword = "changeme"   # Use extraEnv with secretKeyRef instead
              }
            }
          }
        }
        ```

    === ":simple-splunk: Splunk"

        ```hcl
        fluentBit = {
          output = {
            type = "splunk"
            config = {
              splunk = {
                host  = "splunk-hec.example.com"
                port  = 8088
                token = "YOUR-HEC-TOKEN"  # Use extraEnv with secretKeyRef instead
                # index = "main"          # Optional index override
              }
            }
          }
        }
        ```

    === ":simple-datadog: Datadog"

        ```hcl
        fluentBit = {
          output = {
            type = "datadog"
            config = {
              datadog = {
                apiKey = "YOUR-DD-API-KEY"  # Use extraEnv with secretKeyRef instead
                # host = "http-intake.logs.datadoghq.com"  # Default US
                # host = "http-intake.logs.datadoghq.eu"   # EU region
              }
            }
          }
        }
        ```

    === ":material-aws: CloudWatch"

        ```hcl
        fluentBit = {
          output = {
            type = "cloudwatch"
            config = {
              cloudwatch = {
                region        = "us-east-1"
                logGroupName  = "/aws/retriever/events"
                logStreamPrefix = "stream-"
                # autoCreateGroup = true  # Create log group if missing
              }
            }
          }
        }
        ```

        Pods need AWS credentials to write to CloudWatch. For local testing, add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to `extraEnv`. For production EKS, use [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) instead.

    === ":material-aws: S3"

        ```hcl
        fluentBit = {
          output = {
            type = "s3"
            config = {
              s3 = {
                bucket = "my-streamed-events"
                region = "us-east-1"
                # totalFileSize = "100M"     # Rotate after 100MB
                # uploadTimeout = "1m"       # Flush interval
              }
            }
          }
        }
        ```

        Pods need AWS credentials to write to S3. For local testing, add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to `extraEnv`. For production EKS, use [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) instead.

    These settings take effect when you deploy in Step 7, or run `terraform apply` to update an existing deployment.

??? tenx-metricoutputs "Step 6: Configure Metric Outputs (Optional)"

    For **metric outputs** to time-series databases (Prometheus, Datadog, CloudWatch), configure the [metric output modules](https://doc.log10x.com/run/output/metric/) in your pipeline config. Metric outputs aggregate events into metrics (counters, gauges, histograms) before publishing, different from streaming raw events via Fluent Bit.

    **Supported metric outputs:**

    | Output | Config Reference |
    |--------|------------------|
    | Prometheus Remote Write | [remote-write](#remote-write) |
    | Prometheus Push Gateway | [push-gateway](#push-gateway) |
    | Datadog | [datadog](#datadog) |
    | CloudWatch | [cloudwatch](#cloudwatch) |
    | Elastic | [elastic](#elastic) |

    **To enable locally:** Mount your config repository (Step 4) and edit the pipeline config files below.

    **Example: Enable Prometheus Remote Write** in your local pipeline config:

    ```yaml title="apps/retriever/stream/config.yaml"
    # Comment in the line enabling a custom remote write
    - run/output/metric/prometheus/remote-write  # https://doc.log10x.com/run/output/metric/prometheus/remote-write
    ```

    ```yaml title="pipelines/run/output/metric/prometheus/remote-write/config.yaml"
    # Fill the endpoint host and credentials
    - host: http://localhost:9090/api/v1/write # (REQUIRED)

      # 'user' for authentication
      user: my-username # (REQUIRED)

      # 'password' for authentication
      password: my-password # (REQUIRED)
    ```

    See the [Retriever run guide](https://doc.log10x.com/apps/retriever/run/#config-files) for the full list of configurable modules.

??? tenx-terraform "Step 7: Deploy with Terraform"

    **Optional:** If you completed Steps 4-6, verify your config and output settings are ready. Changes take effect when pods start.

    === ":fontawesome-brands-aws: AWS"

        Download the [Terraform configuration](https://github.com/log-10x/terraform-aws-tenx-retriever/blob/main/examples/local-aws/main.tf) and deploy:

        ```bash
        mkdir -p retriever-local && cd retriever-local
        curl -sLO https://raw.githubusercontent.com/log-10x/terraform-aws-tenx-retriever/main/examples/local-aws/main.tf
        terraform init
        terraform apply \
          -var="tenx_api_key=YOUR_API_KEY" \
          -var="aws_access_key_id=$AWS_ACCESS_KEY_ID" \
          -var="aws_secret_access_key=$AWS_SECRET_ACCESS_KEY" \
          -var="local_config_path=/mnt/tenx-config"
        ```

        Omit the `local_config_path` variable if you skipped Step 4 to use the built-in defaults.

        AWS credentials are injected into pods so they can access real S3/SQS from minikube.

        The AWS example includes a CloudWatch Logs log group (`/tenx/{resource_prefix}/query`) for real-time query progress tracking. See Step 10 for how to follow query events.

    === ":material-server: LocalStack"

        Download the [Terraform configuration](https://github.com/log-10x/terraform-aws-tenx-retriever/blob/main/examples/local-localstack/main.tf) and deploy:

        ```bash
        mkdir -p retriever-local && cd retriever-local
        curl -sLO https://raw.githubusercontent.com/log-10x/terraform-aws-tenx-retriever/main/examples/local-localstack/main.tf
        terraform init
        terraform apply \
          -var="tenx_api_key=YOUR_API_KEY" \
          -var="local_config_path=/mnt/tenx-config"
        ```

        Omit the `local_config_path` variable if you skipped Step 4 to use the built-in defaults.

        Ensure LocalStack port-forward is running before applying (`kubectl port-forward -n localstack svc/localstack 4566:4566`).

    **Verify deployment:**

    ```bash
    # Check pods are running (should show 2/2 READY for Fluent Bit sidecar)
    kubectl get pods -n log10x-retriever

    # View retriever logs
    kubectl logs -n log10x-retriever -l app=retriever-10x -c retriever-10x-all-in-one --tail=50
    ```

    **Expected startup log output:**

    ```
    INFO  [com.log10x.ext.quarkus.executor.PipelineExecutor] (main) Initializing cloud accessor...
    INFO  [com.log10x.ext.quarkus.access.aws.AWSAccessor] (main) AWS shared client cache initialized
    INFO  [com.log10x.ext.quarkus.executor.PipelineExecutor] (main) Cloud accessor AWSAccessor initialized
    INFO  [com.log10x.ext.quarkus.executor.PipelineExecutor] (main) Pipeline factory initialized
    INFO  [io.quarkus] (main) run-quarkus 0.2.0 on JVM (powered by Quarkus 3.30.2) started in 1.873s. Listening on: http://0.0.0.0:8080
    INFO  [io.quarkus] (main) Profile prod activated.
    INFO  [io.quarkus] (main) Installed features: [amazon-sdk-sqs, cdi, rest, rest-jackson, scheduler, smallrye-context-propagation, smallrye-health, vertx]
    ```

??? tenx-logfilters "Step 8: Customize Log File Filters (Optional)"

    Control which files in your S3 bucket trigger indexing. By default, only files ending in `.log` are indexed.

    To change the file name filter, modify the Terraform variables in your `main.tf`:

    ```hcl
    # In the retriever_infra module block
    tenx_retriever_index_trigger_prefix = "app/"    # Only index files under the app/ prefix
    tenx_retriever_index_trigger_suffix = ".json"   # Only index .json files
    ```

    Leave `prefix` empty (`""`) to match all paths. The suffix is required. S3 event notifications need at least one filter criterion.

??? tenx-objectstorageindex "Step 9: Test Indexing"

    Upload a test log file to trigger auto-indexing. Only files with `.log` extension trigger indexing (configured via `tenx_retriever_index_trigger_suffix` in Terraform).

    === ":fontawesome-brands-aws: AWS"

        ```bash
        # Create test log file with current timestamp
        echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"level\":\"ERROR\",\"message\":\"Test error\"}" > test.log

        # Upload to S3 (triggers auto-indexing via S3 notification)
        aws s3 cp test.log s3://retriever-logs/app/test.log

        # Check index was created (within 5-15 seconds)
        aws s3 ls s3://retriever-index/indexed/ --recursive
        ```

    === ":material-server: LocalStack"

        ```bash
        # Configure AWS CLI for LocalStack
        export AWS_ACCESS_KEY_ID=test
        export AWS_SECRET_ACCESS_KEY=test
        export AWS_DEFAULT_REGION=us-east-1

        # Create test log file with current timestamp
        echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"level\":\"ERROR\",\"message\":\"Test error\"}" > test.log

        # Upload to S3 (triggers auto-indexing via S3 notification)
        aws --endpoint-url=http://localhost:4566 s3 cp test.log s3://retriever-logs/app/test.log

        # Check index was created (within 5-15 seconds)
        aws --endpoint-url=http://localhost:4566 s3 ls s3://retriever-index/indexed/ --recursive
        ```

    **Verify indexing completed**: check the retriever logs for `IndexTemplates` and `IndexFilterStats` entries:

    ```bash
    kubectl logs -n log10x-retriever -l app=retriever-10x -c retriever-10x-all-in-one --tail=50
    ```

    **Expected indexing log output:**

    ```
    INFO  [executor-thread-3] IndexTemplates - merged templates. templates.size: 1, rawTemplateFiles.size: 0, ...
    INFO  [executor-thread-3] IndexFilterStats - index complete. Bytes: 21, filters.size: 1, probability historgram: [1=>1], key sizes: [0=>1], element counts: [50=>1], epochs: 1
    INFO  [executor-thread-3] ExecutionPipeline - execution of: /etc/tenx/modules/pipelines/run/pipeline.yaml (myObjectStorageIndex) completed in: 7501ms
    ```

    `IndexTemplates` confirms TenXTemplate files were merged and written to the index bucket. `IndexFilterStats` confirms Bloom filters were created for the indexed byte ranges.

??? tenx-objectstoragequery "Step 10: Test Querying"

    **Start port-forward to retriever service** (in a separate terminal):

    ```bash
    kubectl port-forward -n log10x-retriever svc/retriever-retriever-10x-all-in-one 8080:80
    ```

    === ":fontawesome-brands-aws: AWS"

        **Send a query** using the [Query Console](https://doc.log10x.com/apps/retriever/query/) web GUI or CLI. The query page documents all methods, includes sample queries, and shows real-time query progress via CloudWatch Logs.

        Monitor streamed events via Fluent Bit:

        ```bash
        kubectl logs -n log10x-retriever -l app=retriever-10x -c fluent-bit --tail=50
        ```

        Expected output (look for `tenx-cloud-retriever` tag with your matched events):

        ```
        [0] tenx-cloud-retriever: [[<epoch>, {}], {"stream"=>"stderr", "log"=>"<your matched log entry>", ...}]
        ```

        `tenx-template` entries are internal template hashes from the scan phase, not final results. Only `tenx-cloud-retriever` entries are your actual matched events.

    === ":material-server: LocalStack"

        Quick test via curl:

        ```bash
        curl -X POST http://localhost:8080/streamer/query \
          -H "Content-Type: application/json" \
          -d '{
            "from": "now(\"-5m\")",
            "to": "now()",
            "search": "severity_level == \"ERROR\""
          }'
        ```

        The query handler is served at `POST /streamer/query`. The in-engine app path is `@apps/retriever/query`; the public HTTP route keeps the `/streamer/query` name for now, overridable with `LOG10X_RETRIEVER_QUERY_PATH`. The endpoint returns HTTP 200 to acknowledge receipt. Events are processed asynchronously and streamed to Fluent Bit over 30-60 seconds.

        Check the Fluent Bit container logs for streamed events:

        ```bash
        kubectl logs -n log10x-retriever -l app=retriever-10x -c fluent-bit --tail=50
        ```

        Expected output (look for `tenx-cloud-retriever` tag with your matched events):

        ```
        [0] tenx-cloud-retriever: [[<epoch>, {}], {"stream"=>"stderr", "log"=>"<your matched log entry>", ...}]
        ```

        `tenx-template` entries are internal template hashes from the scan phase, not final results. Only `tenx-cloud-retriever` entries are your actual matched events.

??? tenx-delete "Step 11: Teardown"

    Remove all local testing resources when done.

    === ":fontawesome-brands-aws: AWS"

        ```bash
        # Empty S3 buckets first (required before destroy)
        aws s3 rm s3://retriever-logs/ --recursive
        aws s3 rm s3://retriever-index/ --recursive

        # Destroy Terraform resources
        cd retriever-local
        terraform destroy \
          -var="tenx_api_key=YOUR_API_KEY" \
          -var="aws_access_key_id=$AWS_ACCESS_KEY_ID" \
          -var="aws_secret_access_key=$AWS_SECRET_ACCESS_KEY"

        # Optional: Delete minikube cluster
        minikube delete
        ```

        **Important:** S3 buckets cannot be deleted until empty. The `aws s3 rm --recursive` commands remove all objects before `terraform destroy` deletes the buckets.

    === ":material-server: LocalStack"

        ```bash
        # Destroy Terraform resources (S3, SQS, Helm release)
        cd retriever-local
        terraform destroy -var="tenx_api_key=YOUR_API_KEY"

        # Remove LocalStack
        helm uninstall localstack -n localstack
        kubectl delete namespace localstack

        # Optional: Delete minikube cluster entirely
        minikube delete
        ```

## :material-help-circle-outline: Troubleshooting

??? tenx-faq "No events appearing in Fluent Bit logs after query"

    1. **Wait 30-60 seconds**: in this single-node setup, all worker roles (index, query, stream) share resources. Query processing completes once stream workers pick up results from the Stream SQS queue.
    2. **Check the time range**: ensure your query's `from`/`to` range covers the timestamp of your uploaded log file. Using `now("-5m")` queries events from the last 5 minutes.
    3. **Verify query was accepted**: check retriever logs for `QueryWorker` entries:
       ```bash
       kubectl logs -n log10x-retriever -l app=retriever-10x -c retriever-10x-all-in-one --tail=100 | grep -i query
       ```
    4. **Extend processing timeout** by adding `"processingTimeMs": 300000` to your query request body. See [query API reference](https://doc.log10x.com/api/launch/#quarkus) for details.

??? tenx-faq "Query returns no results due to incorrect epoch timestamps or clock skew"

    **Use the [`now()` function](https://doc.log10x.com/api/js/#TenXDate.now) for relative time ranges**: it returns epoch milliseconds and accepts an offset string:

    - `now()`: current time
    - `now("-5m")`: 5 minutes ago
    - `now("-1h")`: 1 hour ago

    If you must use literal epochs, ensure they're in **milliseconds** (not seconds). A common mistake is passing epoch seconds (e.g., `1769076000`) instead of milliseconds (`1769076000000`). Multiply seconds by 1000.

    Additionally, minikube's clock can drift from the host machine after sleep/hibernate. If the retriever's log timestamps don't match your wall clock, resync minikube's clock:

    ```bash
    minikube ssh -- sudo chronyc makestep
    ```

    If `chronyc` is not available, restart minikube instead: `minikube stop && minikube start`.

??? tenx-faq "LocalStack connectivity issues (LocalStack only)"

    If AWS CLI commands fail, re-export the LocalStack environment variables:

    ```bash
    export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
    ```

    Verify LocalStack health and resources:

    ```bash
    # Verify LocalStack is healthy
    curl http://localhost:4566/_localstack/health

    # Check S3 buckets exist
    aws --endpoint-url=http://localhost:4566 s3 ls

    # Check SQS queues exist
    aws --endpoint-url=http://localhost:4566 sqs list-queues
    ```

??? tenx-faq "Terraform errors (AWS only)"

    **S3 bucket name conflict:**

    ```
    Error: creating Amazon S3 Bucket: BucketAlreadyExists
    ```

    S3 bucket names are globally unique across all AWS accounts. Change the `resource_prefix` variable in your `main.tf` to use a unique name:

    ```hcl
    variable "resource_prefix" {
      default = "retriever-myname-12345"  # Add your name/ID to ensure uniqueness
    }
    ```

    **Insufficient permissions:**

    ```
    Error: creating SQS Queue: AccessDenied
    ```

    Your AWS credentials need permissions for S3, SQS, and S3 event notifications. Verify your IAM user/role has the required policies:

    - `s3:CreateBucket`, `s3:PutBucketNotification`, `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:DeleteBucket`
    - `sqs:CreateQueue`, `sqs:GetQueueAttributes`, `sqs:SetQueueAttributes`, `sqs:DeleteQueue`, `sqs:SendMessage`, `sqs:ReceiveMessage`

    **State lock error:**

    ```
    Error: Error acquiring the state lock
    ```

    A previous Terraform run was interrupted. Remove the lock:

    ```bash
    terraform force-unlock LOCK_ID
    ```

    Or if using local state, delete `.terraform.lock.hcl` and retry.
