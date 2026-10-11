#!/usr/bin/env python3
"""
Renders results/results.md and results/results.json from the kept tallies, the plan files
and prices.json. `--check` recomputes results.json and fails if the committed one differs,
so a figure edited without a rerun is caught in CI.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'accounting-lib'))
import tally as T  # noqa: E402


def compute(results: pathlib.Path, prices: dict, targets: list, window_hours: float, run: dict) -> dict:
    control = T.load(results / 'control.tally.json')
    out = {
        'engine_image': run['engine_image'],
        'mcp_version': run['mcp_version'],
        'capture': run['capture'],
        'window_hours': window_hours,
        'month_hours': T.MONTH_HOURS,
        'gb_definition': '1 GB = 1,000,000,000 bytes',
        'prices_read_on': prices['read_on'],
        'control': {
            'events': control['events'],
            'bytes': control['bytes'],
            'by_severity': {s: v['events'] for s, v in T.by_route_severity(control).get('pass', {}).items()},
            'custom_metrics': control['series']['custom_metrics'],
            'label_sets': control['series']['label_sets_per_aggregator'],
        },
        'targets': {},
    }
    idx = prices['indexed_per_million_events']
    flex = prices['flex_storage_per_million_events_month']
    starter = prices['flex_starter_per_million_events_month']
    cm = prices['custom_metrics']
    for t in targets:
        plan = T.load(results / f'plan-{t}.json')
        policy = T.load(results / f'policy-{t}.json')
        tl = T.load(results / f'{t}.tally.json')
        routes = T.by_route(tl)
        mv = T.moved(tl, ('tier_down',))
        off = T.moved(tl, ('offload',))
        events_month = T.monthly(mv['events'], window_hours)
        stored_month = events_month  # held 30 days, the minimum billed
        tier = next((name for name, lo, hi in prices['flex_compute']['tiers_by_cumulative_events_stored'] if lo <= stored_month < hi), 'above L')
        within_starter = events_month < prices['flex_compute']['starter_monthly_limit_events']
        cmc = tl['series']['custom_metrics']
        pm = plan['plan'].get('perEventMove') or {}
        out['targets'][str(t)] = {
            'plan': {
                'target_pct': plan['plan']['targetPct'],
                'achieved_pct_stated': round(plan['plan']['achievedPct'], 2),
                'events_sampled': plan['events_pulled'],
                'planned_patterns': [{'name': r['name'], 'action': r['action'], 'severity': r.get('severity') or '',
                                      'container': r.get('dominantService') or '', 'moved_bytes_stated': round(r.get('movedBytesMonthly') or 0)}
                                     for r in plan['plan']['planned']],
                'stated_events_moved': round(pm.get('events_moved') or 0),
                'stated_bytes_moved': round(sum(r.get('movedBytesMonthly') or 0 for r in plan['plan']['planned'])),
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
                'events_to_flex': round(events_month),
                'gb_to_flex': round(T.monthly(T.gb(mv['bytes']), window_hours), 4),
                'events_in_standard': round(T.monthly(routes.get('pass', {'events': 0})['events'], window_hours)),
                'events_offloaded': round(T.monthly(off['events'], window_hours)),
                'gb_ingested': round(T.monthly(T.gb(tl['bytes']), window_hours), 4),
            },
            'usd_per_month_at_list': {
                'standard_indexing_avoided': {
                    '15d_annual': round(events_month / 1e6 * idx['15d']['annual'], 4),
                    '15d_on_demand': round(events_month / 1e6 * idx['15d']['on_demand'], 4),
                    '30d_annual': round(events_month / 1e6 * idx['30d']['annual'], 4),
                    '30d_on_demand': round(events_month / 1e6 * idx['30d']['on_demand'], 4),
                },
                'flex_storage_added': {
                    'annual': round(stored_month / 1e6 * flex['annual'], 4),
                    'on_demand': round(stored_month / 1e6 * flex['on_demand'], 4),
                },
                'flex_starter_instead': {
                    'annual': round(stored_month / 1e6 * starter['annual'], 4),
                    'on_demand': round(stored_month / 1e6 * starter['on_demand'], 4),
                },
                'ingestion_unchanged': round(T.monthly(T.gb(tl['bytes']), window_hours) * prices['ingestion_per_gb']['annual'], 4),
            },
            'flex_compute': {
                'cumulative_events_stored_at_30_days': round(stored_month),
                'tier': tier,
                'within_starter_monthly_limit': within_starter,
                'price': prices['flex_compute']['price'],
            },
            'custom_metrics': {
                # the output's default: the top tag sets by bytes per aggregator, the same series from every node
                'count_default': tl['series']['custom_metrics_default'],
                'top_series_default': tl['series']['top_series_default'],
                'bytes_share_of_top_series': tl['series']['bytes_share_of_top_series'],
                # every tag set, as one node would publish them with topSeries 0
                'count_every_set_one_node': cmc,
                'label_sets': tl['series']['label_sets_per_aggregator'],
                'fleet': {str(n): {
                    'default_above_pro_allotment': max(0, tl['series']['custom_metrics_default'] - n * cm['allotment_per_host']['pro']),
                    'default_usd_per_month': round(max(0, tl['series']['custom_metrics_default'] - n * cm['allotment_per_host']['pro']) / 100 * cm['per_100_per_month']['annual'], 2),
                    'every_set_per_node_usd_per_month': round(max(0, cmc * n - n * cm['allotment_per_host']['pro']) / 100 * cm['per_100_per_month']['annual'], 2),
                } for n in (10, 100, 300)},
            },
        }
    return out


def render(r: dict, prices: dict) -> str:
    idx = prices['indexed_per_million_events']
    flex = prices['flex_storage_per_million_events_month']
    starter = prices['flex_starter_per_million_events_month']
    cm = prices['custom_metrics']
    L = []
    L.append('# Datadog Flex Logs accounting')
    L.append('')
    L.append(f'Computed from the engine\'s counts at Datadog list prices read {r["prices_read_on"]}. Nothing here was metered by Datadog.')
    L.append('')
    L.append(f'- engine image: `{r["engine_image"]}`')
    L.append(f'- MCP: log10x-mcp {r["mcp_version"]}')
    L.append(f'- capture: `{r["capture"]["name"]}`, sha256 `{r["capture"]["sha256"]}`, {r["capture"]["lines"]:,} lines, {r["control"]["events"]:,} events after grouping, {T.fmt_gb(r["control"]["bytes"])} GB, {r["window_hours"]:g} hours; a month is {r["month_hours"]} hours; {r["gb_definition"]}')
    L.append('')
    L.append('## What a moved event costs at list')
    L.append('')
    L.append('| Line | Annual | On-demand | Datadog\'s wording | Read |')
    L.append('|---|---:|---:|---|---|')
    for ret in ('3d', '7d', '15d', '30d'):
        L.append(f'| Standard indexing avoided, {ret.replace("d", "-day")} retention, per million events | ${idx[ret]["annual"]:.2f} | ${idx[ret]["on_demand"]:.2f} | Per 1M indexed logs ({ret.replace("d", "-day")} retention), per month | [{r["prices_read_on"]}]({idx["url"]}) |')
    L.append(f'| Flex storage added, per million events stored per month | ${flex["annual"]:.2f} | ${flex["on_demand"]:.3f} | {flex["quote"]}; {flex["minimum"]} | [{r["prices_read_on"]}]({flex["url"]}) |')
    L.append(f'| Flex Starter, per million events stored per month, compute bundled | ${starter["annual"]:.2f} | ${starter["on_demand"]:.2f} | {starter["quote"]}; {starter["limit"]} | [{r["prices_read_on"]}]({starter["url"]}) |')
    L.append(f'| Flex compute, XS to L | {prices["flex_compute"]["price"]} | {prices["flex_compute"]["price"]} | {prices["flex_compute"]["price_quote"]} | [{r["prices_read_on"]}]({prices["flex_compute"]["price_url"]}) |')
    L.append(f'| Ingestion, per GB, unchanged by a move | ${prices["ingestion_per_gb"]["annual"]:.2f} | ${prices["ingestion_per_gb"]["on_demand"]:.2f} | {prices["ingestion_per_gb"]["quote"]} | [{r["prices_read_on"]}]({prices["ingestion_per_gb"]["url"]}) |')
    L.append(f'| Custom metrics, per 100 per month above the allotment | ${cm["per_100_per_month"]["annual"]:.2f} | ${cm["per_100_per_month"]["on_demand"]:.2f} | {cm["quote"]}; {cm["allotment_quote"]} | [{r["prices_read_on"]}]({cm["url"]}) |')
    L.append('')
    L.append('Flex compute sizes by cumulative events stored, from Datadog\'s own table: ' +
             ', '.join(f'{n} {lo / 1e9:g} to {hi / 1e9:g} billion' if lo else f'{n} under {hi / 1e9:g} billion' for n, lo, hi in prices['flex_compute']['tiers_by_cumulative_events_stored']) +
             f'. Starter is bundled storage and compute for volumes below {prices["flex_compute"]["starter_monthly_limit_events"] / 1e9:g} billion events a month. '
             f'[{r["prices_read_on"]}]({prices["flex_compute"]["sizing_url"]})')
    L.append('')
    L.append('## What moves, per target')
    L.append('')
    L.append('| Target | Patterns planned | Containers capped | Events the plan states | Events the engine marked tier_down | GB to Flex | Events in Standard | Errors and warnings to Flex | Custom metrics the output publishes |')
    L.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for t, v in r['targets'].items():
        e, p = v['engine'], v['plan']
        L.append(f'| {t}% | {len(p["planned_patterns"])} | {len(p["containers"])} | {T.fmt_int(p["stated_events_moved"])} | {T.fmt_int(e["by_route"].get("tier_down", {"events": 0})["events"])} | {T.fmt_gb(e["by_route"].get("tier_down", {"bytes": 0})["bytes"])} | {T.fmt_int(e["by_route"].get("pass", {"events": 0})["events"])} | {T.fmt_int(e["protected_moved_events"])} | {v["custom_metrics"]["count_default"]:,} |')
    L.append('')
    L.append('The engine moves each pattern\'s excess over its container\'s cap; the plan sets the cap at the largest pattern the container keeps and states the excess, less the share the severity floors keep. Ingestion is unchanged: every event is ingested once, at '
             f'${prices["ingestion_per_gb"]["annual"]:.2f} per GB, before any index routing.')
    L.append('')
    L.append(f'## A month at this capture\'s volume, an illustration')
    L.append('')
    L.append(f'The capture\'s {r["window_hours"]:g} hours scaled to a {r["month_hours"]}-hour month, at the rates above. The volume is one small demo cluster\'s; the rates are what carry.')
    L.append('')
    L.append('| Target | Events to Flex per month | Standard indexing avoided, 15-day annual | Flex storage added, annual | Flex compute tier | Ingestion, unchanged | Custom metrics above a Pro allotment, 10 to 300 nodes |')
    L.append('|---:|---:|---:|---:|---|---:|---:|')
    for t, v in r['targets'].items():
        m, u, c = v['month'], v['usd_per_month_at_list'], v['custom_metrics']
        L.append(f'| {t}% | {T.fmt_int(m["events_to_flex"])} | {T.fmt_usd(u["standard_indexing_avoided"]["15d_annual"])} | {T.fmt_usd(u["flex_storage_added"]["annual"])} | {v["flex_compute"]["tier"]} | {T.fmt_usd(u["ingestion_unchanged"])} | {T.fmt_usd(c["fleet"]["10"]["default_usd_per_month"])} to {T.fmt_usd(c["fleet"]["300"]["default_usd_per_month"])} |')
    L.append('')
    c0 = r['targets'][str(r['targets_list'][0])]['custom_metrics'] if r.get('targets_list') else next(iter(r['targets'].values()))['custom_metrics']
    L.append(f'**Custom metrics.** The Datadog output tags each series with the pattern and where it ran and with nothing that names a node or a process, and publishes the {c0["top_series_default"]} tag sets with the most bytes per aggregator: {c0["count_default"]:,} custom metrics from this capture whatever the node count, carrying {c0["bytes_share_of_top_series"] * 100:.1f}% of the bytes. '
             f'Above a Pro plan\'s allotment of 100 per host that is {T.fmt_usd(c0["fleet"]["10"]["default_usd_per_month"])} a month at 10 nodes, {T.fmt_usd(c0["fleet"]["100"]["default_usd_per_month"])} at 100 and {T.fmt_usd(c0["fleet"]["300"]["default_usd_per_month"])} at 300. '
             f'Every tag set from every node would be {c0["count_every_set_one_node"]:,} per node: {T.fmt_usd(c0["fleet"]["10"]["every_set_per_node_usd_per_month"])}, {T.fmt_usd(c0["fleet"]["100"]["every_set_per_node_usd_per_month"])} and {T.fmt_usd(c0["fleet"]["300"]["every_set_per_node_usd_per_month"])} a month.')
    L.append('')
    for t, v in r['targets'].items():
        p, e, m, u = v['plan'], v['engine'], v['month'], v['usd_per_month_at_list']
        L.append(f'## Target {t}%')
        L.append('')
        L.append(f'**The plan.** The MCP sampled {p["events_sampled"]:,} events of the capture and planned {len(p["planned_patterns"])} patterns for Flex, stating {p["achieved_pct_stated"]:g}% of the Standard-index volume and {T.fmt_int(p["stated_events_moved"])} events moved: ' +
                 ', '.join(f'`{x["name"]}` ({x["severity"] or "no level"}, `{x["container"]}`)' for x in p['planned_patterns']) + '.')
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
        L.append(f'Errors and warnings marked tier_down: {e["protected_moved_events"]:,}. The regulator keeps half of the ERROR and CRITICAL events over a cap and three tenths of the WARN events; the rest take the container\'s action.')
        L.append('')
        L.append('| Pattern moved | Container | Severity | Events | GB |')
        L.append('|---|---|---|---:|---:|')
        for x in e['top_moved']:
            L.append(f'| `{x["pattern"]}` | `{x["container"]}` | {x["severity"]} | {x["events"]:,} | {T.fmt_gb(x["bytes"])} |')
        L.append('')
        L.append(f'**A month at this volume, an illustration.** {T.fmt_int(m["events_to_flex"])} events to Flex ({m["gb_to_flex"]:.3f} GB), {T.fmt_int(m["events_in_standard"])} in Standard, {m["gb_ingested"]:.3f} GB ingested.')
        L.append('')
        L.append('| Line | Per month |')
        L.append('|---|---:|')
        L.append(f'| Standard indexing avoided, 15-day, annual | {T.fmt_usd(u["standard_indexing_avoided"]["15d_annual"])} |')
        L.append(f'| Standard indexing avoided, 15-day, on-demand | {T.fmt_usd(u["standard_indexing_avoided"]["15d_on_demand"])} |')
        L.append(f'| Standard indexing avoided, 30-day, annual | {T.fmt_usd(u["standard_indexing_avoided"]["30d_annual"])} |')
        L.append(f'| Standard indexing avoided, 30-day, on-demand | {T.fmt_usd(u["standard_indexing_avoided"]["30d_on_demand"])} |')
        L.append(f'| Flex storage added, held 30 days, annual | {T.fmt_usd(u["flex_storage_added"]["annual"])} |')
        L.append(f'| Flex storage added, held 30 days, on-demand | {T.fmt_usd(u["flex_storage_added"]["on_demand"])} |')
        L.append(f'| Flex Starter instead of storage plus compute, annual | {T.fmt_usd(u["flex_starter_instead"]["annual"])} |')
        L.append(f'| Flex compute tier at {T.fmt_int(v["flex_compute"]["cumulative_events_stored_at_30_days"])} events stored | {v["flex_compute"]["tier"]}{", within Starter" if v["flex_compute"]["within_starter_monthly_limit"] else ""}; {v["flex_compute"]["price"]} for XS and above |')
        L.append(f'| Ingestion, unchanged | {T.fmt_usd(u["ingestion_unchanged"])} |')
        c = v['custom_metrics']
        L.append(f'| Custom metrics from the engine\'s Datadog metric output | {c["count_default"]:,} series, the top {c["top_series_default"]} tag sets per aggregator ({c["bytes_share_of_top_series"] * 100:.1f}% of the bytes), the same from every node; above a Pro allotment {T.fmt_usd(c["fleet"]["10"]["default_usd_per_month"])} at 10 nodes, {T.fmt_usd(c["fleet"]["300"]["default_usd_per_month"])} at 300. Every tag set would be {c["count_every_set_one_node"]:,} per node |')
        L.append('')
    L.append('## Custom metrics')
    L.append('')
    c0 = r['control']
    L.append(f'The engine\'s Datadog metric output publishes two counters, event volume and bytes, for each label set of two aggregators, `all_events` and `emitted_events`. '
             f'{cm["definition"]} On this capture the control run produced {c0["label_sets"]["all_events"]:,} label sets in `all_events` and {c0["label_sets"]["emitted_events"]:,} in `emitted_events`, {c0["custom_metrics"]:,} custom metrics from one node. '
             f'A move splits label sets by route, so each target\'s count is in its table. {cm["counting"]} {cm["log_based"]}')
    L.append('')
    L.append('## Counting conditions')
    L.append('')
    L.append(f'- Datadog counts indexed events: "{prices["event_counting"]["quote"]}" ([{r["prices_read_on"]}]({prices["event_counting"]["url"]})). With the shipped forwarder path one record is one event; the Receiver groups the lines of a multi-line event into one record, and the engine counted {r["control"]["events"]:,} records from {r["capture"]["lines"]:,} lines here.')
    L.append('- The Flex route is the documented index filter on `@routeState:tier_down`, applied to a Flex index listed before the Standard one. Every event the engine marks `tier_down` carries that field to Datadog.')
    L.append('- The regulator caps each pattern\'s bytes per container per 240 s window; an event over its pattern\'s cap takes the container\'s action. Patterns under 5% of their container\'s bytes in the window are not capped, the first 5 events of a pattern in a window pass, and the severity floors keep a share of each level: a tenth of INFO, DEBUG and TRACE, three tenths of WARN, half of ERROR and CRITICAL. The kept share is drawn at random per event, so a rerun differs within that noise.')
    L.append('- The replay delivers the capture inside one window; each cap the plan wrote is multiplied by the span the plan covers over 240 s, and nothing else in the plan\'s files is changed. `results/policy-*.json` records the files and the factor.')
    L.append(f'- Events and GB are the engine\'s counts of the records it emitted; dollars are those counts at list price. A month is {r["month_hours"]} hours; the capture covers {r["window_hours"]:g}.')
    L.append('')
    L.append('## Reproduce')
    L.append('')
    L.append('```sh')
    L.append('./run.sh                 # everything')
    L.append('./run.sh plan replay     # some stages, in the order given')
    L.append('```')
    L.append('')
    L.append('Stages: `data plan control policy replay count report`. Needs Docker, Node 18 or later and about 1 GB of disk. `plan` installs the pinned log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; the server runs the pinned engine image for its own sampling. Every other stage runs the engine image on the capture. '
             '`ACCT_TARGETS` sets the targets (default `30 50 70`), `ACCT_WINDOW` the span the capture covers (default `10h`).')
    L.append('')
    L.append('| File | What it is |')
    L.append('|---|---|')
    L.append('| `run.sh` | the whole run, in stages |')
    L.append('| `prices.json` | every price used, with its URL and the date read |')
    L.append('| `report.py` | renders `results/results.md` and `results/results.json` from the kept outputs; `--check` fails CI if the committed figures do not follow from them |')
    L.append('| `../accounting-lib/plan.mjs` | asks the released MCP for its plan over stdio and keeps what it wrote |')
    L.append('| `../accounting-lib/replay.config.yaml` | the engine run: shipped enrichment, regulator and aggregators, file in, file out |')
    L.append('| `../accounting-lib/policy.py` | the engine files the tool wrote, caps scaled to the one-window replay |')
    L.append('| `../accounting-lib/count.py` | the two counts, records and aggregators, required to agree |')
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
        readme = open(here / 'README.md').read()
        for t, v in r['targets'].items():
            cell = f'{v["engine"]["by_route"].get("tier_down", {"events": 0})["events"]:,}'
            if f'| {t}% |' not in readme or f'| {cell} |' not in readme:
                raise SystemExit(f'README.md does not carry the {t}% figure {cell}')
        if committed != r:
            for k in r:
                if committed.get(k) != r[k]:
                    print(f'differs: {k}')
            raise SystemExit('results.json does not follow from the kept tallies')
        print('the committed figures follow from the kept tallies: ' +
              ', '.join(f'{t}% moves {v["engine"]["by_route"].get("tier_down", {"events": 0})["events"]:,} events' for t, v in r['targets'].items()))
        return 0
    json.dump(r, open(results / 'results.json', 'w'), indent=1)
    open(results / 'results.md', 'w').write(render(r, prices))
    print(f'wrote {results / "results.md"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
