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
    L.append(f"What the scheduled run's {w['over_10s']:,} records over 10 s waited for: {w['back_within_5s_after_next_line']:,} came back within 5 s after their own container's next raw line (median {s(w['median_s_after_next_line'], 2)} s after it), {w['with_a_next_line'] - w['back_within_5s_after_next_line']:,} later than that, {w['no_next_line_before_stop']:,} had no next line before the stop. The Receiver seals an open event on its source's next head line, on the group size limit, or after 5 s with nothing arriving on the whole input, a timer that is not per source (E81). The waits measured here match the first case: a record came back once its container wrote again.\n")
    la = A['latency_all']
    L.append(f"Every returned record from the first Receiver start ({la['records']:,}): median {s(la['median'], 2)}, p99 {s(la['p99'], 2)}, max {s(la['max'], 1)}; {la['over_10s']:,} over 10 s, by when the line was written: " + ', '.join(f"{k} {v:,}" for k, v in A['latency_over_10s_by_phase'].items()) + '. `latency-over-10s.csv` lists every one with its container.\n')
    L.append('| container | records | median | p99 | max | over 10 s |\n|---|---|---|---|---|---|')
    for c, v in A['latency'].items():
        L.append(f"| {c} | {v['records']:,} | {s(v['median'], 2)} | {s(v['p99'], 2)} | {s(v['max'], 1)} | {v['over_10s']:,} |")
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

    notes = os.path.join(RESULTS, 'notes.md')
    if os.path.exists(notes):
        L.append('## Reading\n')
        L.append(open(notes).read().strip() + '\n')
    open(os.path.join(RESULTS, 'results.md'), 'w').write('\n'.join(L) + '\n')
    print('wrote', os.path.join(RESULTS, 'results.md'))


if __name__ == '__main__':
    main()
