"""Shared arithmetic over the kept tallies. Imported by each folder's report.py."""
import collections
import json

PROTECTED = ('ERROR', 'WARN', 'WARNING', 'CRITICAL', 'FATAL')
MONTH_HOURS = 24 * 30


def load(path):
    return json.load(open(path))


def by_route(tally):
    out = collections.defaultdict(lambda: {'events': 0, 'bytes': 0})
    for k in tally['by_key']:
        out[k['route']]['events'] += k['events']
        out[k['route']]['bytes'] += k['bytes']
    return dict(sorted(out.items()))


def by_route_severity(tally):
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: {'events': 0, 'bytes': 0}))
    for k in tally['by_key']:
        sev = k['severity'] or 'none'
        out[k['route']][sev]['events'] += k['events']
        out[k['route']][sev]['bytes'] += k['bytes']
    return {r: dict(sorted(s.items())) for r, s in sorted(out.items())}


def moved(tally, routes=('tier_down', 'offload')):
    ev = sum(k['events'] for k in tally['by_key'] if k['route'] in routes)
    by = sum(k['bytes'] for k in tally['by_key'] if k['route'] in routes)
    return {'events': ev, 'bytes': by}


def protected_moved(tally, routes=('tier_down', 'offload')):
    ev = sum(k['events'] for k in tally['by_key'] if k['route'] in routes and (k['severity'] or '').upper() in PROTECTED)
    return ev


def top_moved(tally, n=10, routes=('tier_down', 'offload')):
    agg = collections.defaultdict(lambda: {'events': 0, 'bytes': 0})
    for k in tally['by_key']:
        if k['route'] in routes:
            key = (k['pattern'], k['container'], k['severity'] or 'none', k['route'])
            agg[key]['events'] += k['events']
            agg[key]['bytes'] += k['bytes']
    rows = sorted(agg.items(), key=lambda kv: -kv[1]['events'])[:n]
    return [{'pattern': p, 'container': c, 'severity': s, 'route': r, **v} for (p, c, s, r), v in rows]


def by_container_route(tally):
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: {'events': 0, 'bytes': 0}))
    for k in tally['by_key']:
        out[k['container']][k['route']]['events'] += k['events']
        out[k['container']][k['route']]['bytes'] += k['bytes']
    return {c: dict(r) for c, r in sorted(out.items())}


def gb(b):
    """Decimal gigabytes, the unit both vendors' price lists use."""
    return b / 1_000_000_000


def monthly(x, window_hours):
    return x * MONTH_HOURS / window_hours


def fmt_int(n):
    return f'{int(round(n)):,}'


def fmt_usd(x, places=2):
    """Dollars to `places` decimals, with no decimals when the amount rounds to whole dollars."""
    text = f'{x:,.{places}f}'
    return '$' + (text.split('.')[0] if '.' in text and set(text.split('.')[1]) == {'0'} else text)


def fmt_gb(b):
    return f'{gb(b):.3f}'
