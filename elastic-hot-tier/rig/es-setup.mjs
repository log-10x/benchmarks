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
writeFileSync(join(out, 'es-setup.json'), JSON.stringify({ es: ES, requests: requests.length, log }, null, 1) + '\n');
const bad = log.filter((x) => x.status >= 300 && !(x.path.includes('start_trial') && x.status === 403));
for (const x of log) console.log(x.status, x.method, x.path);
if (bad.length) { console.error('FAILED:', bad.map((x) => `${x.status} ${x.method} ${x.path} ${x.body.slice(0, 300)}`).join('\n')); process.exit(1); }
