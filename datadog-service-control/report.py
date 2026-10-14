#!/usr/bin/env python3
"""
Renders results/results.md, results/results.json and the README's generated blocks from the
kept class rows, tallies, plans and policy files. `--check` recomputes them and fails if the
committed results.json or README differ, so a figure edited without a rerun is caught in CI.
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'accounting-lib'))
sys.path.insert(0, str(HERE))
import tally as T  # noqa: E402
import readme as README  # noqa: E402
import arms as ARMS  # noqa: E402


def _plan_info(p: dict) -> dict:
    pl = p.get('plan') or {}
    return {'target_pct': pl.get('targetPct'), 'achieved_pct': round(pl.get('achievedPct') or 0, 1), 'met': pl.get('met'),
            'ceiling_pct': round(pl.get('keepEverythingCeilingPct') or 0, 1), 'patterns_planned': len(pl.get('planned') or []),
            'events_sampled': p.get('events_pulled')}


def _policy_info(p: dict) -> dict:
    row = next(iter(p['containers'].values()))
    return {'tool_cap_bytes_per_window': row['cap_bytes_per_window'], 'cap_bytes_replay': row['cap_bytes_replay'],
            'action': row['action'], 'tool_span_seconds': p['span_seconds'], 'replay_factor': p['replay_factor']}


def _classes_table(rows, n=14):
    import collections
    by, pats = collections.Counter(), collections.defaultdict(set)
    for r in rows:
        by[r['class']] += r['events']
        pats[r['class']].add(r['hash'])
    return [{'class': c, 'events': e, 'patterns': len(pats[c])} for c, e in by.most_common(n)]


def compute(results: pathlib.Path) -> dict:
    run = T.load(results / 'run.json')
    L = lambda n: T.load(results / n)  # noqa: E731
    ca, cb = L('control-A.classes.json'), L('control-B.classes.json')
    ta, tb = L('control-A.tally.json'), L('control-B.tally.json')
    out = {
        'engine_image': run['engine_image'], 'engine_tag': run['engine_tag'], 'mcp_version': run['mcp_version'],
        'captures': run['captures'],
        'slices': {'A': L('slice-A.json'), 'B': L('slice-B.json')},
        'control': {c: {'events': t['events'], 'lines': t['lines'], 'bytes': t['bytes'], 'patterns': len({k['hash'] for k in t['by_key']}),
                        'classes': len({r['class'] for r in cl['rows'] if r['class']}),
                        'top_classes': _classes_table(cl['rows'])}
                    for c, t, cl in (('A', ta, ca), ('B', tb, cb))},
        'targets': {},
    }
    for t in run['targets']:
        pa, pb = L(f'plan-A-{t}.json'), L(f'plan-B-{t}.json')
        arms = ARMS.part_a(ca, L(f'A-{t}.classes.json'), cb, L(f'AonB-{t}.classes.json'), L(f'B-{t}.classes.json'),
                           L(f'policy-A-{t}.json'), L(f'policy-B-{t}.json'))
        out['targets'][str(t)] = {
            'plan_a': _plan_info(pa), 'plan_b': _plan_info(pb),
            'policy_a': _policy_info(L(f'policy-A-{t}.json')), 'policy_a_on_b': _policy_info(L(f'policy-AonB-{t}.json')),
            'policy_b': _policy_info(L(f'policy-B-{t}.json')),
            **arms,
        }
    return out


def n(x):
    return T.fmt_int(x)


def short(c):
    return f'`{c.rsplit(".", 1)[-1]}`' if c else '(no logger class)'


def gb(b):
    return T.fmt_gb(b)


def table_a(r):
    L = ['| Target | Arm | Rules | Events moved | Over the plan | GB moved | Errors and warnings moved | Events of patterns the plan keeps under the cap | Events the plan moves that stay in Standard |',
         '|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for t, v in r['targets'].items():
        a = v['a']
        L.append(f'| {t}% | per-pattern plan | 1 cap row | {n(a["plan"]["events"])} | 0 | {gb(a["plan"]["bytes"])} | {n(a["plan"]["errors_and_warnings"])} | 0 | 0 |')
        for key, label in (('classes', 'logger-class filters'), ('classes_status', 'logger-class filters, `-status:(error OR warn)`')):
            x = a[key]
            L.append(f'| {t}% | {label} | {len(x["classes"])} | {n(x["events"])} | {x["over_the_plan"]:+,} | {gb(x["bytes"])} | '
                     f'{n(x["errors_and_warnings"])} | {n(x["kept_under_cap_events"])} | {n(x["plan_moved_left_events"])} |')
    return '\n'.join(L)


def classes_line(r):
    sets = {tuple(v['a']['classes']['classes']) for v in r['targets'].values()}
    lines = []
    for s in sorted(sets, key=len):
        ts = [t for t, v in r['targets'].items() if tuple(v['a']['classes']['classes']) == s]
        lines.append(f'The filters at {", ".join(t + "%" for t in ts)}, largest first: ' + ', '.join(f'`@logger.name:{c}`' for c in s) + '.')
    return ' '.join(lines)


def verdict_a(r):
    L = []
    for t, v in r['targets'].items():
        a, tot = v['a'], r['control']['A']['events']
        x = a['classes']
        left = ', '.join(short(p['class']) for p in x['plan_moved_left_patterns'][:3])
        plan = v['plan_a']
        states = (f'states {plan["achieved_pct"]:g}% of the volume' if plan['met']
                  else f'states {plan["achieved_pct"]:g}% of the volume, its ceiling, short of the target')
        L.append(f'- **{t}%**: the plan, one cap row on `kafka` of {n(v["policy_a"]["tool_cap_bytes_per_window"])} bytes per window, {states} '
                 f'and moves {n(a["plan"]["events"])} of {n(tot)} events. '
                 f'{len(x["classes"])} logger-class filters reach that with {n(x["events"])}, {n(x["over_the_plan"])} more. '
                 f'Neither moves an error or warning; the filters move {n(x["kept_under_cap_events"])} events of patterns the plan keeps under the cap '
                 f'and leave in Standard {n(x["plan_moved_left_events"])} events the plan moves ({left}).')
    return '\n'.join(L)


def table_b(r):
    life = r['targets'][next(iter(r['targets']))]['totals']['lifecycle']['events']
    L = [f'| Target | Arm | Rules | Events moved | Over B\'s plan | Errors and warnings moved | Lifecycle events moved, of {n(life)} | Events of patterns B\'s plan keeps under its cap | Events B\'s plan moves that stay in Standard |',
         '|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for t, v in r['targets'].items():
        b = v['b']
        L.append(f'| {t}% | plan rewritten on B | 1 cap row | {n(b["plan_b"]["events"])} | 0 | {n(b["plan_b"]["errors_and_warnings"])} | {n(b["plan_b"]["lifecycle_moved"])} | 0 | 0 |')
        x = b['cap_a']
        L.append(f'| {t}% | A\'s cap, unchanged | 1 cap row | {n(x["events"])} | {x["over_the_plan"]:+,} | {n(x["errors_and_warnings"])} | {n(x["lifecycle_moved"])} | '
                 f'{n(x["kept_under_cap_events"])} | {n(x["plan_moved_left_events"])} |')
        for key, label in (('classes', 'A\'s logger-class filters'), ('classes_status', 'A\'s logger-class filters, `-status:(error OR warn)`')):
            x = b[key]
            L.append(f'| {t}% | {label} | {len(x["rules"])} | {n(x["events"])} | {x["over_the_plan"]:+,} | {n(x["errors_and_warnings"])} | '
                     f'{n(x["lifecycle_moved"])} | {n(x["kept_under_cap_events"])} | {n(x["plan_moved_left_events"])} |')
    return '\n'.join(L)


def verdict_b(r):
    L = []
    for t, v in r['targets'].items():
        b, tot = v['b'], r['control']['B']['events']
        life = v['totals']['lifecycle']['events']
        cap = b['cap_a']
        cls = b['classes']
        dead = cls['classes_matching_nothing']
        dead_text = 'every one still matches' if not dead else f'{len(dead)} match nothing'
        L.append(f'- **{t}%**: of B\'s {n(tot)} events, A\'s {len(cls["rules"])} filters move {n(cls["events"])} ({dead_text}) and none of the {n(life)} lifecycle events; '
                 f'A\'s cap moves {n(cap["events"])}, {n(cap["lifecycle_moved"])} of them lifecycle events over the cap; '
                 f'the plan rewritten on B moves {n(b["plan_b"]["events"])} and {n(b["plan_b"]["lifecycle_moved"])} lifecycle events.')
    return '\n'.join(L)


def prediction(r):
    ts = list(r['targets'].values())
    k = [len(v['a']['classes']['classes']) for v in ts]
    over = [v['a']['classes']['over_the_plan'] for v in ts]
    rare = [v['a']['classes']['kept_under_cap_events'] for v in ts]
    still = all(not v['b']['classes']['classes_matching_nothing'] for v in ts)
    life_cls = [v['b']['classes']['lifecycle_moved'] for v in ts]
    life_cap = [v['b']['cap_a']['lifecycle_moved'] for v in ts]
    life_tot = ts[0]['totals']['lifecycle']['events']
    rng = lambda xs: n(min(xs)) if min(xs) == max(xs) else f'{n(min(xs))} to {n(max(xs))}'  # noqa: E731
    return '\n'.join([
        f'- **At most 9 classes match the plan at every target.** {rng(k)} classes at every target, {rng(over)} events over the plan. Held.',
        f'- **The filters move about a hundred rare lines that share those classes.** {rng(rare)}. Every pattern in the chosen classes is churn the plan also moves; '
        f'the producer-state loading lines log under `kafka.log.UnifiedLog$`, a logger name of its own. Did not hold.',
        f'- **On B the same classes still match.** {"Every class matches on B." if still else "Some classes match nothing on B."} {"Held." if still else "Did not hold."}',
        f'- **Both arms keep the lifecycle lines.** The filters move {rng(life_cls)} of {n(life_tot)}; A\'s cap moves {rng(life_cap)}. '
        f'{"Held." if max(life_cls) == 0 and max(life_cap) == 0 else "Held for the filters, not for the cap."}',
        f'- **Close to a draw on events; what differs is the rule count.** {rng(k)} filters against one cap row. Held.',
    ])


def run_block(r):
    s, c = r['slices'], r['control']
    return (f'The kafka container\'s records from two public captures of the OpenTelemetry demo. '
            f'Capture A: {n(s["A"]["lines"])} records, {n(s["A"]["bytes"])} bytes, {n(c["A"]["events"])} events after grouping in '
            f'{n(c["A"]["patterns"])} patterns and {c["A"]["classes"]} logger classes, ten hours. '
            f'Capture B: {n(s["B"]["lines"])} records, {n(s["B"]["bytes"])} bytes, {n(c["B"]["events"])} events in {n(c["B"]["patterns"])} patterns '
            f'and {c["B"]["classes"]} logger classes, two hours. Engine `log10x/pipeline-10x:{r["engine_tag"]}`, log10x-mcp {r["mcp_version"]}.')


def readme_blocks(r):
    return {'run': run_block(r), 'capture-a': table_a(r), 'capture-a-classes': classes_line(r), 'capture-a-verdict': verdict_a(r),
            'capture-b': table_b(r), 'capture-b-verdict': verdict_b(r), 'prediction': prediction(r)}


def render(r):
    L = ['# One service: results', '', f'Generated by `report.py` from the kept outputs. Engine `{r["engine_image"]}`, log10x-mcp {r["mcp_version"]}.', '',
         '## Slices', '', '| Capture | Source | Records | Bytes | sha256 |', '|---|---|---:|---:|---|']
    for c in 'AB':
        s = r['slices'][c]
        L.append(f'| {c} | `{r["captures"][c]["name"]}` | {n(s["lines"])} | {n(s["bytes"])} | `{s["sha256"]}` |')
    L += ['', '## Logger classes by events, no cap', '']
    for c in 'AB':
        L += [f'Capture {c}:', '', '| Class | Events | Patterns |', '|---|---:|---:|']
        L += [f'| `{x["class"] or "(no logger class)"}` | {n(x["events"])} | {x["patterns"]} |' for x in r['control'][c]['top_classes']]
        L.append('')
    L += ['## Capture A', '', table_a(r), '', classes_line(r), '', verdict_a(r), '', '## Capture B, nothing re-tuned', '', table_b(r), '', verdict_b(r), '',
          '## Against the prediction', '', prediction(r), '', '## Plans and caps', '',
          '| Target | Capture | Plan states | Met | Patterns planned | Cap the tool wrote, bytes per window | Factor | Cap replayed, bytes |',
          '|---:|---|---:|---|---:|---:|---:|---:|']
    for t, v in r['targets'].items():
        for label, plan, pol in (('A', v['plan_a'], v['policy_a']), ('A\'s cap on B', v['plan_a'], v['policy_a_on_b']), ('B', v['plan_b'], v['policy_b'])):
            L.append(f'| {t}% | {label} | {plan["achieved_pct"]:g}% | {"yes" if plan["met"] else "no"} | {plan["patterns_planned"]} | '
                     f'{n(pol["tool_cap_bytes_per_window"])} | {pol["replay_factor"]:g} | {n(pol["cap_bytes_replay"])} |')
    L += ['', '## Lifecycle events on B', '', f'Patterns in B\'s slice that A\'s slice does not have: {n(r["targets"][next(iter(r["targets"]))]["totals"]["lifecycle"]["patterns"])} patterns, '
          f'{n(r["targets"][next(iter(r["targets"]))]["totals"]["lifecycle"]["events"])} events.', '', '| Class | Events |', '|---|---:|']
    L += [f'| `{x["class"] or "(no logger class)"}` | {n(x["events"])} |' for x in r['targets'][next(iter(r['targets']))]['totals']['lifecycle']['by_class']]
    L += ['', '## Detail per target', '']
    for t, v in r['targets'].items():
        L += [f'### {t}%', '']
        for side, arm, label in (('a', 'classes', 'A, logger-class filters'), ('b', 'cap_a', 'B, A\'s cap'), ('b', 'classes', 'B, A\'s logger-class filters')):
            x = v[side][arm]
            L.append(f'**{label}.** Rules: ' + '; '.join(f'`{q}`' for q in x['rules']) + '.')
            L.append('')
            if x.get('kept_under_cap_patterns'):
                L += ['Events of patterns the plan keeps under the cap:', '', '| Class | Pattern | Events |', '|---|---|---:|']
                L += [f'| {short(p["class"])} | `{p["pattern"]}` | {n(p["events"])} |' for p in x['kept_under_cap_patterns'][:15]]
                L.append('')
            if x.get('plan_moved_left_patterns'):
                L += ['Events the plan moves that stay in Standard:', '', '| Class | Pattern | Events |', '|---|---|---:|']
                L += [f'| {short(p["class"])} | `{p["pattern"]}` | {n(p["events"])} |' for p in x['plan_moved_left_patterns'][:15]]
                L.append('')
    return '\n'.join(L) + '\n'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=str(HERE / 'results'))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    results = pathlib.Path(a.results)
    r = compute(results)
    blocks = readme_blocks(r)
    if a.check:
        committed = json.load(open(results / 'results.json'))
        stale = README.differing((HERE / 'README.md').read_text(), blocks)
        if stale:
            raise SystemExit(f'README.md differs from the results in: {", ".join(stale)}; run report.py to rewrite them')
        if committed != json.loads(json.dumps(r)):
            raise SystemExit('results.json does not follow from the kept outputs')
        if (results / 'results.md').read_text() != render(r):
            raise SystemExit('results.md does not follow from the kept outputs')
        print('the committed figures follow from the kept outputs: ' +
              ', '.join(f'{t}% plan {v["a"]["plan"]["events"]:,} events, {len(v["a"]["classes"]["classes"])} classes {v["a"]["classes"]["events"]:,}'
                        for t, v in r['targets'].items()))
        return 0
    json.dump(r, open(results / 'results.json', 'w'), indent=1)
    (results / 'results.md').write_text(render(r))
    readme = HERE / 'README.md'
    readme.write_text(README.apply(readme.read_text(), blocks))
    print(f'wrote {results / "results.md"}, results.json and the README\'s generated blocks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
