#!/usr/bin/env python3
"""Score one tool's grouping of a capture against the source-statement labels.

    python3 bench/score.py <capture> <events.jsonl[.gz]> [--out file.json]
                           [--exclude-container NAME ...] [--grouping-only]

<capture> is rec1155, otel215 or zookeeper. The events file holds one JSON
record per event, in input order, with `text` (the event's raw records joined
by newlines) and `message_pattern` (the name the tool gave it); `tenx_origin`
(the typed origin, `<file>:<symbol>`) is optional.

Alignment is checked before anything is scored: the events must be the
capture's events, one for one, in order (same count, and each event's text
hash and Kubernetes container equal the label's). Unlabelled events are
excluded from every score.

Per event, against its statement's label:
  merged   the event's pattern holds mostly another statement's events
  split    the event sits outside its statement's most frequent pattern
  exact    the statement has exactly one pattern and that pattern holds
           only that statement
"""

import argparse
import collections
import csv
import gzip
import hashlib
import json
import os
import re
import glob
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(os.path.dirname(HERE), 'labels')
CAPTURES = ('rec1155', 'otel215', 'zookeeper')

SEVERITY = {'TRACE', 'DEBUG', 'INFO', 'NOTICE', 'WARN', 'WARNING', 'ERROR', 'ERR', 'CRITICAL', 'CRIT',
            'ALERT', 'EMERGENCY', 'EMERG', 'FATAL', 'PANIC', 'trace', 'debug', 'info', 'notice', 'warn',
            'warning', 'err', 'critical', 'crit', 'alert', 'fatal', 'panic'}

# Envelope keys: the engine's reserved words that are not literals, stopwords,
# generic log words or severities. A name word in this set that the
# statement's own format does not hold is envelope that leaked into the name.
ENVELOPE = {
    'level', 'levelname', 'severity', 'time', 'timestamp', 'ts', 'msg', 'message', 'otel', 'otelcol',
    'opentelemetry', 'collector', 'contrib', 'processor', 'processors', 'receiver', 'receivers',
    'exporter', 'exporters', 'pipeline', 'pipelines', 'service', 'services', 'instance', 'instances',
    'component', 'components', 'signal', 'signals', 'resource', 'resources', 'scope', 'scopes',
    'attribute', 'attributes', 'traces', 'span', 'spans', 'flag', 'flags', 'context', 'contexts',
    'baggage', 'metadata', 'namespace', 'verb', 'uid', 'identity', 'protocol', 'priority', 'encoding',
    'headers', 'duration', 'path', 'status', 'id', 'name', 'kind', 'version', 'type', 'caller', 'func',
    'function', 'file', 'line', 'module', 'package', 'class', 'method', 'stack', 'stacktrace', 'pid',
    'tid', 'process', 'thread', 'hostname', 'application', 'com', 'org', 'io', 'net',
}

# Executables found in image scans, mapped to the projects compiled into them.
BINARY_PROJECTS = {
    'valkey-server': {'valkey-io/valkey'},
    'prometheus': {'prometheus/prometheus'},
    'otelcol-contrib': {'open-telemetry/opentelemetry-collector', 'open-telemetry/opentelemetry-collector-contrib',
                        'open-telemetry/opentelemetry-go', 'grpc/grpc-go'},
}

PH = re.compile(r'%[-+# 0]*(?:\d+|\*)?(?:\.\d+)?(?:hh|ll|[hlzjtLq])?[a-zA-Z%]|\{[^{}]*\}|\$\{[^{}]*\}|#\{[^{}]*\}|\$[A-Za-z_]\w*')


def opener(path):
    return gzip.open(path, 'rt', encoding='utf-8') if path.endswith('.gz') else open(path, encoding='utf-8')


def words(s):
    return [w for w in re.split(r'[^A-Za-z0-9]+', s) if w]


def first_word(fmt):
    for part in PH.split(fmt.replace('\\n', ' ').replace('\\t', ' ')):
        ws = [w for w in words(part) if re.match(r'[A-Za-z]', w)]
        if ws:
            return ws[0]
    return None


def basename(origin):
    """tenx_origin is '<file>:<symbol>'; the file part may carry a path."""
    return origin.strip().split(':', 1)[0].rsplit('/', 1)[-1]


def attr_category(r, origin, repo_bases):
    """untyped | exact_file | same_repo_other_file | other_project"""
    if not origin:
        return 'untyped'
    b = basename(origin)
    if b == r['file_base']:
        return 'exact_file'
    if b in repo_bases.get(f"{r['repo']}@{r['ref']}", ()) or r['repo'] in BINARY_PROJECTS.get(b, ()):
        return 'same_repo_other_file'
    return 'other_project'


def load_statements():
    """statements.tsv (rec1155, otel215) and statements_<capture>.tsv (a capture frozen on its own)."""
    st = {}
    for path in sorted(glob.glob(os.path.join(LABELS, 'statements*.tsv'))):
        with open(path, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                r['fmt_words'] = {w.lower() for w in words(PH.sub(' ', r['format'].replace('\\n', ' ')))}
                r['first_word'] = first_word(r['format']) if r['kind'] == 'code' else None
                r['file_base'] = os.path.basename(r['path']) if r['path'] else ''
                if r['statement'] in st:
                    sys.exit(f'statement listed twice: {r["statement"]}')
                st[r['statement']] = r
    return st


def load_repo_bases():
    bases = {}
    for path in sorted(glob.glob(os.path.join(LABELS, 'repo_basenames*.json.gz'))):
        with opener(path) as f:
            for k, v in json.load(f).items():
                bases.setdefault(k, set()).update(v)
    return bases


def container_of(text):
    try:
        d = json.loads(text.split('\n', 1)[0])
    except ValueError:
        return None
    return (d.get('kubernetes') or {}).get('container_name', '<nok8s>')


def pct(a, b):
    return round(100.0 * a / b, 2) if b else None


def score(capture, events_path, exclude=(), grouping_only=False):
    with opener(os.path.join(LABELS, f'labels_{capture}.jsonl.gz')) as f:
        labels = [json.loads(l) for l in f]
    with opener(os.path.join(LABELS, f'texthash_{capture}.txt.gz')) as f:
        hashes = f.read().split()

    pats, origins = [], []
    with opener(events_path) as f:
        for k, line in enumerate(f):
            d = json.loads(line)
            t = d['text']
            if k >= len(labels):
                sys.exit(f'ALIGNMENT: more events than labels ({len(labels)})')
            if hashlib.sha1(t.encode()).hexdigest()[:16] != hashes[k]:
                sys.exit(f'ALIGNMENT: event {k} text differs from the labelled capture')
            if labels[k]['i'] != k or container_of(t) != labels[k]['container']:
                sys.exit(f'ALIGNMENT: event {k} container differs from its label')
            pats.append(d.get('message_pattern') or '')
            origins.append(d.get('tenx_origin') or '')
    n = len(pats)
    if n != len(labels):
        sys.exit(f'ALIGNMENT: {n} events, {len(labels)} labels')

    ST = load_statements()
    repo_bases = load_repo_bases()

    idx = [k for k in range(n) if labels[k]['statement'] and labels[k]['container'] not in exclude]
    stmt = {k: labels[k]['statement'] for k in idx}
    group = {}
    for k in idx:
        r = ST[stmt[k]]
        group[k] = 'not_code' if r['kind'] != 'code' else (
            'source_in_library' if r['library_1_1_89'] else 'source_not_in_library')

    p_s = collections.defaultdict(collections.Counter)   # pattern -> statement counts
    s_p = collections.defaultdict(collections.Counter)   # statement -> pattern counts
    for k in idx:
        p_s[pats[k]][stmt[k]] += 1
        s_p[stmt[k]][pats[k]] += 1
    maj_s = {p: c.most_common(1)[0][0] for p, c in p_s.items()}
    maj_p = {s: c.most_common(1)[0][0] for s, c in s_p.items()}
    exact_pair = {s for s, c in s_p.items() if len(c) == 1 and len(p_s[next(iter(c))]) == 1}
    merged_stmt = {s for s, c in s_p.items() if any(len(p_s[p]) > 1 for p in c)}
    split_stmt = {s for s, c in s_p.items() if len(c) > 1}

    ev = {}
    for k in idx:
        s, p = stmt[k], pats[k]
        ev[k] = dict(merged=(s != maj_s[p]), split=(p != maj_p[s]), exact=(s in exact_pair))
    if not grouping_only:
        for k in idx:
            r = ST[stmt[k]]
            if r['kind'] != 'code':
                continue
            toks = words(pats[k])
            fw = r['first_word']
            ev[k].update(
                attr=attr_category(r, origins[k], repo_bases),
                name_first=bool(toks) and fw is not None and toks[0].lower() == fw.lower(),
                name_sev_or_env=any((t in SEVERITY or t in ENVELOPE) and t.lower() not in r['fmt_words'] for t in toks))

    def summarize(keys):
        keys = list(keys)
        N = len(keys)
        if not N:
            return None
        ss = sorted({stmt[k] for k in keys})
        out = dict(events=N, statements=len(ss))
        out['merged_event_share'] = pct(sum(ev[k]['merged'] for k in keys), N)
        out['merged_events'] = sum(ev[k]['merged'] for k in keys)
        out['split_event_share'] = pct(sum(ev[k]['split'] for k in keys), N)
        out['exact_grouping_events'] = pct(sum(ev[k]['exact'] for k in keys), N)
        out['statements_clean'] = pct(sum(s in exact_pair for s in ss), len(ss))
        out['statements_in_merge'] = pct(sum(s in merged_stmt for s in ss), len(ss))
        out['statements_split'] = pct(sum(s in split_stmt for s in ss), len(ss))
        pps = [len(s_p[s]) for s in ss]
        out['patterns_per_statement_mean'] = round(statistics.mean(pps), 2)
        out['patterns_per_statement_max'] = max(pps)
        ck = [k for k in keys if 'attr' in ev[k]]
        if ck:
            C = len(ck)
            for a in ('untyped', 'exact_file', 'same_repo_other_file', 'other_project'):
                out[f'attr_{a}'] = pct(sum(ev[k]['attr'] == a for k in ck), C)
            for m in ('name_first', 'name_sev_or_env'):
                out[m] = pct(sum(ev[k][m] for k in ck), C)
        return out

    res = dict(capture=capture, events=n, labelled=len(idx), excluded_containers=list(exclude),
               distinct_patterns=len(p_s))
    res['overall'] = summarize(idx)
    res['by_group'] = {g: summarize(k for k in idx if group[k] == g)
                       for g in ('source_in_library', 'source_not_in_library', 'not_code')}
    bc = collections.defaultdict(list)
    for k in idx:
        bc[labels[k]['container']].append(k)
    res['by_container'] = {c: summarize(v) for c, v in sorted(bc.items(), key=lambda x: -len(x[1]))}
    merges = []
    for p, c in p_s.items():
        if len(c) > 1:
            tot = sum(c.values())
            merges.append(dict(pattern=p, events=tot, merged_events=tot - c.most_common(1)[0][1],
                               statements=c.most_common()))
    merges.sort(key=lambda m: (-m['merged_events'], -m['events']))
    splits = []
    for s, c in s_p.items():
        if len(c) > 1:
            tot = sum(c.values())
            splits.append(dict(statement=s, events=tot, split_events=tot - c.most_common(1)[0][1],
                               patterns=len(c), top_patterns=c.most_common(5)))
    splits.sort(key=lambda m: (-m['split_events'], -m['events']))
    res['merges'] = merges
    res['splits'] = splits
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('capture', choices=CAPTURES)
    ap.add_argument('events')
    ap.add_argument('--out')
    ap.add_argument('--exclude-container', action='append', default=[])
    ap.add_argument('--grouping-only', action='store_true',
                    help='score grouping only (for a tool that names no origin)')
    a = ap.parse_args()
    res = score(a.capture, a.events, tuple(a.exclude_container), a.grouping_only)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=1)
    o = res['overall']
    print(f"{a.capture}: {res['labelled']} of {res['events']} events labelled"
          f"{' (excluding ' + ', '.join(a.exclude_container) + ')' if a.exclude_container else ''},"
          f" {res['distinct_patterns']} patterns")
    for k, v in o.items():
        print(f'  {k:30s} {v}')


if __name__ == '__main__':
    main()
