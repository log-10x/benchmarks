#!/usr/bin/env python3
"""Builds the replay feed from the published OpenTelemetry demo sample (otel-sample-200mb.log,
release otel-sample-v1 of log-10x/config): one row per line, in file order, 1/7 s apart
(7 lines a second at speed 1), in the shape forward_send.py sends; and the storm line, the first
Grafana `level=error msg="Could not register plugin"` line.
  make-replay.py <otel-sample-200mb.log>   writes ../results/replay/source.jsonl and storm-line.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')), 'replay')
os.makedirs(out, exist_ok=True)
RATE = 7.0
storm = None
n = 0
with open(sys.argv[1]) as f, open(os.path.join(out, 'source.jsonl'), 'w') as o:
    for i, line in enumerate(f):
        r = json.loads(line)
        c = r['kubernetes']['container_name']
        row = {'t': round(i / RATE, 4), 'container_name': '/' + c, 'container_id': r['docker']['container_id'], 'source': r.get('stream', 'stdout'), 'log': r['log']}
        o.write(json.dumps(row) + '\n')
        n += 1
        if storm is None and c == 'grafana' and 'level=error msg="Could not register plugin"' in r['log']:
            storm = {k: row[k] for k in ('container_name', 'container_id', 'source', 'log')}
json.dump(storm, open(os.path.join(out, 'storm-line.json'), 'w'))
print('rows', n)
