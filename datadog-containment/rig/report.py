#!/usr/bin/env python3
"""Render results/results.md from analysis.json and the run's own files (analyze.py first).
A hand-written results/notes.md, when present, is included verbatim under "Reading"."""
import json, os, sys, csv, datetime

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')


def hms(t):
    return '' if t is None else datetime.datetime.fromtimestamp(float(t), datetime.timezone.utc).strftime('%H:%M:%S')


def n(v):
    return f'{v:,}' if isinstance(v, int) else (f'{v:,.1f}' if isinstance(v, float) else str(v))


def s(v, k=1):
    return '' if v is None else f'{v:.{k}f}'


def esc(t, k=90):
    return str(t)[:k].replace('|', '/').replace('\t', ' ').replace('\n', ' ')


def main():
    A = json.load(open(os.path.join(RESULTS, 'analysis.json')))
    prev = os.path.join(RESULTS, 'previous-runs.json')
    A['previous'] = json.load(open(prev))['runs'] if os.path.exists(prev) else []
    launch = json.load(open(os.path.join(RESULTS, 'values-fleet', 'launch.json')))
    poc = json.load(open(os.path.join(RESULTS, 'planner', 'poc-args.json')))
    env = json.load(open(os.path.join(RESULTS, 'planner', 'poc-envelope.json')))
    d = env.get('data', env)
    fd = d['fleet_default']
    plan = d.get('plan') or {}
    caps = open(os.path.join(RESULTS, 'values-fleet', 'caps.csv')).read().strip()
    actions = open(os.path.join(RESULTS, 'values-fleet', 'actions.csv')).read().strip()
    ph = A['phases']
    L = []
    L.append('# Containment demo: a fleet-default cap on the OpenTelemetry demo\'s own incidents\n')
    L.append('All figures below come from this run\'s files in `results/` and are rendered by `rig/report.py` from `rig/analyze.py`\'s `analysis.json`.\n')

    L.append('## What ran\n')
    L.append(f"- OpenTelemetry demo 3.1.0 (`compose.yaml` + `compose.full.yaml`), every container's stdout and stderr through the Docker `fluentd` driver to Fluent Bit 4.2, which keeps a raw copy, hands each record to the log10x Receiver and writes what comes back to one file per `routeState`.")
    L.append(f"- Receiver: `{launch['image']}`, the released image with its own config and modules, launched with the values log10x-mcp {launch['mcp_version']} renders (below).")
    L.append(f"- Plan: log10x-mcp {poc['mcp_version']} `poc_from_local` on the quiet capture with `{json.dumps(poc['args']['fleet_default'])}`, engine `{poc['engine_image']}`.")
    rig_overlay = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'compose.rig.yaml')
    if os.path.exists(rig_overlay) and 'FLAGD_CACHE=disabled' in open(rig_overlay).read():
        L.append("- Demo setting from the rig: `FLAGD_CACHE=disabled` on checkout, so its flagd provider asks flagd on every order and a scheduled kafkaQueueProblems change reaches it (`rig/README.md`, \"checkout's flag cache\").")
    acts = A.get('activations', [])
    if acts:
        L.append(f"- Scheduler: flagd-ui, seed {A['seed']}, interval 600 s, hold 240 to 480 s, one flag at a time, flags kafkaQueueProblems (on), cartFailure (100%), paymentFailure (100%), recommendationCacheFailure (on), loadGeneratorFloodHomepage (on), emailMemoryLeak (1000x). Scheduled run {hms(ph['scheduled'][0])} to {hms(ph['scheduled'][1])} UTC on {datetime.datetime.fromtimestamp(ph['scheduled'][0], datetime.timezone.utc).date()}.")
    L.append('')

    L.append('## Timeline (UTC)\n')
    L.append('| event | at |\n|---|---|')
    for k, v in sorted(((k, t) for k, ts in ph['events'].items() for t in ts), key=lambda kv: kv[1]):
        L.append(f'| {k} | {v[11:19]} |')
    L.append('')

    L.append('## Quiet run and the fleet default\n')
    q = A['quiet']
    L.append(f"Quiet run {hms(q['start'])} to {hms(q['end'])} UTC, no flag active, Receiver with no cap: {q['raw_lines']:,} raw lines, {q['records']:,} returned records, {q['pairs']} (container, pattern) pairs in {q['containers']} containers, {q['full_windows']} full 4-minute windows, {q['held_in_quiet']} records held.\n")
    L.append(f"The POC on that capture: `met: {str(plan.get('met')).lower()}`, {float(plan.get('achievedPct') or 0):.1f}% reached against the 70% target, keep-everything lever `{plan.get('keepEverythingLever')}`; {len(plan.get('planned', []))} planned and {len(plan.get('kept', []))} kept statements.\n")
    L.append('| fleet default | value |\n|---|---|')
    L.append(f"| `cap_bytes_per_window_per_node` | **{fd['cap_bytes_per_window_per_node']:,}** |")
    L.append(f"| baseline | {fd['baseline_bytes_per_window_per_node']:,.1f} bytes per window: `{fd.get('baseline_statement')}` in {fd.get('baseline_container')} |")
    L.append(f"| headroom, action, error floor | {fd['headroom']}, `{fd['action']}`, {fd['error_floor']} |")
    L.append(f"| sentence | {fd['sentence']} |")
    b = A.get('baseline_in_receiver_bytes')
    if b:
        L.append(f"| the baseline statement in the Receiver's unit (quiet run) | {b['avg_record_bytes_per_window']:,.0f} record bytes per window on average, {b['max_record_bytes_per_window']:,} at most |")
    L.append('')
    L.append('The 20 largest (container, pattern) pairs of the quiet run, by their largest 4-minute window in the bytes the Receiver counts (the compact JSON of the record as it arrives), with the rule that covers each in the scheduled run:\n')
    L.append('| container | pattern | rule | largest window: events | bytes |\n|---|---|---|---|---|')
    for c in q['top_pairs']:
        L.append(f"| {c['container']} | `{c['pattern']}` {esc(c['name'], 50)} | {c['rule']} | {c['max_events']} | {c['max_bytes']:,} |")
    L.append('')

    L.append('## The values the Receiver ran with\n')
    L.append(f"Rendered by log10x-mcp {launch['mcp_version']} (`receiverFleetValues` with the POC's `fleet_default`, then the Fluent Bit Receiver overlay's `renderValues`, the two calls `log10x_advise_install` makes; `results/values-fleet/values.yaml` is the overlay verbatim). Arguments, in order:\n")
    L.append('```text\n' + '\n'.join(launch['args_from_values']) + '\n```\n')
    L.append('Environment from the values: ' + ', '.join(f"`{e['name']}={e['value']}`" for e in launch['env_applied']) + '. ' +
             'Substituted because there is no cluster (the MCP\'s own floor check does the same): ' +
             ', '.join(f"`{e['name']}` points at the mounted `{e['rig_value']}` instead of `{e['value']}`" for e in launch['env_substituted']) + '; ' +
             'left out: ' + ', '.join(f"`{e['name']}`" for e in launch['env_left_out_cluster_only']) + ' (the ConfigMap pull). ' +
             f"Rig plumbing: `TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit`. Measurement only, after the MCP's arguments: `{' '.join(launch['measurement_args'])}`. Resource limits from the values: {launch['resources_limits']['cpus']} CPU, {launch['resources_limits']['memory']}.\n")
    L.append(f"Policy files: {launch['policy_files']}.\n")
    L.append('```text\n' + caps + '\n```\n')
    L.append('```text\n' + actions + '\n```\n')
    cc = plan.get('containerCaps') or {}
    span_s = (d.get('span') or {}).get('seconds') if isinstance(d.get('span'), dict) else None
    if cc and span_s:
        pw = lambda v: v * 240 / span_s   # the MCP's per-window figure (build-report-data.js)
        L.append("Where each row's cap sits (`plan.containerCaps`, in bytes per 4-minute window: each statement at its busiest quiet window in the Receiver's unit, the figure caps.csv is written from): between the largest statement the plan keeps and the smallest it moves, at their geometric mean, so the margin is the same each way. A row with no kept statement gets cap 1: every statement past the first 5 a window takes the row's action.\n")
        L.append('| container | cap in caps.csv | largest kept statement | bytes per window | smallest moved statement | bytes per window | margin each way |\n|---|---|---|---|---|---|---|')
        for c, v in sorted(cc.items(), key=lambda kv: (not kv[1].get('separated'), -(kv[1].get('margin') or 0), kv[0])):
            L.append(f"| {c} | {A['config']['caps'].get(c, 0):,.0f} | {esc(v.get('keptMaxPattern') or '(none)', 50)} | {pw(v.get('keptMaxBytesMonthly') or 0):,.0f} | {esc(v.get('movedMinPattern') or '', 50)} | {pw(v.get('movedMinBytesMonthly') or 0):,.0f} | {(str(round(v['margin'], 1)) + 'x') if v.get('margin') else 'none'} |")
        L.append('')

    if not acts:
        open(os.path.join(RESULTS, 'results.md'), 'w').write('\n'.join(L) + '\n')
        return

    L.append('## Flag timeline\n')
    L.append('| # | flag | variant | on | off | planned s | actual s |\n|---|---|---|---|---|---|---|')
    for a in acts:
        L.append(f"| {a['n']} | {a['flag']} | {a['variant']} | {hms(a['on'])} | {hms(a['off']) or '(stopped)'} | {a['planned_s']:.0f} | {a['actual_s']:.0f} |")
    L.append('')

    t = A['totals_scheduled']
    L.append('## Held records, scheduled run\n')
    L.append(f"{t['returned']:,} returned records: " + ', '.join(f"{k} {v:,}" for k, v in sorted(t['routes'].items())) + '. Every hold is labelled with the rule that made it: a plan row (the container, its cap from caps.csv, `tier_down` from actions.csv) or the fleet default (a container with no row, the fleet cap, `offload`).\n')
    L.append('| rule | container | pattern | held | held bytes | severity | in a flag\'s causal span | outside | windows | quiet max events / bytes |\n|---|---|---|---|---|---|---|---|---|---|')
    for r in sorted(A['held'], key=lambda r: (r['rule'].startswith('plan'), r['container'], -r['held'])):
        sev = ', '.join(f'{k} {v:,}' for k, v in r['severity'].items())
        L.append(f"| {r['rule']} | {r['container']} | `{r['pattern']}` {esc(r['name'], 60)} | {r['held']:,} | {r['held_bytes']:,} | {sev} | {r['in_causal_span']:,} | {r['outside']:,} | {r['windows']} | {r['quiet']['max_events']} / {r['quiet']['max_bytes']:,} |")
    L.append('')

    L.append('## Per flag activation\n')
    L.append('Span: flag on to one 4-minute window after it reverts, or the next flag on. Rows are the containers on the flag\'s causal path (demo 3.1.0 source). "New" holds are patterns with no hold in the 10 minutes before the flag (or since the fleet Receiver started); "steady" holds are patterns already held then, such as every statement of a plan row with cap 1. "First noisy" is the first record of the first pattern whose records in a minute reach 5 and 5 times its rate in those 10 minutes.\n')
    L.append('| # | flag | on to off | container | rule | first noisy | first new hold | new held (offload / tier_down) | kept, same patterns | bytes held (new) | steady held | patterns newly held |\n|---|---|---|---|---|---|---|---|---|---|---|---|')
    others = []
    for pa in A['per_activation']:
        rows = [r for r in pa['containers'] if r['in_causal_path']]
        others += [(pa, r) for r in pa['containers'] if not r['in_causal_path'] and r['held'] > 0]
        if not rows:
            L.append(f"| {pa['n']} | {pa['flag']} | {hms(pa['on'])} to {hms(pa['off'])} | (no hold or noisy pattern on the causal path) | | | | 0 | | | | |")
            continue
        for r in rows:
            pats = '; '.join(f"{esc(p['name'] or p['pattern'], 40)} x{p['held']:,}" for p in r['patterns'][:4]) + (f" +{len(r['patterns']) - 4}" if len(r['patterns']) > 4 else '')
            L.append(f"| {pa['n']} | {pa['flag']} | {hms(pa['on'])} to {hms(pa['off'])} | {r['container']} | {r['rule']} | {hms(r['first_noisy'])} {esc(r['noisy_name'] or '', 30)} | {hms(r['first_held'])} | {r['held']:,} ({r['held_offload']:,} / {r['held_tier_down']:,}) | {r['kept_same_patterns']:,} | {r['held_bytes']:,} | {r['steady_held']:,} | {pats} |")
    L.append('')
    if others:
        L.append('New holds in containers off the flag\'s causal path, inside its span: ' +
                 '; '.join(f"#{pa['n']} {r['container']} {r['held']:,} ({esc(', '.join(p['name'] or p['pattern'] for p in r['patterns'][:3]), 120)}; {r['rule']})" for pa, r in others) + '.\n')

    L.append('## False holds and the plan\'s moves\n')
    fh = [r for r in A['held'] if r['route'] == 'offload' and r['outside'] > 0]
    L.append(f"Fleet-default holds outside every flag's causal span: {sum(r['outside'] for r in fh):,} records in {len(fh)} (container, pattern) pairs.\n")
    if fh:
        L.append('| container | pattern | held outside a causal span | windows | quiet run: max events, max bytes, median bytes per window |\n|---|---|---|---|---|')
        for r in sorted(fh, key=lambda r: -r['outside']):
            qq = r['quiet']
            L.append(f"| {r['container']} | `{r['pattern']}` {esc(r['name'], 60)} | {r['outside']:,} | {r['windows']} | {qq['max_events']}, {qq['max_bytes']:,}, {qq['median_bytes']:,} |")
        L.append('')
    td = A.get('plan_moves_per_window', {})
    if td:
        L.append('The plan\'s rows (`tier_down`), per container per Receiver window:\n')
        L.append('| container | cap in caps.csv | windows | median per window | max | total |\n|---|---|---|---|---|---|')
        for c, v in sorted(td.items(), key=lambda kv: -kv[1]['total']):
            L.append(f"| {c} | {A['config']['caps'].get(c, '')} | {v['windows']} | {v['median']} | {v['max']} | {v['total']:,} |")
        L.append('')

    L.append('## Errors against the 0.5 floor\n')
    e = A['errors']
    L.append(f"ERROR and CRITICAL records held: {e['held']:,}; passed: {e['passed']:,}.\n")
    if e['by_pattern']:
        L.append('| rule | container | pattern | severity | held | passed | flags |\n|---|---|---|---|---|---|---|')
        for r in e['by_pattern'][:20]:
            L.append(f"| {r['rule']} | {r['container']} | `{r['pattern']}` {esc(r['name'], 60)} | {r['severity']} | {', '.join(f'{k} {v:,}' for k, v in r['held'].items())} | {r['passed']:,} | {', '.join(f'{k} {v:,}' for k, v in r['flags'].items())} |")
        L.append('')
    fc = A['floor_check']
    L.append('Records over the cap in a replay of each Receiver window (rb_ts order; the first 5 pass, then pass while the window\'s bytes stay within the cap), by severity and what the Receiver did:\n')
    L.append('| severity | over the cap: passed | held | passed share | floor |\n|---|---|---|---|---|')
    for sev, v in sorted(fc.items()):
        p_ = v.get('pass', 0)
        h_ = sum(c for k, c in v.items() if k != 'pass')
        L.append(f"| {sev} | {p_:,} | {h_:,} | {p_ / max(p_ + h_, 1):.3f} | {A['config']['floors'].get(sev, 0)} |")
    rv = A['replay_vs_actual']
    L.append(f"\nReplay against the Receiver: under the cap and passed {rv.get('under_and_passed', 0):,}, under and held {rv.get('under_and_held', 0):,}, over and passed {rv.get('over_and_passed', 0):,}, over and held {rv.get('over_and_held', 0):,}. Windows start {A['window_phase']['phase_s_mod_240']:.1f} s past a multiple of 240 s of epoch time ({A['window_phase']['source']}); the phase read from the data alone (first pass after a run of holds) is {A['window_phase']['inferred_phase']:.0f} s, with {A['window_phase']['share_of_resets_within_20s_of_inferred']:.1%} of {A['window_phase']['resets']:,} resets within 20 s of it.\n")

    L.append('## Latency\n')
    L.append("Seconds from `fb_ts` (the Docker driver's event time for the line) to `rb_ts` (when Fluent Bit's return-path filter received the record back from the Receiver). For a record that joins several lines, `fb_ts` is its first line's.\n")
    ls = A['latency_scheduled_all']
    L.append(f"Scheduled run ({ls['records']:,} records): median {s(ls['median'], 2)}, p99 {s(ls['p99'], 2)}, max {s(ls['max'], 1)}; {ls['over_10s']:,} over 10 s.\n")
    L.append('| container | records | median | p99 | max | over 10 s |\n|---|---|---|---|---|---|')
    for c, v in A['latency_scheduled'].items():
        L.append(f"| {c} | {v['records']:,} | {s(v['median'], 2)} | {s(v['p99'], 2)} | {s(v['max'], 1)} | {v['over_10s']:,} |")
    L.append('')
    w = A['latency_over_10s_wait']
    if w['over_10s']:
        L.append(f"What the scheduled run's {w['over_10s']:,} records over 10 s waited for, from each record's last raw line and its container's next one: " +
                 ', '.join(f"{k} {v:,}" for k, v in sorted(w['by_cause'].items(), key=lambda kv: -kv[1])) +
                 (f" (median {s(w['median_s_after_next_line'], 2)} s after that line)" if w.get('median_s_after_next_line') is not None else '') + '.\n')
    ra = A.get('release_after_quiet', {}).get('all')
    if ra:
        L.append(f"Records after which their container wrote nothing for 10 s or more: {ra['records'] + ra.get('waited_for_next_line', 0):,}. {ra['records']:,} came back before the container's next line, so a timer released them" +
                 (f", {s(ra['median'], 2)} s after their last line at the median, {s(ra['min'], 2)} s at least, {s(ra['p99'], 2)} s at p99 and {s(ra['max'], 2)} s at most" if ra['records'] else '') +
                 f"; {ra.get('waited_for_next_line', 0):,} came back only with or after that next line." +
                 f" The Receiver's group step seals a source's open event on the source's next head line, on the group size limit (20,000 lines), or 5 s (`groupFlushTimeout`, which the values leave at its default) after the batch that carried the source's last line; a batch leaves the forwarder input up to 2 s after its last line (`parallelEventFlushInterval`).\n")
    if A['previous']:
        L.append("Against the earlier runs (`previous-runs.json`: each run's committed captures measured by this `analyze.py`), scheduled run, seconds as median / p99 / max:\n")
        runs = A['previous']
        L.append('| container | ' + ' | '.join(f"{r['label']} ({r['receiver_image'].split('@')[0].split(':')[-1]}, MCP {r['mcp_version']})" for r in runs) + ' | this run |\n|---|' + '---|' * (len(runs) + 1))
        cell = lambda v: f"{s(v['median'], 2)} / {s(v['p99'], 2)} / {s(v['max'], 1)} ({v['records']:,})" if v else ''
        L.append('| all | ' + ' | '.join(cell(r['latency_scheduled_all']) for r in runs) + f" | {cell(ls)} |")
        for c in sorted(set(A['latency_scheduled']).union(*[set(r['latency_scheduled']) for r in runs])):
            L.append(f"| {c} | " + ' | '.join(cell(r['latency_scheduled'].get(c)) for r in runs) + f" | {cell(A['latency_scheduled'].get(c))} |")
        L.append('')
    la = A['latency_all']
    L.append(f"Every returned record from the first Receiver start ({la['records']:,}): median {s(la['median'], 2)}, p99 {s(la['p99'], 2)}, max {s(la['max'], 1)}; {la['over_10s']:,} over 10 s, by when the line was written: " + ', '.join(f"{k} {v:,}" for k, v in A['latency_over_10s_by_phase'].items()) + '. `latency-over-10s.csv` lists every one with its container.\n')
    L.append('| container | records | median | p99 | max | over 10 s |\n|---|---|---|---|---|---|')
    for c, v in A['latency'].items():
        L.append(f"| {c} | {v['records']:,} | {s(v['median'], 2)} | {s(v['p99'], 2)} | {s(v['max'], 1)} | {v['over_10s']:,} |")
    L.append('')

    ec = A.get('early_close')
    if ec:
        L.append('## Multi-line events closed by a source\'s pause\n')
        L.append("A line of a kind the Receiver joins to the record before it anywhere in the run is not a group head. A record that begins with such a line was opened after its source's previous group had been sealed by something other than a head line, which in a running demo is the per-source flush timer. Each is set against the record before it from the same container; the pause runs from that record's last raw line to this record's first. Blank lines are left out. `early-close.csv` lists every one.\n")
        L.append(f"Scheduled run: {ec['scheduled_records_opened_by_a_non_head_line']:,} records opened by a line that is not a head; " +
                 (', '.join(f"{k} {v:,}" for k, v in ec['by_pause'].items()) + '; ' if ec['by_pause'] else '') +
                 f"{ec['within_7s_of_prev_first_line']:,} within 7 s of the previous record's first line, {ec['within_7s_same_pattern']:,} of them with the previous record's pattern.\n")
        for pr in A['previous']:
            pe = pr['early_close']
            L.append(f"{pr['label'][:1].upper() + pr['label'][1:]}, same measure: {pe['scheduled_records_opened_by_a_non_head_line']:,} records, {pe['within_7s_of_prev_first_line']:,} within 7 s of the previous record's first line, {pe['within_7s_same_pattern']:,} with its pattern.\n")
        if ec['groups']:
            L.append('| container | previous record\'s pattern | first line of the record opened | records | by pause | within 7 s | same pattern | shortest pause s | example |\n|---|---|---|---|---|---|---|---|---|')
            for g in ec['groups'][:20]:
                L.append(f"| {g['container']} | {esc(g['prev_pattern'], 50)} | `{esc(g['first_line_kind'], 48)}` | {g['records']:,} | {', '.join(f'{k} {v}' for k, v in g['by_pause'].items())} | {g['within_7s']:,} | {g['same_pattern']:,} | {s(g['pause_min_s'], 2)} | {hms(g['example_at'])} {esc(g['example_line'], 60)} |")
            L.append('')

    L.append('## Delivery\n')
    for key, title in (('delivery_scheduled', 'Scheduled run'), ('delivery_whole_run', 'Whole run, from the first Receiver start')):
        dd = A[key]
        L.append(f"{title} ({hms(dd['span'][0])} to {hms(dd['span'][1])} UTC, by `fb_ts`): raw lines against the lines the returned records cover (the Receiver joins continuation lines into one record).\n")
        L.append('| container | raw lines | returned records | lines covered | covered minus raw |\n|---|---|---|---|---|')
        tot = [0, 0, 0]
        for c, v in dd['containers'].items():
            L.append(f"| {c} | {v['raw_lines']:,} | {v['returned_records']:,} | {v['lines_covered']:,} | {v['covered_minus_raw']:+,} |")
            tot[0] += v['raw_lines']; tot[1] += v['returned_records']; tot[2] += v['lines_covered']
        L.append(f"| total | {tot[0]:,} | {tot[1]:,} | {tot[2]:,} | {tot[2] - tot[0]:+,} |\n")

    ds = A['delivery_split']
    L.append(f"Lines written up to 60 s before the stop: {ds['to_60s_before_stop']['raw_lines']:,} raw, {ds['to_60s_before_stop']['lines_covered']:,} covered. In the last 60 s: {ds['last_60s']['raw_lines']:,} raw, {ds['last_60s']['lines_covered']:,} covered; the difference is each container's last event, still open in the Receiver when the demo stopped.\n")

    wi = A.get('what_if_fleet_default_alone')
    if wi:
        L.append('## What the fleet default would hold alone\n')
        L.append(f"The same replay with the install seed in place of the plan's rows, so every container takes the fleet default ({A['config']['fleet_cap']:,.0f} bytes): {wi.get('held_expected', 0):,.0f} records held (expected, floors applied), {wi.get('held_expected_in_causal_span', 0):,.0f} of them inside a flag's causal span, {wi.get('held_expected_errors', 0):,.0f} ERROR or CRITICAL.\n")

    runs = A['previous']
    if runs:
        L.append('## Against the earlier runs\n')
        L.append("`previous-runs.json`: " + '; '.join(f"{r['label']}, commit {r['commit']}" for r in runs) + ". Each run's committed captures are measured by this `analyze.py`.\n")
        fh_now = [{'container': r['container'], 'name': r['name'], 'outside': r['outside'], 'held': r['held']} for r in A['held'] if r['route'] == 'offload' and r['outside'] > 0]
        fl = lambda f: ', '.join(f"{x['container']} `{x['name']}` {x['outside']:,} of {x['held']:,}" for x in f) or 'none'
        share = lambda fc, sev: (lambda v: f"{v.get('pass', 0) / max(sum(v.values()), 1):.3f} of {sum(v.values()):,}")(fc.get(sev, {}))
        lat = lambda v: f"{s(v['median'], 2)} / {s(v['p99'], 2)} / {s(v['max'], 1)}"
        ec = lambda e: f"{e['scheduled_records_opened_by_a_non_head_line']:,} ({e['within_7s_of_prev_first_line']:,}; same pattern {e['within_7s_same_pattern']:,})"
        dl = lambda d_: f"{d_['to_60s_before_stop']['raw_lines']:,} / {d_['to_60s_before_stop']['lines_covered']:,}"
        def kafka(pa_list):
            out = []
            for pa in pa_list:
                if pa['flag'] != 'kafkaQueueProblems':
                    continue
                out.append(f"#{pa['n']}: " + (', '.join(f"{r['container']} {r['held']:,}" for r in pa['containers'] if r['in_causal_path'] and r['held']) or 'none'))
            return '; '.join(out) or 'no activation'
        me = {'receiver_image': launch['image'], 'mcp_version': poc['mcp_version'], 'fleet_cap': A['config']['fleet_cap'], 'caps': A['config']['caps'],
              'totals_scheduled': A['totals_scheduled'], 'false_holds': fh_now, 'errors': A['errors'], 'floor_check': A['floor_check'],
              'latency_scheduled_all': A['latency_scheduled_all'], 'early_close': A['early_close'], 'delivery_split': A['delivery_split'],
              'per_activation': A['per_activation']}
        cols = runs + [me]
        rows = [
            ('Receiver', lambda r: r['receiver_image'].split('@')[0]),
            ('log10x-mcp', lambda r: r['mcp_version']),
            ('fleet default cap, bytes per window per node', lambda r: f"{r['fleet_cap']:,.0f}"),
            ('plan rows in caps.csv', lambda r: f"{len(r['caps'])}"),
            ('returned records, scheduled run', lambda r: f"{r['totals_scheduled']['returned']:,}"),
            ('routes', lambda r: ', '.join(f"{k} {v:,}" for k, v in sorted(r['totals_scheduled']['routes'].items()))),
            ('kafkaQueueProblems: new holds on the causal path', lambda r: kafka(r['per_activation'])),
            ('fleet-default holds outside every causal span (outside of held)', lambda r: fl(r['false_holds'])),
            ('ERROR and CRITICAL held / passed', lambda r: f"{r['errors']['held']:,} / {r['errors']['passed']:,}"),
            ('ERROR over the cap, share passed', lambda r: share(r['floor_check'], 'ERROR')),
            ('CRITICAL over the cap, share passed', lambda r: share(r['floor_check'], 'CRITICAL')),
            ('latency median / p99 / max, s', lambda r: lat(r['latency_scheduled_all'])),
            ('records over 10 s', lambda r: f"{r['latency_scheduled_all']['over_10s']:,}"),
            ('records opened by a line that is not a head (within 7 s)', lambda r: ec(r['early_close'])),
            ('lines written up to 60 s before the stop: raw / covered', lambda r: dl(r['delivery_split'])),
        ]
        L.append('| measure | ' + ' | '.join(r['label'] for r in runs) + ' | this run |\n|---|' + '---|' * len(cols))
        for name, f in rows:
            L.append(f"| {name} | " + ' | '.join(f(r) for r in cols) + ' |')
        L.append('')

    notes = os.path.join(RESULTS, 'notes.md')
    if os.path.exists(notes):
        L.append('## Reading\n')
        L.append(open(notes).read().strip() + '\n')
    open(os.path.join(RESULTS, 'results.md'), 'w').write('\n'.join(L) + '\n')
    print('wrote', os.path.join(RESULTS, 'results.md'))


if __name__ == '__main__':
    main()
