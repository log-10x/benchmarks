#!/usr/bin/env python3
"""Containment demo analysis.

Inputs (under RESULTS):
  data/raw.jsonl       every record Fluent Bit received from the Docker fluentd driver
  data/pass.jsonl      records the Receiver returned with routeState != offload
  data/offload.jsonl   records the Receiver returned with routeState == offload
  scheduler.log        `docker logs -t flagd-ui` (Flag scheduler set/reverted lines)
  timeline.jsonl       phase marks written by run.sh

Outputs (under RESULTS):
  quiet-cells.csv      per (container, pattern, 4-min window) bytes in the quiet run
  fleet-default.json   distribution of those cells and the derived cap
  windows.csv          per (window, container, pattern) pass/offload counts and bytes, scheduled run
  incidents.json       per activation: timing, held/kept, bytes, patterns, severities
  false-holds.csv      offload records while no flag was active
  delivery.json        raw vs returned counts per container
"""
import json, sys, os, re, csv, math, statistics, collections, datetime

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'results')
WINDOW = 240.0
ENGINE_FIELDS = {'tenx_hash', 'routeState', 'message_pattern', 'severity_level', 'date'}

def load(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if 'fb_ts' not in r or 'container_name' not in r:
                continue
            r['_ts'] = float(r['fb_ts'])
            r['_line_bytes'] = len(str(r.get('log', '')).encode('utf-8'))
            # The Receiver's utf8Size() equals the compact JSON of the record as it arrived
            # (smoke 3: summaryBytes / summaryVolume = 147, 152, 231, matching to the byte).
            rec = {k: v for k, v in r.items() if k not in ENGINE_FIELDS and not k.startswith('_')}
            r['_bytes'] = len(json.dumps(rec, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
            out.append(r)
    out.sort(key=lambda r: r['_ts'])
    return out

def marks():
    m = {}
    with open(os.path.join(RESULTS, 'timeline.jsonl')) as f:
        for line in f:
            e = json.loads(line)
            m.setdefault(e['event'], []).append(e)
    return m

def activations():
    """Parse scheduler.log (ingest-time ISO stamp, then the flagd-ui log line)."""
    acts, open_ = [], {}
    pat_set = re.compile(r'^(\S+)\s.*Flag scheduler set (\S+) to (\S+) for (\d+)ms')
    pat_rev = re.compile(r'^(\S+)\s.*Flag scheduler reverted (\S+) to (\S+)')
    pat_seed = re.compile(r'^(\S+)\s.*Flag scheduler started with seed (\d+)')
    seed = None
    with open(os.path.join(RESULTS, 'scheduler.log'), errors='replace') as f:
        for line in f:
            m = pat_seed.match(line)
            if m:
                seed = int(m.group(2)); continue
            m = pat_set.match(line)
            if m:
                ts = iso(m.group(1)); flag, variant, dur = m.group(2), m.group(3), int(m.group(4))
                open_[flag] = {'flag': flag, 'variant': variant, 'on': ts, 'planned_ms': dur, 'off': None}
                acts.append(open_[flag]); continue
            m = pat_rev.match(line)
            if m and m.group(2) in open_:
                open_[m.group(2)]['off'] = iso(m.group(1)); del open_[m.group(2)]
    return seed, acts

def iso(s):
    s = s.rstrip('Z')
    if '.' in s:
        head, frac = s.split('.'); frac = (frac + '000000')[:6]; s = head + '.' + frac
    return datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()

def pattern_of(r):
    return r.get('tenx_hash') or 'nohash'

def pct(vals, p):
    if not vals: return 0
    vals = sorted(vals); k = (len(vals) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return vals[lo] if lo == hi else vals[lo] + (vals[hi] - vals[lo]) * (k - lo)

def quiet_run(passed, offloaded, mk):
    qs, qe = mk['quiet_start'][0]['epoch'], mk['quiet_end'][0]['epoch']
    recs = [r for r in passed + offloaded if qs <= r['_ts'] < qe]
    cells = collections.Counter(); counts = collections.Counter(); sample = {}
    for r in recs:
        w = int((r['_ts'] - qs) // WINDOW)
        key = (r['container_name'], pattern_of(r), w)
        cells[key] += r['_bytes']; counts[key] += 1
        sample.setdefault((r['container_name'], pattern_of(r)), str(r.get('log', ''))[:160])
    full_windows = int((qe - qs) // WINDOW)
    cells_full = {k: v for k, v in cells.items() if k[2] < full_windows}
    with open(os.path.join(RESULTS, 'quiet-cells.csv'), 'w', newline='') as f:
        wr = csv.writer(f); wr.writerow(['container', 'pattern', 'window', 'events', 'bytes', 'sample'])
        for k, v in sorted(cells_full.items(), key=lambda kv: -kv[1]):
            wr.writerow([k[0], k[1], k[2], counts[k], v, sample[(k[0], k[1])]])
    vals = list(cells_full.values())
    top = sorted(cells_full.items(), key=lambda kv: -kv[1])[:10]
    out = {
        'quiet_start': qs, 'quiet_end': qe, 'full_windows': full_windows, 'window_s': WINDOW,
        'events': len(recs), 'cells': len(vals),
        'containers': len({k[0] for k in cells_full}), 'patterns': len({(k[0], k[1]) for k in cells_full}),
        'max': max(vals) if vals else 0, 'p99': pct(vals, 0.99), 'p90': pct(vals, 0.90), 'median': pct(vals, 0.5),
        'cap_2x_max': 2 * max(vals) if vals else 0,
        'top10': [{'container': k[0], 'pattern': k[1], 'window': k[2], 'bytes': v, 'events': counts[k], 'sample': sample[(k[0], k[1])]} for k, v in top],
    }
    json.dump(out, open(os.path.join(RESULTS, 'fleet-default.json'), 'w'), indent=1)
    return out

def per_minute(recs, t0, t1, container):
    """{pattern: {minute_index: count}} for records of one container in [t0, t1)."""
    out = collections.defaultdict(collections.Counter)
    for r in recs:
        if r['container_name'] != container or not (t0 <= r['_ts'] < t1):
            continue
        out[pattern_of(r)][int((r['_ts'] - t0) // 60)] += 1
    return out

def incidents(raw, passed, offloaded, acts, mk, cap):
    sched_start = mk['scheduler_start'][0]['epoch']
    run_end = mk['run_end'][0]['epoch']
    all_ret = passed + offloaded
    containers = sorted({r['container_name'] for r in raw})
    results = []
    for a in acts:
        on, off = a['on'], a['off'] or run_end
        pre0 = max(sched_start, on - 600.0)
        span_end = off + WINDOW   # one regulator window after the flag reverts
        per_container = []
        for c in containers:
            pre = per_minute(raw, pre0, on, c)
            pre_minutes = max(1, int((on - pre0) // 60))
            during = per_minute(raw, on, span_end, c)
            noisy = None
            for pat, mins in during.items():
                pre_rate = sum(pre[pat].values()) / pre_minutes
                for m in sorted(mins):
                    if mins[m] >= 5 and mins[m] >= 5 * pre_rate:
                        if noisy is None or m < noisy[0]:
                            noisy = (m, pat, mins[m], pre_rate)
                        break
            held = [r for r in offloaded if r['container_name'] == c and on <= r['_ts'] < span_end]
            kept = [r for r in passed if r['container_name'] == c and on <= r['_ts'] < span_end]
            if not held and noisy is None:
                continue
            first_held = min((r['_ts'] for r in held), default=None)
            held_by_pat = collections.Counter(pattern_of(r) for r in held)
            sev_by_pat = collections.defaultdict(collections.Counter)
            sample_by_pat = {}
            for r in held:
                sev_by_pat[pattern_of(r)][r.get('severity_level', 'unknown')] += 1
                sample_by_pat.setdefault(pattern_of(r), str(r.get('log', ''))[:160])
            per_container.append({
                'container': c,
                'first_noisy_minute': None if noisy is None else noisy[0],
                'first_noisy_at': None if noisy is None else on + noisy[0] * 60,
                'noisy_pattern': None if noisy is None else noisy[1],
                'noisy_minute_events': None if noisy is None else noisy[2],
                'noisy_pre_rate_per_min': None if noisy is None else round(noisy[3], 2),
                'first_held_at': first_held,
                'noisy_to_held_min': None if (noisy is None or first_held is None) else round((first_held - (on + noisy[0] * 60)) / 60, 2),
                'flag_on_to_held_min': None if first_held is None else round((first_held - on) / 60, 2),
                'events_held': len(held), 'events_kept': len(kept),
                'bytes_held': sum(r['_bytes'] for r in held), 'bytes_kept': sum(r['_bytes'] for r in kept),
                'line_bytes_held': sum(r['_line_bytes'] for r in held), 'line_bytes_kept': sum(r['_line_bytes'] for r in kept),
                'patterns_held': [{'pattern': p, 'events': n, 'severity': dict(sev_by_pat[p]), 'sample': sample_by_pat[p]} for p, n in held_by_pat.most_common()],
            })
        per_container.sort(key=lambda x: -x['bytes_held'])
        results.append({**a, 'on_iso': ts_iso(on), 'off_iso': ts_iso(off), 'span_end': span_end, 'containers': per_container})
    json.dump(results, open(os.path.join(RESULTS, 'incidents.json'), 'w'), indent=1)
    return results

def ts_iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%H:%M:%S')

def windows(raw, passed, offloaded, mk):
    t0 = mk['scheduler_start'][0]['epoch']; t1 = mk['run_end'][0]['epoch']
    agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0])  # raw, pass, offload, bytes_pass, bytes_offload
    for src, recs in (('raw', raw), ('pass', passed), ('offload', offloaded)):
        for r in recs:
            if not (t0 <= r['_ts'] < t1):
                continue
            w = int((r['_ts'] - t0) // WINDOW)
            k = (w, r['container_name'], pattern_of(r) if src != 'raw' else 'raw')
            row = agg[k]
            if src == 'raw': row[0] += 1
            elif src == 'pass': row[1] += 1; row[3] += r['_bytes']
            else: row[2] += 1; row[4] += r['_bytes']
    with open(os.path.join(RESULTS, 'windows.csv'), 'w', newline='') as f:
        wr = csv.writer(f); wr.writerow(['window', 'window_start_utc', 'container', 'pattern', 'raw', 'pass', 'offload', 'bytes_pass', 'bytes_offload'])
        for k in sorted(agg):
            wr.writerow([k[0], ts_iso(t0 + k[0] * WINDOW), k[1], k[2]] + agg[k])
    distinct = collections.defaultdict(set)
    for (w, c, p) in agg:
        if p != 'raw': distinct[(w, c)].add(p)
    return {f'{w}:{c}': len(s) for (w, c), s in sorted(distinct.items())}

def false_holds(offloaded, acts, mk):
    t0 = mk['scheduler_start'][0]['epoch']; t1 = mk['run_end'][0]['epoch']
    spans = [(a['on'], (a['off'] or t1) + WINDOW) for a in acts]
    quiet_s = 0.0
    # quiet seconds = scheduled run minus union of spans
    cuts = sorted(spans); merged = []
    for s, e in cuts:
        if merged and s <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], e)
        else: merged.append([s, e])
    quiet_s = (t1 - t0) - sum(min(e, t1) - max(s, t0) for s, e in merged if e > t0 and s < t1)
    fh = collections.Counter(); sample = {}; first = {}
    for r in offloaded:
        if not (t0 <= r['_ts'] < t1): continue
        if any(s <= r['_ts'] < e for s, e in merged): continue
        k = (r['container_name'], pattern_of(r)); fh[k] += 1
        sample.setdefault(k, str(r.get('log', ''))[:160]); first.setdefault(k, r['_ts'])
    with open(os.path.join(RESULTS, 'false-holds.csv'), 'w', newline='') as f:
        wr = csv.writer(f); wr.writerow(['container', 'pattern', 'events_held_while_quiet', 'per_minute', 'first_at_utc', 'sample'])
        for k, n in fh.most_common():
            wr.writerow([k[0], k[1], n, round(n / max(quiet_s / 60, 1e-9), 3), ts_iso(first[k]), sample[k]])
    return {'quiet_seconds': quiet_s, 'held_while_quiet': sum(fh.values()), 'patterns': len(fh)}

def delivery(raw, passed, offloaded):
    """The Receiver joins continuation lines into one event, so compare raw LINES with the
    lines the returned records cover (newlines inside the returned log field + 1)."""
    out = {}
    for c in sorted({r['container_name'] for r in raw}):
        n_raw = sum(1 for r in raw if r['container_name'] == c)
        ret = [r for r in passed + offloaded if r['container_name'] == c]
        n_ret = len(ret)
        lines = sum(str(r.get('log', '')).count('\n') + 1 for r in ret)
        out[c] = {'raw_lines': n_raw, 'returned_records': n_ret, 'returned_lines': lines,
                  'returned_pct': round(100.0 * lines / n_raw, 2) if n_raw else None}
    json.dump(out, open(os.path.join(RESULTS, 'delivery.json'), 'w'), indent=1)
    return out

def main():
    mk = marks()
    raw = load(os.path.join(RESULTS, 'data', 'raw.jsonl'))
    passed = load(os.path.join(RESULTS, 'data', 'pass.jsonl'))
    offloaded = load(os.path.join(RESULTS, 'data', 'offload.jsonl'))
    print('records: raw', len(raw), 'pass', len(passed), 'offload', len(offloaded))
    if 'quiet_end' in mk:
        q = quiet_run(passed, offloaded, mk)
        print('quiet run: cells', q['cells'], 'max', q['max'], 'p99', round(q['p99']), 'p90', round(q['p90']), 'median', round(q['median']), 'cap', q['cap_2x_max'])
    if 'scheduler_start' in mk and 'run_end' in mk:
        seed, acts = activations()
        cap = [e for e in mk.get('receiver_ready', []) if e.get('cap', 0) > 0]
        cap = cap[-1]['cap'] if cap else 0
        inc = incidents(raw, passed, offloaded, acts, mk, cap)
        d = windows(raw, passed, offloaded, mk)
        fh = false_holds(offloaded, acts, mk)
        print('seed', seed, 'activations', len(acts), 'false holds', fh)
        for i in inc:
            print(i['flag'], i['variant'], i['on_iso'], '->', i['off_iso'], [(c['container'], c['events_held'], c['events_kept'], c['noisy_to_held_min']) for c in i['containers'][:3]])
    print('delivery', delivery(raw, passed, offloaded))

if __name__ == '__main__':
    main()
