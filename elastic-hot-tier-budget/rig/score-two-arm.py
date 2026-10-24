#!/usr/bin/env python3
"""Scores the two-arm run (research TWO_ARM_METHOD.md) from timeline.jsonl, meter.jsonl[.gz], the feed and
the delivery dumps; writes score.json and prints the tables.
  1. Arm A's hot store (the hot node's index store) at or under 1.10 S at every reading from 20 minutes
     after the step to the end of the hold.
  2. Arm B's hot store above 1.5 x its pre-step level at some reading in the hold. Pre-step level: the
     mean of B's readings in the 20 minutes before the step. If every B reading from 20 minutes after
     the step to the end of the hold is within 1.10 of that level, the run reports "no differentiator".
  3. Delivery by seq: arm B holds one document per line, seq 1 to the feed's last. Arm A's returned
     records carry the seq of one of their lines and their non-blank line count (_lines): per container,
     the records in seq order must split the container's lines, in feed order, into consecutive runs,
     each with exactly its record's count of non-blank lines and containing its record's seq, with no
     non-blank line left over. Records with neither seq nor container are the Receiver's own messages.
  score-two-arm.py <results dir>"""
import collections, gzip, json, os, re, sys

R = sys.argv[1]
tl = [json.loads(l) for l in open(os.path.join(R, 'timeline.jsonl'))]
ev = {}
for e in tl:
    ev.setdefault(e['event'], e)
M = ev['run_start'].get('M', 60)
S = ev['size_set']['hot_tier_gb'] * 1e9
step = ev['phase_step']['epoch']
hold_end = ev['phase_drain']['epoch']
final_seq = ev.get('feed_stop', {}).get('final_seq')
mp = os.path.join(R, 'meter.jsonl')
meter = [json.loads(l) for l in (open(mp) if os.path.exists(mp) else gzip.open(mp + '.gz', 'rt')) if l.strip()]
meter = [m for m in meter if 'summary' in m]


def arm(m, a):
    s = m['summary'][a]
    return s['hot_node_store'], s['streams']


def streams_hot(streams):
    return sum(v['hot_store'] for v in streams.values())


out = {'S': S, 'M': M, 'step_epoch': step, 'hold_end_epoch': hold_end, 'bind': ev.get('s_binds')}
# 1
w1 = [m for m in meter if step + 20 * M <= m['epoch'] <= hold_end]
a1 = [arm(m, 'a')[0] for m in w1]
out['criterion_1'] = {'readings': len(a1), 'max_of_S': round(max(a1) / S, 3), 'mean_of_S': round(sum(a1) / len(a1) / S, 3),
                      'over_1_10': sum(1 for x in a1 if x > 1.10 * S), 'pass': all(x <= 1.10 * S for x in a1),
                      'streams_max_of_S': round(max(streams_hot(arm(m, 'a')[1]) for m in w1) / S, 3)}
# 2
pre = [arm(m, 'b')[0] for m in meter if step - 20 * M <= m['epoch'] < step]
bpre = sum(pre) / len(pre)
hold = [m for m in meter if step <= m['epoch'] <= hold_end]
bh = [arm(m, 'b')[0] for m in hold]
late = [arm(m, 'b')[0] for m in w1]
out['criterion_2'] = {'pre_step_readings': len(pre), 'pre_step_level': bpre, 'pre_step_max': max(pre), 'hold_readings': len(bh),
                      'hold_max': max(bh), 'hold_max_of_pre': round(max(bh) / bpre, 3), 'pass': max(bh) > 1.5 * bpre,
                      'pass_against_pre_step_max': max(bh) > 1.5 * max(pre),
                      'late_hold_max_of_pre': round(max(late) / bpre, 3), 'no_differentiator': all(x <= 1.10 * bpre for x in late)}
# A's pre-step level, reported beside B's
apre = [arm(m, 'a')[0] for m in meter if step - 20 * M <= m['epoch'] < step]
out['a_pre_step_level_of_S'] = round(sum(apre) / len(apre) / S, 3)


# per-stream table
def row(m):
    ha, sa = arm(m, 'a')
    hb, sb = arm(m, 'b')
    g = lambda s, k: s.get(k, {}).get('hot_store', 0)
    return {'at': m['at'], 'min_from_step': round((m['epoch'] - step) / M, 1), 'a_node': ha, 'a_kept': g(sa, 'tenx-app'), 'a_tier_down': g(sa, 'tenx-tierdown'),
            'b_node': hb, 'b_normal': g(sb, 'native-app'), 'b_overflow': g(sb, 'native-overflow')}


before = [m for m in meter if m['epoch'] < step][-1]
picks = [before] + [min((m for m in meter if m['epoch'] >= step + k * M), key=lambda m: m['epoch'], default=None) for k in (20, 40)] + [[m for m in meter if m['epoch'] <= hold_end][-1]]
out['table'] = [row(m) for m in picks if m]
out['peak_hold'] = {'a_node': max(a for a in (arm(m, 'a')[0] for m in hold)), 'b_node': max(bh)}
out['peak_run'] = {'a_node': max(arm(m, 'a')[0] for m in meter), 'b_node': max(arm(m, 'b')[0] for m in meter)}
last = meter[-1]
out['frozen_last_reading'] = {a: {k: {'frozen_indices': v['frozen_indices'], 'frozen_docs': v['frozen_docs'], 'hot_indices': v['hot_indices']} for k, v in arm(last, a)[1].items()} for a in ('a', 'b')}
out['frozen_last_reading_at'] = last['at']

# 3
src = [json.loads(l) for l in open(os.path.join(R, 'replay', 'source.jsonl'))]
rule = json.load(open(os.path.join(R, 'arm-b-rule.json')))
top = set(rule['top_half'])
nb_re = re.compile(r'[^ \t\n\v\f\r]')
nonblank = [sum(1 for l in r['log'].split('\n') if nb_re.search(l)) for r in src]
cont = [r['container_name'].lstrip('/') for r in src]
n_rows = len(src)


def feed(seq):
    return (seq - 1) % n_rows


def load(name):
    p = os.path.join(R, 'delivery', name)
    rows = []
    if os.path.exists(p):
        for l in gzip.open(p, 'rt'):
            seq, c, lines, route, index = l.rstrip('\n').split('\t')
            rows.append((int(seq) if seq else None, c, int(lines) if lines not in ('', 'None') else None, route, index))
    return rows


fb = json.load(open(os.path.join(R, 'fluentbit-metrics.json')))
lines_in = fb['input']['forward.0']['records']
N = final_seq if isinstance(final_seq, int) else lines_in
d = {'feed_final_seq': final_seq, 'fluent_bit_lines_in': lines_in}
# B
b = load('b.tsv.gz')
cnt = collections.Counter(x[0] for x in b)
d['b'] = {'documents': len(b), 'unnumbered': cnt.pop(None, 0), 'missing': sum(1 for s in range(1, N + 1) if s not in cnt),
          'duplicated': sum(1 for v in cnt.values() if v > 1), 'outside_feed': sum(1 for s in cnt if s < 1 or s > N),
          'wrong_container': sum(1 for x in b if x[0] and 1 <= x[0] <= N and x[1] != cont[feed(x[0])]),
          'wrong_stream': sum(1 for x in b if x[0] and 1 <= x[0] <= N and (('native-overflow' in x[4]) != (cont[feed(x[0])] in top))),
          'on_frozen': sum(1 for x in b if x[4].startswith('partial-')), 'on_hot': sum(1 for x in b if not x[4].startswith('partial-'))}
d['b']['pass'] = d['b']['missing'] == 0 and d['b']['unnumbered'] == 0 and d['b']['documents'] >= N
# A
a = load('a.tsv.gz')
recs = []
unnumbered = 0
own_messages = 0
for seq, c, lines, route, index in a:
    if seq is None:
        if c:
            unnumbered += 1
        else:
            own_messages += 1
        continue
    recs.append((seq, lines or 0, c, index))
recs.sort()
dup = sum(1 for k in range(1, len(recs)) if recs[k][0] == recs[k - 1][0])
outside = sum(1 for x in recs if not 1 <= x[0] <= N or cont[feed(x[0])] != x[2])
expected_total = sum(nonblank[feed(s_)] for s_ in range(1, N + 1))
before_first = sum(nonblank[feed(s_)] for s_ in range(1, recs[0][0])) if recs else expected_total
mismatch = []
spanning = 0
for k, (seq, n, c, index) in enumerate(recs):
    nxt = recs[k + 1][0] if k + 1 < len(recs) else N + 1
    run = range(seq, nxt)
    exp = sum(nonblank[feed(x)] for x in run)
    if exp != n:
        mismatch.append((seq, c, n, exp))
    if len({cont[feed(x)] for x in run if nonblank[feed(x)]}) > 1:
        spanning += 1
returned_total = sum(x[1] for x in recs)
d['a'] = {'records': len(a), 'unnumbered': unnumbered, 'receiver_own_messages': own_messages, 'duplicated_seq': dup,
          'records_outside_feed_or_container': outside, 'runs_mismatched': len(mismatch), 'nonblank_lines_before_first_record': before_first,
          'nonblank_lines_sent': expected_total, 'nonblank_lines_returned': returned_total,
          'blank_lines_sent': sum(1 for s_ in range(1, N + 1) if nonblank[feed(s_)] == 0),
          'records_spanning_containers': spanning,
          'on_frozen': sum(1 for x in a if x[4].startswith('partial-')), 'on_hot': sum(1 for x in a if not x[4].startswith('partial-')),
          'tier_down_records': sum(1 for x in a if x[3] == 'tier_down'), 'mismatch_sample': mismatch[:10]}
d['a']['pass'] = (not mismatch and before_first == 0 and dup == 0 and unnumbered == 0 and outside == 0 and expected_total == returned_total)
out['criterion_3'] = d
json.dump(out, open(os.path.join(R, 'score.json'), 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('criterion_1', 'criterion_2', 'criterion_3')}, indent=1))
print('| UTC | min from step | A hot node | A kept | A tier_down | B hot node | B normal | B overflow |')
for r in out['table']:
    print(f"| {r['at'][11:16]} | {r['min_from_step']} | {r['a_node']/1e6:.1f} MB | {r['a_kept']/1e6:.1f} | {r['a_tier_down']/1e6:.1f} | {r['b_node']/1e6:.1f} MB | {r['b_normal']/1e6:.1f} | {r['b_overflow']/1e6:.1f} |")
