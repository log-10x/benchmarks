// Writes the Receiver values log10x-mcp renders for an Elasticsearch Fluent Bit Receiver,
// through the functions log10x_advise_install calls (receiverFleetValues, then the Fluent
// Bit overlay's renderValues with destination elasticsearch), and a compose overlay that
// launches rig-tenx with them.
//   MCP=<log10x-mcp package> [BACKENDS=elastic] node gen-receiver-values.mjs <out dir> [cap bytes per window per node]
// Without a cap: the install as it ships, nothing held (baseline).
// With a cap: the fleet default, that cap in bytes for every container and tier_down as the
// action for every held line (rateReceiverAbsoluteCap, rateReceiverDefaultAction, outputOffload).
//
// Applied as written: the image, every arg in order, every env var with a plain value.
// Rig plumbing: TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit (Fluent Bit is a separate container).
// Measurement only, after every MCP arg: symbolMessageHashField tenx_hash (the MCP writes it for
// Datadog only, while its Elastic recipe maps tenx_hash and the frozen-tier proof searched it),
// and outputEncodeField so the returned record carries tenx_hash, routeState, message_pattern
// and severity_level.
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, join } from 'path';

const MCP = process.env.MCP;
if (!MCP) throw new Error('set MCP to a log10x-mcp package');
const [outArg, capArg] = process.argv.slice(2);
if (!outArg) throw new Error('usage: gen-receiver-values.mjs <out dir> [cap bytes]');
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
const cap = capArg ? Number(capArg) : undefined;

const { receiverFleetValues } = await import(`${MCP}/build/lib/fleet-default-install.js`);
const { RECEIVER_FORWARDER_SPECS, renderPolicyGitSeedCommands } = await import(`${MCP}/build/lib/advisor/reporter-forwarders.js`);
const mcpVersion = JSON.parse(readFileSync(`${MCP}/package.json`, 'utf8')).version;

const values = receiverFleetValues({
  datadog: false,
  unit: 'bytes',
  elasticHotTier: true,
  ...(cap ? { fleetDefault: { capBytesPerWindowPerNode: cap, action: 'tier_down' } } : {}),
});
const policyGit = process.env.POLICY_BRANCH ? { repo: process.env.POLICY_REPO ?? 'log-10x/config', branch: process.env.POLICY_BRANCH, tokenSecretName: 'log10x-policy-git' } : undefined;
if (cap && !values.fleetDefaultWritten) throw new Error(`fleet default not written: ${values.notes.join(' ')}`);
writeFileSync(join(out, 'receiver-values.json'), JSON.stringify(values, null, 1) + '\n');

const yaml = RECEIVER_FORWARDER_SPECS.fluentbit.renderValues({
  releaseName: 'rig',
  destination: 'elasticsearch',
  builtinLicense: true,
  airgapped: true,
  licenseSecretName: 'log10x-license',
  licenseSecretKey: 'license.jwt',
  backends: (process.env.BACKENDS ?? '').split(',').filter(Boolean),
  engineOptions: values.options,
  engineEnv: values.env,
  ...(policyGit ? { policyGit } : {}),
});
writeFileSync(join(out, 'values.yaml'), yaml);
if (policyGit) writeFileSync(join(out, 'seed.sh'), renderPolicyGitSeedCommands(policyGit, 'bytes') + '\n');

const block = yaml.slice(yaml.indexOf('  - name: log10x'));
const image = /\n\s+image: (\S+)/.exec(block)[1];
const argsText = block.split('\n    args:\n')[1].split('\n    env:\n')[0];
const args = argsText.split('\n').map((l) => /^\s+- "(.*)"$/.exec(l)).filter(Boolean).map((m) => m[1]);
const envText = (block.split('\n    env:\n')[1] ?? '').split(/\n    [a-zA-Z]/)[0];
const env = [];
for (const m of envText.matchAll(/- name: (\S+)\n((?:\s{8,}.*\n?)+)/g)) {
  const body = m[2];
  const v = /^\s+value: (.*)$/m.exec(body);
  env.push({ name: m[1], value: v ? v[1].replace(/^"(.*)"$/, '$1') : undefined, valueFrom: v ? undefined : body.trim() });
}
// Substituted, because there is no cluster: the values read the policy files from a
// Kubernetes ConfigMap (K8S_ENABLED, K8S_CONFIGMAP, K8S_NAMESPACE). The rig mounts policy/ with
// header-only files at /policy instead, so no row exists and the fleet cap and default action
// decide every line, which is what the fleet default installs.
const SUBSTITUTE = {
  K8S_ENABLED: 'false',
  CAP_LOOKUP_FILE: '/policy/caps.csv',
  ACTION_LOOKUP_FILE: '/policy/actions.csv',
  TOTAL_LOOKUP_FILE: '/policy/totals.csv',
};
// CONFIG_GENERATION_FILE is left out: the generation stamp is opt-in and unset by default
// (regulator page), and a header-only file stops the launch.
const LEAVE_OUT = new Set(['K8S_CONFIGMAP', 'K8S_NAMESPACE', 'CONFIG_GENERATION_FILE']);
const FROM_SHELL = new Set(['GH_TOKEN']);
const substituted = [];
const fromShell = [];
const applied = [];
const left = [];
for (const e of env) {
  if (FROM_SHELL.has(e.name)) fromShell.push(e);
  else if (LEAVE_OUT.has(e.name)) left.push(e);
  else if (e.name in SUBSTITUTE) { substituted.push({ name: e.name, rendered: e.value ?? e.valueFrom, rig: SUBSTITUTE[e.name] }); applied.push({ name: e.name, value: SUBSTITUTE[e.name] }); }
  else if (e.value !== undefined) applied.push(e);
  else left.push(e);
}
const rigEnv = [['TENX_FLUENTBIT_OUTPUT_HOST', 'fluent-bit']];
// The MCP renders symbolMessageHashField and the utf8Size field list itself (elasticHotTier), so nothing is added.
const measure = [];

const q = (s) => JSON.stringify(String(s)).replace(/\$/g, '$$$$');
const res = /limits:\s*\{\s*cpu:\s*(\S+),\s*memory:\s*(\S+)\s*\}/.exec(block);
const cpu = res ? (res[1].endsWith('m') ? String(Number(res[1].slice(0, -1)) / 1000) : res[1]) : undefined;
const mem = res ? res[2].replace(/Mi$/, 'M').replace(/Gi$/, 'G') : undefined;
const lines = [
  '# Generated by rig/gen-receiver-values.mjs from values.yaml in this directory. Do not edit.',
  'services:',
  '  tenx:',
  `    image: ${q(image)}`,
  '    container_name: hb-tenx',
  '    environment:',
  ...applied.map((e) => `      - ${q(`${e.name}=${e.value}`)}`),
  ...fromShell.map((e) => `      - ${q(e.name)}`),
  ...rigEnv.map(([k, v]) => `      - ${q(`${k}=${v}`)}`),
  '    tmpfs:',
  '      - /tmp',
  ...(substituted.length ? ['    volumes:', '      - ${RIG_DIR}/policy:/policy:ro'] : []),
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
writeFileSync(
  join(out, 'launch.json'),
  JSON.stringify(
    { mcp_version: mcpVersion, cap_bytes_per_window_per_node: cap ?? null, image, args_from_values: args, env_applied: applied, env_substituted: substituted, env_left_out: left.map((e) => e.name), env_from_shell_by_name: fromShell.map((e) => e.name), policy_git: policyGit ?? null, rig_env: rigEnv, measurement_args: measure, resources_limits: { cpus: cpu, memory: mem }, notes: values.notes },
    null,
    1,
  ) + '\n',
);
console.log(JSON.stringify({ image, args, env_applied: applied.map((e) => e.name), env_left_out: left.map((e) => e.name), env_from_shell_by_name: fromShell.map((e) => e.name), policy_git: policyGit ?? null, notes: values.notes }, null, 1));
