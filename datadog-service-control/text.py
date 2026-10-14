#!/usr/bin/env python3
"""
What a message-text filter selects, and the statement signals in each event's text, for every
pattern of the mixed services on a whole capture.

  text.py --routed runs/full-<c>-control/routed.jsonl --tally results/full-<c>-control.tally.json \
          --plan results/full-<c>-<target>.tally.json --out results/full-<c>-control.text.json

A Datadog index filter can take plain terms and quoted phrases on the message beside the
attribute filters attrs.py measures. For each pattern the plan moves in a mixed service, the
phrase is the longest run of words every one of its events shares, read from the events and
not from the pattern's name; words are maximal runs of letters and digits, matched without
regard to case, so a match here is at least as easy to get as in Datadog. The filter is
`service:<container> "<phrase>"`, so the phrase is tested against every event of the same
container in the capture, and the file records which other patterns' events it also matches.
Among equally long runs, the one matching the fewest events of other patterns is kept.

Three signals that a kept pattern is a piece of a statement, read from the text:

  location  every event of the pattern carries the same `[file:line]` source location, a
            Python logging format; patterns of one container sharing a location are one
            statement;
  frame     a run of words that opens a pattern's name and is shared by at least two
            patterns of the container, where in the text the run is followed by a delimited
            value: a bracket, brace, parenthesis, quote, `@`, `/`, or, for a run of at least
            two words, a colon or an equals sign; the value is what the engine named the
            patterns apart by;
  head      whether the event's text begins with a timestamp, so a line the forwarder emitted
            without one (a configuration dump, an installer's output) can be told apart.

The run fails unless the events read equal the tally, which count.py checked against the
engine's own aggregators.
"""
import argparse
import collections
import json
import re
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'accounting-lib'))
sys.path.insert(0, str(HERE))
import floor as FLOOR  # noqa: E402

WORD = re.compile(r'[A-Za-z0-9]+')
LOCATION = re.compile(r'\[([A-Za-z0-9_./-]+\.[a-z]{1,5}):(\d+)\]')
HEAD = re.compile(r'\d{4}-\d{2}-\d{2}|\d{2} [A-Z][a-z]{2} \d{4}|\d{2}/[A-Z][a-z]{2}/\d{4}')
OPENERS = set('[({\'"@/')
OPENERS_TWO_WORDS = set(':=')


def one(v):
    if isinstance(v, list):
        return v[0] if v else ''
    return '' if v is None else v


def message(full_text):
    out = []
    for raw in full_text.split('\n'):
        try:
            out.append(json.loads(raw).get('log', ''))
        except ValueError:
            out.append(raw)
    return '\n'.join(out)


def has_head(text):
    return bool(HEAD.search(text.split('\n', 1)[0][:40]))


def location(text):
    m = LOCATION.search(text)
    return f'{m.group(1)}:{m.group(2)}' if m else None


def joined(tokens):
    return '\x00' + '\x00'.join(tokens) + '\x00'


def longest_common_run(events):
    """The longest contiguous run of lowercased words shared by every event, as a list of
    candidate runs of that length in order of first appearance in the shortest event."""
    ref = min(events, key=len)
    others = [joined(e) for e in events]
    for length in range(len(ref), 0, -1):
        found = []
        seen = set()
        for i in range(len(ref) - length + 1):
            run = tuple(ref[i:i + length])
            if run in seen:
                continue
            seen.add(run)
            key = joined(run)
            if all(key in o for o in others):
                found.append(run)
        if found:
            return found
    return []


def frame_after(text, words):
    """The character that follows the first contiguous occurrence of `words` in the text, or
    None when the words do not occur contiguously."""
    toks = [(m.group(0), m.end()) for m in WORD.finditer(text)]
    n = len(words)
    for i in range(len(toks) - n + 1):
        if all(toks[i + j][0] == words[j] for j in range(n)):
            end = toks[i + n - 1][1]
            rest = text[end:].lstrip(' \t')
            return rest[:1]
    return None


def qualifies(words, char):
    if char is None or char == '':
        return False
    if char in OPENERS:
        return True
    return char in OPENERS_TWO_WORDS and len(words) >= 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--routed', required=True)
    ap.add_argument('--tally', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    control = json.load(open(a.tally))
    plan = json.load(open(a.plan))
    mixed = FLOOR.mixed_services(control, plan)
    moved = FLOOR.moved_patterns(plan)
    texts = collections.defaultdict(list)    # (container, hash) -> [message text]
    names = {}
    n = 0
    for line in open(a.routed, encoding='utf-8', errors='surrogateescape'):
        d = json.loads(line)
        n += 1
        svc = one(d.get('k8s_container'))
        if svc not in mixed:
            continue
        h = one(d.get('tenx_hash'))
        texts[(svc, h)].append(message(one(d.get('fullText'))))
        names[(svc, h)] = one(d.get('message_pattern'))
    if n != control['events']:
        raise SystemExit(f'{n} events read, the tally has {control["events"]}')

    tokens = {k: [[w.lower() for w in WORD.findall(t)] for t in ts] for k, ts in texts.items()}
    by_service = collections.defaultdict(list)
    for (svc, h) in texts:
        by_service[svc].append(h)

    patterns = []
    families = {}
    for svc in sorted(by_service):
        hashes = by_service[svc]
        # Frames: name-word prefixes shared by at least two patterns, followed by a delimited value.
        prefixes = collections.defaultdict(set)
        for h in hashes:
            words = [w for w in names[(svc, h)].split('_') if w]
            for L in range(1, len(words) + 1):
                prefixes[tuple(words[:L])].add(h)
        frames = {}
        for words, hs in prefixes.items():
            if len(hs) < 2:
                continue
            members = [h for h in hashes
                       if all(qualifies(words, frame_after(t, words)) for t in texts[(svc, h)])]
            if len(members) >= 2:
                frames[' '.join(words)] = sorted(members)
        # Each pattern sits in the longest frame it belongs to.
        frame_of = {}
        for key, members in sorted(frames.items(), key=lambda kv: -len(kv[0].split())):
            for h in members:
                frame_of.setdefault(h, key)
        fam = collections.defaultdict(list)
        for h, key in frame_of.items():
            fam[f'frame:{key}'].append(h)
        # Locations: every event of the pattern carries the same [file:line].
        for h in hashes:
            locs = {location(t) for t in texts[(svc, h)]}
            if len(locs) == 1 and None not in locs:
                fam[f'location:{next(iter(locs))}'].append(h)
        families[svc] = {k: sorted(v) for k, v in sorted(fam.items()) if len(v) >= 2}
        member_of = collections.defaultdict(list)
        for k, v in families[svc].items():
            for h in v:
                member_of[h].append(k)

        service_events = [(h, joined(e)) for h in hashes for e in tokens[(svc, h)]]
        for h in sorted(hashes):
            ts = texts[(svc, h)]
            row = {'container': svc, 'hash': h, 'pattern': names[(svc, h)], 'events': len(ts),
                   'moved': bool(moved[(svc, h)]), 'head_events': sum(1 for t in ts if has_head(t)),
                   'location': next(iter({location(t) for t in ts})) if len({location(t) for t in ts}) == 1 else None,
                   'families': sorted(member_of.get(h, []))}
            if moved[(svc, h)]:
                best = None
                for run in longest_common_run(tokens[(svc, h)]):
                    key = joined(run)
                    hits = collections.Counter(q for q, e in service_events if q != h and key in e)
                    total = sum(hits.values())
                    if best is None or total < best[0]:
                        best = (total, run, hits)
                if best is None:
                    row.update({'phrase': None, 'phrase_words': 0, 'matches': {}})
                else:
                    row.update({'phrase': ' '.join(best[1]), 'phrase_words': len(best[1]),
                                'matches': dict(sorted(best[2].items()))})
            patterns.append(row)

    out = {'events': n, 'mixed_services': sorted(mixed),
           'services': {svc: {'events': sum(len(texts[(svc, h)]) for h in hs), 'patterns': len(hs)} for svc, hs in sorted(by_service.items())},
           'families': families, 'patterns': patterns}
    json.dump(out, open(a.out, 'w'), indent=0)
    phrased = [p for p in patterns if p['moved']]
    alone = sum(1 for p in phrased if p.get('phrase') and not p['matches'])
    print(f'{n} events; {len(patterns)} patterns in {len(by_service)} mixed services; '
          f'{len(phrased)} moved patterns, {alone} with a phrase matching no other pattern; '
          f'{sum(len(v) for v in families.values())} statement families')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
