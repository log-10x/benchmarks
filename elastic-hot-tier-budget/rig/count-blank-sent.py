#!/usr/bin/env python3
"""Blank lines a replay sent: where the sample's blank rows sit in source time, walked through every
replay_start / replay_stop pair in the timeline at its offset and speed, looping over the sample.
Lines in minus this count is the number of non-blank lines the run should return.
  count-blank-sent.py <replay/source.jsonl> <timeline.jsonl>"""
import json, re, sys

src, tl = sys.argv[1], sys.argv[2]
nonspace = re.compile(r'[^ \t\n\v\f\r]')
rows = [json.loads(l) for l in open(src)]
t0 = rows[0]['t']
span = rows[-1]['t'] - t0 + 1
blank = [r['t'] - t0 for r in rows if not any(nonspace.search(s) for s in r['log'].split('\n') if s)]
print(f'blank rows in the sample: {len(blank)}, source time {min(blank)} to {max(blank)} s of {span} s')
events = [json.loads(l) for l in open(tl)]
starts = [e for e in events if e['event'] == 'replay_start']
stops = [e for e in events if e['event'] == 'replay_stop']
total = 0
for s, e in zip(starts, stops):
    off = s['offset_s'] % span
    hi = off + (e['epoch'] - s['epoch']) * s['speed']
    n = sum(1 for k in range(int(hi // span) + 2) for b in blank if off <= k * span + b < hi)
    edge = min(abs(k * span + x - y) for k in range(int(hi // span) + 2) for x in (min(blank), max(blank)) for y in (off, hi))
    total += n
    print(f"speed {s['speed']:>2}, source {off:.0f} to {hi:.0f} s: {n} blank lines; nearest phase edge to a blank row {edge / s['speed']:.0f} wall s")
print(f'blank lines sent: {total}')
