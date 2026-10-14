// Runs log10x-mcp's poc_from_local in file mode on the quiet capture, with the fleet default.
//   MCP=<built log10x-mcp package or checkout> \
//   LOG10X_TENX_MODE=docker LOG10X_RUNTIME_IMAGE=<engine image> \
//   node run-planner.mjs <capture.jsonl> <out dir>
// Writes poc-args.json and poc-envelope.json to <out dir>; the POC writes its report and
// its caps.csv and actions.csv into the working directory, which is <out dir>.
import { writeFileSync, mkdirSync, readFileSync } from 'fs';
import { resolve } from 'path';

const MCP = process.env.MCP;
if (!MCP) throw new Error('set MCP to a built log10x-mcp package or checkout');
const [captureArg, outArg] = process.argv.slice(2);
const capture = resolve(captureArg);
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
process.chdir(out);

const { executePocFromLocal } = await import(`${MCP}/build/tools/poc-from-local.js`);
const version = JSON.parse(readFileSync(`${MCP}/package.json`, 'utf8')).version;
const args = {
  source: 'file',
  path: capture,
  siem: 'datadog',
  forwarder: 'fluent-bit',
  target_percent_reduction: 70,
  fleet_default: { headroom: 2, action: 'offload', error_floor: 0.5 },
};
writeFileSync('poc-args.json', JSON.stringify({ mcp_version: version, engine_image: process.env.LOG10X_RUNTIME_IMAGE, args }, null, 1) + '\n');
const env = await executePocFromLocal(args);
writeFileSync('poc-envelope.json', JSON.stringify(env, null, 1) + '\n');
const sc = env.structuredContent ?? env;
const fd = sc.fleet_default ?? sc.data?.fleet_default;
console.log('mcp', version, 'envelope keys', Object.keys(sc));
console.log('fleet_default', JSON.stringify(fd, null, 1));
