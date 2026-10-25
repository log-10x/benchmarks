#!/usr/bin/env python3
"""Every document in an arm's streams, hot and frozen, read through the stream aliases (ILM moves an
alias to the mounted copy in one step, so no document is read twice): one row per document,
seq, container, non-blank lines (arm A's returned records carry _lines), route, index.
  dump-seq.py <es url> <alias,alias> <out.tsv.gz>"""
import gzip, json, sys, urllib.request

es, aliases, out = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]


def call(method, path, body=None):
    req = urllib.request.Request(es + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


call('POST', f'/{aliases}/_refresh')
src = ['seq', 'kubernetes.container_name', '_lines', 'routeState']
r = call('POST', f'/{aliases}/_search?scroll=5m', {'size': 10000, 'sort': ['_doc'], '_source': src})
n = 0
by_index = {}
with gzip.open(out, 'wt') as o:
    while r['hits']['hits']:
        for h in r['hits']['hits']:
            s = h['_source']
            o.write('\t'.join(str(x) for x in (s.get('seq', ''), (s.get('kubernetes') or {}).get('container_name', ''), s.get('_lines', ''), s.get('routeState', ''), h['_index'])) + '\n')
            by_index[h['_index']] = by_index.get(h['_index'], 0) + 1
            n += 1
        r = call('POST', '/_search/scroll', {'scroll': '5m', 'scroll_id': r['_scroll_id']})
call('DELETE', '/_search/scroll', {'scroll_id': r['_scroll_id']})
counts = call('GET', f'/{aliases}/_count')['count']
print(json.dumps({'aliases': aliases, 'documents_read': n, 'count_api': counts, 'indices': len(by_index), 'by_index': by_index}))
