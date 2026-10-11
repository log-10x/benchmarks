#!/usr/bin/env python3
"""
Point the image's shipped Datadog metric output at the local stand-in for Datadog's intake,
changing nothing else, and add that output to the replay config.

  datadog_config.py --shipped config.yaml --out config.yaml --replay replay.yaml --replay-out replay.yaml
"""
import argparse
import re


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--shipped', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--replay', required=True)
    ap.add_argument('--replay-out', required=True)
    a = ap.parse_args()
    s, n = re.subn(r'(?m)^(\s*)uri:.*$', r'\1uri: http://ddcapture:8080', open(a.shipped).read())
    if n != 1:
        raise SystemExit(f'expected one uri line in the shipped Datadog config, found {n}')
    open(a.out, 'w').write(s)
    anchor = '  - run/modules/output/event/file\n'
    r = open(a.replay).read()
    if anchor not in r:
        raise SystemExit('the replay config has no output include to extend')
    open(a.replay_out, 'w').write(r.replace(anchor, anchor + '  - run/output/metric/datadog\n', 1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
