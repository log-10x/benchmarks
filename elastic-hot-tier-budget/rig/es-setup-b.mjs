// Arm B's cluster, shaped like arm A's after es-setup.mjs: trial licence, a filesystem snapshot repository,
// arm A's ILM policies and ILM poll copied as read from cluster A, and two streams built from arm A's
// templates: native-overflow from tenx-tierdown-tpl (policy tenx-tier-down), native-app from tenx-app-tpl
// (policy tenx-keep), each with a bootstrap write index.
//   ES_URL=<A> ES_URL_B=<B> node es-setup-b.mjs <out dir>
import { writeFileSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';

const A = process.env.ES_URL ?? 'http://127.0.0.1:9200';
const B = process.env.ES_URL_B ?? 'http://127.0.0.1:9201';
const out = resolve(process.argv[2] ?? '.');
mkdirSync(out, { recursive: true });

async function call(base, method, path, body) {
  const r = await fetch(base + path, { method, headers: { 'content-type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text();
  return { cluster: base === A ? 'A' : 'B', method, path, status: r.status, body: text.length > 2000 ? text.slice(0, 2000) : text, json: (() => { try { return JSON.parse(text); } catch { return undefined; } })() };
}
const log = [];
const push = (x) => { log.push({ ...x, json: undefined }); return x; };

push(await call(B, 'POST', '/_license/start_trial?acknowledge=true'));
push(await call(B, 'PUT', '/_snapshot/rig-snapshots', { type: 'fs', settings: { location: '/snapshots' } }));
for (const name of ['tenx-keep', 'tenx-tier-down']) {
  const got = push(await call(A, 'GET', `/_ilm/policy/${name}`));
  push(await call(B, 'PUT', `/_ilm/policy/${name}`, { policy: { phases: got.json[name].policy.phases } }));
}
const cs = push(await call(A, 'GET', '/_cluster/settings?flat_settings=true'));
const poll = cs.json?.persistent?.['indices.lifecycle.poll_interval'];
if (poll) push(await call(B, 'PUT', '/_cluster/settings', { persistent: { 'indices.lifecycle.poll_interval': poll } }));
for (const [from, stream] of [['tenx-tierdown-tpl', 'native-overflow'], ['tenx-app-tpl', 'native-app']]) {
  const got = push(await call(A, 'GET', `/_index_template/${from}`));
  const read = got.json.index_templates[0].index_template;
  const t = Object.fromEntries(['index_patterns', 'template', 'composed_of', 'priority', 'version', '_meta'].filter((k) => k in read).map((k) => [k, read[k]]));
  t.index_patterns = [`${stream}-*`];
  t.template.settings.index.lifecycle.rollover_alias = stream;
  push(await call(B, 'PUT', `/_index_template/${stream}-tpl`, t));
  push(await call(B, 'PUT', `/${stream}-000001`, { aliases: { [stream]: { is_write_index: true } } }));
}
// The overflow template carries arm A's tier_down placement, if any; the check reads where each bootstrap index sits.
let placement;
const tdPlacement = process.env.TD_PLACEMENT;
if (tdPlacement) {
  const tdTier = tdPlacement === 'warm' ? 'data_warm,data_hot' : undefined;
  push(await call(B, 'GET', '/_cluster/health/native-*?wait_for_status=green&wait_for_no_relocating_shards=true&timeout=120s'));
  const shards = (await call(B, 'GET', '/_cat/shards/native-*?format=json&h=index,shard,prirep,state,node')).json ?? [];
  const nodes = (await call(B, 'GET', '/_nodes?filter_path=nodes.*.name,nodes.*.roles')).json?.nodes ?? {};
  const rolesOf = Object.fromEntries(Object.values(nodes).map((n) => [n.name, n.roles]));
  const pref = (await call(B, 'GET', '/native-overflow-000001/_settings/index.routing.allocation.include._tier_preference?flat_settings=true')).json;
  placement = { overflow_tier_preference: pref?.['native-overflow-000001']?.settings?.['index.routing.allocation.include._tier_preference'] ?? null,
    shards: shards.map((x) => ({ ...x, roles: rolesOf[x.node] ?? null })) };
  const want = `data_${tdPlacement}`;
  const wrong = placement.shards.filter((x) => x.index.startsWith('native-overflow-') !== (rolesOf[x.node] ?? []).includes(want));
  if ((placement.overflow_tier_preference ?? undefined) !== tdTier || wrong.length) log.push({ cluster: 'B', method: 'CHECK', path: 'overflow placement', status: 500, body: JSON.stringify(placement) });
}
const check = {};
for (const base of [A, B]) {
  const pol = await call(base, 'GET', '/_ilm/policy/tenx-keep,tenx-tier-down');
  check[base === A ? 'A' : 'B'] = Object.fromEntries(Object.entries(pol.json).map(([k, v]) => [k, v.policy.phases]));
}
const same = JSON.stringify(check.A) === JSON.stringify(check.B);
writeFileSync(join(out, 'es-setup-b.json'), JSON.stringify({ a: A, b: B, ilm_poll: poll ?? null, ilm_policies_identical: same, policies: check, placement, log }, null, 1) + '\n');
for (const x of log) console.log(x.cluster, x.status, x.method, x.path);
const bad = log.filter((x) => x.status >= 300 && !(x.path.includes('start_trial') && x.status === 403));
if (bad.length || !same) { console.error('FAILED:', same ? '' : 'ILM policies differ', bad.map((x) => `${x.status} ${x.method} ${x.path} ${x.body.slice(0, 300)}`).join('\n')); process.exit(1); }
