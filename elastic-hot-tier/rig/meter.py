#!/usr/bin/env python3
"""The cluster's own count, every INTERVAL seconds (default 600), appended to results/meter.jsonl:
  _cat/indices for tenx-* and partial-tenx-* (bytes), _cat/allocation (bytes),
  _ilm/explain for the same indices, and once an hour _stats/store as the machine-readable
  cross-check (the cat APIs are documented for human use).
Exits when results/.down.done appears.
  meter.py [interval_s]"""
import json, os, sys, time, urllib.request

ES = os.environ.get('ES_URL', 'http://127.0.0.1:9200')
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')))
INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 600
OUT = os.path.join(R, 'meter.jsonl')
IDX = 'tenx-*,partial-tenx-*'


def get(path):
    try:
        with urllib.request.urlopen(ES + path, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}


last_stats = 0
while not os.path.exists(os.path.join(R, '.down.done')):
    t = time.time()
    rec = {
        'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t)),
        'epoch': int(t),
        'indices': get(f'/_cat/indices/{IDX}?format=json&bytes=b&expand_wildcards=all&h=index,health,status,docs.count,store.size,pri.store.size,creation.date'),
        'allocation': get('/_cat/allocation?format=json&bytes=b'),
        'ilm': get(f'/{IDX}/_ilm/explain?filter_path=indices.*.phase,indices.*.action,indices.*.step,indices.*.phase_time_millis,indices.*.lifecycle_date_millis,indices.*.index_creation_date_millis,indices.*.age,indices.*.step_info'),
    }
    if t - last_stats >= 3600:
        rec['stats_store'] = get(f'/{IDX}/_stats/store?level=indices&filter_path=indices.*.total.store')
        last_stats = t
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec) + '\n')
    time.sleep(max(1, INTERVAL - (time.time() - t)))
