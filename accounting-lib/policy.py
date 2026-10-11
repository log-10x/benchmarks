#!/usr/bin/env python3
"""
Turn the plan the MCP wrote into the two files the engine reads.

The engine's rate regulator enforces a plan per container: `caps.csv` gives a container
the byte cap each of its patterns may spend per 240 s window, and `actions.csv` gives
the container the action its excess takes. The plan is written per pattern. This maps
one onto the other, and writes down every step so the result can be read back.

Containers: the plan names its patterns but attributes none of them to a service, and
the caps row it rendered keys `<container>`. Each planned pattern is placed in the
container that produced most of its bytes in the engine's own control run of the same
capture.

Action: Datadog plans tier_down only. A CloudWatch plan can offload one pattern and
tier_down another hosted in the same container; the container takes the stronger one,
offload before tier_down, the order the MCP's action-intent writer documents.

Cap: the plan's cap row is bytes per 240 s window, scaled by the MCP from the window it
was told the capture covers. The replay delivers the whole capture inside one window, so
the cap is scaled back up by that window over 240 s.
"""
import argparse
import collections
import json
import pathlib
import re

RESET_WINDOW_SECONDS = 240
ACTION_RANK = {'drop': 5, 'offload': 4, 'tier_down': 3, 'compact': 2, 'sample': 1, 'pass': 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True, help='plan-<target>.json written by plan.mjs')
    ap.add_argument('--control', required=True, help='control tally written by count.py')
    ap.add_argument('--window-seconds', type=int, required=True, help='the window the plan was told the capture covers')
    ap.add_argument('--siem', required=True)
    ap.add_argument('--out-prefix', required=True, help='writes <prefix>.caps.csv, <prefix>.actions.csv, <prefix>.json')
    a = ap.parse_args()

    plan_file = json.load(open(a.plan))
    plan = plan_file.get('plan') or {}
    planned = [{'name': r['name'], 'action': r['action'], 'severity': r.get('severity') or ''}
               for r in plan.get('planned', [])]

    tool_caps = plan_file.get('tool_caps_csv') or ''
    rows = [l for l in tool_caps.splitlines()[1:] if l.strip()]
    if len(rows) != 1:
        raise SystemExit(f'expected one cap row from the tool, found {len(rows)}: {rows}')
    key, value = rows[0].split(',', 1)
    cap_window = int(re.match(r'\d+', value).group(0))
    cap_replay = round(cap_window * a.window_seconds / RESET_WINDOW_SECONDS)

    control = json.load(open(a.control))
    bytes_by_pattern = collections.defaultdict(collections.Counter)
    for k in control['by_key']:
        bytes_by_pattern[k['pattern']][k['container']] += k['bytes']

    containers = {}
    placed = []
    for p in planned:
        hosts = bytes_by_pattern.get(p['name'])
        if not hosts:
            placed.append({**p, 'container': None})
            continue
        container, b = hosts.most_common(1)[0]
        placed.append({**p, 'container': container, 'bytes_in_capture': b})
        c = containers.setdefault(container, {'action': 'pass', 'patterns': []})
        c['patterns'].append(p['name'])
        if ACTION_RANK[p['action']] > ACTION_RANK[c['action']]:
            c['action'] = p['action']

    prefix = pathlib.Path(a.out_prefix)
    reason = f'plan {a.siem} {plan.get("targetPct")} pct; tool cap {cap_window} per {RESET_WINDOW_SECONDS} s window x {a.window_seconds}/{RESET_WINDOW_SECONDS}'
    with open(f'{prefix}.caps.csv', 'w') as f:
        f.write('container,cap\n')
        for c in sorted(containers):
            f.write(f'{c},{cap_replay}::{reason}\n')
    with open(f'{prefix}.actions.csv', 'w') as f:
        f.write('container,action\n')
        for c in sorted(containers):
            f.write(f'{c},{containers[c]["action"]}::plan {a.siem} {plan.get("targetPct")} pct\n')
    json.dump({
        'siem': a.siem,
        'target_pct': plan.get('targetPct'),
        'tool_caps_row': rows[0],
        'tool_caps_key': key,
        'cap_bytes_per_window': cap_window,
        'window_seconds': a.window_seconds,
        'reset_window_seconds': RESET_WINDOW_SECONDS,
        'cap_bytes_replay': cap_replay,
        'planned': placed,
        'containers': {c: containers[c] for c in sorted(containers)},
    }, open(f'{prefix}.json', 'w'), indent=1)
    print(f'{len(planned)} planned patterns -> {len(containers)} containers, cap {cap_window} per window -> {cap_replay} for the replay; '
          + ', '.join(f'{c}={containers[c]["action"]}' for c in sorted(containers)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
