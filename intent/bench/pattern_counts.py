#!/usr/bin/env python3
"""Reconcile the pattern count of this benchmark with ../naming-stability's.

    python3 bench/pattern_counts.py <capture> <intent events> <naming-stability events>
                                    [--out file.json]

<capture> is rec1155 or otel215. The intent events file is what bench/engine.sh
writes; the naming-stability one is what ../naming-stability/bench/engine.sh
writes, for the same image on the same capture. Both are checked against the
labelled capture, event for event, as bench/score.py does.

Reports, per capture:
  whether the two runs gave every event the same pattern name;
  the patterns of every event (the naming-stability count);
  the patterns of labelled events (`distinct_patterns` in bench/score.py);
  the patterns that occur only in unlabelled events, by container.
"""

import argparse
import collections
import gzip
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(os.path.dirname(HERE), 'labels')


def opener(path):
    return gzip.open(path, 'rt', encoding='utf-8') if path.endswith('.gz') else open(path, encoding='utf-8')


def container_of(text):
    try:
        d = json.loads(text.split('\n', 1)[0])
    except ValueError:
        return None
    return (d.get('kubernetes') or {}).get('container_name', '<nok8s>')


def load_events(path, labels, hashes):
    names = []
    with opener(path) as f:
        for k, line in enumerate(f):
            d = json.loads(line)
            t = d['text']
            if k >= len(labels) or hashlib.sha1(t.encode()).hexdigest()[:16] != hashes[k] \
                    or container_of(t) != labels[k]['container']:
                sys.exit(f'ALIGNMENT: {path}: event {k} differs from the labelled capture')
            names.append(d.get('message_pattern') or '')
    if len(names) != len(labels):
        sys.exit(f'ALIGNMENT: {path}: {len(names)} events, {len(labels)} labels')
    return names


def reconcile(capture, intent_path, ns_path):
    with opener(os.path.join(LABELS, f'labels_{capture}.jsonl.gz')) as f:
        labels = [json.loads(l) for l in f]
    with opener(os.path.join(LABELS, f'texthash_{capture}.txt.gz')) as f:
        hashes = f.read().split()
    a = load_events(intent_path, labels, hashes)
    b = load_events(ns_path, labels, hashes)
    differ = sum(x != y for x, y in zip(a, b))

    names = b
    labelled = [k for k, r in enumerate(labels) if r['statement']]
    unlabelled = [k for k, r in enumerate(labels) if not r['statement']]
    p_all = set(names)
    p_lab = {names[k] for k in labelled}
    p_unl = {names[k] for k in unlabelled}
    only = p_unl - p_lab

    # Per container: its unlabelled events and the unlabelled-only patterns
    # they take. A pattern seen in several containers counts in each.
    by_pat = collections.defaultdict(collections.Counter)
    for k in unlabelled:
        if names[k] in only:
            by_pat[names[k]][labels[k]['container']] += 1
    by_container = collections.defaultdict(lambda: dict(unlabelled_events=0, patterns=0))
    for k in unlabelled:
        by_container[labels[k]['container']]['unlabelled_events'] += 1
    for c in by_pat.values():
        for cont in c:
            by_container[cont]['patterns'] += 1
    multi = {p: dict(c) for p, c in sorted(by_pat.items()) if len(c) > 1}

    return dict(
        capture=capture,
        events=len(labels),
        labelled_events=len(labelled),
        unlabelled_events=len(unlabelled),
        unlabelled_multiline_events=sum(1 for k in unlabelled if labels[k]['multiline']),
        events_named_differently_by_the_two_runs=differ,
        patterns_every_event=len(p_all),
        patterns_labelled_events=len(p_lab),
        patterns_unlabelled_events=len(p_unl),
        patterns_in_both=len(p_lab & p_unl),
        patterns_only_in_unlabelled_events=len(only),
        events_in_unlabelled_only_patterns=sum(sum(c.values()) for c in by_pat.values()),
        unlabelled_only_patterns_by_container=dict(
            sorted(by_container.items(), key=lambda x: (-x[1]['patterns'], -x[1]['unlabelled_events'], x[0]))),
        unlabelled_only_patterns_in_more_than_one_container=multi,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('capture', choices=('rec1155', 'otel215'))
    ap.add_argument('intent_events')
    ap.add_argument('naming_stability_events')
    ap.add_argument('--out')
    a = ap.parse_args()
    res = reconcile(a.capture, a.intent_events, a.naming_stability_events)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=1)
            f.write('\n')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
