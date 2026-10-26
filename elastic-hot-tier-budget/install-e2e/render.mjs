// Renders what the E100/E101 install proof applies, from a log10x-mcp build, through the three
// tools' own handlers, and adds nothing to what they return:
//   MCP=<log10x-mcp package> node render.mjs <out dir> <hot_tier_gb> <policy checkout> <containers,...>
// 1. log10x_advise_retriever (destination elasticsearch): the plan's Elasticsearch frozen-tier
//    block, verbatim to recipe.txt; its requests with the comment lines dropped to recipe-requests.json.
// 2. log10x_advise_install (app receiver, forwarder fluentbit, log_destination elasticsearch,
//    builtin licence, airgapped, metrics backend elastic): the plan to install-plan.md; from its values file the sidecar's
//    image, args, env and limits, and from its seed step the policy ConfigMap's data, to receiver.json.
// 3. log10x_setup_recurring (hot_tier_gb on github_actions, the checkout as the config plane):
//    policy.yaml and apply-instructions.md.
import { writeFileSync, mkdirSync, readFileSync } from 'fs';
import { join, resolve } from 'path';
import { createRequire } from 'module';

const MCP = process.env.MCP;
if (!MCP) throw new Error('set MCP to a log10x-mcp package');
const [outArg, gbArg, checkout, containersArg] = process.argv.slice(2);
if (!outArg || !gbArg || !checkout || !containersArg) throw new Error('usage: render.mjs <out dir> <hot_tier_gb> <policy checkout> <containers,...>');
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
const YAML = createRequire(`${MCP}/package.json`)('yaml');
const mcpVersion = JSON.parse(readFileSync(`${MCP}/package.json`, 'utf8')).version;

const { putSnapshot } = await import(`${MCP}/build/lib/discovery/snapshot-store.js`);
const { SNAPSHOT_SCHEMA_VERSION } = await import(`${MCP}/build/lib/discovery/types.js`);
const { executeAdviseRetriever } = await import(`${MCP}/build/tools/advise-retriever.js`);
const { executeAdviseInstall } = await import(`${MCP}/build/tools/advise-install.js`);
const { executeSetupRecurring } = await import(`${MCP}/build/tools/setup-recurring.js`);

// A discovery snapshot of a cluster with Fluent Bit in `logging`; the AWS fields give the
// Retriever plan a bucket and region so it renders its offload section.
const snapshotId = `e100-${Date.now()}`;
putSnapshot({
  schemaVersion: SNAPSHOT_SCHEMA_VERSION,
  snapshotId,
  startedAt: new Date().toISOString(),
  finishedAt: new Date().toISOString(),
  kubectl: {
    available: true,
    namespaces: ['logging'],
    probedNamespaces: ['logging'],
    forwarders: [{ kind: 'fluentbit', namespace: 'logging', workloadKind: 'DaemonSet', workloadName: 'fluent-bit', image: 'cr.fluentbit.io/fluent/fluent-bit:4.2', containerName: 'fluent-bit', labels: {}, readyReplicas: 1 }],
    helmReleases: [],
    log10xApps: [],
    storageClasses: [],
    ingressClasses: [],
    serviceAccountIrsa: [],
    backendAgents: [],
  },
  aws: { available: true, region: 'us-east-1', s3Buckets: [], sqsQueues: [], cwLogGroups: [] },
  recommendations: { suggestedNamespace: 'logging', alreadyInstalled: {} },
  probeLog: [],
});

// 1. advise_retriever
const q = (n) => `https://sqs.us-east-1.amazonaws.com/000000000000/e100-${n}`;
const ret = await executeAdviseRetriever({
  snapshot_id: snapshotId,
  infra_mode: 'existing',
  index_source_bucket: 'e100-retriever-input',
  iam_role_arn: 'arn:aws:iam::000000000000:role/e100-retriever',
  index_queue_url: q('index'),
  query_queue_url: q('query'),
  subquery_queue_url: q('subquery'),
  stream_queue_url: q('stream'),
  license_source: 'builtin',
  destination: 'elasticsearch',
});
const retMd = String(ret.data?.markdown ?? JSON.stringify(ret.data));
writeFileSync(join(out, 'retriever-plan.md'), retMd);
const at = retMd.indexOf('_Elasticsearch frozen tier_');
if (at < 0) throw new Error('advise_retriever rendered no Elasticsearch frozen-tier block; see retriever-plan.md');
const fence = retMd.indexOf('```text\n', at);
const recipe = retMd.slice(fence + '```text\n'.length, retMd.indexOf('\n```', fence + 8));
writeFileSync(join(out, 'recipe.txt'), recipe + '\n');
const requests = [];
const lines = recipe.split('\n').filter((l) => !l.startsWith('#'));
for (let i = 0; i < lines.length; i++) {
  const m = /^(PUT|POST) (\S+)\s*$/.exec(lines[i]);
  if (!m) continue;
  const buf = [];
  let depth = 0;
  for (let j = i + 1; j < lines.length; j++) {
    buf.push(lines[j]);
    for (const ch of lines[j]) depth += ch === '{' ? 1 : ch === '}' ? -1 : 0;
    if (depth === 0) { i = j; break; }
  }
  requests.push({ method: m[1], path: '/' + m[2], body: JSON.parse(buf.join('\n')) });
}
writeFileSync(join(out, 'recipe-requests.json'), JSON.stringify(requests, null, 1) + '\n');

// 2. advise_install
const inst = await executeAdviseInstall({
  snapshot_id: snapshotId,
  app: 'receiver',
  forwarder: 'fluentbit',
  backends: ['elastic'],
  backend_credentials: { elastic: { secretName: 'elastic-credentials', plainValues: { ELASTICSEARCH_HOST: 'http://es-hot:9200' } } },
  airgapped: true,
  license_source: 'builtin',
  log_destination: 'elasticsearch',
}, {});
const md = String(inst.data?.markdown ?? '');
writeFileSync(join(out, 'install-plan.md'), md);
const vAt = md.indexOf('Write `my-receiver-values.yaml`');
if (vAt < 0) throw new Error(`advise_install rendered no values file (mode ${inst.data?.mode}); see install-plan.md`);
const vStart = md.indexOf('```yaml\n', vAt) + '```yaml\n'.length;
const values = YAML.parse(md.slice(vStart, md.indexOf('\n```', vStart)));
const sidecar = values.extraContainers.find((c) => c.name === 'log10x');
const seedAt = md.indexOf("cat <<'POLICY_EOF' | kubectl apply -f -\n");
const seedText = md.slice(seedAt).split('\n').slice(1).join('\n').split('\nPOLICY_EOF')[0];
const cm = YAML.parseAllDocuments(seedText).map((d) => d.toJS()).find((d) => d?.kind === 'ConfigMap');
writeFileSync(join(out, 'receiver.json'), JSON.stringify({ mcp_version: mcpVersion, image: sidecar.image, args: sidecar.args, env: sidecar.env, resources: sidecar.resources, policy_configmap: { name: cm.metadata.name, data: cm.data } }, null, 1) + '\n');

// 3. setup_recurring
const rec = await executeSetupRecurring({
  target_services: [],
  hot_tier_gb: gbArg === 'auto' ? 'auto' : Number(gbArg),
  scheduler: 'github_actions',
  config_plane: checkout,
  nodes_by_container: Object.fromEntries(containersArg.split(',').filter(Boolean).map((c) => [c, 1])),
  confirm: true,
});
if (rec.data?.mode !== 'emit') throw new Error(`setup_recurring did not emit: ${rec.data?.markdown}`);
writeFileSync(join(out, 'policy.yaml'), String(rec.data.policy_yaml));
writeFileSync(join(out, 'apply-instructions.md'), String(rec.data.apply_instructions) + '\n');

// The Receiver as a compose service: the image (ENGINE_IMAGE replaces the rendered one, both
// recorded), every arg in order, every env var with a plain value, the limits. Substituted,
// because there is no cluster: the values read the policy files through the Kubernetes pull
// lane (K8S_ENABLED, K8S_CONFIGMAP, K8S_NAMESPACE); here the seed files are mounted at /policy.
// CONFIG_GENERATION_FILE is left out: the seed carries no config-generation.csv.
// Rig plumbing: TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit (Fluent Bit is a separate container).
const SUBSTITUTE = { K8S_ENABLED: 'false', CAP_LOOKUP_FILE: '/policy/caps.csv', ACTION_LOOKUP_FILE: '/policy/actions.csv', TOTAL_LOOKUP_FILE: '/policy/totals.csv' };
const LEAVE_OUT = new Set(['K8S_NAMESPACE', 'K8S_CONFIGMAP', 'CONFIG_GENERATION_FILE']);
const applied = [];
const substituted = [];
const left = [];
for (const e of sidecar.env) {
  if (LEAVE_OUT.has(e.name)) left.push(e.name);
  else if (e.name in SUBSTITUTE) { substituted.push({ name: e.name, rendered: e.value, rig: SUBSTITUTE[e.name] }); applied.push([e.name, SUBSTITUTE[e.name]]); }
  else if (e.value !== undefined) applied.push([e.name, String(e.value)]);
  else left.push(e.name);
}
const image = process.env.ENGINE_IMAGE || sidecar.image;
const lim = sidecar.resources?.limits ?? {};
const cpus = lim.cpu ? (String(lim.cpu).endsWith('m') ? String(Number(String(lim.cpu).slice(0, -1)) / 1000) : String(lim.cpu)) : undefined;
const mem = lim.memory ? String(lim.memory).replace(/Mi$/, 'M').replace(/Gi$/, 'G') : undefined;
const jq = (v) => JSON.stringify(String(v)).replace(/\$/g, '$$$$');
writeFileSync(join(out, 'compose.receiver.yaml'), [
  '# Generated by install-e2e/render.mjs from log10x_advise_install\'s values (receiver.json). Do not edit.',
  'services:',
  '  tenx:',
  `    image: ${jq(image)}`,
  '    container_name: e100-tenx',
  '    environment:',
  ...applied.map(([k, v]) => `      - ${jq(`${k}=${v}`)}`),
  `      - ${jq('TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit')}`,
  '    tmpfs:',
  '      - /tmp',
  '    volumes:',
  '      - ${RESULTS}/policy:/policy:ro',
  '    command:',
  ...sidecar.args.map((a) => `      - ${jq(a)}`),
  ...(cpus || mem ? ['    deploy:', '      resources:', '        limits:', ...(cpus ? [`          cpus: ${jq(cpus)}`] : []), ...(mem ? [`          memory: ${jq(mem)}`] : [])] : []),
  '',
].join('\n'));
mkdirSync(join(out, 'policy'), { recursive: true });
for (const f of ['caps.csv', 'actions.csv', 'totals.csv']) writeFileSync(join(out, 'policy', f), cm.data[f]);
writeFileSync(join(out, 'launch.json'), JSON.stringify({ mcp_version: mcpVersion, image, image_rendered: sidecar.image, args_from_values: sidecar.args, env_applied: applied.map(([k]) => k), env_substituted: substituted, env_left_out: left, rig_env: ['TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit'], resources_limits: { cpus, memory: mem }, policy_seed_from_configmap: Object.keys(cm.data) }, null, 1) + '\n');

console.log(JSON.stringify({ mcp_version: mcpVersion, recipe_requests: requests.map((r) => `${r.method} ${r.path}`), image: sidecar.image, args: sidecar.args, env: sidecar.env.map((e) => e.name), seed_keys: Object.keys(cm.data) }, null, 1));
