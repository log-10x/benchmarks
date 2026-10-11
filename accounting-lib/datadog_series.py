#!/usr/bin/env python3
"""
Count what the engine's Datadog metric output posted: series per post, the tag sets and
patterns behind them, the distinct series over the run, and whether any series names a host.

  datadog_series.py --posts posts.jsonl --out datadog-series.json

Datadog counts a custom metric per metric name and tag set, so a post's series count is the
number Datadog bills for the hour that post lands in.
"""
import argparse
import collections
import json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--posts', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    posts, union, tag_keys, hosts = [], set(), set(), set()
    for line in open(a.posts):
        p = json.loads(line)
        if '/series' not in p['path']:
            continue
        series = json.loads(p['body']).get('series', [])
        keys = set()
        per_metric = collections.Counter()
        patterns = set()
        for s in series:
            tags = tuple(sorted(s.get('tags') or []))
            keys.add((s['metric'], tags))
            per_metric[s['metric']] += 1
            for t in tags:
                k, _, v = t.partition(':')
                tag_keys.add(k)
                if k == 'message_pattern':
                    patterns.add(v)
            if s.get('host'):
                hosts.add(s['host'])
        union |= keys
        posts.append({'series': len(keys), 'by_metric': dict(sorted(per_metric.items())), 'patterns': len(patterns)})
    if not posts:
        raise SystemExit('no series posts were captured')
    out = {
        'posts': posts,
        'max_series_per_post': max(p['series'] for p in posts),
        'distinct_series_over_run': len(union),
        'tag_keys': sorted(tag_keys),
        'host_field': sorted(hosts),
        'node_or_process_tags': sorted(k for k in tag_keys if k in ('tenx_host_name', 'tenx_pipeline_uuid', 'tenx_parent_uuid', 'k8s_pod', 'host')),
    }
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f'{len(posts)} posts, at most {out["max_series_per_post"]} series in one, {out["distinct_series_over_run"]} distinct over the run; '
          f'node or process tags: {out["node_or_process_tags"] or "none"}; host field: {out["host_field"] or "none"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
