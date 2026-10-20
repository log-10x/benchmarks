#!/usr/bin/env python3
"""Hourly reads of Datadog's own usage metric and of the rig's local route files.
Run under rig/ddenv.sh (DD_API_KEY, DD_APP_KEY, DD_API_HOST). Prints JSON; never prints a key.
  meter.py usage <from epoch> <to epoch>      indexed events an hour by datadog_index and service
  meter.py local <results dir> [<from> <to>]  returned records an hour by route and container
"""
import json, os, sys, time, urllib.parse, urllib.request, glob, gzip
from collections import defaultdict

HOUR = 3600


def dd_query(q, frm, to):
    url = f"https://{os.environ['DD_API_HOST']}/api/v1/query?" + urllib.parse.urlencode({'from': frm, 'to': to, 'query': q})
    req = urllib.request.Request(url, headers={'DD-API-KEY': os.environ['DD_API_KEY'], 'DD-APPLICATION-KEY': os.environ['DD_APP_KEY']})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if d.get('status') != 'ok':
        raise SystemExit(f"query failed: {d.get('error')}")
    return d.get('series', [])


def usage(frm, to):
    q = 'sum:datadog.estimated_usage.logs.ingested_events{datadog_is_excluded:false} by {datadog_index,service}.as_count().rollup(sum, 3600)'
    out = defaultdict(lambda: defaultdict(float))
    for s in dd_query(q, frm, to):
        tags = dict(t.split(':', 1) for t in s.get('tag_set', []) if ':' in t)
        key = f"{tags.get('datadog_index', '?')}/{tags.get('service', '?')}"
        for ts, v in s['pointlist']:
            if v:
                out[int(ts / 1000)][key] += v
    return {time.strftime('%Y-%m-%dT%H:00Z', time.gmtime(h)): dict(sorted(v.items())) for h, v in sorted(out.items())}


def records(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt', errors='replace') as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception:
                continue


def local(results, frm=0, to=1e12):
    data = os.path.join(results, 'data')
    out = defaultdict(lambda: defaultdict(int))
    for route in ('raw', 'pass', 'tier_down', 'offload', 'other'):
        for p in sorted(glob.glob(os.path.join(data, f'{route}*.jsonl*'))):
            for r in records(p):
                t = float(r.get('rb_ts') or r.get('fb_ts') or 0)
                if not (frm <= t < to):
                    continue
                c = (r.get('kubernetes') or {}).get('container_name') or '?'
                h = int(t // HOUR * HOUR)
                out[h][f'{route}'] += 1
                out[h][f'{route}/{c}'] += 1
    return {time.strftime('%Y-%m-%dT%H:00Z', time.gmtime(h)): dict(sorted(v.items())) for h, v in sorted(out.items())}


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'usage':
        print(json.dumps(usage(int(sys.argv[2]), int(sys.argv[3])), indent=1))
    elif cmd == 'local':
        a = [float(x) for x in sys.argv[3:5]] or [0, 1e12]
        print(json.dumps(local(sys.argv[2], *a), indent=1))
    else:
        raise SystemExit(__doc__)
