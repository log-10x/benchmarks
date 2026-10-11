"""
The native-filter control: what Datadog index filters by service move at the events the
plan moves, computed from the same capture's counts.

Selection rule (README, "Native filters at equal events"): per target, the fewest
`service:<container>` filters, largest by events first, whose events reach at least the events
the engine marked tier_down under the plan; the overshoot is reported, not trimmed. The second
variant adds `-status:(error OR warn)`, which keeps ERROR and WARN events in Standard.
"""
import collections

import tally as T

# Severities Datadog's `status:error` and `status:warn` match. CRITICAL and FATAL map to the
# `critical` and `emergency` statuses, which the clause does not name.
STATUS_EXCLUDED = ('ERROR', 'WARN', 'WARNING')


def _sev(row):
    return (row['severity'] or '').upper()


def _arm(rows, plan_rows, kept, plan_events, exclude_status):
    """The filter set for one variant, and what it moves against the plan."""
    eligible = [r for r in rows if not (exclude_status and _sev(r) in STATUS_EXCLUDED)]
    by_container = collections.Counter()
    for r in eligible:
        by_container[r['container']] += r['events']
    chosen, total = [], 0
    for c, ev in sorted(by_container.items(), key=lambda kv: (-kv[1], kv[0])):
        if total >= plan_events:
            break
        chosen.append(c)
        total += ev
    sel = set(chosen)
    moved = [r for r in eligible if r['container'] in sel]
    by_sev = collections.Counter()
    for r in moved:
        by_sev[_sev(r) or 'none'] += r['events']
    kept_moved = [r for r in moved if (r['container'], r['hash']) in kept]
    left = [r for r in plan_rows if r['container'] not in sel or (exclude_status and _sev(r) in STATUS_EXCLUDED)]
    top_kept = collections.Counter()
    for r in kept_moved:
        top_kept[(r['container'], r['pattern'])] += r['events']
    top_left = collections.Counter()
    for r in left:
        top_left[(r['container'], r['pattern'])] += r['events']
    return {
        'filters': [f'service:{c}' for c in chosen],
        'events': sum(r['events'] for r in moved),
        'bytes': sum(r['bytes'] for r in moved),
        'overshoot_events': sum(r['events'] for r in moved) - plan_events,
        'errors_and_warnings': sum(r['events'] for r in moved if _sev(r) in T.PROTECTED),
        'by_severity': dict(sorted(by_sev.items())),
        'kept_under_cap_events': sum(r['events'] for r in kept_moved),
        'kept_under_cap_patterns': len({(r['container'], r['hash']) for r in kept_moved}),
        'plan_moved_left_events': sum(r['events'] for r in left),
        'plan_moved_left_patterns': len({(r['container'], r['hash']) for r in left}),
        'top_kept_under_cap_moved': [{'container': c, 'pattern': p, 'events': e} for (c, p), e in top_kept.most_common(5)],
        'top_plan_moved_left': [{'container': c, 'pattern': p, 'events': e} for (c, p), e in top_left.most_common(5)],
    }


def native_filters(control: dict, target: dict, policy: dict) -> dict:
    rows = control['by_key']
    plan_rows = [r for r in target['by_key'] if r['route'] == 'tier_down']
    plan_events = sum(r['events'] for r in plan_rows)
    plan_by_sev = collections.Counter()
    for r in plan_rows:
        plan_by_sev[_sev(r) or 'none'] += r['events']
    capped = set(policy['containers'])
    marked = collections.Counter()
    for r in target['by_key']:
        if r['container'] in capped and r['route'] == 'tier_down':
            marked[(r['container'], r['hash'])] += r['events']
    kept = {(r['container'], r['hash']) for r in target['by_key']
            if r['container'] in capped and marked[(r['container'], r['hash'])] == 0}
    plan = {
        'events': plan_events,
        'bytes': sum(r['bytes'] for r in plan_rows),
        'errors_and_warnings': sum(r['events'] for r in plan_rows if _sev(r) in T.PROTECTED),
        'by_severity': dict(sorted(plan_by_sev.items())),
        'containers_capped': sorted(capped),
        'patterns_kept_under_a_cap': len(kept),
    }
    filters = _arm(rows, plan_rows, kept, plan_events, exclude_status=False)
    filters_status = _arm(rows, plan_rows, kept, plan_events, exclude_status=True)
    adds_nothing = (filters_status['errors_and_warnings'] <= plan['errors_and_warnings']
                    and filters_status['kept_under_cap_events'] == 0)
    return {'plan': plan, 'filters': filters, 'filters_without_errors_and_warnings': filters_status,
            'key_adds_nothing_at_this_target': adds_nothing}
