#!/usr/bin/env python3
"""Render results/results-tables.md from the analyze.py outputs."""
import json, os, sys, csv, datetime

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'results')

def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def kb(n):
    return f'{n/1024:.1f} KB' if n < 1048576 else f'{n/1048576:.2f} MB'

def main():
    out = []
    fd = json.load(open(os.path.join(RESULTS, 'fleet-default.json')))
    out.append('## Fleet default\n')
    out.append(f"Quiet run {iso(fd['quiet_start'])} to {iso(fd['quiet_end'])} UTC, {fd['full_windows']} full windows of {int(fd['window_s'])} s, "
               f"{fd['events']} events, {fd['containers']} containers, {fd['patterns']} (container, pattern) pairs, {fd['cells']} cells.\n")
    out.append('| Cell statistic (bytes per pattern per container per 4-minute window) | Value |\n|---|---|')
    for k in ('max', 'p99', 'p90', 'median'):
        out.append(f"| {k} | {int(round(fd[k]))} |")
    out.append(f"| **cap = 2 x max** | **{fd['cap_2x_max']}** |\n")
    out.append('Largest cells in the quiet run:\n')
    out.append('| container | pattern | window | events | bytes | sample |\n|---|---|---|---|---|---|')
    for t in fd['top10']:
        out.append(f"| {t['container']} | {t['pattern']} | {t['window']} | {t['events']} | {t['bytes']} | `{t['sample'][:90].replace('|', '/')}` |")
    out.append('')
    inc = json.load(open(os.path.join(RESULTS, 'incidents.json')))
    out.append('## Incidents\n')
    out.append('| # | flag | variant | on (UTC) | off (UTC) | container | first noisy minute | first held | noisy to held (min) | events held | events kept | bytes never sent | patterns held |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for i, a in enumerate(inc, 1):
        if not a['containers']:
            out.append(f"| {i} | {a['flag']} | {a['variant']} | {a['on_iso']} | {a['off_iso']} | (no container met the 5x rule and nothing was held) | | | | | | | |")
            continue
        for c in a['containers']:
            noisy = '' if c['first_noisy_at'] is None else iso(c['first_noisy_at'])[11:] + f" (+{c['first_noisy_minute']} min, {c['noisy_pattern']})"
            held = '' if c['first_held_at'] is None else iso(c['first_held_at'])[11:]
            n2h = '' if c['noisy_to_held_min'] is None else c['noisy_to_held_min']
            pats = '; '.join(f"{p['pattern']} x{p['events']} {'/'.join(f'{k}:{v}' for k, v in p['severity'].items())}" for p in c['patterns_held'][:4])
            out.append(f"| {i} | {a['flag']} | {a['variant']} | {a['on_iso']} | {a['off_iso']} | {c['container']} | {noisy} | {held} | {n2h} | {c['events_held']} | {c['events_kept']} | {kb(c['bytes_held'])} ({kb(c['line_bytes_held'])} of log text) | {pats} |")
    out.append('')
    out.append('### Held patterns per incident (samples)\n')
    for i, a in enumerate(inc, 1):
        for c in a['containers']:
            if not c['patterns_held']: continue
            out.append(f"**{i}. {a['flag']} / {c['container']}**\n")
            out.append('| pattern | events held | severity | sample |\n|---|---|---|---|')
            for p in c['patterns_held'][:8]:
                out.append(f"| {p['pattern']} | {p['events']} | {'/'.join(f'{k}:{v}' for k, v in p['severity'].items())} | `{p['sample'][:110].replace('|', '/')}` |")
            out.append('')
    out.append('## False holds (offload while no flag was active)\n')
    rows = list(csv.DictReader(open(os.path.join(RESULTS, 'false-holds.csv'))))
    if not rows:
        out.append('None.\n')
    else:
        out.append('| container | pattern | events held while quiet | per minute | first at (UTC) | sample |\n|---|---|---|---|---|---|')
        for r in rows[:25]:
            out.append(f"| {r['container']} | {r['pattern']} | {r['events_held_while_quiet']} | {r['per_minute']} | {r['first_at_utc']} | `{r['sample'][:100].replace('|', '/')}` |")
        out.append('')
    out.append('## Delivery check (raw records received by Fluent Bit vs records returned by the Receiver)\n')
    d = json.load(open(os.path.join(RESULTS, 'delivery.json')))
    out.append('| container | raw lines | returned records | lines covered | covered % |\n|---|---|---|---|---|')
    for c, v in d.items():
        out.append(f"| {c} | {v['raw_lines']} | {v['returned_records']} | {v['returned_lines']} | {v['returned_pct']} |")
    out.append('')
    open(os.path.join(RESULTS, 'results-tables.md'), 'w').write('\n'.join(out))
    print('wrote', os.path.join(RESULTS, 'results-tables.md'))

if __name__ == '__main__':
    main()
