#!/usr/bin/env python3
"""Arm A's records by the lines they hold (engine ask E103). Reads the feed (replay/source.jsonl: seq s is
row (s - 1) mod rows), the feed's last seq (timeline feed_stop), and every record the Receiver returned, kept
whole by Fluent Bit (data/returned.jsonl, ARM_A_ONLY). Each record's non-blank lines are matched to the
non-blank lines sent: the first at or after the record's seq, each next one the nearest unused sent line with
the same text after the line before it (or, failing that, the nearest unused one before it). A record whose
matched lines came from more than one container is a cross-container record.
Reports: records, cross-container records, non-blank lines sent, matched, missing (sent, in no record) and
unmatched (returned, no unused sent line: a duplicate or a changed line), records whose lines are out of feed
order; beside them, the count the 2026-10-24 README used (records sorted by seq, each the run of seqs up to
the next record's, spanning containers), which assumes lines are grouped in arrival order; and the documents
in Elasticsearch (delivery/a.tsv.gz) with their summed line counts. Exit 1 on any cross-container record,
missing or unmatched line.
  score-e103.py <results dir>
  score-e103.py --self-test <results dir>   regroups the same lines in arrival order at the same record seqs;
                                            the count must equal the run-based count and be above 0"""
import bisect, collections, gzip, json, os, re, sys

NB = re.compile(r'[^ \t\n\v\f\r]')
WINDOW = 200000


def opener(p):
    if os.path.exists(p):
        return open(p)
    return gzip.open(p + '.gz', 'rt')


def load(R):
    src = [json.loads(l) for l in open(os.path.join(R, 'replay', 'source.jsonl'))]
    final = None
    for l in open(os.path.join(R, 'timeline.jsonl')):
        e = json.loads(l)
        if e.get('event') == 'feed_stop':
            final = e.get('final_seq')
    recs, own = [], 0
    with opener(os.path.join(R, 'data', 'returned.jsonl')) as f:
        for l in f:
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get('seq') is None:
                own += 1
                continue
            recs.append((int(r['seq']), (r.get('kubernetes') or {}).get('container_name'), r.get('log') or '', r.get('_lines')))
    return src, final, recs, own


def sent_lines(src, N):
    n = len(src)
    ent = []          # (seq, text, container) per non-blank line, in feed order
    for s in range(1, N + 1):
        r = src[(s - 1) % n]
        c = r['container_name'].lstrip('/')
        for t in r['log'].split('\n'):
            if NB.search(t):
                ent.append((s, t.rstrip(), c))
    return ent


def score(ent, recs, src, N):
    pos = collections.defaultdict(list)
    for i, (_, t, _) in enumerate(ent):
        pos[t].append(i)
    seqs = [e[0] for e in ent]
    used = bytearray(len(ent))

    def take(t, prev):
        p = pos.get(t)
        if not p:
            return None
        k = bisect.bisect_right(p, prev)
        j = k
        while j < len(p) and p[j] - prev <= WINDOW:
            if not used[p[j]]:
                return p[j]
            j += 1
        j = k - 1
        while j >= 0 and prev - p[j] <= WINDOW:
            if not used[p[j]]:
                return p[j]
            j -= 1
        return None

    cross, unmatched, out_of_order, examples = 0, 0, 0, []
    for seq, c, log, _ in sorted(recs, key=lambda x: x[0]):
        prev = bisect.bisect_left(seqs, seq) - 1
        got = []
        for t in log.split('\n'):
            if not NB.search(t):
                continue
            i = take(t.rstrip(), prev)
            if i is None:
                unmatched += 1
                continue
            used[i] = 1
            got.append(i)
            prev = i
        out_of_order += any(got[k] > got[k + 1] for k in range(len(got) - 1))
        if len({ent[i][2] for i in got}) > 1:
            cross += 1
            if len(examples) < 5:
                examples.append({'record_seq': seq, 'filed_under': c, 'lines': [{'seq': ent[i][0], 'container': ent[i][2]} for i in got]})
    return cross, unmatched, out_of_order, examples, used


def run_based(recs, src, N):
    n = len(src)
    nonblank = [sum(1 for l in r['log'].split('\n') if NB.search(l)) for r in src]
    cont = [r['container_name'].lstrip('/') for r in src]
    rs = sorted((s, (ln or 0)) for s, _, _, ln in recs)
    spanning, mismatched = 0, 0
    for k, (s, ln) in enumerate(rs):
        nxt = rs[k + 1][0] if k + 1 < len(rs) else N + 1
        run = range(s, nxt)
        if sum(nonblank[(x - 1) % n] for x in run) != ln:
            mismatched += 1
        if len({cont[(x - 1) % n] for x in run if nonblank[(x - 1) % n]}) > 1:
            spanning += 1
    return spanning, mismatched


def es_side(R):
    p = os.path.join(R, 'delivery', 'a.tsv.gz')
    if not os.path.exists(p):
        return None
    docs = numbered = lines = 0
    for l in gzip.open(p, 'rt'):
        seq, c, ln, route, index = l.rstrip('\n').split('\t')
        docs += 1
        if seq:
            numbered += 1
            lines += int(ln) if ln not in ('', 'None') else 0
    return {'documents': docs, 'numbered_documents': numbered, 'summed_lines': lines}


def main():
    self_test = sys.argv[1] == '--self-test'
    R = sys.argv[2] if self_test else sys.argv[1]
    src, final, recs, own = load(R)
    N = final or max(s for s, *_ in recs)
    ent = sent_lines(src, N)
    if self_test:
        # the same record seqs, each holding every sent line from its seq to the next record's seq
        heads = sorted({s for s, *_ in recs})
        by_seq = collections.defaultdict(list)
        for s, t, c in ent:
            by_seq[s].append(t)
        n = len(src)
        fake = []
        for k, s in enumerate(heads):
            nxt = heads[k + 1] if k + 1 < len(heads) else N + 1
            lines = [t for x in range(s, nxt) for t in by_seq.get(x, [])]
            fake.append((s, src[(s - 1) % n]['container_name'].lstrip('/'), '\n'.join(lines), len(lines)))
        cross, unmatched, ooo, ex, used = score(ent, fake, src, N)
        spanning, mism = run_based(fake, src, N)
        before = sum(1 for s, *_ in ent if s < heads[0])
        missing = len(ent) - sum(used)
        ok = cross == spanning and cross > 0 and unmatched == 0 and missing == before
        print(json.dumps({'self_test': 'PASS' if ok else 'FAIL', 'arrival_order_records': len(fake), 'cross_container_by_lines': cross,
                          'run_based_count': spanning, 'unmatched': unmatched, 'missing': missing, 'lines_before_first_record': before}))
        sys.exit(0 if ok else 1)
    cross, unmatched, ooo, examples, used = score(ent, recs, src, N)
    spanning, mism = run_based(recs, src, N)
    missing = len(ent) - sum(used)
    out = {'feed_final_seq': final, 'records': len(recs), 'receiver_own_messages': own, 'cross_container_records': cross,
           'nonblank_lines_sent': len(ent), 'lines_matched': sum(used), 'lines_missing': missing, 'lines_unmatched': unmatched,
           'records_out_of_feed_order': ooo,
           'readme_run_based_count': spanning, 'readme_runs_mismatched': mism,
           'elasticsearch': es_side(R), 'examples': examples}
    out['verdict'] = 'PASS' if not (cross or missing or unmatched) else 'FAIL'
    json.dump(out, open(os.path.join(R, 'score-e103.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'examples'}, indent=1))
    sys.exit(0 if out['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
