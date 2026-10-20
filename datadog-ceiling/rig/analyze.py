#!/usr/bin/env python3
"""Every measure of the ceiling run, into results/results.json. Run under rig/ddenv.sh once
Datadog's usage metric has reported the last hour (it lags one to two hours).
Datadog numbers come from datadog.estimated_usage.logs.ingested_events (labelled meter_*);
local numbers come from the rig's capture files (raw, pass, tier_down, offload, other)."""
import calendar, collections, glob, gzip, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')))
sys.path.insert(0, HERE)
import meter  # noqa: E402

W = 240
HOUR = 3600
ERR = {'ERROR', 'CRITICAL', 'FATAL'}


def iso(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


def hh(t):
    return time.strftime('%Y-%m-%dT%H:00Z', time.gmtime(t))


def recs(route):
    """The rig's capture of one route: results/data/<route>.jsonl when present, else the slim
    committed form results/captures/<route>.tsv.gz (rig/slim.py, the same fields)."""
    full = sorted(glob.glob(os.path.join(R, 'data', route + '.jsonl*')))
    if full:
        for p in full:
            for r in meter.records(p):
                k = r.get('kubernetes') or {}
                c = k.get('container_name')
                if not c or 'fb_ts' not in r:
                    continue
                log = r.get('log') or ''
                yield {'c': c, 'ts': float(r['fb_ts']), 'rb': float(r.get('rb_ts') or r['fb_ts']), 'route': route,
                       'h': r.get('tenx_hash'), 'name': r.get('message_pattern'), 'sev': r.get('severity_level'),
                       'lines': sum(1 for x in log.split('\n') if x.strip())}
        return
    p = os.path.join(R, 'captures', route + '.tsv.gz')
    if not os.path.exists(p):
        return
    with gzip.open(p, 'rt') as f:
        next(f)
        for line in f:
            c, fb, rb, h, name, sev, lines = line.rstrip('\n').split('\t')
            yield {'c': c, 'ts': float(fb), 'rb': float(rb or fb), 'route': route, 'h': h or None,
                   'name': name or None, 'sev': sev or None, 'lines': int(lines)}


tl = [json.loads(l) for l in open(os.path.join(R, 'timeline.jsonl')) if l.strip()]
ev = lambda name: [e for e in tl if e['event'] == name]
X = json.load(open(os.path.join(R, 'x.json')))
b0 = [e for e in ev('budget_run') if not e.get('dry_run')][0]['epoch']
end = (ev('run_end') or [{'epoch': time.time()}])[-1]['epoch']
base0 = ev('baseline_start')[0]['epoch']
ret = []
for route in ('pass', 'tier_down', 'offload', 'other'):
    ret.extend(recs(route))
raw = list(recs('raw'))
std = [x for x in ret if x['route'] in ('pass', 'other')]
held = [x for x in ret if x['route'] == 'tier_down']
A = {'x': X}

# The regulator's windows: its counters reset every 240 s from a fixed phase (config
# rate-object-cap.js, rateReceiverResetIntervalMs). The phase is read from the data: a held
# statement goes from tier_down back to pass at each window start.
seq = collections.defaultdict(list)
for x in ret:
    if x['ts'] >= b0 and x['route'] in ('pass', 'tier_down'):
        seq[(x['c'], x['h'])].append((x['ts'], x['route']))
starts = collections.Counter()
for k, v in seq.items():
    v.sort()
    for (t0_, a), (t1_, b) in zip(v, v[1:]):
        if a == 'tier_down' and b == 'pass':
            starts[int(t1_ % W)] += 1
PH = max(range(W), key=lambda p: sum(starts[(p + d) % W] for d in range(0, 4)))
A['window_phase_s'] = {'phase': PH, 'transitions': sum(starts.values()), 'within_4s': sum(starts[(PH + d) % W] for d in range(0, 4))}
win = lambda t: int((t - PH) // W)
wstart = lambda w: w * W + PH

# --- hourly table: the meter and the local capture -------------------------------------
frm = calendar.timegm(time.strptime('2026-10-20T01:00:00Z', '%Y-%m-%dT%H:%M:%SZ'))
if os.environ.get('DD_API_KEY') and os.environ.get('DD_APP_KEY'):
    usage = meter.usage(frm, int(time.time()))
    meter_source = {'read_at': iso(time.time()), 'live': True}
    json.dump({'read_at': meter_source['read_at'], 'hours': usage}, open(os.path.join(R, 'meter-hourly-latest.json'), 'w'), indent=1)
else:
    snap = sorted(glob.glob(os.path.join(R, 'meter-hourly-*.json')))[-1]
    usage = json.load(open(snap))['hours']
    meter_source = {'read_at': json.load(open(snap))['read_at'], 'live': False, 'file': os.path.basename(snap)}
A['meter_source'] = meter_source
loc = collections.defaultdict(collections.Counter)
for x in raw:
    loc[hh(x['ts'])]['raw_lines'] += 1
for x in ret:
    loc[hh(x['rb'])][x['route']] += 1
    if x['c'] == 'frontend':
        loc[hh(x['rb'])]['frontend_' + x['route']] += 1
# allowances, per hour: for every window and every statement that had lines moved in it,
# 5 sample lines, and for an error statement K = 50 more (one node).
win_held = collections.defaultdict(set)
for x in held:
    win_held[win(x['ts'])].add((x['c'], x['h'], x['sev'] in ERR))
allow = collections.Counter()
allow_f = collections.Counter()
for w, s in win_held.items():
    a = sum(5 + (50 if e else 0) for (_, _, e) in s)
    allow[hh(wstart(w))] += a
    allow_f[hh(wstart(w))] += sum(5 + (50 if e else 0) for (c, _, e) in s if c == 'frontend')
rows = []
allowed = X['allowed_events_per_hour']
allowed_f = X['frontend']['allowed_events_per_hour']
for h in sorted(set(usage) | set(loc)):
    u = usage.get(h, {})
    m_main = sum(v for k, v in u.items() if k.startswith('main/'))
    m_flex = sum(v for k, v in u.items() if k.startswith('tenx-offload/'))
    m_check = u.get('main/ceiling-routing-check', 0) + u.get('tenx-offload/ceiling-routing-check', 0)
    t = calendar.timegm(time.strptime(h, '%Y-%m-%dT%H:00Z'))
    phase = 'startup' if t < base0 - 300 else 'baseline' if t < b0 - 300 else 'budget' if t < end else 'after'
    rows.append({'hour': h, 'phase': phase, 'meter_main': m_main, 'meter_tenx_offload': m_flex,
                 'meter_ingested': m_main + m_flex, 'meter_routing_check': m_check,
                 'meter_main_frontend': u.get('main/frontend', 0), 'meter_main_inventory': u.get('main/inventory', 0),
                 'local_raw_lines': loc[h]['raw_lines'], 'local_pass': loc[h]['pass'] + loc[h]['other'],
                 'local_tier_down': loc[h]['tier_down'], 'local_offload': loc[h]['offload'],
                 'local_frontend_pass': loc[h]['frontend_pass'], 'local_frontend_tier_down': loc[h]['frontend_tier_down'],
                 'allowed': allowed, 'allowances': allow[h], 'allowed_plus_allowances': round(allowed + allow[h]),
                 'frontend_allowed': allowed_f, 'frontend_allowances': allow_f[h],
                 'growth_vs_baseline': round((m_main + m_flex) / X['baseline_main_events_per_hour'], 2)})
A['hourly'] = rows

# --- windows: Standard lines per window, whole and by service ---------------------------
wstd = collections.Counter(win(x['ts']) for x in std)
whe = collections.Counter(win(x['ts']) for x in held)
A['windows_budget'] = [{'window': iso(wstart(w)), 'standard': wstd[w], 'tier_down': whe[w]}
                       for w in range(win(b0) + 1, win(end))]

# --- criterion 2: the new statement (the injected service) ------------------------------
inj = ev('inject_start')
if inj:
    i0 = inj[0]['epoch']
    i1 = (ev('inject_stop') or [{'epoch': end}])[0]['epoch']
    rows = []
    for w in range(win(i0), win(i1) + 1):
        p = sum(1 for x in std if x['c'] == 'inventory' and win(x['ts']) == w)
        d = sum(1 for x in held if x['c'] == 'inventory' and win(x['ts']) == w)
        rw = sum(1 for x in raw if x['c'] == 'inventory' and win(x['ts']) == w)
        rows.append({'window': iso(wstart(w)), 'raw': rw, 'standard': p, 'tier_down': d})
    A['new_statement'] = {'service': 'inventory', 'start': iso(i0), 'stop': iso(i1), 'windows': rows,
                          'statements': sorted({x['name'] for x in ret if x['c'] == 'inventory'} - {None})}

# --- criterion 4: error statements per window -------------------------------------------
eps = collections.defaultdict(lambda: collections.Counter())
for x in ret:
    if x['sev'] in ERR and x['ts'] >= b0:
        eps[(x['c'], x['name'], x['sev'])][(win(x['ts']), x['route'])] += 1
err = []
for (c, n, s), cnt in eps.items():
    ws = sorted({w for (w, _) in cnt})
    per = [{'window': iso(wstart(w)), 'standard': cnt[(w, 'pass')] + cnt[(w, 'other')], 'tier_down': cnt[(w, 'tier_down')]} for w in ws]
    storm = [p for p in per if p['tier_down'] > 0]
    err.append({'container': c, 'statement': n, 'level': s, 'windows': len(per),
                'windows_with_lines_moved': len(storm),
                'max_standard_in_a_window': max(p['standard'] for p in per),
                'max_standard_in_a_window_with_lines_moved': max((p['standard'] for p in storm), default=None),
                'total_standard': sum(p['standard'] for p in per), 'total_tier_down': sum(p['tier_down'] for p in per),
                'storm_windows': storm})
A['errors'] = sorted(err, key=lambda e: -e['total_tier_down'])

# --- criterion 3: the budget runs --------------------------------------------------------
runs = []
for e in ev('budget_run'):
    d = os.path.join(R, e['dir'])
    rep = open(os.path.join(d, 'report.txt')).read() if os.path.exists(os.path.join(d, 'report.txt')) else ''
    runs.append({'at': e['at'], 'dry_run': e.get('dry_run'), 'exit': e['exit'], 'commit': e['commit'], 'dir': e['dir'],
                 'lines': [l[len('[tenx-recur] '):] for l in rep.splitlines() if l.startswith('[tenx-recur] ') and 'policy loaded' not in l and not l.startswith('[tenx-recur] actions')]})
A['budget_runs'] = runs

# --- criterion 6: delivery ----------------------------------------------------------------
t0 = ev('receiver_ready')[0]['epoch']
cut = end - 60
rl = collections.Counter(x['c'] for x in raw if t0 <= x['ts'] < cut)
cov = collections.Counter()
for x in ret:
    if t0 <= x['ts'] < cut:
        cov[x['c']] += x['lines']
rl = collections.Counter()
for x in raw:
    if t0 <= x['ts'] < cut:
        rl[x['c']] += x['lines']
# Non-blank lines on both sides: a blank line at the end of a grouped record has no text to
# count. The replay sends every container under one tag, so a multi-line group can take a
# neighbour's line (email lines inside cart and payment records); the totals are unaffected.
A['delivery'] = {'span': [iso(t0), iso(cut)], 'raw_lines': sum(rl.values()), 'lines_covered_by_returned_records': sum(cov.values()),
                 'returned_records': collections.Counter(x['route'] for x in ret),
                 'by_container': {c: {'raw': rl[c], 'covered': cov[c]} for c in sorted(set(rl) | set(cov))}}
sent = sum(1 for x in ret if x['route'] in ('pass', 'tier_down', 'other'))
A['sent_to_datadog_local'] = sent

json.dump(A, open(os.path.join(R, 'results.json'), 'w'), indent=1, default=lambda o: dict(o))
print(json.dumps({'hourly': A['hourly'], 'delivery': {k: v for k, v in A['delivery'].items() if k != 'by_container'}, 'sent': sent}, indent=1, default=lambda o: dict(o)))
