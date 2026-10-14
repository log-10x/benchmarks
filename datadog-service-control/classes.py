#!/usr/bin/env python3
"""
Add each event's log4j logger class to a replay's tally.

  classes.py --routed runs/<run>/routed.jsonl --tally results/<run>.tally.json --out results/<run>.classes.json

The replay writes each event's source records (`fullText`, one JSON record per source line).
Kafka's log4j layout ends the message line with the logger in parentheses, for example
`(org.apache.kafka.storage.internals.log.LogSegment)`; Datadog's Kafka log pipeline parses
it into `logger.name`. An event's class is the first of its lines that ends that way: the
first line for a message followed by a stack trace, the last for a multi-line message such
as a config dump. Events with none (the image's shell start-up output) have no class.

Rows are (route, severity, pattern, hash, class) with events and bytes. The run fails unless
their totals per (route, severity, pattern, hash) equal the tally's rows, which count.py
has checked against the engine's own aggregators.
"""
import argparse
import collections
import json
import re

LOGGER = re.compile(r'\(([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\)\s*$')


def one(v):
    if isinstance(v, list):
        return v[0] if v else ''
    return '' if v is None else v


def logger_class(full_text: str) -> str:
    for raw in full_text.split('\n'):
        try:
            line = json.loads(raw).get('log', '')
        except ValueError:
            line = raw
        m = LOGGER.search(line or '')
        if m:
            return m.group(1)
    return ''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--routed', required=True)
    ap.add_argument('--tally', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ev, by = collections.Counter(), collections.Counter()
    for line in open(a.routed, encoding='utf-8', errors='surrogateescape'):
        d = json.loads(line)
        k = (one(d.get('routeState')) or 'pass', one(d.get('k8s_container')), one(d.get('severity_level')),
             one(d.get('message_pattern')), one(d.get('tenx_hash')), logger_class(one(d.get('fullText'))))
        ev[k] += 1
        by[k] += int(d['utfeightSize_of'])
    tally = json.load(open(a.tally))
    want = {(r['route'], r['container'], r['severity'], r['pattern'], r['hash']): (r['events'], r['bytes'])
            for r in tally['by_key']}
    got = collections.defaultdict(lambda: [0, 0])
    for k in ev:
        got[k[:5]][0] += ev[k]
        got[k[:5]][1] += by[k]
    diffs = [k for k in set(want) | set(got) if tuple(got.get(k, (0, 0))) != want.get(k, (0, 0))]
    if diffs:
        raise SystemExit(f'{len(diffs)} keys differ between the class rows and the tally, e.g. {diffs[:3]}')
    rows = [{'route': k[0], 'container': k[1], 'severity': k[2], 'pattern': k[3], 'hash': k[4], 'class': k[5],
             'events': ev[k], 'bytes': by[k]} for k in sorted(ev)]
    per_hash = collections.defaultdict(set)
    for r in rows:
        per_hash[r['hash']].add(r['class'])
    json.dump({'rows': rows, 'hashes_with_more_than_one_class': sorted(h for h, c in per_hash.items() if len(c) > 1)},
              open(a.out, 'w'), indent=0)
    by_class = collections.Counter()
    for r in rows:
        by_class[r['class']] += r['events']
    print(f'{sum(ev.values())} events, {len(by_class)} classes, equal to the tally; '
          f'top: {", ".join(f"{c.rsplit(".", 1)[-1] or "(none)"}={n}" for c, n in by_class.most_common(6))}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
