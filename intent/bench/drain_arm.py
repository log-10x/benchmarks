#!/usr/bin/env python3
"""Drain3 on the labelled events, with the settings of ../pattern-identity.

    python3 bench/drain_arm.py <capture> <input.log[.gz]> <out dir> [--arm strong|baseline]
                               [--unit event|record]

Every Drain3 parameter comes from pattern-identity/bench/identity.py, imported
here rather than copied: depth, similarity threshold, children and cluster
caps, numeric parametrisation, masking per arm, the 1,024-character cap on the
message, and the reference pass (one instance sees the whole stream in memory,
then each message is matched back read-only with full_search_strategy
"fallback" and takes the template it matches as its name).

A record is one line of the capture. In rec1155 and otel215 it is a Docker
JSON line and the message is its `log` value; the zookeeper capture is the
program's own text output, so the message is the whole line.

What Drain3 is given, per --unit:
  event   (default) one message per labelled event: the `log` values of the
          event's records joined by newlines. This hands Drain3 the engine's
          multi-line grouping for free.
  record  one message per record, as pattern-identity feeds it; an event is
          named by its first record.

A message the read-only match cannot place gets a name of its own, so it
counts as a split, never as a merge.

Writes <out dir>/events.jsonl.gz (text, message_pattern per event, input
order, for bench/score.py) and <out dir>/drain_stats.json.
"""

import argparse
import gzip
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LABELS = HERE.parent / 'labels'
sys.path.insert(0, str(HERE.parent.parent / 'pattern-identity' / 'bench'))

import drainver  # noqa: E402  which distribution provides the drain3 module
import identity  # noqa: E402  the pattern-identity harness: settings and Drain3 plumbing

PLAIN_TEXT = {'zookeeper'}  # captures whose records are the program's own lines, not Docker JSON


def read_records(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rb') as f:
        data = f.read().decode('utf-8')
    lines = data.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def message_of(record):
    """The harness's rule: the record's `log` value, empty when absent or unparseable."""
    try:
        return json.loads(record).get('log', '') or ''
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('capture', choices=('rec1155', 'otel215', 'zookeeper'))
    ap.add_argument('input')
    ap.add_argument('out')
    ap.add_argument('--arm', choices=('strong', 'baseline'), default='strong')
    ap.add_argument('--unit', choices=('event', 'record'), default='event')
    a = ap.parse_args()

    with gzip.open(LABELS / f'labels_{a.capture}.jsonl.gz', 'rt', encoding='utf-8') as f:
        counts = [json.loads(l)['records'] for l in f]
    records = read_records(a.input)
    if sum(counts) != len(records):
        sys.exit(f'input has {len(records)} records, the labels describe {sum(counts)}')

    spans, pos = [], 0
    for c in counts:
        spans.append((pos, pos + c))
        pos += c

    msg = (lambda r: r) if a.capture in PLAIN_TEXT else message_of
    if a.unit == 'event':
        messages = ['\n'.join(msg(r) for r in records[s:e]) for s, e in spans]
    else:
        messages = [msg(r) for r in records]

    arm = {**identity.ARMS[a.arm], 'persistence_restart': False, 'warm_start_b_from_a': False}
    tm = identity.train(messages, range(len(messages)), arm, identity.DRAIN_SIM_TH)
    shape, unmatched = [], 0
    for i, m in enumerate(messages):
        t = identity.lookup_template(tm, m, identity.REFERENCE_MATCH_STRATEGY)
        if t is None:
            t = f'<unmatched:{i}>'
            unmatched += 1
        shape.append(t)

    os.makedirs(a.out, exist_ok=True)
    with gzip.open(os.path.join(a.out, 'events.jsonl.gz'), 'wt', encoding='utf-8') as f:
        for k, (s, e) in enumerate(spans):
            name = shape[k] if a.unit == 'event' else shape[s]
            f.write(json.dumps({'message_pattern': name, 'text': '\n'.join(records[s:e])},
                               ensure_ascii=False) + '\n')
    stats = {
        'capture': a.capture, 'arm': a.arm, 'unit': a.unit, 'drain3': drainver.label(),
        'settings': {'depth': identity.DRAIN_DEPTH, 'sim_th': identity.DRAIN_SIM_TH,
                     'max_children': identity.DRAIN_MAX_CHILDREN, 'max_clusters': identity.DRAIN_MAX_CLUSTERS,
                     'parametrize_numeric_tokens': identity.PARAMETRIZE_NUMERIC_TOKENS,
                     'line_cap': identity.LINE_CAP, 'match_strategy': identity.REFERENCE_MATCH_STRATEGY},
        'messages': len(messages), 'clusters': len(tm.drain.clusters),
        'distinct_names': len(set(shape)), 'unmatched': unmatched,
    }
    with open(os.path.join(a.out, 'drain_stats.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=1)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
