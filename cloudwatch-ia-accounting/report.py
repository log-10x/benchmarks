#!/usr/bin/env python3
"""
Renders results/results.md and results/results.json from the kept tallies, the plan files
and prices.json. `--check` recomputes results.json and fails if the committed one differs.
"""
import argparse
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'accounting-lib'))
import tally as T  # noqa: E402
import readme as README  # noqa: E402


def compute(results: pathlib.Path, prices: dict, targets: list, window_hours: float, run: dict) -> dict:
    control = T.load(results / 'control.tally.json')
    out = {
        'engine_image': run['engine_image'],
        'engine_tag': run.get('engine_tag', ''),
        'mcp_version': run['mcp_version'],
        'capture': run['capture'],
        'window_hours': window_hours,
        'month_hours': T.MONTH_HOURS,
        'gb_definition': '1 GB = 1,000,000,000 bytes',
        'prices_read_on': prices['read_on'],
        'region': prices['region'],
        'control': {
            'events': control['events'],
            'bytes': control['bytes'],
            'by_severity': {s: v['events'] for s, v in T.by_route_severity(control).get('pass', {}).items()},
        },
        'targets': {},
    }
    std = prices['ingest_standard_per_gb']['price']
    ia = prices['ingest_ia_per_gb']['price']
    sto = prices['storage_per_gb_month']
    ins = prices['insights_per_gb_scanned']['price']
    s3s = prices['s3_standard_storage_per_gb_month']['price']
    s3p = prices['s3_put_per_1000']['price']
    s3o = prices['s3_output']
    ovh = prices['put_log_events_overhead']['bytes_per_event']
    for t in targets:
        plan = T.load(results / f'plan-{t}.json')
        policy = T.load(results / f'policy-{t}.json')
        tl = T.load(results / f'{t}.tally.json')
        routes = T.by_route(tl)
        std_b = routes.get('pass', {'bytes': 0, 'events': 0})
        ia_b = routes.get('tier_down', {'bytes': 0, 'events': 0})
        off_b = routes.get('offload', {'bytes': 0, 'events': 0})
        m = lambda x: T.monthly(x, window_hours)  # noqa: E731
        gb_std, gb_ia, gb_off = m(T.gb(std_b['bytes'])), m(T.gb(ia_b['bytes'])), m(T.gb(off_b['bytes']))
        # One object per upload: at most one every upload_timeout per node and tag, or
        # sooner when the buffer reaches total_file_size.
        objects_month = 0
        if off_b['bytes']:
            by_size = math.ceil(m(off_b['bytes']) / s3o['total_file_size_bytes'])
            by_time = math.ceil(T.MONTH_HOURS * 3600 / s3o['upload_timeout_seconds'])
            objects_month = max(by_size, by_time)
        out['targets'][str(t)] = {
            'plan': {
                'target_pct': plan['plan']['targetPct'],
                'achieved_pct_stated': round(plan['plan']['achievedPct'], 2),
                'events_sampled': plan['events_pulled'],
                'planned_patterns': [{'name': r['name'], 'action': r['action'], 'severity': r.get('severity') or '',
                                      'container': r.get('dominantService') or '', 'moved_bytes_stated': round(r.get('movedBytesMonthly') or 0)}
                                     for r in plan['plan']['planned']],
                'planned_count': len(plan['plan']['planned']),
                'stated_bytes_moved': round(sum(r.get('movedBytesMonthly') or 0 for r in plan['plan']['planned'] if r['action'] == 'tier_down')),
                'tool_caps_csv': policy['tool_caps_csv'],
                'tool_actions_csv': policy['tool_actions_csv'],
                'span_seconds': policy['span_seconds'],
                'replay_factor': policy['replay_factor'],
                'unattributed_planned': policy['unattributed_planned'],
                'containers': policy['containers'],
            },
            'engine': {
                'events': tl['events'],
                'bytes': tl['bytes'],
                'by_route': routes,
                'by_route_severity': T.by_route_severity(tl),
                'protected_moved_events': T.protected_moved(tl),
                'top_moved': T.top_moved(tl),
                'agreement': tl['agreement'],
                'replay_seconds': tl['replay_seconds'],
            },
            'month': {
                'gb_standard': round(gb_std, 4), 'gb_ia': round(gb_ia, 4), 'gb_offloaded': round(gb_off, 4),
                'events_standard': round(m(std_b['events'])), 'events_ia': round(m(ia_b['events'])), 'events_offloaded': round(m(off_b['events'])),
                'overhead_bytes_26_per_event_ia': round(m(ia_b['events']) * ovh),
                's3_objects': objects_month,
            },
            'usd_per_month_at_list': {
                'ingest_standard_for_what_stays': round(gb_std * std, 4),
                'ingest_ia_for_the_moved_slice': round(gb_ia * ia, 4),
                'ingest_standard_the_moved_slice_would_have_cost': round(gb_ia * std, 4),
                'ingest_avoided_by_offload': round(gb_off * std, 4),
                'storage_per_month_all_classes_compressed': round((gb_std + gb_ia) * sto['compression_ratio'] * sto['price'], 4),
                'insights_one_full_scan_of_the_ia_slice': round(gb_ia * ins, 4),
                's3_storage_offloaded': round(gb_off * s3s, 4),
                's3_put': round(objects_month / 1000 * s3p, 6),
            },
        }
    return out



def readme_blocks(r: dict, prices: dict) -> dict:
    """Every figure the README quotes from this run, rendered from results.json and prices.json."""
    c, cap = r['control'], r['capture']
    pr = lambda k: prices[k]['price']
    B = {}
    B['run'] = (f'The OpenTelemetry demo capture, {cap["lines"]:,} lines, {c["events"]:,} events after grouping, {T.gb(c["bytes"]):.3f} GB '
                f'over {r["window_hours"]:g} hours. Engine `log10x/pipeline-10x:{r["engine_tag"]}`, log10x-mcp {r["mcp_version"]} with the S3 '
                f'retriever declared installed, prices read {r["prices_read_on"]}.')
    B['rates'] = (f'**Dollars per GB at list.** Ingest: ${pr("ingest_standard_per_gb"):.2f} Standard, ${pr("ingest_ia_per_gb"):.2f} Infrequent Access. '
                  f'Storage: ${pr("storage_per_gb_month"):.2f} per GB-month in both classes, on compressed bytes at AWS\'s stated '
                  f'{prices["storage_per_gb_month"]["compression_ratio"]:g} ratio. Logs Insights: ${pr("insights_per_gb_scanned"):.3f} per GB scanned. '
                  f'S3 Standard: ${pr("s3_standard_storage_per_gb_month"):.3f} per GB-month and ${pr("s3_put_per_1000"):.3f} per 1,000 PUT requests. '
                  f'A GB moved to Infrequent Access costs ${pr("ingest_ia_per_gb"):.2f} instead of ${pr("ingest_standard_per_gb"):.2f} to ingest and '
                  f'the same to store; a GB offloaded costs nothing to ingest and ${pr("s3_standard_storage_per_gb_month"):.3f} a month in S3. The '
                  f'{prices["put_log_events_overhead"]["bytes_per_event"]} bytes per event in the PutLogEvents batch-size rule are shown as a separate '
                  f'line; no AWS page read bills them. The full table with every URL is in [`results/results.md`](results/results.md).')
    L = ['| Target | Patterns planned | Containers | GB the plan states to IA | GB the engine marked to IA | GB offloaded | GB in Standard | Share of the bill the plan states | Share of the bytes the engine moved | Errors and warnings moved |',
         '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for t, v in r['targets'].items():
        p, e = v['plan'], v['engine']['by_route']
        tot = sum(x['bytes'] for x in e.values())
        b = lambda k: e.get(k, {'bytes': 0})['bytes']
        L.append(f'| {t}% | {p["planned_count"]} | {len(p["containers"])} | {T.fmt_gb(p["stated_bytes_moved"])} | {T.fmt_gb(b("tier_down"))} | '
                 f'{T.fmt_gb(b("offload"))} | {T.fmt_gb(b("pass"))} | {p["achieved_pct_stated"]:.1f}% | {(b("tier_down") + b("offload")) / tot * 100:.1f}% | '
                 f'{v["engine"]["protected_moved_events"]:,} |')
    B['moves'] = '\n'.join(L)
    N = []
    for t, v in r['targets'].items():
        p = v['plan']
        by_a = {}
        for cname, cv in sorted(p['containers'].items()):
            by_a.setdefault(cv['action'], []).append(cname)
        parts = []
        for action in ('offload', 'tier_down'):
            cs = by_a.get(action, [])
            if not cs:
                continue
            parts.append(f'{action} on {len(cs)} container{"s" if len(cs) != 1 else ""}' +
                         (f' ({", ".join(f"`{x}`" for x in cs)})' if action == 'offload' else ''))
        line = f'- **{t}%**: {p["planned_count"]} patterns; ' + ', '.join(parts)
        if p['unattributed_planned']:
            line += f'; {p["unattributed_planned"]} planned pattern{"s" if p["unattributed_planned"] != 1 else ""} carried no container and {"are" if p["unattributed_planned"] != 1 else "is"} not in the files'
        N.append(line + '.')
    B['moves-notes'] = '\n'.join(N)
    M = ['| Target | GB to IA per month | Ingest at the IA rate | Ingest at Standard the same GB would cost | GB offloaded per month | Ingest avoided by offload |',
         '|---:|---:|---:|---:|---:|---:|']
    for t, v in r['targets'].items():
        m, u = v['month'], v['usd_per_month_at_list']
        M.append(f'| {t}% | {m["gb_ia"]:.3f} | {T.fmt_usd(u["ingest_ia_for_the_moved_slice"])} | {T.fmt_usd(u["ingest_standard_the_moved_slice_would_have_cost"])} | '
                 f'{m["gb_offloaded"]:.3f} | {T.fmt_usd(u["ingest_avoided_by_offload"])} |')
    B['month'] = '\n'.join(M)
    return B

def render(r: dict, prices: dict) -> str:
    L = []
    L.append('# CloudWatch Logs Infrequent Access accounting')
    L.append('')
    L.append(f'Computed from the engine\'s counts at AWS list prices for {r["region"]}, read {r["prices_read_on"]}. Nothing here was metered by AWS.')
    L.append('')
    L.append(f'- engine image: `{r["engine_image"]}`')
    L.append(f'- MCP: log10x-mcp {r["mcp_version"]}')
    L.append(f'- capture: `{r["capture"]["name"]}`, sha256 `{r["capture"]["sha256"]}`, {r["capture"]["lines"]:,} lines, {r["control"]["events"]:,} events after grouping, {T.fmt_gb(r["control"]["bytes"])} GB, {r["window_hours"]:g} hours; a month is {r["month_hours"]} hours; {r["gb_definition"]}')
    L.append('')
    L.append('## Dollars per GB at list')
    L.append('')
    L.append('| Line | Per GB | AWS\'s wording | Read |')
    L.append('|---|---:|---|---|')
    L.append(f'| Ingest, Standard | ${prices["ingest_standard_per_gb"]["price"]:.2f} | {prices["ingest_standard_per_gb"]["quote"]} | [{r["prices_read_on"]}]({prices["ingest_standard_per_gb"]["url"]}) |')
    L.append(f'| Ingest, Infrequent Access | ${prices["ingest_ia_per_gb"]["price"]:.2f} | {prices["ingest_ia_per_gb"]["quote"]} | [{r["prices_read_on"]}]({prices["ingest_ia_per_gb"]["url"]}) |')
    L.append(f'| Storage, per GB-month, both classes | ${prices["storage_per_gb_month"]["price"]:.2f} | {prices["storage_per_gb_month"]["quote"]}; {prices["storage_per_gb_month"]["compression"]}; {prices["storage_per_gb_month"]["same_in_both_classes"]} | [{r["prices_read_on"]}]({prices["storage_per_gb_month"]["url"]}), [classes]({prices["storage_per_gb_month"]["classes_url"]}) |')
    L.append(f'| Logs Insights, per GB scanned | ${prices["insights_per_gb_scanned"]["price"]:.3f} | {prices["insights_per_gb_scanned"]["quote"]} | [{r["prices_read_on"]}]({prices["insights_per_gb_scanned"]["url"]}) |')
    L.append(f'| S3 Standard storage, per GB-month | ${prices["s3_standard_storage_per_gb_month"]["price"]:.3f} | {prices["s3_standard_storage_per_gb_month"]["quote"]} | [{r["prices_read_on"]}]({prices["s3_standard_storage_per_gb_month"]["url"]}) |')
    L.append(f'| S3 PUT, per 1,000 requests | ${prices["s3_put_per_1000"]["price"]:.3f} | {prices["s3_put_per_1000"]["quote"]} | [{r["prices_read_on"]}]({prices["s3_put_per_1000"]["url"]}) |')
    L.append('')
    L.append(f'A GB moved from Standard to Infrequent Access costs ${prices["ingest_ia_per_gb"]["price"]:.2f} instead of ${prices["ingest_standard_per_gb"]["price"]:.2f} to ingest, and the same to store; a GB offloaded costs nothing to ingest, ${prices["s3_standard_storage_per_gb_month"]["price"]:.3f} per month in S3. The price list carries publication date {prices["price_list"]["publication_date"]} ([index.json]({prices["price_list"]["url"]})). {prices["class_immutable"]}')
    L.append('')
    L.append('## What moves, per target')
    L.append('')
    L.append('| Target | Patterns planned | Containers | GB the plan states to IA | GB the engine marked to IA | GB offloaded | GB in Standard | Errors and warnings moved |')
    L.append('|---:|---:|---:|---:|---:|---:|---:|---:|')
    for t, v in r['targets'].items():
        e, p = v['engine'], v['plan']
        L.append(f'| {t}% | {p["planned_count"]} | {len(p["containers"])} | {T.fmt_gb(p["stated_bytes_moved"])} | {T.fmt_gb(e["by_route"].get("tier_down", {"bytes": 0})["bytes"])} | {T.fmt_gb(e["by_route"].get("offload", {"bytes": 0})["bytes"])} | {T.fmt_gb(e["by_route"].get("pass", {"bytes": 0})["bytes"])} | {T.fmt_int(e["protected_moved_events"])} |')
    L.append('')
    L.append('The engine moves each pattern\'s excess over its container\'s cap; the plan sets the cap at the largest pattern the container keeps and states the excess, less the share the severity floors keep. Offload acts on the whole container: its cap is the one-byte minimum.')
    L.append('')
    L.append(f'## A month at this capture\'s volume, an illustration')
    L.append('')
    L.append(f'The capture\'s {r["window_hours"]:g} hours scaled to a {r["month_hours"]}-hour month, at the rates above. The volume is one small demo cluster\'s; the rates are what carry.')
    L.append('')
    L.append('| Target | GB to IA per month | Ingest at the IA rate | Ingest at Standard the same GB would cost | GB offloaded per month | Ingest avoided by offload |')
    L.append('|---:|---:|---:|---:|---:|---:|')
    for t, v in r['targets'].items():
        m, u = v['month'], v['usd_per_month_at_list']
        L.append(f'| {t}% | {m["gb_ia"]:.3f} | {T.fmt_usd(u["ingest_ia_for_the_moved_slice"])} | {T.fmt_usd(u["ingest_standard_the_moved_slice_would_have_cost"])} | {m["gb_offloaded"]:.3f} | {T.fmt_usd(u["ingest_avoided_by_offload"])} |')
    L.append('')
    for t, v in r['targets'].items():
        p, e, m, u = v['plan'], v['engine'], v['month'], v['usd_per_month_at_list']
        L.append(f'## Target {t}%')
        L.append('')
        names = p['planned_patterns']
        shown = ', '.join(f'`{x["name"]}` ({x["action"]}, {x["severity"] or "no level"})' for x in names[:12])
        more = f', and {len(names) - 12} more' if len(names) > 12 else ''
        L.append(f'**The plan.** The MCP sampled {p["events_sampled"]:,} events of the capture and planned {len(names)} patterns, stating {p["achieved_pct_stated"]:g}% of the bill: {shown}{more}.')
        L.append(f'Its engine files, as written (a cap is bytes per pattern per 240 s window over the {p["span_seconds"] / 3600:g} hours the plan covers; the replay multiplies each cap by {p["replay_factor"]:g} because it delivers the capture inside one window):')
        L.append('')
        L.append('```')
        L.append(p['tool_caps_csv'].rstrip('\n'))
        L.append(p['tool_actions_csv'].rstrip('\n'))
        L.append('```')
        L.append('')
        L.append(f'**The engine.** {e["events"]:,} events replayed in {e["replay_seconds"]} s; the records and the engine\'s aggregators agree on every one of {e["agreement"]["keys_compared"]:,} keys.')
        L.append('')
        L.append('| Route | Events | GB | Events by severity |')
        L.append('|---|---:|---:|---|')
        for route, rv in e['by_route'].items():
            sev = e['by_route_severity'][route]
            L.append(f'| {route} | {rv["events"]:,} | {T.fmt_gb(rv["bytes"])} | ' + ', '.join(f'{s} {sv["events"]:,}' for s, sv in sev.items()) + ' |')
        L.append('')
        L.append(f'Errors and warnings moved: {e["protected_moved_events"]:,}. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container\'s action.')
        L.append('')
        L.append('| Pattern moved | Container | Severity | Route | Events | GB |')
        L.append('|---|---|---|---|---:|---:|')
        for x in e['top_moved']:
            L.append(f'| `{x["pattern"]}` | `{x["container"]}` | {x["severity"]} | {x["route"]} | {x["events"]:,} | {T.fmt_gb(x["bytes"])} |')
        L.append('')
        L.append(f'**A month at this volume, an illustration.** {m["gb_ia"]:.3f} GB to Infrequent Access ({T.fmt_int(m["events_ia"])} events), {m["gb_offloaded"]:.3f} GB offloaded ({T.fmt_int(m["events_offloaded"])} events), {m["gb_standard"]:.3f} GB in Standard.')
        L.append('')
        L.append('| Line | Per month |')
        L.append('|---|---:|')
        L.append(f'| Ingest, Standard, for what stays | {T.fmt_usd(u["ingest_standard_for_what_stays"])} |')
        L.append(f'| Ingest, Infrequent Access, for the moved slice | {T.fmt_usd(u["ingest_ia_for_the_moved_slice"])} |')
        L.append(f'| Ingest at Standard, what the moved slice would have cost | {T.fmt_usd(u["ingest_standard_the_moved_slice_would_have_cost"])} |')
        L.append(f'| Ingest avoided by offload | {T.fmt_usd(u["ingest_avoided_by_offload"])} |')
        L.append(f'| Storage for one month of data held one month, both classes, compressed at AWS\'s stated ratio | {T.fmt_usd(u["storage_per_month_all_classes_compressed"])} |')
        L.append(f'| Logs Insights, one full scan of the IA slice | {T.fmt_usd(u["insights_one_full_scan_of_the_ia_slice"])} |')
        L.append(f'| S3 storage for one month of offloaded data held one month | {T.fmt_usd(u["s3_storage_offloaded"])} |')
        L.append(f'| S3 PUT, {m["s3_objects"]:,} objects | {T.fmt_usd(u["s3_put"], 4)} |')
        L.append(f'| PutLogEvents batch-size rule, 26 bytes per event, for the IA slice | {T.fmt_int(m["overhead_bytes_26_per_event_ia"])} bytes; not a billed quantity on any AWS page read |')
        L.append('')
    L.append('## What Infrequent Access lacks')
    L.append('')
    L.append(f'From AWS\'s log class table ([{r["prices_read_on"]}]({prices["ia_table_url"]})), marked "No" for Infrequent Access: ' + ', '.join(prices['ia_lacks']) + '.')
    L.append('Supported in both classes: ' + ', '.join(prices['ia_has']) + '.')
    L.append('')
    L.append('## Counting conditions')
    L.append('')
    L.append('- CloudWatch bills ingestion by the bytes of each event message. Bytes here are the UTF-8 size of each record the engine emitted; with the shipped forwarder path the forwarder sends that record as the event message.')
    L.append(f'- The 26 bytes per event in the PutLogEvents batch-size rule are shown as a separate line. {prices["put_log_events_overhead"]["billed"]} ([{r["prices_read_on"]}]({prices["put_log_events_overhead"]["url"]}))')
    L.append('- The split is forwarder-side: the `tenx.tier_down` tag goes to a log group in the Infrequent Access class, `tenx.offload` to the S3 output, and the class is fixed when the group is created.')
    L.append('- The regulator caps each pattern\'s bytes per container per 240 s window; an event over its pattern\'s cap takes the container\'s action. Patterns under 5% of their container\'s bytes in the window are not capped, the first 5 events of a pattern in a window pass, and the severity floors keep a share of each level: a tenth of INFO, DEBUG and TRACE, three tenths of WARN, half of ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within that noise.')
    L.append('- The replay delivers the capture inside one window; each cap the plan wrote is multiplied by the span the plan covers over 240 s, and nothing else in the plan\'s files is changed. `results/policy-*.json` records the files and the factor.')
    L.append(f'- A month is {r["month_hours"]} hours; the capture covers {r["window_hours"]:g}. Storage and S3 storage accrue per GB-month and are shown per GB-month of data held.')
    L.append('')
    L.append('## Reproduce')
    L.append('')
    L.append('```sh')
    L.append('./run.sh                 # everything')
    L.append('./run.sh plan replay     # some stages, in the order given')
    L.append('```')
    L.append('')
    L.append('Stages: `data plan control policy replay count report`. Needs Docker, Node 18 or later and about 1 GB of disk. `plan` installs the pinned log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio with the S3 retriever declared installed, so the plan can offload; the server runs the pinned engine image for its own sampling. Every other stage runs the engine image on the capture. '
             '`ACCT_TARGETS` sets the targets (default `30 50 70`), `ACCT_WINDOW` the span the capture covers (default `10h`).')
    L.append('')
    L.append('| File | What it is |')
    L.append('|---|---|')
    L.append('| `run.sh` | the whole run, in stages |')
    L.append('| `prices.json` | every price used, with its URL and the date read |')
    L.append('| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |')
    L.append('| `../accounting-lib/` | the MCP driver, the engine run, the policy mapping and the two-way count, shared with [`datadog-flex-accounting/`](../datadog-flex-accounting/) |')
    L.append('| `results/plan-<target>.json` | the plan the MCP wrote, its notes and the caps row it rendered |')
    L.append('| `results/policy-<target>.caps.csv`, `.actions.csv`, `.json` | the files the engine read |')
    L.append('| `results/<target>.tally.json`, `results/control.tally.json` | the counts per route, container, severity and pattern |')
    L.append('')
    L.append('## Data')
    L.append('')
    L.append(f'`{r["capture"]["name"]}` from [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1), {r["capture"]["bytes"]:,} bytes, {r["capture"]["lines"]:,} lines, sha256 `{r["capture"]["sha256"]}`: Kubernetes container output captured through Fluentd from a cluster running the OpenTelemetry demo, 36 containers, about ten hours. The same asset the [`splunk-license/`](../splunk-license/) and [`otel-denominators/`](../otel-denominators/) benchmarks run on.')
    L.append('')
    return '\n'.join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=str(pathlib.Path(__file__).resolve().parent / 'results'))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    here = pathlib.Path(__file__).resolve().parent
    results = pathlib.Path(a.results)
    prices = json.load(open(here / 'prices.json'))
    run = json.load(open(results / 'run.json'))
    r = compute(results, prices, run['targets'], run['window_hours'], run)
    if a.check:
        committed = json.load(open(results / 'results.json'))
        stale = README.differing(open(here / 'README.md').read(), readme_blocks(r, prices))
        if stale:
            raise SystemExit(f'README.md differs from the results in: {", ".join(stale)}; run report.py to rewrite them')
        if committed != r:
            for k in r:
                if committed.get(k) != r[k]:
                    print(f'differs: {k}')
            raise SystemExit('results.json does not follow from the kept tallies')
        print('the committed figures follow from the kept tallies: ' +
              ', '.join(f'{t}% moves {T.fmt_gb(v["engine"]["by_route"].get("tier_down", {"bytes": 0})["bytes"])} GB to IA' for t, v in r['targets'].items()))
        return 0
    json.dump(r, open(results / 'results.json', 'w'), indent=1)
    open(results / 'results.md', 'w').write(render(r, prices))
    readme = here / 'README.md'
    readme.write_text(README.apply(readme.read_text(), readme_blocks(r, prices)))
    print(f'wrote {results / "results.md"} and the README\'s generated blocks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
