#!/usr/bin/env python3
"""
Count one replay two ways and require them to agree.

1. The records: routed.jsonl has one line per event with the route the regulator marked,
   its container, severity, pattern and byte size.
2. The engine's own aggregators: summaries.jsonl holds the `all_events` and
   `emitted_events` summaries the Receiver's metric outputs publish, with event and
   byte counts per label set.

Both are tallied per (route, container, severity, pattern, hash). A multi-line event is one
message whose source lines are joined by newlines: the record's size counts those joins,
the engine's byte counter counts the lines, so the two differ by one byte per join. The
run fails if any key differs in events, or in bytes once the joins are taken out. The
tally keeps both figures; results.md prices the message bytes, the size the forwarder
sends on.
"""
import argparse
import collections
import json


def one(v):
    if isinstance(v, list):
        return v[0] if v else ''
    return '' if v is None else v


TOP_SERIES = 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--routed', required=True)
    ap.add_argument('--summaries', required=True)
    ap.add_argument('--seconds', type=int, default=None)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    rec_ev = collections.Counter()
    rec_by = collections.Counter()
    rec_lines = collections.Counter()
    for line in open(a.routed, encoding='utf-8', errors='surrogateescape'):
        d = json.loads(line)
        k = (one(d.get('routeState')) or 'pass', one(d.get('k8s_container')), one(d.get('severity_level')),
             one(d.get('message_pattern')), one(d.get('tenx_hash')))
        rec_ev[k] += 1
        rec_by[k] += int(d['utfeightSize_of'])
        rec_lines[k] += max(1, int(d.get('groupSize') or 1))

    agg_ev = collections.Counter()
    agg_by = collections.Counter()
    tag_sets = collections.defaultdict(set)
    for line in open(a.summaries, encoding='utf-8', errors='surrogateescape'):
        d = json.loads(line)
        k = (one(d.get('routeState')) or 'pass', one(d.get('k8s_container')), one(d.get('severity_level')),
             one(d.get('message_pattern')), one(d.get('tenx_hash')))
        tag_sets[d['inputName']].add(k)
        if d['inputName'] != 'all_events':
            continue
        agg_ev[k] += int(d['summaryVolume'])
        agg_by[k] += int(d['summaryBytes'])

    keys = set(rec_ev) | set(agg_ev)
    line_bytes = {k: rec_by[k] - (rec_lines[k] - rec_ev[k]) for k in keys}
    diffs = [(k, rec_ev[k], agg_ev[k], line_bytes[k], agg_by[k]) for k in keys
             if rec_ev[k] != agg_ev[k] or line_bytes[k] != agg_by[k]]
    if diffs:
        for d in diffs[:10]:
            print('mismatch', d)
        raise SystemExit(f'{len(diffs)} of {len(keys)} keys differ between the records and the engine aggregators')

    by_key = [{'route': k[0], 'container': k[1], 'severity': k[2], 'pattern': k[3], 'hash': k[4],
               'events': rec_ev[k], 'bytes': rec_by[k], 'lines': rec_lines[k], 'line_bytes': line_bytes[k]}
              for k in sorted(keys)]
    # Every aggregator publishes two counters per label set, event volume and bytes. The
    # Datadog output publishes the TOP_SERIES label sets with the most bytes, each from both aggregators
    # (its shipped `topSeries` default); the count of what it publishes and the share of
    # bytes those sets carry are taken on the all_events aggregator's label sets.
    series = {name: len(s) for name, s in sorted(tag_sets.items())}
    ranked = sorted(((rec_by[k], k) for k in keys), reverse=True)
    total_bytes = sum(rec_by.values())
    top_sets = min(TOP_SERIES, len(ranked))
    top_bytes = sum(b for b, _ in ranked[:top_sets])
    default_metrics = sum(min(TOP_SERIES, n) for n in series.values()) * 2
    out = {
        'events': sum(rec_ev.values()),
        'bytes': sum(rec_by.values()),
        'lines': sum(rec_lines.values()),
        'line_bytes': sum(line_bytes.values()),
        'keys': len(keys),
        'agreement': {'records_vs_engine_aggregators': 'equal on every key: events, and bytes once the newlines joining a multi-line event are taken out',
                      'keys_compared': len(keys), 'joined_lines': sum(rec_lines.values()) - sum(rec_ev.values())},
        'series': {'label_sets_per_aggregator': series, 'counters_per_label_set': 2,
                   'custom_metrics': 2 * sum(series.values()),
                   'top_series_default': TOP_SERIES,
                   'custom_metrics_default': default_metrics,
                   'bytes_share_of_top_series': round(top_bytes / total_bytes, 4) if total_bytes else 0},
        'replay_seconds': a.seconds,
        'by_key': by_key,
    }
    json.dump(out, open(a.out, 'w'), indent=0)
    by_route = collections.Counter()
    for k in keys:
        by_route[k[0]] += rec_ev[k]
    print(f'{out["events"]} events from {out["lines"]} lines, {out["bytes"]} bytes, {len(keys)} keys, records and aggregators agree; '
          f'by route {dict(sorted(by_route.items()))}; custom metrics {out["series"]["custom_metrics"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
