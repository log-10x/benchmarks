"""
The floor: what stays in Standard after a buyer's own levers, and what is left in it for a
per-pattern plan. Computed from the kept tallies of the whole captures (count.py checked them
against the engine's aggregators) and the attribute cells attrs.py wrote.

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
  4   bucket 3's moved patterns, split by what selects them: a native attribute cell holding
      that pattern alone, a cell it shares only with other patterns the plan moves, or only
      the pattern ID.
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


def _bands(rows, pattern_events):
    out = collections.Counter()
    for r in rows:
        out[band(pattern_events[(r['container'], r['hash'])])] += r['events']
    return {label: out.get(label, 0) for _, _, label in BANDS}


def _sum(rows):
    return {'events': sum(r['events'] for r in rows), 'bytes': sum(r['bytes'] for r in rows)}


def decompose(control: dict, plan: dict, policy: dict, cells: dict) -> dict:
    rows = control['by_key']
    total = _sum(rows)
    pattern_events = collections.Counter()
    for r in rows:
        pattern_events[(r['container'], r['hash'])] += r['events']
    moved = collections.Counter()
    for r in plan['by_key']:
        if r['route'] == MOVED:
            moved[(r['container'], r['hash'])] += r['events']
    floor = [r for r in rows if in_floor(r)]
    b1 = [r for r in floor if _sev(r) in T.PROTECTED]
    info = [r for r in floor if _sev(r) not in T.PROTECTED]
    by_service = collections.defaultdict(list)
    for r in info:
        by_service[r['container']].append(r)
    b2a, b2b, b3m, b3k = [], [], [], []
    services = {}
    for svc, rs in sorted(by_service.items()):
        m = [r for r in rs if moved[(svc, r['hash'])]]
        k = [r for r in rs if not moved[(svc, r['hash'])]]
        kind = '2a' if not k else '2b' if not m else '3'
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

    # Bucket 4: what selects each of bucket 3's moved patterns.
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
    return {
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
