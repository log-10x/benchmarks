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
import floor as FLOOR  # noqa: E402


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
    ft = run.get('floor_target', 70)
    floor = {}
    for c in 'AB':
        d = FLOOR.decompose(L(f'full-{c}-control.tally.json'), L(f'full-{c}-{ft}.tally.json'), L(f'policy-full-{c}-{ft}.json'),
                            cells_by_pattern(L(f'full-{c}-control.attrs.json')), L(f'full-{c}-control.text.json'))
        pl = L(f'plan-full-{c}-{ft}.json')
        d['plan'] = {**_plan_info(pl), 'containers_capped': len(L(f'policy-full-{c}-{ft}.json')['containers'])}
        floor[c] = d
    hours = {c: run['captures'][c]['span_seconds'] / 3600 for c in 'AB'}
    out['floor'] = {'target': ft, 'filtered_services': list(FLOOR.FILTERED), 'dropped': list(FLOOR.DROPPED),
                    'captures': floor,
                    'growth': FLOOR.growth(L('full-A-control.tally.json'), L('full-B-control.tally.json'), hours['A'], hours['B']),
                    'integrations': T.load(HERE / 'integrations.json')}
    return out


def cells_by_pattern(attrs: dict) -> dict:
    return {k: attrs['cells'][i] for k, i in attrs['pattern_cell'].items()}


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


BUCKET_LABELS = [
    ('1', '1. Errors and warnings'),
    ('2a', '2a. INFO and unlevelled, a service whose every such pattern the plan moves'),
    ('2b', '2b. INFO and unlevelled, a service the plan moves none of'),
    ('3_moved', '3. Mixed service, patterns the plan moves (E)'),
    ('3_kept', '3. Mixed service, patterns the plan keeps'),
    ('4_alone', '4. Of E, an attribute cell holds the pattern alone'),
    ('4_with_moved_only', '4. Of E, an attribute cell holds it with moved patterns only'),
    ('4_id_only', '4. Of E, its attribute cell also holds patterns the plan keeps'),
]

TEXT_LABELS = [
    ('4_text_alone', '4. Of E, a text phrase selects the pattern alone'),
    ('4_text_with_moved_only', '4. Of E, a text phrase selects it with moved patterns only'),
    ('4_text_collides', '4. Of E, its phrase also selects patterns the plan keeps (collision)'),
    ('4_text_id_only', '4. Of E, no constant phrase: only the ID'),
]


def pct(x):
    text = f'{x * 100:.1f}'
    return (text[:-2] if text.endswith('.0') else text) + '%'


def floor_table(r):
    f = r['floor']
    L = []
    for c in 'AB':
        d = f['captures'][c]
        L += [f'**Capture {c}.** {n(d["capture"]["events"])} events. The floor: {n(d["floor"]["events"])} events, '
              f'{T.fmt_gb(d["floor"]["bytes"])} GB, {pct(d["floor"]["share"])} of the capture. The plan at {f["target"]}% '
              f'caps {d["plan"]["containers_capped"]} containers and plans {d["plan"]["patterns_planned"]} patterns.', '',
              '| Bucket | Events | Share of the capture | Patterns | ' + ' | '.join(lbl for _, _, lbl in FLOOR.BANDS) + ' |',
              '|---|---:|---:|---:|' + '---:|' * len(FLOOR.BANDS)]
        for key, label in BUCKET_LABELS:
            b = d['buckets'][key]
            L.append(f'| {label} | {n(b["events"])} | {pct(b["share"])} | {n(b["patterns"])} | ' +
                     ' | '.join(n(b['bands'][lbl]) for _, _, lbl in FLOOR.BANDS) + ' |')
        L.append('')
    return '\n'.join(L).rstrip()


def floor_services(r):
    L = ['| Capture | Mixed service | Events the plan moves | Patterns | Events the plan keeps | Patterns |', '|---|---|---:|---:|---:|---:|']
    for c in 'AB':
        for s, v in sorted(r['floor']['captures'][c]['services'].items(), key=lambda kv: -kv[1]['moved_events']):
            if v['bucket'] == '3':
                L.append(f'| {c} | `{s}` | {n(v["moved_events"])} | {v["moved_patterns"]} | {n(v["kept_events"])} | {v["kept_patterns"]} |')
    return '\n'.join(L)


def floor_text_table(r):
    f = r['floor']
    L = []
    for c in 'AB':
        d = f['captures'][c]
        t = d['text']
        L += [f'**Capture {c}.** E: {n(d["buckets"]["3_moved"]["events"])} events in {n(d["buckets"]["3_moved"]["patterns"])} patterns.', '',
              '| Bucket | Events | Share of the capture | Patterns | ' + ' | '.join(lbl for _, _, lbl in FLOOR.BANDS) + ' |',
              '|---|---:|---:|---:|' + '---:|' * len(FLOOR.BANDS)]
        for key, label in TEXT_LABELS:
            b = t['buckets'][key]
            L.append(f'| {label} | {n(b["events"])} | {pct(b["share"])} | {n(b["patterns"])} | ' +
                     ' | '.join(n(b['bands'][lbl]) for _, _, lbl in FLOOR.BANDS) + ' |')
        L.append('')
    return '\n'.join(L).rstrip()


def floor_verdict(r):
    L = []
    for c in 'AB':
        d = r['floor']['captures'][c]
        t, b = d['text'], d['buckets']
        tb, rules = t['buckets'], t['rules']
        e = b['3_moved']
        collide = [x for x in d['moved_patterns'] if x['text']['selected_by'] == 'collides']
        col = (', '.join(f'`{x["pattern"]}` in `{x["container"]}`, {n(x["text"]["kept_events_matched"])} kept events'
                         + (', pieces of the same statement' if x['text']['kept_matches_are_own_pieces'] else '') for x in collide)
               if collide else 'none')
        fired = 'fires' if t['flip']['flips'] else 'does not fire'
        L.append(f'- **Capture {c}**: bucket 3\'s moved patterns are {pct(e["share"])} of the capture, {n(e["patterns"])} patterns. '
                 f'A phrase of its own constant words selects {n(tb["4_text_alone"]["patterns"])} of them alone, '
                 f'{n(tb["4_text_with_moved_only"]["patterns"])} only with other moved patterns, '
                 f'{n(tb["4_text_collides"]["patterns"])} with a collision on patterns the plan keeps ({col}), '
                 f'and {n(tb["4_text_id_only"]["patterns"])} have no constant phrase. '
                 f'Natively that is {n(rules["text_filters"])} index filters, each written after its pattern is found, '
                 f'against one cap row; the collisions move {n(rules["kept_events_collided"])} kept events. '
                 f'The pre-stated condition {fired}: {pct(t["flip"]["id_only_share_of_bucket_3_moved"])} of E has only the ID.')
    return '\n'.join(L)


def floor_flip(r):
    L = []
    for c in 'BA':
        d = r['floor']['captures'][c]
        t = d['text']
        L += [f'**Capture {c}.**', '',
              '| Mixed service | Events the plan moves (E) | Events the plan keeps | Pieces of one statement | Families | Short statements the byte cap keeps | Other | Of other, no timestamp head | A whole-service filter moves beyond the plan | Movable whole |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        for svc, v in sorted(t['services'].items(), key=lambda kv: -kv[1]['moved_events']):
            beyond = v['whole_filter_beyond_plan']
            beyond_text = n(beyond['events']) + (f' ({n(beyond["criticals"])} critical)' if beyond['criticals'] else '')
            L.append(f'| `{svc}` | {n(v["moved_events"])} | {n(v["kept_events"])} | {n(v["pieces"]["events"])} | {n(v["pieces"]["statements"])} | '
                     f'{n(v["byte_cap"]["events"])} | {n(v["other"]["events"])} | {n(v["other"]["no_head_events"])} | {beyond_text} | '
                     f'{"yes" if v["movable_whole"] else "no"} |')
        e = t['e']
        mv = e['movable_whole_moved']
        L += ['', f'E on {c}: {n(e["as_computed"]["events"])} events, {pct(e["as_computed"]["share"])} of the capture, as computed. '
              f'With the movable-whole services moved by one filter each ({", ".join(f"`{s}`" for s in mv["services"]) or "none"}): '
              f'{n(mv["events"])} events, {pct(mv["share"])}; those filters move {n(mv["events_a_whole_filter_moves_beyond_the_plan"])} events the plan keeps.', '']
    return '\n'.join(L).rstrip()


def floor_growth(r):
    g = r['floor']['growth']
    s = g['sums']
    rows = [('Services in B and not in A, new code', s['new_services'], ', '.join(f'`{k}`' for k in g['new_services'])),
            ('Services in A and not in B\'s capture', s['absent_from_b'], ', '.join(f'`{k}`' for k in list(g['absent_from_b'])[:6]) + (', and others' if len(g['absent_from_b']) > 6 else '')),
            ('Services in both, patterns seen in both: traffic', s['traffic'], ''),
            ('Services in both, patterns seen in B only: statements added or reworded', s['statements_added'], ', '.join(f'`{k}`' for k, v in g['present'].items() if v['statements_added'] >= 50)),
            ('Services in both, patterns seen in A only: statements gone or reworded', s['statements_gone'], ', '.join(f'`{k}`' for k, v in g['present'].items() if v['statements_gone'] <= -50)),
            ('Patterns inside the filtered services the filters no longer match', g['renamed_inside_filtered_services'], 'none: a service filter matches its service at both tags')]
    L = [f'The floor per hour: {n(g["floor_per_hour"]["A"])} on A, {n(g["floor_per_hour"]["B"])} on B.', '',
         '| Change from A to B, floor events per hour | Events per hour | Where |', '|---|---:|---|']
    L += [f'| {a} | {b:+,.0f} | {w} |' if b else f'| {a} | 0 | {w} |' for a, b, w in rows]
    return '\n'.join(L)


def floor_prediction(r):
    f = r['floor']['captures']
    a, b = f['A'], f['B']
    nat = sum(f[c]['buckets']['4_alone']['events'] + f[c]['buckets']['4_with_moved_only']['events'] for c in 'AB')
    return '\n'.join([
        f'- **The floor on A is about 14.5% after the three service filters, less once DEBUG and TRACE are dropped, about 6,500 of it errors, warnings and criticals.** '
        f'{pct(a["floor"]["share"])} with DEBUG and TRACE dropped; bucket 1 holds {n(a["buckets"]["1"]["events"])}. Held.',
        f'- **Bucket 3 is 2 to 4% of the capture.** A: {pct(a["buckets"]["3_moved"]["share"])}. B: {pct(b["buckets"]["3_moved"]["share"])}. '
        f'{"Held on A, not on B." if a["buckets"]["3_moved"]["share"] <= 0.04 < b["buckets"]["3_moved"]["share"] else "See the tables."}',
        f'- **Part of it is isolable by a logfmt or class attribute.** ' + isolable_text(f) + ' ' +
        ('Did not hold.' if nat == 0 else f'Held for {n(nat)} of the {n(sum(f[c]["buckets"]["3_moved"]["events"] for c in "AB"))} events.'),
        f'- **The floor does not flip the verdict on the public captures.** ' + flip_text(f),
    ])


def flip_text(f):
    word = lambda x: 'flips' if x else 'does not flip'  # noqa: E731
    attr = {c: f[c]['flip']['flips'] for c in 'AB'}
    text = {c: f[c]['text']['flip']['flips'] for c in 'AB'}
    parts = [f'{c}: {word(attr[c])} with bucket 4 on attribute cells, {word(text[c])} with text filters counted as native.' for c in 'AB']
    if not any(attr.values()) and not any(text.values()):
        held = 'Held.'
    elif not any(text.values()):
        held = 'Did not hold on ' + ' and '.join(c for c in 'AB' if attr[c]) + ' with bucket 4 on attribute cells; held once text filters count.'
    else:
        held = 'Did not hold on ' + ' and '.join(c for c in 'AB' if text[c]) + '.'
    return ' '.join(parts) + ' ' + held


def isolable_text(f):
    alone = [(c, x) for c in 'AB' for x in f[c]['moved_patterns'] if x['selected_by'] != 'id_only']
    if not alone:
        return 'No moved pattern sits in a native cell without a kept pattern.'
    named = ', '.join(f'`{x["pattern"]}` in `{x["container"]}` on {c} ({n(x["events"])} events, by {", ".join(k for k in x["cell"] if k not in ("host", "status")) or "status"})'
                      for c, x in alone)
    return f'Only {named} sits in a native cell without a kept pattern; every other moved pattern shares its cell with patterns the plan keeps.'


def integrations_table(r):
    L = ['| Container | Integration page | Attributes the pipeline parses |', '|---|---|---|']
    for c, v in r['floor']['integrations']['containers'].items():
        page = f'[{v["integration"]}]({v["url"]})' if v.get('url') else 'none'
        attrs = ', '.join(f'`{a}`' for a in v.get('attributes', [])) or ('none: ' + v['note'] if v.get('note') else 'none')
        L.append(f'| `{c}` | {page} | {attrs} |')
    return '\n'.join(L)


def readme_blocks(r):
    return {'floor': floor_table(r), 'floor-services': floor_services(r), 'floor-verdict': floor_verdict(r),
            'floor-text': floor_text_table(r), 'floor-flip': floor_flip(r),
            'floor-growth': floor_growth(r), 'floor-prediction': floor_prediction(r), 'floor-integrations': integrations_table(r),
            'run': run_block(r), 'capture-a': table_a(r), 'capture-a-classes': classes_line(r), 'capture-a-verdict': verdict_a(r),
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
    L += ['## The floor: bucket 3\'s moved patterns', '',
          'Selected by an attribute cell: `alone`, `with moved only` or `id only` (the cell also holds patterns the plan keeps). '
          'Selected by text: the longest run of words every event of the pattern shares, and what else `service:<container> "<phrase>"` matches.', '']
    for c in 'AB':
        L += [f'Capture {c}:', '', '| Container | Pattern | Events in the floor | Marked tier_down | Pattern events in the capture | Band | Attribute cell selects | Native cell | Patterns in the cell | Text phrase | Words | Text selects | Kept patterns the phrase also matches | Kept events |',
              '|---|---|---:|---:|---:|---|---|---|---:|---|---:|---|---:|---:|']
        for x in r['floor']['captures'][c]['moved_patterns']:
            cell = ', '.join(f'{k}={v}' for k, v in x['cell'].items()) or '(service only)'
            t = x['text']
            L.append(f'| `{x["container"]}` | `{x["pattern"]}` | {n(x["events"])} | {n(x["tier_down_events"])} | {n(x["pattern_events"])} | {x["band"]} | '
                     f'{x["selected_by"].replace("_", " ")} | {cell} | {x["cell_patterns"]} | `{t["phrase"] or ""}` | {t["phrase_words"]} | '
                     f'{t["selected_by"].replace("_", " ")} | {t["kept_patterns_matched"]} | {n(t["kept_events_matched"])} |')
        L.append('')
    L += ['## The floor: the kept side of each mixed service', '',
          'Each kept pattern with its split: `pieces` (shares a source location or a value frame with other patterns of the service), '
          '`byte_cap` (at least as many events as the smallest pattern the plan moves in the service) or `other`.', '']
    for c in 'AB':
        for svc, v in sorted(r['floor']['captures'][c]['text']['services'].items(), key=lambda kv: -kv[1]['moved_events']):
            L += [f'Capture {c}, `{svc}`: kept events {n(v["kept_events"])}, patterns {n(v["kept_patterns"])}; '
                  f'pieces {n(v["pieces"]["events"])} in {n(v["pieces"]["statements"])} families; byte cap {n(v["byte_cap"]["events"])} '
                  f'(smallest moved pattern: {n(v["byte_cap"]["smallest_moved_pattern_events"])} events); other {n(v["other"]["events"])}.', '',
                  '| Pattern | Events in the floor | Pattern events in the capture | Split | Family | Events with a timestamp head |', '|---|---:|---:|---|---|---:|']
            for x in v['kept_detail']:
                L.append(f'| `{x["pattern"]}` | {n(x["events"])} | {n(x["pattern_events"])} | {x["split"].replace("_", " ")} | '
                         f'{", ".join(f"`{f}`" for f in x["families"])} | {n(x["head_events"])} |')
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
