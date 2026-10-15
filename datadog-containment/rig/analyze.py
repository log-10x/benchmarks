#!/usr/bin/env python3
"""Containment demo analysis: every measure in results.md, from the run's files.

Inputs (under RESULTS):
  data/raw.jsonl                what Fluent Bit received from the Docker fluentd driver
  data/pass.jsonl               what the Receiver returned with routeState pass
  data/offload.jsonl            ... with routeState offload (the fleet default's action)
  data/tier_down.jsonl          ... with routeState tier_down (the plan's actions.csv rows)
  data/other.jsonl              ... with any other routeState
  timeline.jsonl                phase marks written by run.sh and run-unattended.sh
  scheduler.log                 the flagd-ui scheduler's set / reverted lines
  receiver.log                  docker logs -t of the Receiver
  values-fleet/launch.json      what the Receiver was launched with
  values-fleet/caps.csv         the per-container caps the Receiver read
  planner/poc-envelope.json     the POC's result

Outputs (under RESULTS):
  analysis.json                 every table results.md prints
  quiet-cells.csv               per (container, pattern, 4-minute window) of the quiet run
  held.csv                      one row per (route, container, pattern) held in the scheduled run
  latency-over-10s.csv          every returned record that came back more than 10 s after fb_ts
  windows.csv                   per Receiver window: held and kept per (container, pattern)

Times: fb_ts is the Docker driver's event time for the line (millisecond resolution);
rb_ts is the wall-clock time Fluent Bit's return-path filter received the record back.
The Receiver's 4-minute windows are placed on rb_ts (the Receiver decides a record shortly
before returning it); their phase is read from the data (first pass after a run of holds).
"""
import json, sys, os, re, csv, gzip, math, bisect, collections, datetime, statistics

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
WINDOW = 240.0
ENGINE_FIELDS = {'tenx_hash', 'routeState', 'message_pattern', 'severity_level', 'rb_ts', 'date'}
ROUTES = ('pass', 'offload', 'tier_down', 'other')
HELD = ('offload', 'tier_down', 'other')
ERRORS = ('ERROR', 'CRITICAL', 'FATAL')

# Where each scheduled flag acts, from the demo 3.1.0 source (the service that reads the flag,
# then the services that log its effect).
CAUSAL = {
    'kafkaQueueProblems': ['checkout', 'kafka', 'accounting', 'fraud-detection', 'astronomy-db'],
    'cartFailure': ['cart', 'frontend', 'frontend-proxy', 'checkout'],
    'paymentFailure': ['payment', 'checkout', 'frontend', 'frontend-proxy'],
    'recommendationCacheFailure': ['recommendation', 'frontend'],
    'loadGeneratorFloodHomepage': ['load-generator', 'frontend-proxy', 'frontend', 'product-catalog',
                                   'currency', 'ad', 'recommendation', 'cart', 'image-provider'],
    'emailMemoryLeak': ['email', 'checkout'],
}


def hms(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%H:%M:%S')


def pct(vals, p):
    if not vals:
        return None
    v = sorted(vals)
    k = (len(v) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] if lo == hi else v[lo] + (v[hi] - v[lo]) * (k - lo)


class Rec:
    __slots__ = ('ts', 'rb', 'route', 'c', 'h', 'name', 'sev', 'bytes', 'lines', 'head', 'text')


def load(name, route=None):
    out, samples = [], {}
    p = os.path.join(RESULTS, 'data', name + '.jsonl')
    if not os.path.exists(p) and os.path.exists(p + '.gz'):
        p += '.gz'   # the committed captures
    if not os.path.exists(p):
        return out, samples
    opener = gzip.open if p.endswith('.gz') else open
    with opener(p, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = r.get('kubernetes') or {}
            c = k.get('container_name')
            if 'fb_ts' not in r or not c:
                continue
            x = Rec()
            x.ts = float(r['fb_ts'])
            x.rb = float(r['rb_ts']) if 'rb_ts' in r else None
            x.route = route
            x.c = c
            x.h = r.get('tenx_hash') or 'nohash'
            x.name = r.get('message_pattern') or ''
            x.sev = r.get('severity_level') or 'none'
            body = {kk: v for kk, v in r.items() if kk not in ENGINE_FIELDS}
            x.bytes = len(json.dumps(body, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
            log = str(r.get('log', ''))
            x.lines = log.count('\n') + 1
            x.head = None
            x.text = log
            if (c, x.h) not in samples:
                samples[(c, x.h)] = log[:200]
            out.append(x)
    out.sort(key=lambda x: x.ts)
    return out, samples


def marks():
    m = collections.defaultdict(list)
    for line in open(os.path.join(RESULTS, 'timeline.jsonl')):
        line = line.strip()
        if line:
            e = json.loads(line)
            m[e['event']].append(e)
    return m


def iso(s):
    s = s.rstrip('Z')
    if '.' in s:
        head, frac = s.split('.')
        s = head + '.' + (frac + '000000')[:6]
    return datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()


def activations(t0, t1):
    """scheduler.log: ingest stamp, then the flagd-ui line (which carries its own clock)."""
    acts, open_ = [], {}
    p_set = re.compile(r'^(\S+)\s+(\d\d:\d\d:\d\d\.\d+) \[info\] Flag scheduler set (\S+) to (\S+) for (\d+)ms')
    p_rev = re.compile(r'^(\S+)\s+(\d\d:\d\d:\d\d\.\d+) \[info\] Flag scheduler reverted (\S+) to')
    seed = None
    for line in open(os.path.join(RESULTS, 'scheduler.log'), errors='replace'):
        m = re.search(r'Flag scheduler started with seed (\d+)', line)
        if m:
            seed = int(m.group(1))
        m = p_set.match(line)
        if m:
            day = m.group(1)[:10]
            t = iso(day + 'T' + m.group(2))
            if t0 <= t < t1:
                a = {'flag': m.group(3), 'variant': m.group(4), 'on': t, 'planned_s': int(m.group(5)) / 1000, 'off': None}
                acts.append(a)
                open_[a['flag']] = a
            continue
        m = p_rev.match(line)
        if m and m.group(3) in open_:
            open_[m.group(3)]['off'] = iso(m.group(1)[:10] + 'T' + m.group(2))
            del open_[m.group(3)]
    return seed, acts


def caps_file(path):
    caps = {}
    if os.path.exists(path):
        for row in csv.reader(open(path)):
            if not row or row[0] == 'container':
                continue
            caps[row[0]] = float(row[1].split(':')[0])
    return caps


def window_phase(returned, held_keys):
    """Phase of the Receiver's 4-minute windows on rb_ts: a pattern's first pass after a run
    of holds is a reset. Returns (phase in [0, 240), share of resets within 20 s after it)."""
    by = collections.defaultdict(list)
    for x in returned:
        if (x.c, x.h) in held_keys and x.rb is not None:
            by[(x.c, x.h)].append(x)
    resets = []
    for k, rs in by.items():
        rs.sort(key=lambda x: x.rb)
        prev_held = False
        for x in rs:
            if x.route == 'pass' and prev_held:
                resets.append(x.rb)
            prev_held = x.route in HELD
    if not resets:
        return 0.0, 0.0, 0
    best = (0, -1)
    for p in range(240):
        score = sum(1 for t in resets if (t - p) % WINDOW < 20)
        if score > best[1]:
            best = (p, score)
    return float(best[0]), best[1] / len(resets), len(resets)


def main():
    mk = marks()
    raw, raw_samples = load('raw')
    ret, samples = [], {}
    for route in ROUTES:
        rs, sm = load(route, route)
        ret += rs
        for k, v in sm.items():
            samples.setdefault(k, v)
    for k, v in raw_samples.items():
        samples.setdefault(k, v)
    ret.sort(key=lambda x: x.ts)
    names = {}
    sev_of = collections.defaultdict(collections.Counter)
    for x in ret:
        if x.name:
            names.setdefault((x.c, x.h), x.name)
        sev_of[(x.c, x.h)][x.sev] += 1
    A = {}

    # ---- phases ----
    q0, q1 = mk['quiet_start'][-1]['epoch'], mk['quiet_end'][-1]['epoch']
    fleet_ready = [e for e in mk['receiver_ready'] if 'values-fleet' in e.get('values', '')]
    fr = fleet_ready[-1]['epoch'] if fleet_ready else None
    s0 = mk['scheduler_start'][-1]['epoch'] if 'scheduler_start' in mk else None
    s1 = mk['run_end'][-1]['epoch'] if 'run_end' in mk else max(x.ts for x in raw)
    first_ready = mk['receiver_ready'][0]['epoch']
    A['phases'] = {'quiet': [q0, q1], 'fleet_receiver_ready': fr, 'scheduled': [s0, s1], 'first_receiver_ready': first_ready,
                   'events': {k: [e['at'] for e in v] for k, v in mk.items()}}

    launch = json.load(open(os.path.join(RESULTS, 'values-fleet', 'launch.json')))
    fleet_cap = float(launch['fleet_default_input']['capBytesPerWindowPerNode'])
    caps = caps_file(os.path.join(RESULTS, 'values-fleet', 'caps.csv'))
    cap_for = lambda c: caps.get(c, fleet_cap) if caps.get(c, fleet_cap) != 0 else fleet_cap
    floor, opts = {}, {}
    args = launch['args_from_values']
    for i in range(2, len(args) - 1, 2):
        if args[i] == 'rateReceiverSeverityFloors':
            lv, v = args[i + 1].split('=')
            floor[lv] = float(v)
        else:
            opts[args[i]] = args[i + 1]
    base = int(opts.get('rateReceiverBaselineCount', 5))
    def rule_of(c):
        if c in caps:
            return f'plan row: {c}, cap {caps[c]:,.0f}, tier_down'
        return f"fleet default: {fleet_cap:,.0f}, {opts.get('rateReceiverDefaultAction', 'pass')}"
    A['config'] = {'fleet_cap': fleet_cap, 'caps': caps, 'floors': floor, 'options': opts}

    # ---- quiet run ----
    qrec = [x for x in ret if q0 <= x.ts < q1]
    nwin = int((q1 - q0) // WINDOW)
    qcells = collections.defaultdict(lambda: [0, 0])
    for x in qrec:
        w = int((x.ts - q0) // WINDOW)
        if w < nwin:
            qcells[(x.c, x.h, w)][0] += 1
            qcells[(x.c, x.h, w)][1] += x.bytes
    with open(os.path.join(RESULTS, 'quiet-cells.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['container', 'pattern', 'message_pattern', 'window', 'events', 'record_bytes', 'sample'])
        for k, v in sorted(qcells.items(), key=lambda kv: -kv[1][1]):
            wr.writerow([k[0], k[1], names.get((k[0], k[1]), ''), k[2], v[0], v[1], samples.get((k[0], k[1]), '')[:160]])
    qpair = collections.defaultdict(list)
    for (c, h, w), v in qcells.items():
        qpair[(c, h)].append(v)
    def qstats(c, h):
        v = qpair.get((c, h), [])
        if not v:
            return {'windows_seen': 0, 'max_events': 0, 'max_bytes': 0, 'median_bytes': 0}
        return {'windows_seen': len(v), 'max_events': max(e for e, b in v), 'max_bytes': max(b for e, b in v),
                'median_bytes': statistics.median(b for e, b in v)}
    qraw = collections.Counter(x.c for x in raw if q0 <= x.ts < q1)
    A['quiet'] = {'start': q0, 'end': q1, 'full_windows': nwin, 'records': len(qrec), 'raw_lines': sum(qraw.values()),
                  'containers': len({x.c for x in qrec}), 'pairs': len(qpair),
                  'held_in_quiet': sum(1 for x in qrec if x.route in HELD),
                  'top_pairs': [{'container': c, 'pattern': h, 'name': names.get((c, h), ''), 'rule': rule_of(c),
                                 'max_events': max(e for e, b in v), 'max_bytes': max(b for e, b in v)}
                                for (c, h), v in sorted(qpair.items(), key=lambda kv: (-max(b for e, b in kv[1]), kv[0]))[:20]]}

    # ---- the POC's baseline in the Receiver's unit ----
    env = json.load(open(os.path.join(RESULTS, 'planner', 'poc-envelope.json')))
    d = env.get('data', env)
    fd = d['fleet_default']
    bc = fd.get('baseline_container')
    bn = fd.get('baseline_statement')
    bpairs = [(c, h) for (c, h) in qpair if c == bc and names.get((c, h)) == bn]
    A['baseline_in_receiver_bytes'] = None
    if bpairs:
        c, h = bpairs[0]
        tot = sum(b for (cc, hh, w), (e, b) in qcells.items() if (cc, hh) == (c, h))
        A['baseline_in_receiver_bytes'] = {'container': c, 'pattern': h, 'name': bn,
                                           'avg_record_bytes_per_window': tot / max(nwin, 1),
                                           'max_record_bytes_per_window': max(b for e, b in qpair[(c, h)]),
                                           'mcp_baseline_bytes_per_window': fd.get('baseline_bytes_per_window_per_node')}

    if s0 is None:
        json.dump(A, open(os.path.join(RESULTS, 'analysis.json'), 'w'), indent=1, default=str)
        print('quiet only')
        return

    # ---- scheduled run ----
    seed, acts = activations(s0, s1)
    for i, x in enumerate(acts):
        x['off_eff'] = x['off'] if x['off'] else s1
        nxt = acts[i + 1]['on'] if i + 1 < len(acts) else s1
        x['span_end'] = min(x['off_eff'] + WINDOW, nxt, s1)
    A['seed'] = seed
    A['activations'] = [{'n': i + 1, 'flag': x['flag'], 'variant': x['variant'], 'on': x['on'], 'off': x['off'],
                         'planned_s': x['planned_s'], 'actual_s': (x['off_eff'] - x['on']), 'span_end': x['span_end']}
                        for i, x in enumerate(acts)]

    S = [x for x in ret if s0 <= x.ts < s1]
    SR = [x for x in raw if s0 <= x.ts < s1]
    held_keys = {(x.c, x.h) for x in ret if x.route in HELD and x.ts >= (fr or s0)}
    inferred, phase_fit, nresets = window_phase([x for x in ret if x.ts >= (fr or s0)], held_keys)
    # The windows start at the Forward client's connection to the fleet Receiver.
    connect = None
    rl = os.path.join(RESULTS, 'receiver.log')
    if os.path.exists(rl):
        for line in open(rl, errors='replace'):
            if 'client connected to Forward protocol input' in line:
                connect = iso(line.split()[0])
                break
    phase = (connect % WINDOW) if connect else inferred
    A['window_phase'] = {'phase_s_mod_240': phase, 'source': 'receiver.log connect' if connect else 'inferred',
                         'connect': connect, 'inferred_phase': inferred, 'share_of_resets_within_20s_of_inferred': phase_fit, 'resets': nresets}
    widx = lambda t: int((t - phase) // WINDOW)
    wstart = lambda i: i * WINDOW + phase

    def causal_flags(x):
        return [a['flag'] for a in acts if a['on'] <= x.ts < a['span_end'] and x.c in CAUSAL.get(a['flag'], [])]

    # held summary per (route, container, pattern)
    g = collections.defaultdict(list)
    for x in S:
        if x.route in HELD:
            g[(x.route, x.c, x.h)].append(x)
    held_rows = []
    for (route, c, h), rs in sorted(g.items(), key=lambda kv: (kv[0][0], kv[0][1], -len(kv[1]))):
        inside = [x for x in rs if causal_flags(x)]
        flags = collections.Counter(f for x in rs for f in causal_flags(x))
        sev = collections.Counter(x.sev for x in rs)
        held_rows.append({'route': route, 'rule': rule_of(c), 'container': c, 'pattern': h, 'name': names.get((c, h), ''), 'held': len(rs),
                          'held_bytes': sum(x.bytes for x in rs), 'held_lines': sum(x.lines for x in rs),
                          'severity': dict(sev), 'in_causal_span': len(inside), 'outside': len(rs) - len(inside),
                          'flags': dict(flags), 'windows': len({widx(x.rb or x.ts) for x in rs}),
                          'first': rs[0].ts, 'last': rs[-1].ts, 'listed_in_caps': c in caps,
                          'quiet': qstats(c, h), 'sample': samples.get((c, h), '')[:160]})
    A['held'] = held_rows
    with open(os.path.join(RESULTS, 'held.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        cols = ['route', 'rule', 'container', 'pattern', 'name', 'held', 'held_bytes', 'held_lines', 'in_causal_span', 'outside', 'windows', 'listed_in_caps']
        wr.writerow(cols + ['severity', 'flags', 'first_utc', 'last_utc', 'quiet_max_events', 'quiet_max_bytes', 'sample'])
        for r in held_rows:
            wr.writerow([r[k] for k in cols] + ['/'.join(f'{k}:{v}' for k, v in r['severity'].items()),
                                                 '/'.join(f'{k}:{v}' for k, v in r['flags'].items()), hms(r['first']), hms(r['last']),
                                                 r['quiet']['max_events'], r['quiet']['max_bytes'], r['sample']])

    # per activation
    per_act = []
    for i, a in enumerate(acts):
        on, end = a['on'], a['span_end']
        pre0 = max(on - 600.0, fr or s0)
        span = [x for x in S if on <= x.ts < end]
        pre = [x for x in ret if pre0 <= x.ts < on]
        pre_held = {(x.c, x.h) for x in pre if x.route in HELD}
        pre_rate = collections.Counter((x.c, x.h) for x in pre)
        pre_min = max(1.0, (on - pre0) / 60)
        rows = []
        for c in sorted({x.c for x in span}):
            cs = [x for x in span if x.c == c]
            per_min = collections.Counter((x.h, int((x.ts - on) // 60)) for x in cs)
            noisy = None
            for (h, m), n in sorted(per_min.items(), key=lambda kv: kv[0][1]):
                rate = pre_rate[(c, h)] / pre_min
                if n >= 5 and n >= 5 * rate:
                    if noisy is None or m < noisy[1]:
                        noisy = (h, m, n, rate)
            new_held = [x for x in cs if x.route in HELD and (c, x.h) not in pre_held]
            steady_held = [x for x in cs if x.route in HELD and (c, x.h) in pre_held]
            if not new_held and noisy is None:
                continue
            hp = {x.h for x in new_held}
            kept = [x for x in cs if x.route == 'pass' and x.h in hp]
            first_noisy = None
            if noisy:
                first_noisy = min(x.ts for x in cs if x.h == noisy[0] and int((x.ts - on) // 60) == noisy[1])
            pats = []
            for h in sorted(hp, key=lambda h: (-sum(1 for x in new_held if x.h == h), h)):
                hs = [x for x in new_held if x.h == h]
                ks = [x for x in kept if x.h == h]
                pats.append({'pattern': h, 'rule': rule_of(c), 'name': names.get((c, h), ''), 'held': len(hs), 'kept': len(ks),
                             'routes': dict(collections.Counter(x.route for x in hs)), 'severity': dict(collections.Counter(x.sev for x in hs)),
                             'bytes': sum(x.bytes for x in hs), 'first_held': hs[0].ts, 'last_held': hs[-1].ts,
                             'first_seen': min(x.ts for x in cs if x.h == h), 'sample': samples.get((c, h), '')[:160]})
            rows.append({'container': c, 'rule': rule_of(c), 'in_causal_path': c in CAUSAL.get(a['flag'], []),
                         'first_noisy': first_noisy, 'noisy_pattern': noisy[0] if noisy else None,
                         'noisy_name': names.get((c, noisy[0]), '') if noisy else None,
                         'noisy_events_in_minute': noisy[2] if noisy else None, 'noisy_pre_rate_per_min': round(noisy[3], 2) if noisy else None,
                         'first_held': new_held[0].ts if new_held else None,
                         'noisy_to_held_s': (new_held[0].ts - first_noisy) if (new_held and first_noisy) else None, 'first_held_route': new_held[0].route if new_held else None,
                         'held': len(new_held), 'held_bytes': sum(x.bytes for x in new_held),
                         'held_offload': sum(1 for x in new_held if x.route == 'offload'), 'held_tier_down': sum(1 for x in new_held if x.route == 'tier_down'),
                         'kept_same_patterns': len(kept), 'kept_container': sum(1 for x in cs if x.route == 'pass'),
                         'steady_held': len(steady_held), 'steady_held_bytes': sum(x.bytes for x in steady_held),
                         'steady_patterns': dict(collections.Counter(names.get((c, x.h), x.h) for x in steady_held).most_common(4)),
                         'patterns': pats})
        rows.sort(key=lambda r: (-r['held'], r['container']))
        per_act.append({'n': i + 1, 'flag': a['flag'], 'variant': a['variant'], 'on': on, 'off': a['off'], 'span_end': end, 'containers': rows})
    A['per_activation'] = per_act

    # per Receiver window: held / kept per (container, pattern), for every pair held at least once
    wtab = collections.defaultdict(lambda: [0, 0, 0])  # pass, offload, tier_down
    for x in S:
        if (x.c, x.h) in held_keys and x.rb is not None:
            k = (widx(x.rb), x.c, x.h)
            wtab[k][0 if x.route == 'pass' else (1 if x.route == 'offload' else 2)] += 1
    with open(os.path.join(RESULTS, 'windows.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['window_start_utc', 'flags_in_window', 'container', 'pattern', 'name', 'pass', 'offload', 'tier_down'])
        for (w, c, h), v in sorted(wtab.items()):
            fl = ','.join(sorted({a['flag'] for a in acts if a['on'] < wstart(w) + WINDOW and a['off_eff'] > wstart(w)})) or 'none'
            wr.writerow([hms(wstart(w)), fl, c, h, names.get((c, h), ''), *v])

    # the plan's own moves: tier_down per container per Receiver window
    td = collections.defaultdict(collections.Counter)
    for x in S:
        if x.route == 'tier_down':
            td[x.c][widx(x.rb or x.ts)] += 1
    A['plan_moves_per_window'] = {c: {'windows': len(v), 'median': statistics.median(v.values()), 'max': max(v.values()), 'total': sum(v.values())}
                                  for c, v in td.items()}

    # errors against the floor: over-cap records of ERROR / CRITICAL patterns, replayed per
    # Receiver window in rb_ts order (first rateReceiverBaselineCount always pass, then pass
    # while the window's bytes stay at or under the cap; the rest are over the cap).
    cells = collections.defaultdict(list)
    for x in ret:
        if x.ts >= (fr or s0) and x.rb is not None and x.ts < s1:
            cells[(x.c, x.name or x.h, widx(x.rb))].append(x)   # the regulator's key: message_pattern @ container
    over = collections.defaultdict(lambda: collections.Counter())
    replay_held = 0
    replay_match = collections.Counter()
    for (c, h, w), rs in cells.items():
        rs.sort(key=lambda x: x.rb)
        cum, cap = 0, cap_for(c)
        for n, x in enumerate(rs):
            is_over = not (n < base or cum + x.bytes <= cap)
            cum += x.bytes
            if x.ts < s0:
                continue
            if is_over:
                over[x.sev][x.route] += 1
                replay_match['over_and_' + ('held' if x.route in HELD else 'passed')] += 1
            else:
                replay_match['under_and_' + ('held' if x.route in HELD else 'passed')] += 1
    A['floor_check'] = {sev: dict(v) for sev, v in over.items()}
    A['replay_vs_actual'] = dict(replay_match)
    err_held = [x for x in S if x.route in HELD and x.sev in ERRORS]
    err_pass = [x for x in S if x.route == 'pass' and x.sev in ERRORS]
    eh = collections.defaultdict(lambda: collections.Counter())
    for x in err_held:
        eh[(x.c, x.h, x.sev)][x.route] += 1
    ep = collections.Counter((x.c, x.h, x.sev) for x in err_pass)
    A['errors'] = {'held': len(err_held), 'passed': len(err_pass),
                   'by_pattern': [{'container': c, 'rule': rule_of(c), 'pattern': h, 'name': names.get((c, h), ''), 'severity': s, 'held': dict(v), 'passed': ep[(c, h, s)],
                                   'flags': dict(collections.Counter(f for x in err_held if (x.c, x.h) == (c, h) for f in causal_flags(x)))}
                                  for (c, h, s), v in sorted(eh.items(), key=lambda kv: -sum(kv[1].values()))]}

    # latency: every returned record of the Receiver runs, rb_ts - fb_ts
    lat = collections.defaultdict(list)
    slow = []
    for x in ret:
        if x.rb is None or x.ts < first_ready:
            continue
        dlt = x.rb - x.ts
        lat[x.c].append(dlt)
        if dlt > 10:
            slow.append((x, dlt))
    A['latency'] = {c: {'records': len(v), 'median': pct(v, 0.5), 'p99': pct(v, 0.99), 'max': max(v), 'over_10s': sum(1 for d in v if d > 10)}
                    for c, v in sorted(lat.items())}
    allv = [d for v in lat.values() for d in v]
    A['latency_all'] = {'records': len(allv), 'median': pct(allv, 0.5), 'p99': pct(allv, 0.99), 'max': max(allv) if allv else None,
                        'over_10s': len(slow)}
    with open(os.path.join(RESULTS, 'latency-over-10s.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['container', 'fb_ts_utc', 'rb_ts_utc', 'seconds', 'route', 'lines_in_record', 'pattern', 'name', 'sample'])
        for x, dlt in sorted(slow, key=lambda s: s[0].ts):
            wr.writerow([x.c, hms(x.ts), hms(x.rb), round(dlt, 3), x.route, x.lines, x.h, names.get((x.c, x.h), ''), samples.get((x.c, x.h), '')[:100]])
    A['latency_over_10s_by_container'] = dict(collections.Counter(x.c for x, d in slow))

    # Each returned record against the raw lines it covers. The Receiver joins consecutive lines
    # of one source (the forwarder tag, here one container) into a record, in order, so a
    # record's first line is found by its time and text and its last line is lines - 1 further.
    raw_by_c = collections.defaultdict(list)
    for x in raw:
        raw_by_c[x.c].append(x)
    pos = {}
    for c, rs in raw_by_c.items():
        for i, x in enumerate(rs):
            pos.setdefault((c, x.ts, x.text), i)
    def last_index(x):
        i = pos.get((x.c, x.ts, x.text.split('\n')[0]))
        if i is None:
            return None
        j = i + x.lines - 1
        return j if j < len(raw_by_c[x.c]) else None

    # scheduled phase alone, and what the records over 10 s waited for
    lat_s = collections.defaultdict(list)
    wait = collections.Counter()
    after_next = []
    for x in ret:
        if x.rb is None or not (s0 <= x.ts < s1):
            continue
        dlt = x.rb - x.ts
        lat_s[x.c].append(dlt)
        if dlt > 10:
            j = last_index(x)
            rl = raw_by_c[x.c]
            if j is None:
                wait['not aligned to raw lines'] += 1
            elif j + 1 >= len(rl) or rl[j + 1].ts > x.rb + 1:
                wait['back before its container wrote again'] += 1
            elif x.rb - rl[j + 1].ts <= 5:
                wait['back within 5 s after its container\'s next line'] += 1
                after_next.append(x.rb - rl[j + 1].ts)
            else:
                wait['back more than 5 s after its container\'s next line'] += 1
    A['latency_scheduled'] = {c: {'records': len(v), 'median': pct(v, 0.5), 'p99': pct(v, 0.99), 'max': max(v), 'over_10s': sum(1 for d in v if d > 10)}
                              for c, v in sorted(lat_s.items())}
    alls = [d for v in lat_s.values() for d in v]
    A['latency_scheduled_all'] = {'records': len(alls), 'median': pct(alls, 0.5), 'p99': pct(alls, 0.99), 'max': max(alls) if alls else None,
                                  'over_10s': sum(1 for d in alls if d > 10)}
    A['latency_over_10s_wait'] = {'over_10s': sum(wait.values()), 'by_cause': dict(wait), 'median_s_after_next_line': pct(after_next, 0.5)}
    by_phase = collections.Counter()
    for x, dlt in slow:
        by_phase['before the quiet run' if x.ts < q0 else 'quiet run' if x.ts < q1 else 'between quiet end and scheduler start' if x.ts < s0 else 'scheduled run' if x.ts < s1 else 'after run end'] += 1
    A['latency_over_10s_by_phase'] = dict(by_phase)

    # Release after a source goes quiet: records of the scheduled run whose container wrote
    # nothing for at least 10 s after the record's last line, so only a timer could release
    # them; seconds from that last line to rb_ts.
    rel = collections.defaultdict(list)
    waited = collections.Counter()
    for x in ret:
        if x.rb is None or not (s0 <= x.ts < s1):
            continue
        j = last_index(x)
        if j is None:
            continue
        rl = raw_by_c[x.c]
        nxt = rl[j + 1].ts if j + 1 < len(rl) else s1
        if nxt - rl[j].ts >= 10:
            if x.rb < nxt:
                rel[x.c].append(x.rb - rl[j].ts)
            else:
                waited[x.c] += 1
    allr = [d for v in rel.values() for d in v]
    A['release_after_quiet'] = {'all': {'records': len(allr), 'median': pct(allr, 0.5), 'p99': pct(allr, 0.99), 'min': min(allr) if allr else None, 'max': max(allr) if allr else None,
                                        'waited_for_next_line': sum(waited.values())},
                                'waited_for_next_line': dict(waited),
                                'containers': {c: {'records': len(v), 'median': pct(v, 0.5), 'max': max(v)} for c, v in sorted(rel.items())}}

    # Multi-line events closed by a source's own pause. A line kind the Receiver joins to the
    # record before it anywhere in the run is not a group head; a record that begins with such
    # a line was opened after the source's previous group had been sealed by something other
    # than a head line, which in a running demo is the per-source flush timer. Each such record
    # is set against the record before it from the same container: the pause is from that
    # record's last raw line to this record's first.
    ANSI = re.compile(r'\x1b\[[0-9;]*m')
    def kind(line):
        return re.sub(r'[0-9a-fA-F]{4,}|\d+', '0', ANSI.sub('', line).rstrip())[:48]
    rr = sorted((x for x in ret if first_ready <= x.ts < s1), key=lambda x: (x.ts, x.rb or 0))
    by_c = collections.defaultdict(list)
    for x in rr:
        by_c[x.c].append(x)
    inner = collections.defaultdict(collections.Counter)
    for c, rs in by_c.items():
        for x in rs:
            for l in x.text.split('\n')[1:]:
                inner[c][kind(l)] += 1
    splits = []
    for c, rs in by_c.items():
        for a, b in zip(rs, rs[1:]):
            k = kind(b.text.split('\n')[0])
            if not k.strip() or not inner[c][k]:
                continue   # a blank line is left out: the Receiver both opens and joins on one
            j = last_index(a)
            a_last = raw_by_c[c][j].ts if j is not None else None
            splits.append({'container': c, 'at': b.ts, 'phase': 'scheduled' if b.ts >= s0 else 'before the scheduled run',
                           'receiver_restart_between': bool(fr and a.ts < fr <= b.ts),
                           'prev_pattern': a.name or a.h, 'prev_lines': a.lines, 'pattern': b.name or b.h, 'lines': b.lines,
                           'same_pattern': (a.name or a.h) == (b.name or b.h),
                           'first_line_kind': k, 'joined_elsewhere': inner[c][k],
                           'pause_s': (b.ts - a_last) if a_last is not None else None, 'from_prev_first_line_s': b.ts - a.ts,
                           'route': b.route, 'first_line': ANSI.sub('', b.text.split('\n')[0])[:120]})
    def bucket(p):
        return 'unaligned' if p is None else 'under 3 s' if p < 3 else '3 to 5 s' if p < 5 else '5 to 7 s' if p <= 7 else 'over 7 s'
    sched = [r for r in splits if r['phase'] == 'scheduled' and not r['receiver_restart_between']]
    groups = collections.defaultdict(list)
    for r in sched:
        groups[(r['container'], r['prev_pattern'], r['first_line_kind'])].append(r)
    A['early_close'] = {
        'scheduled_records_opened_by_a_non_head_line': len(sched),
        'by_pause': dict(collections.Counter(bucket(r['pause_s']) for r in sched)),
        'within_7s_of_prev_first_line': sum(1 for r in sched if r['from_prev_first_line_s'] <= 7),
        'within_7s_same_pattern': sum(1 for r in sched if r['from_prev_first_line_s'] <= 7 and r['same_pattern']),
        'whole_run_records_opened_by_a_non_head_line': len(splits),
        'groups': sorted(({'container': c, 'prev_pattern': pp, 'first_line_kind': k, 'records': len(v),
                           'by_pause': dict(collections.Counter(bucket(r['pause_s']) for r in v)),
                           'within_7s': sum(1 for r in v if r['pause_s'] is not None and r['pause_s'] <= 7),
                           'same_pattern': sum(1 for r in v if r['same_pattern']),
                           'pause_min_s': min((r['pause_s'] for r in v if r['pause_s'] is not None), default=None),
                           'example_at': v[0]['at'], 'example_line': v[0]['first_line'], 'example_pattern': v[0]['pattern']}
                          for (c, pp, k), v in groups.items()), key=lambda g: (-g['within_7s'], -g['records']))}
    with open(os.path.join(RESULTS, 'early-close.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        cols = ['container', 'at', 'phase', 'receiver_restart_between', 'pause_s', 'from_prev_first_line_s', 'prev_pattern', 'prev_lines', 'pattern', 'lines', 'same_pattern', 'route', 'joined_elsewhere', 'first_line']
        wr.writerow(cols)
        for r in splits:
            wr.writerow([hms(r['at']) if k == 'at' else (round(r[k], 3) if isinstance(r[k], float) else r[k]) for k in cols])

    # delivery: raw lines against the lines the returned records cover, whole run and scheduled run
    def delivery(t0, t1):
        rl = collections.Counter(x.c for x in raw if t0 <= x.ts < t1)
        rr = collections.Counter()
        cov = collections.Counter()
        byroute = collections.defaultdict(collections.Counter)
        for x in ret:
            if t0 <= x.ts < t1:
                rr[x.c] += 1
                cov[x.c] += x.lines
                byroute[x.c][x.route] += 1
        return {c: {'raw_lines': rl[c], 'returned_records': rr[c], 'lines_covered': cov[c], 'routes': dict(byroute[c]),
                    'covered_minus_raw': cov[c] - rl[c]} for c in sorted(set(rl) | set(rr))}
    A['delivery_whole_run'] = {'span': [first_ready, s1], 'containers': delivery(first_ready, s1)}
    A['delivery_scheduled'] = {'span': [s0, s1], 'containers': delivery(s0, s1)}
    def tail_cov(t0, t1):
        rl = sum(1 for x in raw if t0 <= x.ts < t1)
        cv = sum(x.lines for x in ret if t0 <= x.ts < t1)
        return {'raw_lines': rl, 'lines_covered': cv}
    A['delivery_split'] = {'to_60s_before_stop': tail_cov(first_ready, s1 - 60), 'last_60s': tail_cov(s1 - 60, s1)}
    A['totals_scheduled'] = {'raw_lines': len(SR), 'returned': len(S), 'routes': dict(collections.Counter(x.route for x in S)),
                             'bytes_by_route': {r: sum(x.bytes for x in S if x.route == r) for r in ROUTES}}

    # what-if: the fleet default alone (the install seed, no plan rows), same replay
    wi = collections.Counter()
    for (c, h, w), rs in cells.items():
        cum = 0
        for n, x in enumerate(rs):
            is_over = not (n < base or cum + x.bytes <= fleet_cap)
            cum += x.bytes
            if is_over and x.ts >= s0:
                f = floor.get(x.sev, 0.0)
                wi['held_expected'] += (1 - f)
                wi['held_expected_in_causal_span'] += (1 - f) if causal_flags(x) else 0
                wi['held_expected_errors'] += (1 - f) if x.sev in ERRORS else 0
    A['what_if_fleet_default_alone'] = {k: round(v, 1) for k, v in wi.items()}

    json.dump(A, open(os.path.join(RESULTS, 'analysis.json'), 'w'), indent=1, default=str)
    print('raw', len(raw), 'returned', len(ret), 'scheduled returned', len(S), 'routes', dict(collections.Counter(x.route for x in S)))
    print('activations', len(acts), 'phase', A['window_phase'])


if __name__ == '__main__':
    main()
