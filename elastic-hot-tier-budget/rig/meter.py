#!/usr/bin/env python3
"""The cluster's own count, every INTERVAL seconds (default 600), appended to results/meter.jsonl:
  _cat/indices for tenx-* and partial-tenx-* (bytes), _cat/allocation (bytes),
  _ilm/explain for the same indices, and once an hour _stats/store as the machine-readable
  cross-check (the cat APIs are documented for human use).
With ES_URL_B set (the two-arm run) each reading first refreshes both arms' indices on hot (a shard
no one searches goes search-idle and writes nothing to its store until a refresh), the same reads of
arm B's cluster for native-* and partial-native-* go under "b", and "summary" gives per arm the hot node's index store and disk, the
warm node's index store, and per stream the store of its indices on hot and on warm (by the node each shard sits on, _cat/shards)
and the indices and documents mounted on frozen.
Exits when results/.down.done appears.
  meter.py [interval_s]"""
import json, os, re, sys, time, urllib.request

ES = os.environ.get('ES_URL', 'http://127.0.0.1:9200')
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')))
INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 600
OUT = os.path.join(R, 'meter.jsonl')
IDX = 'tenx-*,partial-tenx-*'
ES_B = os.environ.get('ES_URL_B')
IDX_B = 'native-*,partial-native-*'


def get(path, base=None):
    try:
        with urllib.request.urlopen((base or ES) + path, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}


def refresh(base, idx):
    try:
        req = urllib.request.Request(base + f'/{idx}/_refresh', method='POST')
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get('_shards')
    except Exception as e:
        return {'error': str(e)}


def reads(base, idx):
    return {
        'indices': get(f'/_cat/indices/{idx}?format=json&bytes=b&expand_wildcards=all&h=index,health,status,docs.count,store.size,pri.store.size,creation.date', base),
        'allocation': get('/_cat/allocation?format=json&bytes=b', base),
        'shards': get(f'/_cat/shards/{idx}?format=json&bytes=b&h=index,shard,prirep,state,store,node', base),
        'nodes': get('/_nodes/stats/fs,indices?filter_path=nodes.*.name,nodes.*.roles,nodes.*.fs.total.total_in_bytes,nodes.*.fs.total.available_in_bytes,nodes.*.indices.store.size_in_bytes', base),
        'ilm': get(f'/{idx}/_ilm/explain?filter_path=indices.*.phase,indices.*.action,indices.*.step,indices.*.phase_time_millis,indices.*.lifecycle_date_millis,indices.*.index_creation_date_millis,indices.*.age,indices.*.step_info', base),
    }


def tier(roles):
    return 'hot' if 'data_hot' in roles else 'warm' if 'data_warm' in roles else 'other'


def summary(r):
    nodes = (r.get('nodes') or {}).get('nodes') or {}
    hot = [n for n in nodes.values() if 'data_hot' in n.get('roles', [])]
    warm = [n for n in nodes.values() if 'data_warm' in n.get('roles', []) and 'data_hot' not in n.get('roles', [])]
    store = lambda ns: sum(int(n['indices']['store']['size_in_bytes']) for n in ns) if ns else None
    out = {'hot_node_store': store(hot), 'hot_node_disk': sum(int(n['fs']['total']['total_in_bytes']) for n in hot) if hot else None,
           'warm_node_store': store(warm), 'streams': {}}
    roles = {n.get('name'): n.get('roles', []) for n in nodes.values()}
    # a relocating shard reads "<from> -> <ip> <id> <to>"; its store is counted where it is read from
    where, by_tier = {}, {}
    for sh in r.get('shards') if isinstance(r.get('shards'), list) else []:
        t = tier(roles.get((sh.get('node') or '').split(' -> ')[0], [])) if sh.get('node') else 'unassigned'
        where.setdefault(sh['index'], set()).add(t)
        k = (sh['index'], t)
        by_tier[k] = by_tier.get(k, 0) + int(sh.get('store') or 0)
    for i in r.get('indices') if isinstance(r.get('indices'), list) else []:
        name = i['index']
        mounted = name.startswith('partial-') or name.startswith('restored-')
        stream = re.sub(r'-\d{6}$', '', re.sub(r'^(partial-|restored-)', '', name))
        st = out['streams'].setdefault(stream, {'hot_store': 0, 'hot_indices': 0, 'hot_docs': 0, 'warm_store': 0, 'warm_indices': 0, 'warm_docs': 0,
                                                'other_store': 0, 'frozen_indices': 0, 'frozen_docs': 0})
        docs = int(i.get('docs.count') or 0)
        if mounted:
            st['frozen_indices'] += 1
            st['frozen_docs'] += docs
            continue
        tiers = where.get(name) or {'hot'}
        if tiers <= {'hot'} or tiers <= {'warm'}:
            t = next(iter(tiers))
            st[f'{t}_store'] += int(i.get('store.size') or 0)
            st[f'{t}_indices'] += 1
            st[f'{t}_docs'] += docs
        else:
            for t in tiers:
                st[f'{t}_store' if t in ('hot', 'warm') else 'other_store'] += by_tier.get((name, t), 0)
            st['hot_indices' if 'hot' in tiers else 'warm_indices'] += 1
            st['hot_docs' if 'hot' in tiers else 'warm_docs'] += docs
    return out


last_stats = 0
while not os.path.exists(os.path.join(R, '.down.done')):
    t = time.time()
    rf = {'a': refresh(ES, 'tenx-*'), 'b': refresh(ES_B, 'native-*')} if ES_B else None
    rec = {'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t)), 'epoch': int(t), **reads(ES, IDX)}
    if ES_B:
        rec['refresh'] = rf
        rec['b'] = reads(ES_B, IDX_B)
        rec['summary'] = {'a': summary(rec), 'b': summary(rec['b'])}
    if t - last_stats >= 3600:
        rec['stats_store'] = get(f'/{IDX}/_stats/store?level=indices&filter_path=indices.*.total.store')
        if ES_B:
            rec['b']['stats_store'] = get(f'/{IDX_B}/_stats/store?level=indices&filter_path=indices.*.total.store', ES_B)
        last_stats = t
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec) + '\n')
    time.sleep(max(1, INTERVAL - (time.time() - t)))
