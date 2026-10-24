#!/usr/bin/env python3
"""Arm B's forwarder rule: the services that make up the top half of bytes (UTF-8 bytes of each line)
in the first <minutes> minutes of the feed at <speed>, largest first until their share reaches half.
The feed starts at offset 0, so those minutes are the rows with source time under minutes x 60 x speed.
  top-half.py <source.jsonl> <speed> <minutes> <out.json>"""
import collections, json, sys

src, speed, minutes, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
limit = minutes * 60 * speed
by = collections.Counter()
lines = collections.Counter()
t0 = None
for l in open(src):
    r = json.loads(l)
    t0 = r['t'] if t0 is None else t0
    if r['t'] - t0 >= limit:
        break
    c = r['container_name'].lstrip('/')
    by[c] += len(r['log'].encode('utf-8'))
    lines[c] += 1
total = sum(by.values())
top, cum = [], 0
for c, b in by.most_common():
    if cum >= total / 2:
        break
    top.append(c)
    cum += b
rows = [{'service': c, 'bytes': b, 'lines': lines[c], 'share': round(b / total, 4)} for c, b in by.most_common()]
res = {'source': src, 'speed': speed, 'minutes': minutes, 'source_seconds': limit, 'lines': sum(lines.values()), 'bytes': total,
       'top_half': top, 'top_half_bytes': cum, 'top_half_share': round(cum / total, 4), 'regex': '^(' + '|'.join(top) + ')$', 'services': rows}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('lines', 'bytes', 'top_half', 'top_half_share', 'regex')}))
for r in rows[:8]:
    print(r)
