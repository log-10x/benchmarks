#!/usr/bin/env python3
"""
Write the engine's two files from what the MCP returned, unchanged but for the replay's
time scale.

The tool's `engine_policy` holds `caps.csv` and `actions.csv` as the engine reads them:
a cap is bytes per pattern per 240 s regulator window, scaled by the tool from the span
its plan covers. The replay delivers the whole capture inside one window, so every cap is
multiplied by that span over 240 s; the actions file is copied as it is. Nothing else is
derived here.
"""
import argparse
import json
import pathlib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True, help='plan-<target>.json written by plan.mjs')
    ap.add_argument('--out-prefix', required=True)
    a = ap.parse_args()
    plan_file = json.load(open(a.plan))
    policy = plan_file.get('engine_policy')
    if not policy:
        raise SystemExit('the tool returned no engine_policy: the plan has no volume action')
    span = int(policy['span_seconds'])
    window = int(policy['reset_window_seconds'])
    factor = span / window
    caps_out = ['container,cap']
    rows = []
    for line in policy['caps_csv'].splitlines()[1:]:
        if not line.strip():
            continue
        container, value = line.split(',', 1)
        bytes_text, rest = value.split(':', 1)
        cap = int(bytes_text)
        scaled = max(1, round(cap * factor))
        caps_out.append(f'{container},{scaled}:{rest}')
        rows.append({'container': container, 'cap_bytes_per_window': cap, 'cap_bytes_replay': scaled})
    prefix = pathlib.Path(a.out_prefix)
    open(f'{prefix}.caps.csv', 'w').write('\n'.join(caps_out) + '\n')
    open(f'{prefix}.actions.csv', 'w').write(policy['actions_csv'])
    actions = {l.split(',', 1)[0]: l.split(',', 1)[1].split(':', 1)[0] for l in policy['actions_csv'].splitlines()[1:] if l.strip()}
    json.dump({
        'target_pct': (plan_file.get('plan') or {}).get('targetPct'),
        'tool_caps_csv': policy['caps_csv'],
        'tool_actions_csv': policy['actions_csv'],
        'span_seconds': span,
        'reset_window_seconds': window,
        'replay_factor': factor,
        'unattributed_planned': policy.get('unattributed_planned', 0),
        'containers': {r['container']: {'action': actions.get(r['container']), **r} for r in rows},
    }, open(f'{prefix}.json', 'w'), indent=1)
    print(f'{len(rows)} container rows from the tool, caps x {factor:g} for the one-window replay; '
          + ', '.join(f"{r['container']}={actions.get(r['container'])}" for r in rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
