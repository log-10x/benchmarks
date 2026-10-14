"""
The floor: what stays in Standard after a buyer's own levers, and what is left in it for a
per-pattern plan. Computed from the kept tallies of the whole captures (count.py checked them
against the engine's aggregators), the attribute cells attrs.py wrote and the text signals
text.py wrote.

The levers, fixed before the run: an index filter per service with `-status:(error OR warn)`
for `opentelemetry-collector`, `kafka` and `cart` (datadog-flex-accounting's 70% set), and
DEBUG and TRACE dropped everywhere. What remains in Standard is the floor.

Every floor event goes in exactly one bucket:
  1   errors and warnings (ERROR, WARN, CRITICAL, FATAL);
  2a  INFO and unlevelled in a service whose INFO and unlevelled patterns the plan moves
      every one of: one more service filter does what the plan does;
  2b  INFO and unlevelled in a service the plan moves none of: one more service filter could
      move it whole, and the plan leaves it;
  3   INFO and unlevelled in a mixed service, one with both patterns the plan moves and
      patterns it keeps, split into the moved patterns (E on the demo) and the kept ones;
  4   bucket 3's moved patterns, split by what selects them. Attribute cells first: a cell
      holding that pattern alone, a cell it shares only with other patterns the plan moves,
      or a cell that also holds patterns the plan keeps. Then message text: a phrase of the
      pattern's own constant words that selects it alone, one that also selects other moved
      patterns only, one that also selects patterns the plan keeps (a collision), or no
      phrase at all, which leaves the pattern ID.

The kept side of each mixed service is split by what the text shows: pieces of one statement
(patterns sharing a source location or a value frame, text.py), short statements the byte cap
keeps although Datadog bills Standard per event (at least as many events as the smallest
pattern the plan moves in the service), and the rest. A mixed service is movable whole by
one service filter when that rest is patterns seen once in the capture.
"""
import collections

import tally as T

FILTERED = ('opentelemetry-collector', 'kafka', 'cart')
STATUS_EXCLUDED = ('ERROR', 'WARN', 'WARNING')
DROPPED = ('DEBUG', 'TRACE')
MOVED = 'tier_down'
BANDS = [(1, 1, 'seen once'), (2, 10, '2 to 10'), (11, 100, '11 to 100'), (101, 1000, '101 to 1,000'), (1001, 10 ** 12, 'over 1,000')]
FLIP_SHARE = 0.05


def _sev(r):
    return (r['severity'] or '').upper()


def band(n):
    return next(label for lo, hi, label in BANDS if lo <= n <= hi)


def in_floor(r):
    s = _sev(r)
    if s in DROPPED:
        return False
    return r['container'] not in FILTERED or s in STATUS_EXCLUDED


def moved_patterns(plan: dict) -> collections.Counter:
    """Events the engine marked tier_down, per (container, hash)."""
    moved = collections.Counter()
    for r in plan['by_key']:
        if r['route'] == MOVED:
            moved[(r['container'], r['hash'])] += r['events']
    return moved


def _split_services(control: dict, plan: dict):
    rows = control['by_key']
    moved = moved_patterns(plan)
    floor = [r for r in rows if in_floor(r)]
    b1 = [r for r in floor if _sev(r) in T.PROTECTED]
    info = [r for r in floor if _sev(r) not in T.PROTECTED]
    by_service = collections.defaultdict(list)
    for r in info:
        by_service[r['container']].append(r)
    kinds = {}
    for svc, rs in by_service.items():
        m = [r for r in rs if moved[(svc, r['hash'])]]
        k = [r for r in rs if not moved[(svc, r['hash'])]]
        kinds[svc] = '2a' if not k else '2b' if not m else '3'
    return rows, moved, floor, b1, by_service, kinds


def mixed_services(control: dict, plan: dict) -> set:
    """The services with both patterns the plan moves and patterns it keeps among their INFO
    and unlevelled floor events."""
    _, _, _, _, _, kinds = _split_services(control, plan)
    return {s for s, k in kinds.items() if k == '3'}


def _bands(rows, pattern_events):
    out = collections.Counter()
    for r in rows:
        out[band(pattern_events[(r['container'], r['hash'])])] += r['events']
    return {label: out.get(label, 0) for _, _, label in BANDS}


def _sum(rows):
    return {'events': sum(r['events'] for r in rows), 'bytes': sum(r['bytes'] for r in rows)}


def decompose(control: dict, plan: dict, policy: dict, cells: dict, text: dict = None) -> dict:
    rows, moved, floor, b1, by_service, kinds = _split_services(control, plan)
    total = _sum(rows)
    pattern_events = collections.Counter()
    for r in rows:
        pattern_events[(r['container'], r['hash'])] += r['events']
    b2a, b2b, b3m, b3k = [], [], [], []
    services = {}
    for svc, rs in sorted(by_service.items()):
        m = [r for r in rs if moved[(svc, r['hash'])]]
        k = [r for r in rs if not moved[(svc, r['hash'])]]
        kind = kinds[svc]
        services[svc] = {'bucket': kind, 'events': sum(r['events'] for r in rs),
                         'moved_events': sum(r['events'] for r in m), 'kept_events': sum(r['events'] for r in k),
                         'moved_patterns': len({r['hash'] for r in m}), 'kept_patterns': len({r['hash'] for r in k}),
                         'capped': svc in policy['containers']}
        if kind == '2a':
            b2a += rs
        elif kind == '2b':
            b2b += rs
        else:
            b3m += m
            b3k += k

    # Bucket 4 by attribute cell: what selects each of bucket 3's moved patterns.
    kept_hashes = {(r['container'], r['hash']) for r in b3k}
    b4 = {'alone': [], 'with_moved_only': [], 'id_only': []}
    detail = []
    for (svc, h) in sorted({(r['container'], r['hash']) for r in b3m}):
        cell = cells.get(f'{svc}\t{h}') or {'members': [h], 'attributes': {}}
        members = set(cell['members'])
        if members == {h}:
            kind = 'alone'
        elif not any((svc, x) in kept_hashes or not moved[(svc, x)] for x in members - {h}):
            kind = 'with_moved_only'
        else:
            kind = 'id_only'
        ev = [r for r in b3m if r['container'] == svc and r['hash'] == h]
        b4[kind] += ev
        detail.append({'container': svc, 'hash': h, 'pattern': ev[0]['pattern'], 'events': sum(r['events'] for r in ev),
                       'pattern_events': pattern_events[(svc, h)], 'band': band(pattern_events[(svc, h)]),
                       'selected_by': kind, 'cell': cell['attributes'], 'cell_patterns': len(members),
                       'tier_down_events': moved[(svc, h)]})
    detail.sort(key=lambda d: -d['events'])

    e = _sum(b3m)
    id_only = _sum(b4['id_only'])
    flips = e['events'] >= FLIP_SHARE * total['events'] and id_only['events'] > e['events'] / 2
    # The same test with the mixed services where the plan keeps a single event moved whole by
    # one more service filter: a reading of bucket 2, reported beside the rule, not instead of it.
    single = {s for s, v in services.items() if v['bucket'] == '3' and v['kept_events'] <= 1}
    e2 = sum(r['events'] for r in b3m if r['container'] not in single)
    id2 = sum(d['events'] for d in detail if d['selected_by'] == 'id_only' and d['container'] not in single)
    flips2 = e2 >= FLIP_SHARE * total['events'] and id2 > e2 / 2
    bucket = lambda rs: {**_sum(rs), 'share': round(sum(r['events'] for r in rs) / total['events'], 4),  # noqa: E731
                         'patterns': len({(r['container'], r['hash']) for r in rs}), 'bands': _bands(rs, pattern_events)}
    floor_by_service = collections.Counter()
    for r in floor:
        floor_by_service[r['container']] += r['events']
    out = {
        'capture': total,
        'floor': {**_sum(floor), 'share': round(sum(r['events'] for r in floor) / total['events'], 4)},
        'floor_by_service': dict(floor_by_service.most_common()),
        'buckets': {'1': bucket(b1), '2a': bucket(b2a), '2b': bucket(b2b), '3_moved': bucket(b3m), '3_kept': bucket(b3k),
                    '4_alone': bucket(b4['alone']), '4_with_moved_only': bucket(b4['with_moved_only']), '4_id_only': bucket(b4['id_only'])},
        'tier_down_in_3_moved': sum(d['tier_down_events'] for d in detail),
        'services': services,
        'moved_patterns': detail,
        'flip': {'rule': f'bucket 3 moved >= {FLIP_SHARE:.0%} of the capture and more than half of it selectable only by the ID',
                 'bucket_3_moved_share': round(e['events'] / total['events'], 4),
                 'id_only_share_of_bucket_3_moved': round(id_only['events'] / e['events'], 4) if e['events'] else 0,
                 'flips': flips,
                 'with_single_kept_event_services_moved_whole': {
                     'services': sorted(single), 'bucket_3_moved_events': e2,
                     'bucket_3_moved_share': round(e2 / total['events'], 4),
                     'id_only_share': round(id2 / e2, 4) if e2 else 0, 'flips': flips2}},
    }
    if text is not None:
        out['text'] = by_text(text, b3m, b3k, b1, moved, pattern_events, detail, total, bucket)
    return out


def by_text(text: dict, b3m, b3k, b1, moved, pattern_events, detail, total, bucket) -> dict:
    """Bucket 4 recomputed with message-text filters counted as native, the kept side of each
    mixed service split by the text signals, and E under each reading."""
    rows = {(p['container'], p['hash']): p for p in text['patterns']}
    is_moved = {k: p['moved'] for k, p in rows.items()}

    # Bucket 4 by text phrase.
    b4 = {'alone': [], 'with_moved_only': [], 'collides': [], 'id_only': []}
    for d in detail:
        key = (d['container'], d['hash'])
        p = rows[key]
        kept_hits = {h: n for h, n in p['matches'].items() if not is_moved[(d['container'], h)]}
        moved_hits = {h: n for h, n in p['matches'].items() if is_moved[(d['container'], h)]}
        if not p.get('phrase'):
            kind = 'id_only'
        elif kept_hits:
            kind = 'collides'
        elif moved_hits:
            kind = 'with_moved_only'
        else:
            kind = 'alone'
        own = set(p['families'])
        d['text'] = {'phrase': p.get('phrase'), 'phrase_words': p.get('phrase_words', 0), 'selected_by': kind,
                     'kept_patterns_matched': len(kept_hits), 'kept_events_matched': sum(kept_hits.values()),
                     'moved_patterns_matched': len(moved_hits), 'moved_events_matched': sum(moved_hits.values()),
                     'kept_matches': kept_hits,
                     'kept_matches_are_own_pieces': bool(kept_hits) and all(own & set(rows[(d['container'], h)]['families']) for h in kept_hits)}
        b4[kind] += [r for r in b3m if (r['container'], r['hash']) == key]
    e = _sum(b3m)['events']
    text_id_only = sum(r['events'] for r in b4['id_only'])
    flips = e >= FLIP_SHARE * total['events'] and text_id_only > e / 2

    # The kept side of each mixed service.
    kept_by_service = collections.defaultdict(list)
    for r in b3k:
        kept_by_service[r['container']].append(r)
    services = {}
    for svc in sorted(kept_by_service):
        kept = collections.defaultdict(int)
        for r in kept_by_service[svc]:
            kept[r['hash']] += r['events']
        smallest_moved = min((pattern_events[(svc, h)] for (s, h) in moved if s == svc and moved[(s, h)]), default=0)
        pieces, byte_cap, other = {}, {}, {}
        families = set()
        for h, ev in kept.items():
            p = rows[(svc, h)]
            if p['families']:
                pieces[h] = ev
                families.update(p['families'])
            elif pattern_events[(svc, h)] >= smallest_moved:
                byte_cap[h] = ev
            else:
                other[h] = ev
        # Families sharing a pattern are one statement.
        statements = _components({f: {h for h in pieces if f in rows[(svc, h)]['families']} for f in families})
        no_head = sum(rows[(svc, h)]['events'] - rows[(svc, h)]['head_events'] for h in other)
        criticals = sum(r['events'] for r in b1 if r['container'] == svc and _sev(r) in ('CRITICAL', 'FATAL') and not moved[(svc, r['hash'])])
        movable = all(pattern_events[(svc, h)] == 1 for h in other)
        services[svc] = {
            'kept_events': sum(kept.values()), 'kept_patterns': len(kept),
            'pieces': {'events': sum(pieces.values()), 'patterns': len(pieces), 'statements': statements,
                       'families': sorted(families)},
            'byte_cap': {'events': sum(byte_cap.values()), 'patterns': len(byte_cap), 'smallest_moved_pattern_events': smallest_moved},
            'other': {'events': sum(other.values()), 'patterns': len(other), 'no_head_events': no_head,
                      'seen_once_patterns': sum(1 for h in other if pattern_events[(svc, h)] == 1)},
            'whole_filter_beyond_plan': {'info_and_unlevelled': sum(kept.values()), 'criticals': criticals,
                                         'events': sum(kept.values()) + criticals},
            'movable_whole': movable,
            'moved_events': sum(r['events'] for r in b3m if r['container'] == svc),
            'kept_detail': sorted(({'hash': h, 'pattern': rows[(svc, h)]['pattern'], 'events': ev, 'pattern_events': pattern_events[(svc, h)],
                                    'split': 'pieces' if h in pieces else 'byte_cap' if h in byte_cap else 'other',
                                    'families': rows[(svc, h)]['families'], 'head_events': rows[(svc, h)]['head_events']}
                                   for h, ev in kept.items()), key=lambda x: (-x['events'], x['pattern'])),
        }
    movable = sorted(s for s, v in services.items() if v['movable_whole'])
    e_movable = sum(v['moved_events'] for s, v in services.items() if v['movable_whole'])
    beyond = sum(v['whole_filter_beyond_plan']['events'] for s, v in services.items() if v['movable_whole'])
    rules = {'text_filters': len(detail), 'with_collisions': len({(r['container'], r['hash']) for r in b4['collides']}),
             'kept_events_collided': sum(d['text']['kept_events_matched'] for d in detail if d['text']['selected_by'] == 'collides')}
    return {
        'buckets': {'4_text_alone': bucket(b4['alone']), '4_text_with_moved_only': bucket(b4['with_moved_only']),
                    '4_text_collides': bucket(b4['collides']), '4_text_id_only': bucket(b4['id_only'])},
        'flip': {'bucket_3_moved_share': round(e / total['events'], 4),
                 'id_only_share_of_bucket_3_moved': round(text_id_only / e, 4) if e else 0, 'flips': flips},
        'rules': rules,
        'services': services,
        'e': {'as_computed': {'events': e, 'share': round(e / total['events'], 4)},
              'movable_whole_moved': {'services': movable, 'events': e - e_movable, 'share': round((e - e_movable) / total['events'], 4),
                                      'events_a_whole_filter_moves_beyond_the_plan': beyond}},
    }


def _components(groups: dict) -> int:
    """How many connected sets the groups form, two groups joined when they share a member."""
    parent = {g: g for g in groups}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    by_member = collections.defaultdict(list)
    for g, members in groups.items():
        for m in members:
            by_member[m].append(g)
    for gs in by_member.values():
        for g in gs[1:]:
            parent[find(g)] = find(gs[0])
    return len({find(g) for g in groups})


def growth(control_a: dict, control_b: dict, a_hours: float, b_hours: float) -> dict:
    """The floor's change per hour from A to B. Services in B's capture and not A's are new code;
    services in A's and not B's are absent from B's capture. In services present in both, a
    pattern seen in both captures changes with traffic, and a pattern seen in one only is a
    statement added or gone (code). No service is renamed between the two, so the service
    filters match the same services in both."""
    def rates(control, hours):
        out = collections.defaultdict(collections.Counter)
        for r in control['by_key']:
            if in_floor(r):
                out[r['container']][r['hash']] += r['events'] / hours
        return out
    ra, rb = rates(control_a, a_hours), rates(control_b, b_hours)
    new = {s: round(sum(v.values()), 1) for s, v in rb.items() if s not in ra}
    gone = {s: round(-sum(v.values()), 1) for s, v in ra.items() if s not in rb}
    present = {}
    for s in sorted(set(ra) & set(rb)):
        shared = set(ra[s]) & set(rb[s])
        present[s] = {'traffic': round(sum(rb[s][h] - ra[s][h] for h in shared), 1),
                      'statements_added': round(sum(v for h, v in rb[s].items() if h not in shared), 1),
                      'statements_gone': round(-sum(v for h, v in ra[s].items() if h not in shared), 1)}
    tot = lambda d: round(sum(sum(v.values()) for v in d.values()), 1)  # noqa: E731
    return {'floor_per_hour': {'A': tot(ra), 'B': tot(rb)},
            'new_services': dict(sorted(new.items(), key=lambda kv: -kv[1])),
            'absent_from_b': dict(sorted(gone.items(), key=lambda kv: kv[1])),
            'present': dict(sorted(present.items(), key=lambda kv: -abs(sum(kv[1].values())))),
            'sums': {'new_services': round(sum(new.values()), 1), 'absent_from_b': round(sum(gone.values()), 1),
                     'traffic': round(sum(v['traffic'] for v in present.values()), 1),
                     'statements_added': round(sum(v['statements_added'] for v in present.values()), 1),
                     'statements_gone': round(sum(v['statements_gone'] for v in present.values()), 1)},
            'renamed_inside_filtered_services': 0}
