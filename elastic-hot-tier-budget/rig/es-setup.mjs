// Prepares the rig cluster and applies log10x-mcp's Elasticsearch frozen-tier recipe verbatim.
//   MCP=<log10x-mcp package> node es-setup.mjs <out dir>
// 1. Starts the self-managed trial licence (searchable snapshots need Enterprise features).
// 2. Registers the filesystem snapshot repository `rig-snapshots` at /snapshots (Elastic
//    Cloud provides `found-snapshots`; a self-managed cluster registers its own).
// 3. Sends every request in elasticFrozenTierRecipe({ repository: 'rig-snapshots' }).body,
//    in order, and writes the recipe and each response to <out dir>.
import { writeFileSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';

const MCP = process.env.MCP;
const ES = process.env.ES_URL ?? 'http://127.0.0.1:9200';
if (!MCP) throw new Error('set MCP to a log10x-mcp package');
const out = resolve(process.argv[2] ?? '.');
mkdirSync(out, { recursive: true });
const { elasticFrozenTierRecipe } = await import(`${MCP}/build/lib/offload-recipes.js`);

async function call(method, path, body) {
  const r = await fetch(ES + (path.startsWith('/') ? path : '/' + path), {
    method,
    headers: { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await r.text();
  return { method, path, status: r.status, body: text.length > 2000 ? text.slice(0, 2000) : text };
}

const log = [];
log.push(await call('POST', '/_license/start_trial?acknowledge=true'));
log.push(await call('GET', '/_license'));
log.push(await call('PUT', '/_snapshot/rig-snapshots', { type: 'fs', settings: { location: '/snapshots' } }));

const recipe = elasticFrozenTierRecipe({ repository: 'rig-snapshots' });
writeFileSync(join(out, 'recipe.txt'), recipe.body + '\n\nNOTE: ' + recipe.note + '\n');

// The body is comment lines, then "PUT <path>" and an optional JSON object, per request.
const lines = recipe.body.split('\n');
const requests = [];
for (let i = 0; i < lines.length; i++) {
  const m = /^(PUT|POST|GET|DELETE) (\S+)\s*(\{.*\})?\s*$/.exec(lines[i]);
  if (!m) continue;
  let json = m[3];
  if (!json && lines[i + 1]?.startsWith('{')) {
    let depth = 0;
    const buf = [];
    for (let j = i + 1; j < lines.length; j++) {
      buf.push(lines[j]);
      for (const ch of lines[j]) depth += ch === '{' ? 1 : ch === '}' ? -1 : 0;
      if (depth === 0) { i = j; break; }
    }
    json = buf.join('\n');
  }
  requests.push({ method: m[1], path: m[2], body: json ? JSON.parse(json) : undefined });
}
for (const q of requests) log.push(await call(q.method, q.path, q.body));
// The recipe's tenx-keep never leaves hot (its control). A customer's kept stream has its own policy;
// this run's is time-scaled: KEEP_ROLLOVER then frozen KEEP_FROZEN_AFTER after rollover. The tier_down
// index rolls TD_ROLLOVER instead of the recipe's 1h. ILM_POLL, when set, scales ILM's poll with them.
const keepRollover = process.env.KEEP_ROLLOVER ?? '1h';
const keepFrozenAfter = process.env.KEEP_FROZEN_AFTER ?? `${Number(process.env.KEEP_HOT_HOURS ?? 6) - 1}h`;
const tdRollover = process.env.TD_ROLLOVER ?? '15m';
log.push(await call('PUT', '/_ilm/policy/tenx-keep', { policy: { phases: {
  hot: { min_age: '0ms', actions: { rollover: { max_age: keepRollover, max_primary_shard_size: '50gb' } } },
  frozen: { min_age: keepFrozenAfter, actions: { searchable_snapshot: { snapshot_repository: 'rig-snapshots' } } },
} } }));
log.push(await call('PUT', '/_ilm/policy/tenx-tier-down', { policy: { phases: {
  hot: { min_age: '0ms', actions: { rollover: { max_age: tdRollover, max_primary_shard_size: '50gb' } } },
  frozen: { min_age: '1m', actions: { searchable_snapshot: { snapshot_repository: 'rig-snapshots' } } },
} } }));
if (process.env.ILM_POLL) log.push(await call('PUT', '/_cluster/settings', { persistent: { 'indices.lifecycle.poll_interval': process.env.ILM_POLL } }));
writeFileSync(join(out, 'es-setup.json'), JSON.stringify({ es: ES, requests: requests.length, log }, null, 1) + '\n');
const bad = log.filter((x) => x.status >= 300 && !(x.path.includes('start_trial') && x.status === 403));
for (const x of log) console.log(x.status, x.method, x.path);
if (bad.length) { console.error('FAILED:', bad.map((x) => `${x.status} ${x.method} ${x.path} ${x.body.slice(0, 300)}`).join('\n')); process.exit(1); }
