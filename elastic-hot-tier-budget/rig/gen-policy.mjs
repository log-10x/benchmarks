// Writes policy.yaml through log10x-mcp's own emitPolicyYaml (the file log10x_setup_recurring writes
// for a github_actions hot-tier run), with this run's size, node counts (one Receiver serves every
// container) and policy checkout, and the run's test branch in place of the default one.
//   MCP=<pkg> node gen-policy.mjs <out policy.yaml> <hot_tier_gb> <checkout> <branch> <containers,...>
import { writeFileSync } from 'fs';
const MCP = process.env.MCP;
const { emitPolicyYaml } = await import(`${MCP}/build/lib/scheduler-manifest-emitter.js`);
const [out, gb, checkout, branch, containers] = process.argv.slice(2);
let y = emitPolicyYaml({
  target_services: [],
  target_percent: 30,
  scheduler: 'github_actions',
  config_plane: checkout,
  exceptions: [],
  min_delta_pp: 2,
  hot_tier_gb: gb === 'auto' ? 'auto' : Number(gb),
  keep_count: 50,
  nodes_by_container: Object.fromEntries(containers.split(',').filter(Boolean).map((c) => [c, 1])),
});
y = y.replace(/policy_branch: log10x-policy/, `policy_branch: ${branch}`);
writeFileSync(out, y);
console.log(y);
