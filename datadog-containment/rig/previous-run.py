#!/usr/bin/env python3
"""Earlier runs' headline figures, for the comparison tables in results.md.

For each earlier run, given as COMMIT=LABEL, reads that commit's committed captures and files
from git, runs this analyze.py on them in a temporary directory, so every run is measured by
the same code, and writes results/previous-runs.json in the order given.
  python3 rig/previous-run.py 8e416c6='1.1.141 run' <commit>='first 1.1.142 run'
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, '..', 'results')
BASE = 'datadog-containment/results/'
FILES = ['data/raw.jsonl.gz', 'data/pass.jsonl.gz', 'data/offload.jsonl.gz', 'data/tier_down.jsonl.gz',
         'timeline.jsonl', 'scheduler.log', 'receiver.log', 'values-fleet/launch.json', 'values-fleet/caps.csv',
         'planner/poc-envelope.json', 'planner/poc-args.json']


def measure(commit, label):
    with tempfile.TemporaryDirectory() as tmp:
        for f in FILES:
            os.makedirs(os.path.dirname(os.path.join(tmp, f)), exist_ok=True)
            got = subprocess.run(['git', '-C', HERE, 'show', f'{commit}:{BASE}{f}'], capture_output=True)
            if got.returncode == 0:
                open(os.path.join(tmp, f), 'wb').write(got.stdout)
        subprocess.run([sys.executable, os.path.join(HERE, 'analyze.py'), tmp], check=True, stdout=subprocess.DEVNULL)
        A = json.load(open(os.path.join(tmp, 'analysis.json')))
        launch = json.load(open(os.path.join(tmp, 'values-fleet', 'launch.json')))
        poc = json.load(open(os.path.join(tmp, 'planner', 'poc-args.json')))
    fh = [{'container': r['container'], 'pattern': r['pattern'], 'name': r['name'], 'outside': r['outside'], 'held': r['held']}
          for r in A['held'] if r['route'] == 'offload' and r['outside'] > 0]
    return {
        'label': label,
        'commit': commit,
        'receiver_image': launch['image'],
        'mcp_version': poc['mcp_version'],
        'scheduled': A['phases']['scheduled'],
        'fleet_cap': A['config']['fleet_cap'],
        'caps': A['config']['caps'],
        'totals_scheduled': A['totals_scheduled'],
        'activations': A['activations'],
        'per_activation': [{'n': pa['n'], 'flag': pa['flag'],
                            'containers': [{k: r[k] for k in ('container', 'rule', 'in_causal_path', 'held', 'held_offload', 'held_tier_down', 'kept_same_patterns', 'first_held')}
                                           for r in pa['containers']]} for pa in A['per_activation']],
        'false_holds': fh,
        'errors': {'held': A['errors']['held'], 'passed': A['errors']['passed']},
        'floor_check': A['floor_check'],
        'latency_scheduled_all': A['latency_scheduled_all'],
        'latency_scheduled': A['latency_scheduled'],
        'latency_over_10s_wait': A['latency_over_10s_wait'],
        'release_after_quiet': A['release_after_quiet']['all'],
        'early_close': {k: v for k, v in A['early_close'].items() if k != 'groups'},
        'delivery_split': A['delivery_split'],
    }


runs = []
for arg in sys.argv[1:] or ['8e416c6=1.1.141 run']:
    commit, _, label = arg.partition('=')
    runs.append(measure(commit, label or commit))
json.dump({'runs': runs}, open(os.path.join(RESULTS, 'previous-runs.json'), 'w'), indent=1)
print('wrote', os.path.join(RESULTS, 'previous-runs.json'), [r['label'] for r in runs])
