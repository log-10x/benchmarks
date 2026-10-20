#!/usr/bin/env python3
"""Slim captures for the commit: per record only what analyze.py reads (container, ingest and
return times, route, pattern hash, statement name, level, non-blank lines), no log text.
  slim.py  (reads results/data/*.jsonl, writes results/captures/<route>.tsv.gz)"""
import gzip, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import meter
R = os.path.abspath(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')))
os.makedirs(os.path.join(R, 'captures'), exist_ok=True)
for route in ('raw', 'pass', 'tier_down', 'offload', 'other'):
    p = os.path.join(R, 'data', route + '.jsonl')
    if not os.path.exists(p):
        continue
    n = 0
    with gzip.open(os.path.join(R, 'captures', route + '.tsv.gz'), 'wt') as out:
        out.write('container\tfb_ts\trb_ts\ttenx_hash\tmessage_pattern\tseverity_level\tlines\n')
        for r in meter.records(p):
            c = (r.get('kubernetes') or {}).get('container_name')
            if not c or 'fb_ts' not in r:
                continue
            lines = sum(1 for x in (r.get('log') or '').split('\n') if x.strip())
            out.write('\t'.join([c, r['fb_ts'], r.get('rb_ts') or '', r.get('tenx_hash') or '', r.get('message_pattern') or '', r.get('severity_level') or '', str(lines)]) + '\n')
            n += 1
    print(route, n)
