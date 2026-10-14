#!/usr/bin/env python3
"""Render results/results-tables.md from the analyze.py outputs."""
import json, os, sys, csv, datetime

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'results')

def hms(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%H:%M:%S')

def kb(n):
    return f'{n/1024:.1f} KB' if n < 1048576 else f'{n/1048576:.2f} MB'

def esc(s, n):
    return s[:n].replace('|', '/').replace('\t', ' ').replace('\n', ' ')

def main():
    out = []
    inc = json.load(open(os.path.join(RESULTS, 'incidents.json')))
    out.append('## Incidents\n')
    out.append('Every container is unlisted in the header-only `caps.csv`, so every hold below took the '
               'fleet default cap and the no-row default action (`rateReceiverDefaultAction offload`). '
               'Holds are counted from the flag turning on to one 4-minute window after it reverted; a '
               'pattern already held in the 10 minutes before the flag (the plan\'s steady moves) is '
               'counted apart as a steady hold.\n')
    out.append('| # | flag | on to off (UTC) | container | first noisy minute | first held minute | noisy to held (min) | events held | events kept (container) | bytes never sent | patterns held (severity) |\n|---|---|---|---|---|---|---|---|---|---|---|')
    noisy_only = []
    for i, a in enumerate(inc, 1):
        rows = [c for c in a['containers'] if c['events_held'] > 0]
        noisy_only += [(i, a, c) for c in a['containers'] if c['events_held'] == 0]
        label = f"{a['flag']} {a['variant']}"
        span = f"{a['on_iso']} to {a['off_iso']}"
        if not rows:
            out.append(f"| {i} | {label} | {span} | (nothing held) | | | | 0 | | | |")
            continue
        for c in rows:
            noisy = '' if c['first_noisy_at'] is None else f"+{c['first_noisy_minute']} ({hms(c['first_noisy_at'])})"
            held = '' if c['first_held_at'] is None else f"+{c['first_held_minute']} ({hms(c['first_held_at'])})"
            n2h = '' if c['noisy_to_held_min'] is None else c['noisy_to_held_min']
            pats = '; '.join(f"{p['name'][:40] or p['pattern']} x{p['events']} ({'/'.join(f'{k}:{v}' for k, v in p['severity'].items())})" for p in c['patterns_held'][:4])
            more = f" +{len(c['patterns_held']) - 4} more" if len(c['patterns_held']) > 4 else ''
            out.append(f"| {i} | {label} | {span} | {c['container']} | {noisy} | {held} | {n2h} | {c['events_held']} | {c['events_kept_container']} | {kb(c['bytes_held'])} ({kb(c['line_bytes_held'])} log text) | {pats}{more} |")
    out.append('')
    steady = [(i, a, c) for i, a in enumerate(inc, 1) for c in a['containers'] if c['steady_held']]
    if steady:
        out.append('Steady holds inside incident spans (patterns held before the flag, the plan\'s moves): ' +
                   '; '.join(f"#{i} {c['container']} {c['steady_held']} events" for i, a, c in steady) + '.\n')
    if noisy_only:
        out.append('Containers that met the 5x rule during an incident but had nothing held: ' +
                   '; '.join(f"#{i} {c['container']} (+{c['first_noisy_minute']} min, {c['noisy_minute_events']} events of {c['noisy_pattern']} vs {c['noisy_pre_rate_per_min']}/min before)" for i, a, c in noisy_only) + '.\n')
    out.append('### Held patterns per incident (samples)\n')
    for i, a in enumerate(inc, 1):
        for c in a['containers']:
            if not c['patterns_held']:
                continue
            out.append(f"**{i}. {a['flag']} / {c['container']}**\n")
            out.append('| pattern | name | events held | severity | sample |\n|---|---|---|---|---|')
            for p in c['patterns_held'][:8]:
                out.append(f"| {p['pattern']} | {esc(p['name'], 50)} | {p['events']} | {'/'.join(f'{k}:{v}' for k, v in p['severity'].items())} | `{esc(p['sample'], 110)}` |")
            out.append('')
    out.append('## Holds outside incident spans (scheduled run)\n')
    rows = list(csv.DictReader(open(os.path.join(RESULTS, 'false-holds.csv'))))
    planned = [r for r in rows if r['planned_move'] == 'yes']
    other = [r for r in rows if r['planned_move'] == 'no']
    if planned:
        out.append('Planned moves (the four patterns the plan tiers down; held by design):\n')
        out.append('| container | pattern | events held | bytes | per minute | sample |\n|---|---|---|---|---|---|')
        for r in planned:
            out.append(f"| {r['container']} | {r['pattern']} | {r['events_held_outside_incidents']} | {int(r['bytes']):,} | {r['per_minute']} | `{esc(r['sample'], 80)}` |")
        out.append('')
    out.append('False holds (any other pattern held while no flag was active):\n')
    if not other:
        out.append('None.\n')
    else:
        out.append('| container | pattern | events held | bytes | per minute | severity | first at (UTC) | sample |\n|---|---|---|---|---|---|---|---|')
        for r in other[:25]:
            out.append(f"| {r['container']} | {r['pattern']} | {r['events_held_outside_incidents']} | {int(r['bytes']):,} | {r['per_minute']} | {r['severity']} | {r['first_at_utc']} | `{esc(r['sample'], 90)}` |")
        out.append('')
    d = json.load(open(os.path.join(RESULTS, 'delivery.json')))
    out.append(f"## Delivery check (final run, {hms(d['span'][0])} to {hms(d['span'][1])} UTC)\n")
    out.append('Raw lines Fluent Bit received against the lines the Receiver returned (pass + offload); '
               'a returned record can cover several raw lines when the Receiver joins a multi-line event.\n')
    out.append('| container | raw lines | returned records | lines covered | covered % |\n|---|---|---|---|---|')
    for c, v in d['containers'].items():
        out.append(f"| {c} | {v['raw_lines']} | {v['returned_records']} | {v['returned_lines']} | {v['returned_pct']} |")
    out.append('')
    open(os.path.join(RESULTS, 'results-tables.md'), 'w').write('\n'.join(out))
    print('wrote', os.path.join(RESULTS, 'results-tables.md'))

if __name__ == '__main__':
    main()
