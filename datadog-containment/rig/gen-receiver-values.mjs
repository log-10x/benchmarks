// Writes the Receiver values log10x-mcp renders for a Datadog Fluent Bit Receiver, through the
// same two functions log10x_advise_install calls (receiverFleetValues, then the Fluent Bit
// overlay's renderValues), and a compose overlay that launches rig-tenx with them.
//   MCP=<built log10x-mcp> node gen-receiver-values.mjs <out dir> [<poc-envelope.json>]
// Without an envelope: the values before a fleet default (quiet run). With one: the
// envelope's fleet_default goes in as advise_install's fleet_default argument.
//
// Outputs in <out dir>:
//   values.yaml                  the rendered Fluent Bit chart overlay, verbatim
//   receiver-values.json         receiverFleetValues' result, verbatim
//   policy-configmap.yaml        the policy ConfigMap seed every Receiver install applies
//   caps.csv, actions.csv        the policy files the Receiver reads (see below)
//   compose.receiver.yaml        the rig-tenx service: the values' image, args and env
//   launch.json                  what was applied, what was substituted, and why
//
// Policy files: the POC's own log10x-caps.csv and log10x-actions.csv when it wrote rows (in a
// cluster log10x_configure_engine puts them in the policy ConfigMap in place of the seed);
// otherwise the seed's caps.csv and actions.csv.
//
// Applied as written: the image, every arg in order, every env var with a plain value.
// Substituted, because there is no cluster here (the same substitution as the MCP's own
// scripts/check-fleet-default-floors): the policy pull (K8S_NAMESPACE, K8S_ENABLED,
// K8S_CONFIGMAP, CONFIG_GENERATION_FILE) is left out, and CAP_LOOKUP_FILE and
// ACTION_LOOKUP_FILE point at the mounted policy files instead of the pulled ConfigMap.
// Rig plumbing: TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit (Fluent Bit is a separate container,
// not the same pod). Measurement only, after every MCP arg: outputEncodeField adds
// message_pattern and severity_level to the returned record; the shipped config computes
// fullText("tenx_hash","routeState") from the values, and the rig's list keeps both.
import { readFileSync, writeFileSync, mkdirSync, existsSync, copyFileSync } from 'fs';
import { resolve, dirname, join } from 'path';

const MCP = process.env.MCP;
if (!MCP) throw new Error('set MCP to a built log10x-mcp package or checkout');
const [outArg, envelopeArg] = process.argv.slice(2);
const out = resolve(outArg);
mkdirSync(out, { recursive: true });

const { receiverFleetValues } = await import(`${MCP}/build/lib/fleet-default-install.js`);
const { RECEIVER_FORWARDER_SPECS, renderPolicyConfigMapManifest } = await import(`${MCP}/build/lib/advisor/reporter-forwarders.js`);
const mcpVersion = JSON.parse(readFileSync(`${MCP}/package.json`, 'utf8')).version;

let fleetDefault;
let pocDir;
if (envelopeArg) {
  const env = JSON.parse(readFileSync(envelopeArg, 'utf8'));
  const fd = (env.data ?? env.structuredContent ?? env).fleet_default;
  if (!fd || !fd.computed) throw new Error(`the POC computed no fleet default: ${fd ? fd.reason : 'no fleet_default in the envelope'}`);
  fleetDefault = { capBytesPerWindowPerNode: fd.cap_bytes_per_window_per_node, action: fd.action, errorFloor: fd.error_floor };
  pocDir = dirname(resolve(envelopeArg));
}

const values = receiverFleetValues({ datadog: true, ...(fleetDefault ? { fleetDefault } : {}) });
if (fleetDefault && !values.fleetDefaultWritten) throw new Error(`fleet default not written: ${values.notes.join(' ')}`);
writeFileSync(join(out, 'receiver-values.json'), JSON.stringify(values, null, 1) + '\n');

const yaml = RECEIVER_FORWARDER_SPECS.fluentbit.renderValues({
  releaseName: 'rig',
  destination: 'datadog',
  builtinLicense: true,
  airgapped: true,
  licenseSecretName: 'log10x-license',
  licenseSecretKey: 'license.jwt',
  engineOptions: values.options,
  engineEnv: values.env,
});
writeFileSync(join(out, 'values.yaml'), yaml);
const seed = renderPolicyConfigMapManifest('rig');
writeFileSync(join(out, 'policy-configmap.yaml'), seed);

// The log10x container block of the overlay.
const block = yaml.slice(yaml.indexOf('  - name: log10x'));
const image = /\n\s+image: (\S+)/.exec(block)[1];
const argsText = block.split('\n    args:\n')[1].split('\n    env:\n')[0];
const args = argsText.split('\n').map((l) => /^\s+- "(.*)"$/.exec(l)).filter(Boolean).map((m) => m[1]);
const envText = block.split('\n    env:\n')[1].split(/\n    [a-zA-Z]/)[0];
const env = [];
for (const m of envText.matchAll(/- name: (\S+)\n((?:\s{8,}.*\n?)+)/g)) {
  const body = m[2];
  const v = /^\s+value: (.*)$/m.exec(body);
  env.push({ name: m[1], value: v ? v[1].replace(/^"(.*)"$/, '$1') : undefined, valueFrom: v ? undefined : body.trim() });
}

const CLUSTER_ONLY = new Set(['K8S_NAMESPACE', 'K8S_ENABLED', 'K8S_CONFIGMAP', 'CONFIG_GENERATION_FILE']);
const SUBSTITUTED = { CAP_LOOKUP_FILE: '/etc/tenx/lookups/caps.csv', ACTION_LOOKUP_FILE: '/etc/tenx/lookups/actions.csv' };
const applied = [];
const left = [];
const substituted = [];
for (const e of env) {
  if (CLUSTER_ONLY.has(e.name)) left.push(e);
  else if (e.name in SUBSTITUTED) substituted.push({ ...e, rig_value: SUBSTITUTED[e.name] });
  else if (e.value !== undefined) applied.push(e);
  else left.push(e);
}
const rigEnv = [['TENX_FLUENTBIT_OUTPUT_HOST', 'fluent-bit']];
const measure = ['outputEncodeField', 'fullText("tenx_hash","routeState","message_pattern","severity_level")'];

// Policy files.
let policySource = 'install seed (policy-configmap.yaml)';
const seedFile = (key) => {
  const m = new RegExp(`  ${key}: \\|\\n((?:    .*\\n)+)`).exec(seed);
  return m[1].split('\n').map((l) => l.replace(/^    /, '')).join('\n');
};
let caps = seedFile('caps.csv');
let actions = seedFile('actions.csv');
if (pocDir && existsSync(join(pocDir, 'log10x-caps.csv'))) {
  const pc = readFileSync(join(pocDir, 'log10x-caps.csv'), 'utf8');
  const pa = existsSync(join(pocDir, 'log10x-actions.csv')) ? readFileSync(join(pocDir, 'log10x-actions.csv'), 'utf8') : '';
  if (pc.trim().split('\n').length > 1) {
    caps = pc;
    actions = pa.trim().split('\n').length > 1 ? pa : actions;
    policySource = "the POC's log10x-caps.csv and log10x-actions.csv";
  }
}
writeFileSync(join(out, 'caps.csv'), caps);
writeFileSync(join(out, 'actions.csv'), actions);

// Compose overlay. `$` is doubled so compose does not interpolate a value.
const q = (s) => JSON.stringify(String(s)).replace(/\$/g, '$$$$');
const res = /limits:\s*\{\s*cpu:\s*(\S+),\s*memory:\s*(\S+)\s*\}/.exec(block);
const cpu = res ? (res[1].endsWith('m') ? String(Number(res[1].slice(0, -1)) / 1000) : res[1]) : undefined;
const mem = res ? res[2].replace(/Mi$/, 'M').replace(/Gi$/, 'G') : undefined;
const lines = [
  '# Generated by rig/gen-receiver-values.mjs from values.yaml in this directory. Do not edit.',
  'services:',
  '  tenx:',
  `    image: ${q(image)}`,
  '    container_name: rig-tenx',
  '    environment:',
  ...applied.map((e) => `      - ${q(`${e.name}=${e.value}`)}`),
  ...substituted.map((e) => `      - ${q(`${e.name}=${e.rig_value}`)}`),
  ...rigEnv.map(([k, v]) => `      - ${q(`${k}=${v}`)}`),
  '    volumes:',
  `      - ${q(`${out}/caps.csv:/etc/tenx/lookups/caps.csv:ro`)}`,
  `      - ${q(`${out}/actions.csv:/etc/tenx/lookups/actions.csv:ro`)}`,
  '    command:',
  ...args.map((a) => `      - ${q(a)}`),
  ...measure.map((a) => `      - ${q(a)}`),
  ...(cpu || mem
    ? ['    deploy:', '      resources:', '        limits:', ...(cpu ? [`          cpus: ${q(cpu)}`] : []), ...(mem ? [`          memory: ${q(mem)}`] : [])]
    : []),
  '    restart: unless-stopped',
  '',
];
writeFileSync(join(out, 'compose.receiver.yaml'), lines.join('\n'));
const launch = {
  mcp_version: mcpVersion,
  fleet_default_input: fleetDefault ?? null,
  image,
  args_from_values: args,
  env_from_values: env,
  env_applied: applied,
  env_substituted: substituted,
  env_left_out_cluster_only: left,
  rig_env: rigEnv,
  measurement_args: measure,
  resources_limits: { cpus: cpu, memory: mem },
  policy_files: policySource,
  notes: values.notes,
};
writeFileSync(join(out, 'launch.json'), JSON.stringify(launch, null, 1) + '\n');
console.log(JSON.stringify({ mcpVersion, image, args, applied, substituted, left: left.map((e) => e.name), policySource, cpu, mem }, null, 1));
