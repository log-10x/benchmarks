# Install plan: Receiver sidecar

- **App**: Receiver (sidecar)
- **Forwarder**: `fluentbit`
- **Metrics backends**: `elastic`
- **Airgapped**: yes (engine emits only to user-owned backends)
- **License**: none in the plan. The engine runs its built-in Free tier: up to 10 nodes, no expiry, airgapped. Nothing is minted or stored and no licence Secret is created. To license it later, re-run with `license_source: "signin"` or `license_source: "paste"`; the plan then adds the step that creates the licence Secret.

# Receiver advisor: install + verify + teardown

## Target
- **app**: receiver
- **forwarder**: fluentbit
- **release**: `my-receiver`
- **namespace**: `logging`
- **snapshot**: `e100-1792971977960`

## Notes
- Destination is `mock` (events written to forwarder stdout). Ideal for dogfooding or smoke tests; switch to `elasticsearch`, `splunk`, `datadog`, or `cloudwatch` for production.
- The Receiver counts bytes and stamps `tenx_hash` and `utf8Size` (the size its byte limits count) on every record it returns, which the hot-tier run (log10x_setup_recurring `hot_tier_gb`) reads from its indices. Send kept lines to the `tenx-app` alias and `routeState: tier_down` lines to `tenx-tierdown`, with the Elasticsearch frozen-tier recipe from log10x_advise_retriever (`destination: "elasticsearch"`).

## Preflight
| Check | Status | Detail |
|---|---|---|
| kubectl | `ok` | context `undefined` |
| namespace | `ok` | `logging` exists |
| forwarder alignment | **warn** | no existing forwarder detected; the plan installs one from scratch |
| release collision | `ok` | no `my-receiver` release in `logging`: clear to install |
| license | `ok` | no licence configured: the engine runs its built-in Free tier (up to 10 nodes, no expiry, airgapped) and logs that it does at startup. Nothing to mint, store or mount. To license it later, re-run the wizard with `license_source: "signin"` or `"paste"`; the plan then adds a step that creates the licence Secret. |
| destination-expander | `?` | Compaction is only lossless end to end when the destination can expand the encoded events again at read time, and that expander is a separate install on the destination, not part of this release: the [10x Splunk app](https://doc.log10x.com/apps/receiver/compact/splunk/), or the [l1es plugin](https://doc.log10x.com/apps/receiver/compact/elasticsearch/) for self-managed Elasticsearch 8.17.0 / OpenSearch 2.19.0. Install it before you compact anything the destination is searched on, or those searches return compacted lines. Managed and serverless platforms (Datadog, CloudWatch, Elastic Cloud Serverless) have nowhere to install one. Compaction is not offered on ClickHouse, where it measured about 7% of table bytes and the bill is compute. Use tier_down or offload on all of these instead of compaction. |

## Install
### 1. Add Fluent Bit Helm repo
_Makes the fluent/fluent-bit chart available to `helm install`._

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
helm search repo fluent/fluent-bit
```

### 2. Create target namespace
_The Reporter installs into `logging`. `--create-namespace` on helm install will also do this, but a separate step makes retries idempotent._

```bash
kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -
```

### 3. Seed the engine-policy ConfigMap
_The receiver reads its byte caps (caps.csv) and per-service actions (actions.csv) from the `log10x-action-intent` ConfigMap via the engine's kubernetes pull lane. This seeds it with a no-op policy so the pod boots policy-ready (a missing ConfigMap aborts the engine launch by design), and grants every ServiceAccount in `logging` read access to this one ConfigMap. `log10x_configure_engine` writes the real policy here later._

```bash
cat <<'POLICY_EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: log10x-action-intent
  namespace: logging
  labels:
    app.kubernetes.io/managed-by: log10x-mcp
    app.kubernetes.io/component: engine-policy
data:
  caps.csv: |
    container,cap
    tenx-seed,1::install seed; replaced by log10x_configure_engine
  actions.csv: |
    container,action
    tenx-seed,pass::install seed; replaced by log10x_configure_engine
  totals.csv: |
    container,total
    tenx-seed,1::install seed; replaced by the budget run
  regulator-unit: bytes
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: log10x-policy-reader
  namespace: logging
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["log10x-action-intent"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: log10x-policy-reader
  namespace: logging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: log10x-policy-reader
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: Group
    name: system:serviceaccounts:logging
POLICY_EOF
```

### 4. Write Helm values
_Tenx config + Fluent Bit-specific output destination (`mock`)._

Write `my-receiver-values.yaml`:

```yaml
# Receiver overlay for Fluent Bit (upstream fluent/fluent-bit chart).
# Layer on top of your existing values:
#   helm upgrade --install <release> fluent/fluent-bit \
#     -f your-existing-fluent-bit-values.yaml \
#     -f my-receiver.yaml --namespace <namespace>

extraContainers:
  - name: log10x
    image: log10x/edge-10x:1.1.147@sha256:a043ccd828742c4eccee09abb654ce6a7357b6123f73300ed04f8605e874b8c4
    imagePullPolicy: IfNotPresent
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
    args:
      - "@run/input/forwarder/fluentbit"
      - "@apps/receiver"
      - "symbolMessageHashField"
      - "tenx_hash"
      - "outputEncodeField"
      - "fullText(\"tenx_hash\",\"routeState\",\"message_pattern\",\"severity_level\",\"utf8Size\")"
    env:
      - name: TENX_AIRGAPPED
        value: "true"
      - name: K8S_NAMESPACE
        valueFrom:
          fieldRef:
            fieldPath: metadata.namespace
      - name: K8S_ENABLED
        value: "true"
      - name: K8S_CONFIGMAP
        value: log10x-action-intent
      - name: CAP_LOOKUP_FILE
        value: /tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/caps.csv
      - name: ACTION_LOOKUP_FILE
        value: /tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/actions.csv
      - name: CONFIG_GENERATION_FILE
        value: /tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/config-generation.csv
      - name: TOTAL_LOOKUP_FILE
        value: /tmp/tenx/kubernetes/$(K8S_NAMESPACE)/log10x-action-intent/totals.csv
    volumeMounts:
      - name: tenx-tmp
        mountPath: /tmp
    resources:
      requests: { cpu: 100m, memory: 256Mi }
      limits:   { cpu: 500m, memory: 512Mi }

extraVolumes:
  - name: tenx-tmp
    emptyDir: {}

# Replace the chart's default config with the sidecar bypass pattern.
# Inputs: tail your sources + receive processed events back from the
# sidecar on :24225 with Tag_Prefix tenx. (so filters and the ingest
# handoff Match kube.* and skip the returning tenx.*).
# Filters: enrichment (kubernetes metadata) on kube.* only.
# Outputs: handoff to the sidecar on 127.0.0.1:24224 + destination
# for the returning tenx.* events.
config:
  service: |
    [SERVICE]
        Daemon Off
        Flush {{ .Values.flush }}
        Log_Level {{ .Values.logLevel }}
        Parsers_File /fluent-bit/etc/parsers.conf
        Parsers_File /fluent-bit/etc/conf/custom_parsers.conf
        HTTP_Server On
        HTTP_Listen 0.0.0.0
        HTTP_Port {{ .Values.metricsPort }}
        Health_Check On

  inputs: |
    [INPUT]
        Name tail
        Path /var/log/containers/*.log
        Exclude_Path /var/log/containers/*fluent-bit*.log,/var/log/containers/*fluentd*.log,/var/log/containers/*filebeat*.log,/var/log/containers/*logstash*.log,/var/log/containers/*otel-collector*.log,/var/log/containers/*opentelemetry-collector*.log
        multiline.parser docker, cri
        Tag kube.*
        Mem_Buf_Limit 5MB
        Skip_Long_Lines On

    # Egress: returning events from the 10x sidecar. Tag_Prefix tenx.
    # prevents enrichment filters and the sidecar-handoff output from
    # re-firing (they Match kube.* only).
    [INPUT]
        Name forward
        Listen 0.0.0.0
        Port 24225
        Tag_Prefix tenx.

  filters: |
    [FILTER]
        Name kubernetes
        Match kube.*
        Merge_Log On
        Keep_Log Off
        K8S-Logging.Parser On
        K8S-Logging.Exclude On

  outputs: |
    # Hand off to the Log10x sidecar.
    [OUTPUT]
        Name forward
        Match kube.*
        Host 127.0.0.1
        Port 24224
        Retry_Limit False

    # Destination for processed tenx.* events. Replace with your real
    # destination (es, splunk, kafka, s3, ...): this stdout block is
    # safe for dogfooding.
    [OUTPUT]
        Name stdout
        Match tenx.*
        Format json_lines
```

### 5. Install via Helm
_Deploys the Fluent Bit chart with the 10x Receiver sidecar enabled._

```bash
helm upgrade --install my-receiver fluent/fluent-bit \
  -n logging --create-namespace \
  -f my-receiver-values.yaml
```

### 6. Wait for rollout
_Blocks until the workload reports Ready. Uses the chart's own label selector (legacy Helm for elastic charts, k8s-recommended elsewhere): a mismatched selector silently returns "No resources found" and exits 0._

```bash
kubectl -n logging rollout status daemonset -l app.kubernetes.io/instance=my-receiver --timeout=5m || true
kubectl -n logging rollout status deployment -l app.kubernetes.io/instance=my-receiver --timeout=5m || true
kubectl -n logging rollout status statefulset -l app.kubernetes.io/instance=my-receiver --timeout=10m || true
```

## GitOps: MCP-managed runtime config (optional)

Compaction is a per-source switch: the chart `optimize` flag makes the sidecar emit `encode()` for every event it sees, smaller on a destination whose 10x expander is installed (see the prerequisite below; run log10x_measure_compaction for the ratio on the real stream). The compactReceiver cap file is the exception list under that switch: with compactReceiverDefault true, a CSV keyed by the pattern name lists the patterns to keep as full text. Wire GitOps once and edit the list as PRs; the engine hot-reloads the CSV without a pod restart.

**Enable this if:**
- You compact the source and want to keep specific patterns in full text (audit, compliance, debug).
- You want decisions to evolve over time without redeploying the receiver.
- You want the MCP to manage the cap-file via PRs (review-able, reversible).

**Skip this if:**
- You will turn on the chart `optimize` feature flag later to compact every event of this source. Install the destination expander first (see the prerequisite below).
- You will not be using the receiver app at all (this section is receiver-only).

### Repo layout

Mirror this in your GitOps config repo (the engine pulls it on each poll):

```
pipelines/run/receive/compact/compact-cap.csv # the exception list: one row per pattern, keyed by the pattern name (message_pattern, the first column of log10x_top_patterns), boolean true|false value; in-place writes hot-reload (no restart)
pipelines/run/receive/compact/compact-object-cap.js # predicate logic: JS change → pipeline restart (rarely needed; CSV covers most cases)
```

### Pod env vars

Set these on the receiver pod (helm `--set env.<NAME>=<value>` or the chart's env block):

| Env | Required | Default | Note |
|---|---|---|---|
| `GH_FILES_ENABLED` | **yes** | `true` | switch for the GitHub puller of the files `paths` lists (on this engine GH_ENABLED pulls the regulator policy folder `log10x/policy/` instead, which this repo does not carry) |
| `GH_REPO` | **yes** | `your-org/your-config-repo` | owner/name of the GitOps config repo (forked from log-10x/config recommended) |
| `GH_TOKEN` | **yes** | `<github PAT>` | PAT with Contents: Read scope; store as a k8s Secret + reference via valueFrom |
| `GH_BRANCH` | optional | `main` | branch to pull from |
| `GH_SYNC_INTERVAL` | optional | `30s` | engine re-fetches the repo this often |
| `compactReceiverLookupFile` | **yes** | `pipelines/run/receive/compact/compact-cap.csv` | must match the path inside your GitOps repo; one row per pattern, keyed by the pattern name (message_pattern), boolean true\|false value |
| `compactReceiverDefault` | optional | `true` | `true`: a listed pattern with value false keeps its full text, every other pattern compacts (the exception list under the chart `optimize` flag). `false`: only listed patterns with value true compact. |

### Once wired, author entries via the MCP

Run `log10x_configure_engine` to compose the per-pattern compact decisions and emit a literal `gh` PR command. Example:

```
log10x_configure_engine \
  gitops_repo=your-org/your-config-repo \
  service=payment-service \
  target_percent=30 \
  destination=datadog
```

### Caveats
- Compaction is only lossless end to end when the destination can expand the encoded events again at read time, and that expander is a separate install on the destination, not part of this release: the [10x Splunk app](https://doc.log10x.com/apps/receiver/compact/splunk/), or the [l1es plugin](https://doc.log10x.com/apps/receiver/compact/elasticsearch/) for self-managed Elasticsearch 8.17.0 / OpenSearch 2.19.0. Install it before you compact anything the destination is searched on, or those searches return compacted lines. Managed and serverless platforms (Datadog, CloudWatch, Elastic Cloud Serverless) have nowhere to install one. Compaction is not offered on ClickHouse, where it measured about 7% of table bytes and the bill is compute. Use tier_down or offload on all of these instead of compaction.
- The `paths` glob in `pipelines/gitops/config.yaml` is `test/*.csv`, and it is a YAML list, which does not read environment variables, so `GH_PATH` does not change it. Fork the config repo and edit `paths` to cover `pipelines/run/receive/compact/*`.
- Customers running multiple receiver pods all watching the same GitOps repo will see fan-out: a single PR triggers reload on every pod within a poll window. That is the intended behavior: kept here as a heads-up for capacity planning.
- Hot-reload requires in-place writes (the gitops pattern). Do not source the cap-file via a Kubernetes ConfigMap mount: CM swaps the file via a symlink rename, which the engine's stat-based watcher will not see.

## Verify
Each probe below answers one specific question: run them in order. A probe passes when its commands exit 0 and (optionally) match the `expectOutput` regex.

### 1. pods-ready: Are all Fluent Bit pods Ready (with the log10x sidecar)?
_Expect to pass within 300s._

```bash
kubectl -n logging wait --for=condition=Ready pod -l app.kubernetes.io/instance=my-receiver --timeout=5m
```

Expect output matching: `condition met`

### 2. sidecar-alive: Is the log10x sidecar running and processing events?

```bash
kubectl -n logging logs -l app.kubernetes.io/instance=my-receiver -c log10x --tail=400 | grep -E 'tenx|pattern|receiver|template' | head -20
```

### 3. forwarder-handoff: Is Fluent Bit forwarding kube.* events to the sidecar on 127.0.0.1:24224?

```bash
kubectl -n logging logs -l app.kubernetes.io/instance=my-receiver -c fluent-bit --tail=400 | grep -E '\\[OUTPUT\\].*forward|127\\.0\\.0\\.1:24224' | head -10
```

### 4. tenx-mock-events: Are returning tenx.* events reaching the stdout destination?
_Expect to pass within 120s._

```bash
kubectl -n logging logs -l app.kubernetes.io/instance=my-receiver -c fluent-bit --tail=200 | grep -E '"tag":"tenx\\.' | head -5
```

Expect output matching: `tenx.`

## Teardown
### 1. Uninstall the Helm release
_Removes the forwarder DaemonSet/Deployment/StatefulSet, its ServiceAccount, ConfigMaps, and the 10x Reporter sidecar._

```bash
helm -n logging uninstall my-receiver
```

### 2. Clean up derived resources
_Helm does not reap PVCs or Secrets that were created outside of the release. Selector honors the chart family's label convention (k8s-recommended vs legacy Helm)._

```bash
kubectl -n logging delete pvc -l app.kubernetes.io/instance=my-receiver --ignore-not-found
kubectl -n logging delete secret reporter-credentials --ignore-not-found
```

### 3. Verify nothing remains
_Confirm no pods, services, or configmaps are lingering under the release label._

```bash
kubectl -n logging get all,configmap,secret,pvc -l app.kubernetes.io/instance=my-receiver
```

---
_Plan built from snapshot `e100-1792971977960`._

**Next actions** (after running the plan above):
  - Verify the install is healthy: `log10x_doctor`, runs all freshness/auth/config checks across reporter, receiver, retriever.
  - Confirm the config snapshot picked up the change: `log10x_discover_env`, shows what the engine sees as the active config.