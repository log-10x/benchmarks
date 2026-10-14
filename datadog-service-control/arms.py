"""
The arms on one service, computed from the kept class rows (classes.py), which equal the
tallies count.py checked against the engine's own aggregators.

Selection rule (README, "Selection rule"): per target, the fewest logger classes, largest by
events first, whose events reach at least the events the engine marked tier_down under the
plan on capture A; the overshoot is reported, not trimmed. The filter for a class is
`service:kafka @logger.name:<class>`. Events with no logger class cannot be named by such a
filter and are never chosen. The second variant adds `-status:(error OR warn)`.

On capture B nothing is re-tuned: A's chosen classes, A's cap carried to B's span, and the
plan rewritten on B.
"""
import collections

import tally as T

STATUS_EXCLUDED = ('ERROR', 'WARN', 'WARNING')
MOVED = 'tier_down'


def _sev(r):
    return (r['severity'] or '').upper()


def _short(cls):
    return cls.rsplit('.', 1)[-1] if cls else '(no logger class)'


def choose(control_rows, plan_events, exclude_status):
    by_class = collections.Counter()
    for r in control_rows:
        if r['class'] and not (exclude_status and _sev(r) in STATUS_EXCLUDED):
            by_class[r['class']] += r['events']
    chosen, total = [], 0
    for c, ev in sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0])):
        if total >= plan_events:
            break
        chosen.append(c)
        total += ev
    return chosen


def _filter_moves(rows, classes, exclude_status):
    sel = set(classes)
    return [r for r in rows if r['class'] in sel and not (exclude_status and _sev(r) in STATUS_EXCLUDED)]


def _patterns(rows):
    agg = collections.Counter()
    cls = {}
    for r in rows:
        agg[(r['hash'], r['pattern'])] += r['events']
        cls[(r['hash'], r['pattern'])] = r['class']
    return [{'pattern': p, 'hash': h, 'class': cls[(h, p)], 'events': e} for (h, p), e in agg.most_common()]


def _summary(moved_rows, total_events):
    by_sev = collections.Counter()
    for r in moved_rows:
        by_sev[_sev(r) or 'none'] += r['events']
    ev = sum(r['events'] for r in moved_rows)
    return {'events': ev, 'bytes': sum(r['bytes'] for r in moved_rows),
            'share_of_events': round(ev / total_events, 4) if total_events else 0,
            'errors_and_warnings': sum(r['events'] for r in moved_rows if _sev(r) in T.PROTECTED),
            'by_severity': dict(sorted(by_sev.items()))}


def _kept_hashes(plan_rows):
    marked = collections.Counter()
    seen = set()
    for r in plan_rows:
        seen.add(r['hash'])
        if r['route'] == MOVED:
            marked[r['hash']] += r['events']
    return {h for h in seen if marked[h] == 0}


def _against_plan(arm_moved, control_rows, plan_rows, plan_events):
    """What an arm moves of the patterns the plan keeps under the cap, and what it leaves of
    the events the plan moves."""
    kept = _kept_hashes(plan_rows)
    kept_moved = [r for r in arm_moved if r['hash'] in kept]
    arm_keys = collections.Counter()
    for r in arm_moved:
        arm_keys[(r['hash'], _sev(r))] += r['events']
    # The plan's moved events, by pattern and severity, less what the arm moves of the same
    # pattern and severity: what the plan moves that the arm leaves in Standard.
    plan_keys = collections.Counter()
    plan_cls = {}
    for r in plan_rows:
        if r['route'] == MOVED:
            plan_keys[(r['hash'], _sev(r))] += r['events']
            plan_cls[r['hash']] = (r['pattern'], r['class'])
    left = collections.Counter()
    for k, n in plan_keys.items():
        rest = n - min(n, arm_keys.get(k, 0))
        if rest:
            left[k[0]] += rest
    return {
        'over_the_plan': sum(r['events'] for r in arm_moved) - plan_events,
        'kept_under_cap_events': sum(r['events'] for r in kept_moved),
        'kept_under_cap_patterns': _patterns(kept_moved),
        'plan_moved_left_events': sum(left.values()),
        'plan_moved_left_patterns': [{'pattern': plan_cls[h][0], 'hash': h, 'class': plan_cls[h][1], 'events': n}
                                     for h, n in left.most_common()],
    }


def part_a(control_a, plan_a, control_b, cap_on_b, plan_b, policy_a, policy_b):
    a_rows, b_rows = control_a['rows'], control_b['rows']
    a_total = sum(r['events'] for r in a_rows)
    b_total = sum(r['events'] for r in b_rows)
    plan_a_moved = [r for r in plan_a['rows'] if r['route'] == MOVED]
    plan_events = sum(r['events'] for r in plan_a_moved)
    a_hashes = {r['hash'] for r in a_rows}
    lifecycle = {r['hash'] for r in b_rows if r['hash'] not in a_hashes}
    lifecycle_rows = [r for r in b_rows if r['hash'] in lifecycle]
    lifecycle_events = sum(r['events'] for r in lifecycle_rows)
    lifecycle_by_class = collections.Counter()
    for r in lifecycle_rows:
        lifecycle_by_class[r['class']] += r['events']

    def lifecycle_moved(rows):
        return sum(r['events'] for r in rows if r['hash'] in lifecycle)

    out = {'a': {}, 'b': {}}
    plan_arm = {'rules': ['one cap row: ' + policy_a['tool_caps_csv'].strip().splitlines()[1].split('::')[0]],
                **_summary(plan_a_moved, a_total), 'over_the_plan': 0}
    out['a']['plan'] = plan_arm
    chosen = {}
    for variant, excl in (('classes', False), ('classes_status', True)):
        cls = choose(a_rows, plan_events, excl)
        chosen[variant] = cls
        moved = _filter_moves(a_rows, cls, excl)
        out['a'][variant] = {'rules': [f'service:kafka @logger.name:{c}' + (' -status:(error OR warn)' if excl else '') for c in cls],
                             'classes': cls, **_summary(moved, a_total),
                             **_against_plan(moved, a_rows, plan_a['rows'], plan_events)}

    b_plan_moved = [r for r in plan_b['rows'] if r['route'] == MOVED]
    b_plan_events = sum(r['events'] for r in b_plan_moved)
    out['b']['plan_b'] = {'rules': ['one cap row: ' + policy_b['tool_caps_csv'].strip().splitlines()[1].split('::')[0]],
                          **_summary(b_plan_moved, b_total), 'over_the_plan': 0,
                          'lifecycle_moved': lifecycle_moved(b_plan_moved)}
    cap_moved = [r for r in cap_on_b['rows'] if r['route'] == MOVED]
    out['b']['cap_a'] = {'rules': ['the same cap row, carried to B\'s span'], **_summary(cap_moved, b_total),
                         **_against_plan(cap_moved, b_rows, plan_b['rows'], b_plan_events),
                         'lifecycle_moved': lifecycle_moved(cap_moved)}
    for variant, excl in (('classes', False), ('classes_status', True)):
        moved = _filter_moves(b_rows, chosen[variant], excl)
        out['b'][variant] = {'rules': out['a'][variant]['rules'], **_summary(moved, b_total),
                             **_against_plan(moved, b_rows, plan_b['rows'], b_plan_events),
                             'lifecycle_moved': lifecycle_moved(moved),
                             'classes_matching_nothing': [c for c in chosen[variant] if not any(r['class'] == c for r in b_rows)]}
    out['totals'] = {'a_events': a_total, 'b_events': b_total, 'plan_a_events': plan_events, 'plan_b_events': b_plan_events,
                     'lifecycle': {'events': lifecycle_events, 'patterns': len(lifecycle),
                                   'by_class': [{'class': c, 'events': n} for c, n in lifecycle_by_class.most_common()]}}
    return out
