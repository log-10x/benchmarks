#!/usr/bin/env python3
"""The fleet cap for the capped phases, from the baseline's returned records.
Every record the Receiver returned with fb_ts in [from, to) is counted in its cell
(container, message_pattern, 4-minute window from `from`) at the UTF-8 size of its line.
The cap is the per-pattern per-window byte limit c at which the bytes above c, summed over
the cells, are TARGET (default 0.5) of the baseline bytes: the same per-pattern limit for
every container, as the fleet default writes it (rateReceiverAbsoluteCap).
  cap.py <from epoch> <to epoch> [target]   prints JSON, last line the cap"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.environ.get('RESULTS', os.path.join(HERE, '..', 'results')))
lo, hi = float(sys.argv[1]), float(sys.argv[2])
target = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
WINDOW = 240.0
cells = {}
records = 0
for name in ('pass.jsonl', 'other.jsonl'):
    p = os.path.join(R, 'data', name)
    if not os.path.exists(p):
        continue
    with open(p, errors='replace') as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            try:
                ts = float(r.get('fb_ts') or 0)
            except ValueError:
                continue
            if not (lo <= ts < hi):
                continue
            c = (r.get('kubernetes') or {}).get('container_name') or ''
            k = (c, r.get('message_pattern') or '', int((ts - lo) // WINDOW))
            cells[k] = cells.get(k, 0) + len((r.get('log') or '').encode('utf-8'))
            records += 1
sizes = sorted(cells.values())
total = sum(sizes)
if not total:
    raise SystemExit('no baseline records in range')


def over(c):
    return sum(s - c for s in sizes if s > c)


a, b = 0.0, float(sizes[-1])
for _ in range(60):
    m = (a + b) / 2
    if over(m) > target * total:
        a = m
    else:
        b = m
cap = max(1, round(b))
print(json.dumps({'from': lo, 'to': hi, 'records': records, 'cells': len(sizes), 'bytes': total,
                  'target_share_over_cap': target, 'cap_bytes_per_window_per_node': cap,
                  'share_over_cap_at_cap': round(over(cap) / total, 4),
                  'cells_over_cap': sum(1 for s in sizes if s > cap)}))
print(cap)
