# Retriever advisor: install + verify + teardown

## Target
- **app**: retriever
- **release**: `my-retriever`
- **namespace**: `logging`
- **snapshot**: `e100-1792971977960`

## Notes
- Retriever infra (S3 buckets, SQS queues, IAM role + IRSA binding, CloudWatch log groups) is provisioned via the Terraform module, NOT by this advisor. The plan below assumes infra already exists.
- No licence key is written into the values file. The engine runs on its built-in Free tier (up to 10 nodes, no expiry, airgapped) until a key is supplied, and a key is supplied at install time with `--set-string tenx.apiKey="$LOG10X_API_KEY"` so it stays out of any file on disk.

## Preflight
| Check | Status | Detail |
|---|---|---|
| kubectl | `ok` | context `undefined` |
| namespace | `ok` | `logging` exists |
| release collision | `ok` | no `my-retriever` release in `logging`: clear to install |
| AWS access | `ok` | account `?`, region `us-east-1` |
| input S3 bucket | `ok` | `e100-retriever-input` |
| index S3 prefix | `ok` | e100-retriever-input/indexing-results/ |
| IRSA role | `ok` | `arn:aws:iam::000000000000:role/e100-retriever` |
| SQS index queue | `ok` | `https://sqs.us-east-1.amazonaws.com/000000000000/e100-index` |
| SQS query queue | `ok` | `https://sqs.us-east-1.amazonaws.com/000000000000/e100-query` |
| SQS subquery queue | `ok` | `https://sqs.us-east-1.amazonaws.com/000000000000/e100-subquery` |
| SQS stream queue | `ok` | `https://sqs.us-east-1.amazonaws.com/000000000000/e100-stream` |
| queryLogGroup configured | **warn** | queryLogGroup is empty in helm values. Per-query CloudWatch observability disabled; queryEventLog calls early-return without writing.
To enable, set:
  queryLogGroup: log10x-retriever-query-events  # CW log group (pre-create via Terraform or aws logs create-log-group)
AND ensure the retriever IRSA role (arn:aws:iam::000000000000:role/e100-retriever) has logs:CreateLogStream and logs:PutLogEvents on arn:aws:logs:{region}:{account}:log-group:{logGroup}:* |

## Install
### 1. Add Retriever Helm repo
_Makes the log10x/retriever-10x chart available to `helm install`._

```bash
helm repo add log10x https://log-10x.github.io/helm-charts
helm repo update
helm search repo log10x/retriever-10x
```

### 2. Create target namespace
_The Retriever installs into `logging`._

```bash
kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -
```

### 3. Write Helm values
_Wires the tenx block, IRSA ServiceAccount, S3 buckets, and all four SQS queue URLs into the chart._

Write `my-retriever-values.yaml`:

```yaml
tenx:
  enabled: true
  # apiKey: pass at install time with --set-string tenx.apiKey="$LOG10X_API_KEY"
  runtimeName: "my-retriever"
  gitToken: "public-repo-no-token-needed"
  config:
    git:
      enabled: true
      url: "https://github.com/log-10x/config.git"

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::000000000000:role/e100-retriever"

inputBucket: "e100-retriever-input"
indexBucket: "e100-retriever-input/indexing-results/"

indexQueueUrl: "https://sqs.us-east-1.amazonaws.com/000000000000/e100-index"
queryQueueUrl: "https://sqs.us-east-1.amazonaws.com/000000000000/e100-query"
subQueryQueueUrl: "https://sqs.us-east-1.amazonaws.com/000000000000/e100-subquery"
streamQueueUrl: "https://sqs.us-east-1.amazonaws.com/000000000000/e100-stream"
```

### 4. Install via Helm
_Deploys the indexer + query-handler + stream-worker + filter CronJobs._

```bash
helm upgrade --install my-retriever log10x/retriever-10x \
  -n logging --create-namespace \
  -f my-retriever-values.yaml
```

### 5. Wait for rollout
_Blocks until indexer + query-handler + stream-worker report Ready._

```bash
kubectl -n logging rollout status deployment -l app.kubernetes.io/instance=my-retriever --timeout=10m || true
```

## Forwarder offload (cost reduction that keeps every line)
Route the slice 10x marks for offload (`routeState == "offload"`) to the customer's own S3 before the SIEM bills it; the Retriever indexes that bucket and fetches it back by stamped identity. Nothing is deleted, it is relocated: every line is kept.

Target: `s3://e100-retriever-input/app/` (region `us-east-1`), newline-delimited JSON.
Prerequisite on the engine side: run the receiver with `outputOffload true` (full-text events plus the `routeState` marker, every event flowing back).

**fluent-bit offload recipe**

```ini
[SERVICE]
    Grace 5                # let the re-emitted chunks flush before shutdown

# 1) map the routeState marker to a dedicated routing key for the rewrite_tag
#    Rules below. offload/tier_down/drop get their own tags; pass, compact and
#    sample stay on tenx.app for the SIEM. (Keeping rec["routeState"]=="drop"
#    explicit so the noise slice is unambiguous.)
[FILTER]
    Name    lua
    Match   tenx.*
    call    tag_route
    code    function tag_route(tag,ts,rec) local r=rec["routeState"] if r=="offload" then rec["_route"]="offload" elseif r=="tier_down" then rec["_route"]="tier_down" elseif r=="drop" then rec["_route"]="drop" else rec["_route"]="siem" end return 2,ts,rec end

# 2) route each non-SIEM action to its own tag. KEEP=true (4th field): KEEP=false
#    drops the re-emitted record entirely in fluent-bit. The original copy stays
#    on tenx.app and the routed slices are excluded from it in step 3.
[FILTER]
    Name    rewrite_tag
    Match   tenx.*
    Rule    $_route ^offload$   tenx.offload   true
    Rule    $_route ^tier_down$ tenx.tier_down true
    Rule    $_route ^drop$      tenx.drop      true

# 3) keep the routed slices OUT of the SIEM path (the KEEP=true originals on
#    tenx.app). What remains on tenx.app is pass/compact/sample == _route siem.
[FILTER]
    Name    grep
    Match   tenx.app
    Regex   _route ^siem$

# 4) strip the markers (tenx_hash kept).
#    tenx.* spans the retagged tags and the kept tenx.app (the wildcard
#    crosses dots). Safe here because the split is forwarder-side: the routing
#    decision is already carried by the tag, not by a field the destination reads.
[FILTER]
    Name       record_modifier
    Match      tenx.*
    Remove_key routeState
    Remove_key _route

# 5) offload slice -> customer-owned S3 as JSONL
[OUTPUT]
    Name          s3
    Match         tenx.offload
    bucket        e100-retriever-input
    region        us-east-1
    s3_key_format /app/$UUID.jsonl
    use_put_object On
    json_date_format iso8601

# 6) tier_down slice -> your cheaper in-platform SIEM tier.
#    PLACEHOLDER: replace with the OUTPUT for your cheap tier, e.g. a second
#    [OUTPUT] Name cloudwatch_logs pointed at an Infrequent-Access log group,
#    a datadog output tagged to a Flex index, or an azure_logs_ingestion output
#    to an Azure Basic/Auxiliary table. See cloudwatchIaRecipe() /
#    datadogFlexRecipe() / azureLogsTierRecipe() for the destination-side TF.
# [OUTPUT]
#     Name   <your_cheap_tier_output>
#     Match  tenx.tier_down

# 7) drop slice -> SUPPRESSED. The null output discards the noise slice.
[OUTPUT]
    Name   null
    Match  tenx.drop

# 8) pass / compact / sample -> your existing SIEM output, Match tenx.app.
#    compact already carries the engine's encoded bytes on the wire, so no
#    special handling beyond routing it to the SIEM.
```

_Placement: all FILTERs sit on the 10x return path (`Match tenx.*`); `routeState` only exists on post-sidecar records. The lua filter maps the marker to a routing key `_route`, the `rewrite_tag` Rules send offload/tier_down/drop to their own tags (S3 / cheap-tier / `null`), and pass/compact/sample stay on `tenx.app` for the SIEM._

Prerequisites:
- Engine: the receiver runs with `outputOffload true` (full-text events + `routeState` marker, all events flow back to the forwarder).
- IAM: the forwarder's identity can `s3:PutObject` to `e100-retriever-input/app/*`: see `forwarderWriteIamPolicy()` (only the `offload` branch needs this grant).
- Match the route-state name as a STRING (`routeState == "offload"`, `"tier_down"`, `"drop"`, ...), never a boolean test (the engine writes the action name as a JSON string).
- Encoding: KEEP the shipped default `fluentbitOutputEncodeType: delimited`, which delivers `routeState` as its own record field. Do NOT set it to `json`: that collapses the record into a single string field, the routing lua stops matching, and the offload/drop slices silently fall through to the SIEM with no error.
- The lua filter (marker -> routing key) and `KEEP=true` are both mandatory in this shape: the routes are keyed off `_route`, and KEEP=false drops the re-emitted record (verified live on fluent-bit v5).

Other supported forwarders: vector, fluentd, otel-collector, logstash, cribl.

**Forwarder write access** (the one new IAM grant: the Retriever's own role only READS the source bucket). Ready-to-apply Terraform, EKS IRSA, non-EKS noted at the bottom:

```hcl
# Forwarder-write IAM for the offload loop. The forwarder PutObjects the
# routeState=="offload" slice to the Retriever input bucket; the Retriever's own role only
# READS it, so this is a SEPARATE, additive grant.

variable "bucket" {
  type        = string
  description = "Retriever input bucket. Objects land at <bucket>/<prefix>/..."
}
variable "prefix" {
  type        = string
  default     = "app"
  description = "Key prefix == Retriever target. PutObject is scoped to <bucket>/<prefix>/*."
}
variable "oidc_provider_arn" {
  type        = string
  description = "Cluster IAM OIDC provider ARN (arn:aws:iam::<acct>:oidc-provider/oidc.eks.<region>.amazonaws.com/id/<id>)."
}
variable "namespace"       { type = string }   # forwarder ServiceAccount namespace
variable "service_account" { type = string }   # forwarder ServiceAccount name
variable "name_prefix" {
  type    = string
  default = "tenx-forwarder-offload"
}

locals {
  # IRSA conditions key on the issuer URL (no scheme): the part after oidc-provider/.
  oidc_issuer = split("oidc-provider/", var.oidc_provider_arn)[1]
}

# PutObject scoped to <bucket>/<prefix>/*
data "aws_iam_policy_document" "write" {
  statement {
    sid       = "TenxForwarderOffloadWrite"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["arn:aws:s3:::${var.bucket}/${var.prefix}/*"]
  }
}

resource "aws_iam_policy" "write" {
  name   = "${var.name_prefix}-write"
  policy = data.aws_iam_policy_document.write.json
}

# IRSA trust: OIDC-federated assume-role pinned to ONE ServiceAccount.
data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "forwarder_offload" {
  name               = var.name_prefix
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

resource "aws_iam_role_policy_attachment" "write" {
  role       = aws_iam_role.forwarder_offload.name
  policy_arn = aws_iam_policy.write.arn
}

# Annotate the forwarder ServiceAccount: eks.amazonaws.com/role-arn = <this arn>
output "forwarder_offload_role_arn" {
  value = aws_iam_role.forwarder_offload.arn
}

# Non-EKS: reuse aws_iam_policy.write unchanged; only the identity differs.
#   EC2/self-managed:  attach it to the node instance-profile role.
#   on-prem/outside AWS: attach it to an aws_iam_user + aws_iam_access_key,
#                        feed the key into the forwarder's S3 output creds.
```

**Or down-tier in the SIEM instead of offloading** (keep events in-platform at a cheaper tier, same `routeState` marker, no second attribute):

_Elasticsearch frozen tier_: Elasticsearch tiering is INDEX-level, so the shipper routes the marked slice to its own index and ILM does the rest. Verified live: the frozen index reported store=0b locally while the hot control stayed at 19.2kb, and a term query on `tenx_hash` still returned 400/400 with `routeState` aggregatable, so the down-tiered slice remains retrievable by stamped identity. PREREQUISITE: searchable snapshots need an Enterprise licence (Elastic documents no lower tier for them), plus a registered snapshot repository (Elastic Cloud provides `found-snapshots` by default). RESIDENCY: the tier_down template prefers data_warm, so the slice is written on warm and mounts on frozen from there, taking no room on hot. A cluster with no data_warm node places it on hot instead (the preference falls back to data_hot), and the hot-tier run counts it there. KEPT LINES: tenx-keep rolls over daily and mounts the rolled index on frozen 6 days later, so a kept line stays on hot 7 days at most; the hot-tier run reads that from the policy. The tier_down alias rolls over hourly and the kept alias daily, one frozen index per rollover. The recipe has no delete phase, so applying it removes no data; a delete phase at the retention the account wants keeps the shard count on frozen bounded. ON ELASTIC CLOUD HOSTED THE SAVING IS NOT AUTOMATIC: Hosted is priced by provisioned resources, so moving data out of hot creates headroom and the deployment must then be RESIZED to bank it. Do not tell a Hosted customer their bill drops on its own; tell them their hot tier can shrink. Self-managed differs: the saving is disk you stop buying. OPERATIONAL NOTE: ILM polls every 10 minutes by default (`indices.lifecycle.poll_interval`), so a transition will not be visible immediately after rollover; that is not a failure.

```text
# 1) Policy for the tier_down slice: roll over hourly, then mount the rolled
#    index as a PARTIALLY-MOUNTED searchable snapshot in the frozen tier as soon
#    as ILM sees it. The template in 3) writes the slice on warm, so it waits
#    there for its mount and takes no room on hot. With the default 10-minute
#    poll: rollover at the first poll past the hour, the snapshot and mount
#    three polls later.
PUT _ilm/policy/tenx-tier-down
{
  "policy": { "phases": {
    "hot":    { "min_age": "0ms", "actions": { "rollover": { "max_primary_shard_size": "50gb", "max_age": "1h" } } },
    "frozen": { "min_age": "1m", "actions": { "searchable_snapshot": { "snapshot_repository": "found-snapshots" } } }
  }}
}

# 2) Policy for everything we keep: roll over daily, then mount the rolled index
#    on the frozen tier in the same repository. The frozen min_age, counted from
#    rollover, is how long kept lines stay on hot: 6 days after the daily
#    rollover, 7 days at most. The hot-tier run (log10x_setup_recurring
#    hot_tier_gb) reads it, max_age plus min_age, as a kept line's hours on hot.
#    No delete phase: applying the recipe removes no data. Still the control:
#    tier_down lines reach frozen within about two hours of arriving, kept lines
#    only after this retention, so "the slice moved" stays distinct from
#    "everything moved".
PUT _ilm/policy/tenx-keep
{
  "policy": { "phases": {
    "hot":    { "min_age": "0ms", "actions": { "rollover": { "max_primary_shard_size": "50gb", "max_age": "1d" } } },
    "frozen": { "min_age": "6d", "actions": { "searchable_snapshot": { "snapshot_repository": "found-snapshots" } } }
  }}
}

# 3) Templates. The marker decides WHICH INDEX an event lands in; the index
#    decides which policy governs it. tenx_hash and routeState are mapped as
#    keyword so both survive as queryable fields in frozen (verified).
PUT _index_template/tenx-tierdown-tpl
{
  "index_patterns": ["tenx-tierdown-*"],
  "template": {
    "settings": {
      "index.lifecycle.name": "tenx-tier-down",
      "index.lifecycle.rollover_alias": "tenx-tierdown",
      "index.routing.allocation.include._tier_preference": "data_warm,data_hot",
      "number_of_replicas": 0
    },
    "mappings": { "properties": {
      "tenx_hash":  { "type": "keyword" },
      "routeState": { "type": "keyword" },
      "@timestamp": { "type": "date" }
    }}
  }
}

PUT _index_template/tenx-app-tpl
{
  "index_patterns": ["tenx-app-*"],
  "template": {
    "settings": {
      "index.lifecycle.name": "tenx-keep",
      "index.lifecycle.rollover_alias": "tenx-app",
      "number_of_replicas": 0
    },
    "mappings": { "properties": {
      "tenx_hash":  { "type": "keyword" },
      "routeState": { "type": "keyword" },
      "@timestamp": { "type": "date" }
    }}
  }
}

# 4) Bootstrap the write indices. Both policies use rollover, so each alias
#    needs an initial backing index flagged is_write_index. Skipping this is the
#    usual reason ILM sits in check-rollover-ready forever.
PUT tenx-tierdown-000001
{ "aliases": { "tenx-tierdown": { "is_write_index": true } } }

PUT tenx-app-000001
{ "aliases": { "tenx-app": { "is_write_index": true } } }

# 5) Verify, once data has rolled over and aged past min_age. The frozen index
#    is RENAMED with a partial- prefix, which is how you know it mounted:
#
#   GET _cat/indices/*tenx-tierdown*?h=index,docs.count,store.size
#     partial-tenx-tierdown-000001   <docs>   0b     <- data now in found-snapshots
#
#   GET tenx-tierdown-000001/_ilm/explain        -> phase: frozen, step: complete
#   POST partial-tenx-tierdown-000001/_search
#     { "query": { "term": { "tenx_hash": "<a hash you indexed>" } } }
#   ...must still return the documents. If it does not, STOP: the slice is
#   cheap but unretrievable and the down-tier is not worth doing.
```

Point the forwarder at the `tenx-tierdown` alias for events where `routeState == "tier_down"`, and at `tenx-app` for everything else. There is no separate cheap-tier endpoint to configure: on Elasticsearch the index IS the tier selector.

Fetch back: `log10x_retriever_query` by pattern identity returns the offloaded events from S3.

## Verify
Each probe below answers one specific question: run them in order. A probe passes when its commands exit 0 and (optionally) match the `expectOutput` regex.

### 1. pods-ready: Are indexer + query-handler + stream-worker pods Ready?
_Expect to pass within 600s._

```bash
kubectl -n logging wait --for=condition=Ready pod -l app.kubernetes.io/instance=my-retriever --timeout=10m
```

Expect output matching: `condition met`

### 2. indexer-healthy: Is the indexer processing messages from the index queue?
_Expect to pass within 120s._

```bash
kubectl -n logging logs -l app.kubernetes.io/instance=my-retriever,app.kubernetes.io/component=indexer --tail=200 | grep -iE 'index|processed|bloom' | head -20
```

### 3. query-endpoint-healthy: Is the query endpoint responding?

```bash
kubectl -n logging get ingress,svc -l app.kubernetes.io/instance=my-retriever
```

### 4. retriever-service-accessibility: Is the Retriever Service reachable from outside the cluster? If type=ClusterIP, use port-forward, LoadBalancer, or deploy the MCP server inside the cluster.

```bash
kubectl -n logging get svc -l app.kubernetes.io/instance=my-retriever -o json 2>/dev/null | jq -r '.items[] | "Service \(.metadata.name): type=\(.spec.type) port=\(.spec.ports[0].port // "?")"' 2>/dev/null || kubectl -n logging get svc -l app.kubernetes.io/instance=my-retriever -o wide
```

### 5. s3-offload-input: Is the forwarder offloading the dropped slice into the source bucket?

```bash
aws s3 ls s3://e100-retriever-input/app/ --recursive --summarize 2>/dev/null | tail -5 || echo "no objects under app/ yet: if this stays empty the forwarder offload is NOT wired. See the 'Forwarder offload' section: the receiver needs outputOffload=true, the per-forwarder recipe applied, and the forwarder-write IRSA (s3:PutObject to this bucket/app/)."
```

### 6. s3-indexing-results: Is the indexer writing to the index bucket?

```bash
aws s3 ls s3://e100-retriever-input/indexing-results/ --summarize 2>/dev/null | tail -5 || echo "no index results yet (may take a few minutes after first index run). If s3-offload-input is also empty, fix the forwarder offload first: the indexer has nothing to index."
```

### 7. sqs-drainage: Is the index queue being drained (messages not piling up)?

```bash
aws sqs get-queue-attributes --queue-url "https://sqs.us-east-1.amazonaws.com/000000000000/e100-index" --attribute-names ApproximateNumberOfMessages --output json
```

## Teardown
### 1. Uninstall the Helm release
_Removes indexer, query-handler, stream-worker deployments, filter CronJobs, ConfigMaps, and the chart-created ServiceAccount. LEAVES AWS infra (S3, SQS, IAM role) intact: that lifecycle belongs to Terraform._

```bash
helm -n logging uninstall my-retriever
```

### 2. Clean up derived resources
_Helm does not reap PVCs or Secrets created outside the release._

```bash
kubectl -n logging delete pvc -l app.kubernetes.io/instance=my-retriever --ignore-not-found
```

### 3. Verify nothing remains
_Confirm no workloads are lingering under the release label._

```bash
kubectl -n logging get all,configmap,secret,pvc -l app.kubernetes.io/instance=my-retriever
```

### 4. (Optional) teardown AWS infra
_If you're fully removing the Retriever, tear down the Terraform module that created the S3 buckets, SQS queues, and IAM role. Skipping this leaves empty AWS infra behind (zero-cost for SQS idle, pennies for S3 storage)._

```bash
# From your terraform directory:
# terraform destroy -target=module.retriever_aws_infra
```

## How to query the Retriever from outside the cluster

The Retriever Service defaults to **ClusterIP** (cluster-internal only). `log10x_retriever_query` and `log10x_retriever_series` send HTTP requests to the Retriever: from your laptop the cluster-internal URL will fail with ENOTFOUND or ECONNREFUSED.

Pick one option:

### Option A: kubectl port-forward (dev/test, ephemeral)

```bash
kubectl port-forward -n logging svc/my-retriever-retriever-10x-all-in-one 18080:80
```

Then set the Retriever URL so the MCP server can reach it:

```bash
export __SAVE_LOG10X_RETRIEVER_URL__=http://localhost:18080
```

The port-forward is ephemeral: it stops when the terminal session ends. Restart it whenever you need to run retriever queries.

### Option B: Migrate the Service to LoadBalancer (persistent)

Add to your Terraform module call or values file:

```yaml
# retriever-values-lb.yaml
retriever:
  service:
    type: LoadBalancer
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
```

Apply with:

```bash
helm upgrade my-retriever log10x/retriever-10x -n logging -f retriever-values-lb.yaml
```

After the LoadBalancer is provisioned, run `kubectl -n logging get svc my-retriever-retriever-10x-all-in-one` to get the external hostname, then:

```bash
export __SAVE_LOG10X_RETRIEVER_URL__=http://<external-hostname>
```

### Option C: Deploy the MCP server inside the cluster

When the MCP server runs as a pod in the same cluster, the chart-default ClusterIP URL (`http://my-retriever-retriever-10x-all-in-one.logging.svc.cluster.local:80`) resolves correctly with no additional configuration. This is the cleanest path for shared teams and CI pipelines.

---
_Plan built from snapshot `e100-1792971977960`._

**Next actions** (after running the plan above):
  - Verify the install is healthy: `log10x_doctor`, runs all freshness/auth/config checks across reporter, receiver, retriever.
  - Confirm the config snapshot picked up the change: `log10x_discover_env`, shows what the engine sees as the active config.