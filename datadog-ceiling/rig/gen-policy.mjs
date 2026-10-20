// Writes policy.yaml through log10x-mcp's own emitPolicyYaml (the file log10x_setup_recurring
// writes for a github_actions budget run), with this run's X, service budget, indexes, node
// counts (one Receiver serves every container) and policy repo checkout.
//   MCP=<pkg> node gen-policy.mjs <out policy.yaml> <usd_monthly> <service> <service_usd> <checkout> <branch> <containers,...>
import { writeFileSync } from 'fs';
const MCP = process.env.MCP;
const { emitPolicyYaml } = await import(`${MCP}/build/lib/scheduler-manifest-emitter.js`);
const [out, usd, svc, svcUsd, checkout, branch, containers] = process.argv.slice(2);
let y = emitPolicyYaml({
  target_services: [],
  target_percent: 30,
  scheduler: 'github_actions',
  config_plane: checkout,
  exceptions: [],
  min_delta_pp: 2,
  budget_usd_monthly: Number(usd),
  standard_indexes: ['main'],
  keep_count: 50,
  ...(svc && svc !== '-' ? { service_budgets: { [svc]: Number(svcUsd) } } : {}),
  nodes_by_container: Object.fromEntries(containers.split(',').map((c) => [c, 1])),
});
// The emitter names the default branch; this run's branch is a throwaway test branch.
y = y.replace(/policy_branch: log10x-policy/, `policy_branch: ${branch}`);
writeFileSync(out, y);
console.log(y);
