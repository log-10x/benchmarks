#!/usr/bin/env python3
"""Scores the run against the criteria in the method. Reads results/meter.jsonl, timeline.jsonl,
cap.out and the local captures (results/data/*.jsonl); with the cluster up (run.sh es-up) it also
runs the retrievability queries. Writes results/summary.json and results/hourly.csv and prints
the tables.
  analyze.py [--no-es]"""
import csv, glob, gzip, json, os, sys, urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')))
ES = os.environ.get('ES_URL', 'http://127.0.0.1:9200')
USE_ES = '--no-es' not in sys.argv
WINDOW = 240

tl = [json.loads(l) for l in open(os.path.join(R, 'timeline.jsonl'))]
ev = {}
for e in tl:
    ev.setdefault(e['event'], e)
T0 = ev['run_start']['epoch']
CAPPED = ev.get('phase_capped', {}).get('epoch')
GROWTH = ev.get('phase_growth', {}).get('epoch')
STORM = ev.get('storm_start')
DRAIN = ev.get('phase_drain', {}).get('epoch')
cap = None
if os.path.exists(os.path.join(R, 'cap.out')):
    lines = open(os.path.join(R, 'cap.out')).read().strip().splitlines()
    cap_info = json.loads(lines[0])
    cap = int(lines[-1])
else:
    cap_info = None


def phase(t):
    if CAPPED is None or t < CAPPED:
        return 'baseline'
    if GROWTH is None or t < GROWTH:
        return 'capped'
    if DRAIN is None or t < DRAIN:
        return 'growth'
    return 'drain'


def records(name):
    for p in sorted(glob.glob(os.path.join(R, 'data', name + '*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt', errors='replace') as f:
            for line in f:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def nonblank(s):
    return sum(1 for x in (s or '').split('\n') if x.strip())


# ---- meter: hot and frozen bytes per reading --------------------------------------------
meter = [json.loads(l) for l in open(os.path.join(R, 'meter.jsonl'))]
rows = []
for m in meter:
    if not isinstance(m.get('indices'), list):
        continue
    hot_app = hot_td = frozen = 0
    docs_app = docs_td_hot = docs_frozen = 0
    for i in m['indices']:
        n, s, d = i['index'], int(i.get('store.size') or 0), int(i.get('docs.count') or 0)
        if n.startswith('partial-'):
            frozen += s; docs_frozen += d
        elif n.startswith('tenx-tierdown-'):
            hot_td += s; docs_td_hot += d
        elif n.startswith('tenx-app-'):
            hot_app += s; docs_app += d
    rows.append({'at': m['at'], 'epoch': m['epoch'], 'h': round((m['epoch'] - T0) / 3600, 2), 'phase': phase(m['epoch']),
                 'hot_app_bytes': hot_app, 'hot_tierdown_bytes': hot_td, 'frozen_local_bytes': frozen,
                 'docs_app': docs_app, 'docs_tierdown_hot': docs_td_hot, 'docs_frozen': docs_frozen,
                 'tierdown_indices_hot': sum(1 for i in m['indices'] if i['index'].startswith('tenx-tierdown-')),
                 'tierdown_indices_frozen': sum(1 for i in m['indices'] if i['index'].startswith('partial-'))})
with open(os.path.join(R, 'hourly.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# ---- criterion 1: residency per tier-down index ------------------------------------------
created, frozen_at, first_doc, store_partial = {}, {}, {}, {}
for m in meter:
    if isinstance(m.get('indices'), list):
        for i in m['indices']:
            base = i['index'].replace('partial-', '')
            if base.startswith('tenx-tierdown-'):
                created.setdefault(base, int(i['creation.date']) / 1000 if not i['index'].startswith('partial-') else None)
                if not i['index'].startswith('partial-') and int(i.get('docs.count') or 0) > 0:
                    first_doc.setdefault(base, m['epoch'])
                if i['index'].startswith('partial-'):
                    store_partial[base] = int(i.get('store.size') or 0)
    ilm = (m.get('ilm') or {}).get('indices') or {}
    for name, x in ilm.items():
        base = name.replace('partial-', '')
        if base.startswith('tenx-tierdown-') and x.get('phase') == 'frozen' and x.get('phase_time_millis'):
            frozen_at.setdefault(base, x['phase_time_millis'] / 1000)
res = []
for base in sorted(created):
    c = created[base]
    fz = frozen_at.get(base)
    res.append({'index': base, 'created': c, 'first_doc_seen_by_meter': first_doc.get(base), 'frozen_at': fz,
                'minutes_creation_to_frozen': round((fz - c) / 60, 1) if (fz and c) else None,
                'partial_local_store_bytes': store_partial.get(base)})
last_reading = meter[-1]['epoch'] if meter else 0
eligible = [x for x in res if x['created'] and x['created'] + 3600 + 1200 <= last_reading]
c1_fail = [x for x in eligible if x['index'] != 'tenx-tierdown-000001' and (x['frozen_at'] is None or x['minutes_creation_to_frozen'] > 80 or (x['partial_local_store_bytes'] or 0) != 0)]

# ---- regulator check on local captures (criterion 2, local half) -------------------------
cells = defaultdict(lambda: {'pass_bytes': 0, 'pass_lines': 0, 'td_bytes': 0, 'td_lines': 0, 'err_pass_lines': 0})
for name, kind in (('pass', 'pass'), ('other', 'pass'), ('tier_down', 'td')):
    for r in records(name):
        try:
            ts = float(r.get('fb_ts') or 0)
        except ValueError:
            continue
        if not ts or CAPPED is None or ts < CAPPED:
            continue
        k = ((r.get('kubernetes') or {}).get('container_name'), r.get('message_pattern') or '', int((ts - CAPPED) // WINDOW))
        b = len((r.get('log') or '').encode('utf-8'))
        c = cells[k]
        c[kind + '_bytes'] += b
        c[kind + '_lines'] += nonblank(r.get('log'))
        if kind == 'pass' and (r.get('severity_level') or '').upper() in ('ERROR', 'CRITICAL', 'FATAL'):
            c['err_pass_lines'] += 1
over = []
for k, c in cells.items():
    if c['td_lines'] and cap is not None:
        # held lines exist, so the cell went over its cap: what passed must be at most the cap
        # plus the 5-line sample and, for error lines, 50 more (by bytes for the cap, by lines for
        # the sample and keep count, so the bound used is cap + the largest 55 lines).
        if c['pass_bytes'] > cap and c['pass_lines'] > 5 + c['err_pass_lines'] and c['err_pass_lines'] <= 50:
            # over the cap by bytes with no sample/keep explanation: recorded, judged below
            over.append({'cell': list(k), **c})

# ---- hourly hot growth ---------------------------------------------------------------------
hourly = []
by_hour = defaultdict(list)
for r in rows:
    by_hour[int(r['h'])].append(r)
prev = None
for h in sorted(by_hour):
    last = by_hour[h][-1]
    if prev is not None:
        hourly.append({'hour': h, 'phase': last['phase'], 'hot_app_growth_bytes': last['hot_app_bytes'] - prev['hot_app_bytes'],
                       'hot_tierdown_bytes_end': last['hot_tierdown_bytes'], 'frozen_local_bytes_end': last['frozen_local_bytes'],
                       'docs_frozen_end': last['docs_frozen'], 'tierdown_indices_frozen_end': last['tierdown_indices_frozen']})
    prev = last

# ---- criterion 4: delivery -------------------------------------------------------------------
raw_lines = sum(nonblank(r.get('log')) for r in records('raw'))
ret_lines = {n: sum(nonblank(r.get('log')) for r in records(n) if 'fb_ts' in r) for n in ('pass', 'tier_down', 'offload', 'other')}
ret_records = {n: sum(1 for r in records(n)) for n in ('pass', 'tier_down', 'offload', 'other')}

# ---- criterion 5: storm ----------------------------------------------------------------------
storm = None
if STORM:
    s0, s1 = STORM['epoch'], STORM['until']
    per_w = defaultdict(lambda: {'pass': 0, 'td': 0})
    for name, kind in (('pass', 'pass'), ('tier_down', 'td')):
        for r in records(name):
            if (r.get('kubernetes') or {}).get('container_name') != 'grafana' or 'Could not register plugin' not in (r.get('log') or ''):
                continue
            ts = float(r.get('fb_ts') or 0)
            if s0 <= ts <= s1 + 60:
                per_w[int((ts - CAPPED) // WINDOW)][kind] += 1
    line_bytes = len(json.load(open(os.path.join(R, 'replay', 'storm-line.json')))['log'].encode())
    allowed = max(5, (cap or 0) // line_bytes) + 50
    storm = {'line_bytes': line_bytes, 'cap_lines_equiv': (cap or 0) // line_bytes, 'allowed_per_window': allowed,
             'windows': [{'w': w, **v} for w, v in sorted(per_w.items())]}

# ---- criterion 3: retrievability (needs the cluster) ----------------------------------------
retr = None
if USE_ES:
    try:
        td_by_hash = defaultdict(int)
        for r in records('tier_down'):
            if r.get('tenx_hash'):
                td_by_hash[r['tenx_hash']] += 1
        top = sorted(td_by_hash.items(), key=lambda x: -x[1])[:10]
        out = []
        for h, n in top:
            q = json.dumps({'query': {'term': {'tenx_hash': h}}}).encode()
            def count(idx):
                req = urllib.request.Request(f'{ES}/{idx}/_count', data=q, headers={'content-type': 'application/json'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read())['count']
            out.append({'tenx_hash': h, 'local': n, 'frozen': count('partial-tenx-tierdown-*'), 'all_tierdown': count('partial-tenx-tierdown-*,tenx-tierdown-*')})
        retr = out
    except Exception as e:
        retr = {'error': str(e)}

summary = {'t0': T0, 'cap': cap_info, 'criterion_1_residency': {'indices': res, 'failures': c1_fail},
           'criterion_2_hourly': hourly, 'criterion_2_cells_over_cap_unexplained': len(over), 'criterion_2_examples': over[:5],
           'criterion_3_retrievability': retr,
           'criterion_4_delivery': {'raw_nonblank_lines': raw_lines, 'returned_nonblank_lines': ret_lines, 'returned_records': ret_records},
           'criterion_5_storm': storm}
json.dump(summary, open(os.path.join(R, 'summary.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != 'criterion_2_examples'}, indent=1)[:12000])
