#!/usr/bin/env python3
"""
For every pattern, the smallest cell of native attribute values that holds all its events,
and which patterns share that cell.

  attrs.py --routed runs/<run>/routed.jsonl --tally results/<run>.tally.json \
           --integrations integrations.json --out results/<run>.attrs.json

The attributes, fixed before the count (integrations.json): `service` (the container),
`status` (the severity as Datadog maps it; an unlevelled line is info), `source` and `host`
on every log; the attributes the container's documented integration pipeline parses; and the
top-level keys of a line that is a JSON object. A pattern's cell is the set of attribute
values every one of its events carries; a filter on that cell selects the pattern's events
and the events of every pattern that falls in it. Only exact values count, no wildcards.

The run fails unless the events read equal the tally, which count.py checked against the
engine's aggregators.
"""
import argparse
import collections
import json
import re

STATUS = {'ERROR': 'error', 'WARN': 'warn', 'WARNING': 'warn', 'INFO': 'info', 'DEBUG': 'debug', 'TRACE': 'trace',
          'CRITICAL': 'critical', 'FATAL': 'emergency', '': 'info'}
LOG4J = re.compile(r'\(([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\)\s*$')
# Datadog's postgresql pipeline, rule default_format: %{_pg_timestamp} \[%{_pg_pid}\] %{_pg_body}
PG_DEFAULT = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)? (?:[0-9A-Za-z+-]+)? ?\[(\d+)\] (\w+):  (?:[A-Z0-9]{5}: )?(.*?)(?: at character \d+)?$')


def one(v):
    if isinstance(v, list):
        return v[0] if v else ''
    return '' if v is None else v


def first_record(full_text):
    raw = full_text.split('\n', 1)[0]
    try:
        return json.loads(raw)
    except ValueError:
        return {'log': raw}


def lines(full_text):
    out = []
    for raw in full_text.split('\n'):
        try:
            out.append(json.loads(raw).get('log', ''))
        except ValueError:
            out.append(raw)
    return out


def parse(parser, full_text, log):
    if parser == 'log4j-logger':
        for line in lines(full_text):
            m = LOG4J.search(line or '')
            if m:
                return {'logger.name': m.group(1)}
        return {}
    if parser == 'postgresql-default':
        m = PG_DEFAULT.match(log.rstrip('\n'))
        return {'postgres.pid': m.group(1), 'postgres.error_severity': m.group(2), 'postgres.message': m.group(3)} if m else {}
    return {}


def json_keys(log):
    s = (log or '').strip()
    if not (s.startswith('{') and s.endswith('}')):
        return {}
    try:
        obj = json.loads(s)
    except ValueError:
        return {}
    return {f'json.{k}': str(v) for k, v in obj.items() if isinstance(v, (str, int, float, bool))} if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--routed', required=True)
    ap.add_argument('--tally', required=True)
    ap.add_argument('--integrations', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    integ = json.load(open(a.integrations))['containers']
    combos = collections.Counter()   # (container, hash, frozenset(attrs)) -> events
    n = 0
    for line in open(a.routed, encoding='utf-8', errors='surrogateescape'):
        d = json.loads(line)
        svc, h, sev = one(d.get('k8s_container')), one(d.get('tenx_hash')), one(d.get('severity_level')).upper()
        full = one(d.get('fullText'))
        rec = first_record(full)
        log = rec.get('log', '') if isinstance(rec, dict) else ''
        attrs = {'service': svc, 'status': STATUS.get(sev, sev.lower()), 'source': (integ.get(svc) or {}).get('integration') or svc,
                 'host': ((rec.get('kubernetes') or {}).get('host') if isinstance(rec, dict) else '') or ''}
        attrs.update(parse((integ.get(svc) or {}).get('parser'), full, log))
        attrs.update(json_keys(log))
        combos[(svc, h, frozenset(attrs.items()))] += 1
        n += 1
    tally = json.load(open(a.tally))
    if n != tally['events']:
        raise SystemExit(f'{n} events read, the tally has {tally["events"]}')
    by_container = collections.defaultdict(lambda: collections.defaultdict(list))
    for (svc, h, attrs), ev in combos.items():
        by_container[svc][h].append((attrs, ev))
    # Each distinct cell once; every pattern points at its own.
    cells, index, pattern_cell = [], {}, {}
    for svc, pats in sorted(by_container.items()):
        for h, cs in sorted(pats.items()):
            sig = frozenset.intersection(*[c for c, _ in cs])
            key = (svc, sig)
            if key not in index:
                members = sorted(q for q, qcs in pats.items() if any(sig <= c for c, _ in qcs))
                index[key] = len(cells)
                cells.append({'service': svc, 'attributes': {k: v for k, v in sorted(sig) if k not in ('service', 'source')},
                              'members': members})
            pattern_cell[f'{svc}\t{h}'] = index[key]
    json.dump({'events': n, 'cells': cells, 'pattern_cell': pattern_cell}, open(a.out, 'w'), indent=0)
    alone = sum(1 for i in pattern_cell.values() if len(cells[i]['members']) == 1)
    print(f'{n} events, {len(pattern_cell)} patterns in {len(cells)} cells, {alone} alone in their cell')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
