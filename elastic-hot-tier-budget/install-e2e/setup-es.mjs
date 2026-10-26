// Prepares the cluster and applies the recipe's requests as render.mjs extracted them, unchanged.
//   node setup-es.mjs <results dir>
// Cluster preparation, not recipe: the self-managed trial licence (searchable snapshots need
// Enterprise features) and a filesystem snapshot repository registered under the name the
// recipe renders (`found-snapshots`, the repository Elastic Cloud provides). Then every request
// in recipe-requests.json in order, and a check that the tier_down write index sits on a warm node.
import { readFileSync, writeFileSync } from 'fs';
import { join, resolve } from 'path';

const ES = process.env.ES_URL ?? 'http://127.0.0.1:9200';
const dir = resolve(process.argv[2] ?? '.');
const requests = JSON.parse(readFileSync(join(dir, 'recipe-requests.json'), 'utf8'));

async function call(method, path, body) {
  const r = await fetch(ES + path, { method, headers: { 'content-type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text();
  return { method, path, status: r.status, body: text.slice(0, 2000) };
}
const json = async (path) => (await fetch(ES + path)).json();

const prep = [
  await call('POST', '/_license/start_trial?acknowledge=true'),
  await call('PUT', '/_snapshot/found-snapshots', { type: 'fs', settings: { location: '/snapshots' } }),
];
const applied = [];
for (const q of requests) applied.push(await call(q.method, q.path, q.body));

const roles = await json('/_nodes?filter_path=nodes.*.name,nodes.*.roles');
const rolesOf = Object.fromEntries(Object.values(roles.nodes).map((n) => [n.name, n.roles]));
let placement = [];
for (let i = 0; i < 60; i++) {
  placement = (await json('/_cat/shards/tenx-*?format=json&h=index,shard,prirep,state,node')).map((x) => ({ ...x, roles: rolesOf[x.node] ?? null }));
  if (placement.length >= 2 && placement.every((x) => x.state === 'STARTED')) break;
  await new Promise((r) => setTimeout(r, 2000));
}
const td = placement.find((x) => x.index === 'tenx-tierdown-000001');
const tdOnWarm = !!td && (td.roles ?? []).includes('data_warm');
writeFileSync(join(dir, 'es-setup.json'), JSON.stringify({ es: ES, prep, applied, placement, tier_down_write_index_on_warm: tdOnWarm }, null, 1) + '\n');
for (const x of [...prep, ...applied]) console.log(x.status, x.method, x.path);
console.log('placement', JSON.stringify(placement.map((x) => `${x.index}@${x.node}(${(x.roles ?? []).join('+')})`)));
const bad = applied.filter((x) => x.status >= 300).concat(prep.filter((x) => x.status >= 300 && !(x.path.includes('start_trial') && x.status === 403)));
if (bad.length || !tdOnWarm) {
  console.error('FAILED:', bad.map((x) => `${x.status} ${x.method} ${x.path} ${x.body.slice(0, 300)}`).join('\n'), tdOnWarm ? '' : 'tier_down write index not on a warm node');
  process.exit(1);
}
