// The rig's policy.yaml, from the MCP's own emitter (the file log10x_setup_recurring
// writes), with the rig's policy branch and the time-scaled meter window added.
//   node gen-policy.mjs <out> <rows_per_hour|auto> <checkout> <branch> <containers,comma> [meter_minutes]
import { writeFileSync } from 'fs';
const MCP = process.env.MCP;
const { emitPolicyYaml } = await import(`${MCP}/build/lib/scheduler-manifest-emitter.js`);
const [out, rate, checkout, branch, containers, meterMinutes] = process.argv.slice(2);
let y = emitPolicyYaml({
  target_services: [],
  target_percent: 30,
  scheduler: 'github_actions',
  config_plane: checkout,
  exceptions: [],
  min_delta_pp: 2,
  rows_per_hour: rate === 'auto' ? 'auto' : Number(rate),
  clickhouse_table: 'default.otel_logs',
  keep_count: 50,
  nodes_by_container: Object.fromEntries(containers.split(',').filter(Boolean).map((c) => [c, 1])),
  env_id: 'edge',
});
y = y.replace(/policy_branch: log10x-policy/, `policy_branch: ${branch}`);
if (meterMinutes && Number(meterMinutes) !== 60) {
  y = y.replace(/(\n  rows_per_hour: [^\n]+\n)/, `$1  # time-scaled rig: the meter's window, read as a rate an hour (60 in production)\n  meter_minutes: ${Number(meterMinutes)}\n`);
}
writeFileSync(out, y);
console.log(y);
