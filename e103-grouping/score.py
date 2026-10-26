#!/usr/bin/env python3
"""E103 scorer. Reads the sender's manifest (one row per line sent: seq, case, container, event) and the
records the Receiver returned (Fluent Bit's file output, one JSON record per line). Each returned record's
message (`log`) is split on "\\n" and each line is matched to the line sent by its token e103id=<seq>.
Reports, per case and in total: records returned, lines returned, cross-container records (a record whose
lines came from more than one sender container), lines missing, lines duplicated; and, as diagnostics, the
stack-trace events returned whole (head and every continuation line in one record holding nothing else)
and the cross-container records by the pause in their episode. When the returned records carry _fb_tag (the
Forward tag they came back under), records whose tag is not tenx.<the tag their first line was sent under>.
Exit status: 0 PASS; 1 FAIL (any cross-container record, missing line, duplicated line or wrong tag); 2 bad input.
  score.py <results dir>        reads sent.jsonl[.gz], returned.jsonl[.gz], in.jsonl[.gz]; writes score.json
  score.py --self-test          checks the verdict on a built clean input and a built broken input"""
import collections, gzip, json, os, re, sys, tempfile

TOKEN = re.compile(r'e103id\W{1,3}(\d+)')


def rows(path):
    for p in (path, path + '.gz'):
        if os.path.exists(p):
            f = gzip.open(p, 'rt') if p.endswith('.gz') else open(p)
            with f:
                for l in f:
                    l = l.strip()
                    if l:
                        try:
                            yield json.loads(l)
                        except ValueError:
                            yield {'_unparsed': l}
            return
    raise FileNotFoundError(path)


def score(R):
    sent = {r['seq']: r for r in rows(os.path.join(R, 'sent.jsonl'))}
    recs = list(rows(os.path.join(R, 'returned.jsonl')))
    try:
        fb_in = sum(1 for r in rows(os.path.join(R, 'in.jsonl')) if 'seq' in r)
    except FileNotFoundError:
        fb_in = None
    cases = sorted({r['case'] for r in sent.values()})
    per = {c: collections.Counter() for c in cases}
    seen = collections.Counter()
    tot = collections.Counter()
    cross, cross_by_pause = [], {c: collections.Counter() for c in cases}
    ev_records = collections.defaultdict(set)   # event -> record indices holding any of its lines
    rec_events = []                              # record index -> set of events
    for i, rec in enumerate(recs):
        msg = rec.get('log')
        if not isinstance(msg, str):
            tot['records_without_log'] += 1
            rec_events.append(set())
            continue
        lines = msg.split('\n')
        seqs = []
        for l in lines:
            m = TOKEN.search(l)
            if m and int(m.group(1)) in sent:
                seqs.append(int(m.group(1)))
            elif l.strip():
                tot['nonblank_lines_without_token'] += 1
        tot['lines_returned'] += len(lines)
        if not seqs:
            tot['records_without_sent_line'] += 1
            rec_events.append(set())
            continue
        for s in seqs:
            seen[s] += 1
        case = sent[seqs[0]]['case']
        per[case]['records'] += 1
        if '_fb_tag' in rec:
            tot['tag_checked'] += 1
            if rec['_fb_tag'] != 'tenx.' + sent[seqs[0]]['tag']:
                per[case]['records_wrong_tag'] += 1
        per[case]['lines_returned'] += len(lines)
        conts = [sent[s]['container'] for s in seqs]
        evs = {sent[s]['event'] for s in seqs}
        rec_events.append(evs)
        for e in evs:
            ev_records[e].add(i)
        if len(set(conts)) > 1:
            per[case]['cross_container_records'] += 1
            per[case]['lines_in_cross_container_records'] += len(seqs)
            cross_by_pause[case][max(sent[s]['pause'] for s in seqs)] += 1
            k = (rec.get('kubernetes') or {}).get('container_name') if isinstance(rec.get('kubernetes'), dict) else None
            cross.append({'case': case, 'filed_under': k, 'record_seq': rec.get('seq'),
                          'lines': [{'seq': s, 'container': sent[s]['container'], 'line': sent[s]['line']} for s in seqs]})
    events = collections.defaultdict(list)
    for s, r in sent.items():
        per[r['case']]['lines_sent'] += 1
        if seen[s] == 0:
            per[r['case']]['lines_missing'] += 1
        elif seen[s] > 1:
            per[r['case']]['lines_duplicated'] += 1
        if r['kind'] == 'trace':
            events[r['event']].append(s)
    for e, ss in events.items():
        c = sent[ss[0]]['case']
        per[c]['trace_events'] += 1
        held = ev_records.get(e, set())
        whole = len(held) == 1 and rec_events[next(iter(held))] == {e} and all(seen[s] == 1 for s in ss)
        per[c]['trace_events_whole'] += int(whole)
    total = collections.Counter()
    for c in cases:
        total.update(per[c])
    total.update({k: v for k, v in tot.items() if k != 'lines_returned'})
    total['records'] += tot['records_without_sent_line'] + tot['records_without_log']
    total['lines_returned'] = tot['lines_returned']
    verdict = 'PASS' if not (total['cross_container_records'] or total['lines_missing'] or total['lines_duplicated'] or total['records_wrong_tag']) else 'FAIL'
    out = {'verdict': verdict, 'records_in_returned_file': len(recs), 'fluent_bit_in_records': fb_in,
           'cases': {c: dict(per[c], cross_container_by_pause_s={str(k): v for k, v in sorted(cross_by_pause[c].items())}) for c in cases},
           'total': dict(total), 'cross_container_examples': cross[:20]}
    return out


KEYS = ['lines_sent', 'records', 'lines_returned', 'cross_container_records', 'lines_in_cross_container_records',
        'lines_missing', 'lines_duplicated', 'records_wrong_tag', 'trace_events', 'trace_events_whole']


def report(out):
    print('| case | ' + ' | '.join(KEYS) + ' | cross by pause (s) |')
    print('|' + '---|' * (len(KEYS) + 2))
    for c, d in out['cases'].items():
        print(f'| {c} | ' + ' | '.join(str(d.get(k, 0)) for k in KEYS) + f" | {json.dumps(d['cross_container_by_pause_s'])} |")
    t = out['total']
    print(f'| total | ' + ' | '.join(str(t.get(k, 0)) for k in KEYS) + ' | |')
    print(json.dumps({k: out[k] for k in ('verdict', 'records_in_returned_file', 'fluent_bit_in_records')} |
                     {k: t.get(k, 0) for k in ('records_without_sent_line', 'records_without_log', 'nonblank_lines_without_token', 'tag_checked')}))


def self_test():
    """A clean input must PASS; the same input with one cross-container record (the README's shape: a
    jaeger head that took kafka's banner lines) must FAIL, and so must one record back under the wrong tag."""
    def build(d, broken, bad_tag=False):
        sent = [(1, 'b', 'b-jaeger', 'b0A', 'single'), (2, 'b', 'b-kafka', 'b0Bbanner', 'banner'), (3, 'b', 'b-kafka', 'b0Bbanner', 'banner'),
                (4, 'd', 'd-orders', 'd0A', 'trace'), (5, 'd', 'd-orders', 'd0A', 'trace')]
        with open(os.path.join(d, 'sent.jsonl'), 'w') as f:
            for s, c, cont, ev, kind in sent:
                f.write(json.dumps({'seq': s, 'case': c, 'ep': 0, 'pause': 0, 'tag': 'app.replay', 'container': cont, 'event': ev, 'kind': kind,
                                    'role': 'head', 'line': f'line e103id={s}'}) + '\n')
        recs = ([['line e103id=1', 'banner e103id=2', 'banner e103id=3']] if broken else [['line e103id=1'], ['banner e103id=2', 'banner e103id=3']])
        recs.append(['head e103id=4', '\tat x e103id=5'])
        with open(os.path.join(d, 'returned.jsonl'), 'w') as f:
            for i, r in enumerate(recs):
                tag = 'tenx.wrong' if bad_tag and i == 0 else 'tenx.app.replay'
                f.write(json.dumps({'log': '\n'.join(r), 'kubernetes': {'container_name': 'x'}, '_fb_tag': tag}) + '\n')
    ok = True
    for name, broken, bad_tag, want in (('clean', False, False, 'PASS'), ('cross-container', True, False, 'FAIL'), ('wrong tag', False, True, 'FAIL')):
        with tempfile.TemporaryDirectory() as d:
            build(d, broken, bad_tag)
            got = score(d)
            print(json.dumps({'input': name, 'want': want, 'got': got['verdict'],
                              'cross_container_records': got['total'].get('cross_container_records', 0),
                              'records_wrong_tag': got['total'].get('records_wrong_tag', 0)}))
            ok &= got['verdict'] == want
    return ok


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        sys.exit(0 if self_test() else 1)
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    try:
        out = score(sys.argv[1])
    except FileNotFoundError as e:
        print(f'missing input: {e}', file=sys.stderr)
        sys.exit(2)
    json.dump(out, open(os.path.join(sys.argv[1], 'score.json'), 'w'), indent=1)
    report(out)
    sys.exit(0 if out['verdict'] == 'PASS' else 1)
