// Run log10x-mcp 1.30.49's poc_from_local (file mode) on the quiet capture.
import { executePocFromLocal } from '<log10x-mcp-1.30.49 package>/build/tools/poc-from-local.js';
import { writeFileSync } from 'fs';
const W = process.argv[2];
const env = await executePocFromLocal({ source: 'file', path: `${W}/quiet-raw.jsonl`, siem: 'datadog', forwarder: 'fluent-bit', target_percent_reduction: 70 });
writeFileSync(`${W}/planner-envelope.json`, JSON.stringify(env, null, 1));
const plan = env.plan ?? env.data?.plan ?? env.structuredContent?.plan;
console.log('envelope keys:', Object.keys(env));
console.log('plan found:', !!plan);
