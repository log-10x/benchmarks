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
import readme as README  # noqa: E402
import filters as F  # noqa: E402


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
        'control': {
            'events': control['events'],
            'bytes': control['bytes'],
            'by_severity': {s: v['events'] for s, v in T.by_route_severity(control).get('pass', {}).items()},
            'custom_metrics': control['series']['custom_metrics'],
            'label_sets': control['series']['label_sets_per_aggregator'],
            'datadog_series': datadog_series_summary(T.load(results / 'datadog-series-control.json')),
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
        stored_month = events_month  # held 30 days, the minimum billed on a scalable tier
        tiers = prices['flex_compute']['tiers_by_cumulative_events_stored']
        months_min = starter['minimum_retention_months']
        months_list = starter['price_list_minimum_retention_months']
        # Starter: below its monthly limit, and below its stored limit when every event is held
        # the minimum retention. Otherwise the scalable tier for the events stored at 30 days.
        within_starter = (events_month < prices['flex_compute']['starter_monthly_limit_events']
                          and events_month * months_min < tiers[0][2])
        scalable = [x for x in tiers if x[0] != 'Starter']
        tier = 'Starter' if within_starter else next(
            (name for name, lo, hi in scalable if lo <= stored_month < hi), scalable[0][0] if stored_month < scalable[0][1] else 'above L')
        avoided15, avoided30 = events_month / 1e6 * idx['15d']['annual'], events_month / 1e6 * idx['30d']['annual']
        starter_min = events_month / 1e6 * starter['annual'] * months_min
        scalable_30 = events_month / 1e6 * flex['annual']
        added = starter_min if within_starter else scalable_30
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
                'flex_added': {
                    'tier': tier,
                    'starter_minimum_months': months_min,
                    'starter_minimum_annual': round(starter_min, 4),
                    'starter_minimum_on_demand': round(events_month / 1e6 * starter['on_demand'] * months_min, 4),
                    'starter_price_list_months': months_list,
                    'starter_price_list_annual': round(events_month / 1e6 * starter['annual'] * months_list, 4),
                    'scalable_30_days_annual': round(scalable_30, 4),
                    'scalable_30_days_on_demand': round(events_month / 1e6 * flex['on_demand'], 4),
                    'scalable_compute': prices['flex_compute']['price'],
                    'at_tier_annual': round(added, 4),
                    'at_tier_excludes_compute': not within_starter,
                },
                # From the cent amounts the tables show, so each row's subtraction checks.
                'net_against_15d_annual': round(round(avoided15, 2) - round(added, 2), 2),
                'net_against_30d_annual': round(round(avoided30, 2) - round(added, 2), 2),
                'ingestion_unchanged': round(T.monthly(T.gb(tl['bytes']), window_hours) * prices['ingestion_per_gb']['annual'], 4),
            },
            'flex_compute': {
                'cumulative_events_stored_at_30_days': round(stored_month),
                'tier': tier,
                'within_starter_monthly_limit': within_starter,
                'price': prices['flex_compute']['price'],
            },
            'custom_metrics': custom_metrics(T.load(results / f'datadog-series-{t}.json'), tl, cmc, cm),
            'native_filters': F.native_filters(control, tl, policy),
        }
    return out



def custom_metrics(ds, tl, cmc, cm):
    """What the shipped Datadog output posted on this run (datadog-series-<t>.json), priced at
    10, 100 and 300 nodes: its series carry no node or process tag, so the count is the same
    from every node. Every tag set from every node is the tally's label sets, for comparison."""
    measured = ds['max_series_per_post']
    allot = cm['allotment_per_host']['pro']
    per100 = cm['per_100_per_month']['annual']
    return {
        'count_measured': measured,
        'distinct_over_run': ds['distinct_series_over_run'],
        'posts': len(ds['posts']),
        'node_or_process_tags': ds['node_or_process_tags'],
        'host_field': ds['host_field'],
        'tag_keys': ds['tag_keys'],
        'top_series_default': tl['series']['top_series_default'],
        'bytes_share_of_top_series': tl['series']['bytes_share_of_top_series'],
        'count_every_set_one_node': cmc,
        'label_sets': tl['series']['label_sets_per_aggregator'],
        'fleet': {str(n): {
            'measured_above_pro_allotment': max(0, measured - n * allot),
            'measured_usd_per_month': round(max(0, measured - n * allot) / 100 * per100, 2),
            'every_set_per_node_usd_per_month': round(max(0, cmc * n - n * allot) / 100 * per100, 2),
        } for n in (10, 100, 300)},
    }


def datadog_series_summary(ds):
    return {'max_series_per_post': ds['max_series_per_post'], 'distinct_series_over_run': ds['distinct_series_over_run'],
            'posts': len(ds['posts']), 'tag_keys': ds['tag_keys'], 'node_or_process_tags': ds['node_or_process_tags'],
            'host_field': ds['host_field']}


def signed(x):
    """A dollar amount with its sign: + saves, - costs more."""
    return ('+' if x >= 0 else '-') + T.fmt_usd(abs(x))


def starter_sign_sentence(r: dict) -> str:
    """The sign of tier down at this capture's volume, per retention of the indexing avoided."""
    ts = list(r['targets'].values())
    if not all(v['usd_per_month_at_list']['flex_added']['tier'] == 'Starter' for v in ts):
        return 'At this capture\'s volume not every target falls in Starter; the month table gives each target\'s tier.'
    n15 = [v['usd_per_month_at_list']['net_against_15d_annual'] for v in ts]
    n30 = [v['usd_per_month_at_list']['net_against_30d_annual'] for v in ts]
    word = lambda xs: 'more than' if max(xs) < 0 else ('less than' if min(xs) > 0 else 'about the same as')  # noqa: E731
    return (f'At this capture\'s volume every target falls in Starter, and tier down to Flex Starter costs {word(n15)} the 15-day '
            f'indexing it avoids and {word(n30)} the 30-day indexing.')


def month_table(r: dict, with_ingestion: bool) -> list:
    """Per target: the tier the volume falls in, what Flex adds at that tier, and the net against each retention."""
    head = ('| Target | Events to Flex per month | Flex tier | Flex added at that tier, annual | Standard indexing avoided, 15-day annual | Net, 15-day | '
            'Standard indexing avoided, 30-day annual | Net, 30-day |' + (' Ingestion, unchanged |' if with_ingestion else '') +
            ' Custom metrics above a Pro allotment, 10 to 300 nodes |')
    M = [head, '|---:|---:|---|---:|---:|---:|---:|---:|' + ('---:|' if with_ingestion else '') + '---:|']
    for t, v in r['targets'].items():
        m, u, cm = v['month'], v['usd_per_month_at_list'], v['custom_metrics']
        fa = u['flex_added']
        added = (f'{T.fmt_usd(fa["at_tier_annual"])}, held {fa["starter_minimum_months"]} months' if fa['tier'] == 'Starter'
                 else f'{T.fmt_usd(fa["at_tier_annual"])} held 30 days, plus compute by quote')
        lo, hi = cm['fleet']['10']['measured_usd_per_month'], cm['fleet']['300']['measured_usd_per_month']
        fleet = T.fmt_usd(lo) if lo == hi else f'{T.fmt_usd(lo)} to {T.fmt_usd(hi)}'
        M.append(f'| {t}% | {m["events_to_flex"]:,} | {fa["tier"]} | {added} | {T.fmt_usd(u["standard_indexing_avoided"]["15d_annual"])} | '
                 f'{signed(u["net_against_15d_annual"])} | {T.fmt_usd(u["standard_indexing_avoided"]["30d_annual"])} | {signed(u["net_against_30d_annual"])} |'
                 + (f' {T.fmt_usd(u["ingestion_unchanged"])} |' if with_ingestion else '') + f' {fleet} |')
    starters = [(t, v['usd_per_month_at_list']['flex_added']) for t, v in r['targets'].items()
                if v['usd_per_month_at_list']['flex_added']['tier'] == 'Starter']
    if starters:
        fa0 = starters[0][1]
        M.append('')
        M.append(f'Net is the indexing avoided less what Flex adds; a minus sign means the move costs more than it saves. At '
                 f'{fa0["starter_price_list_months"]} months, the shortest Starter retention on Datadog\'s price list, the Starter rows '
                 f'cost ' + T.join_and([f'{T.fmt_usd(fa["starter_price_list_annual"])} at {t}%' for t, fa in starters]) + ' a month.')
    return M


def readme_blocks(r: dict, prices: dict) -> dict:
    """Every figure the README quotes from this run, rendered from results.json and prices.json."""
    c, cap = r['control'], r['capture']
    idx = prices['indexed_per_million_events']
    flex = prices['flex_storage_per_million_events_month']
    starter = prices['flex_starter_per_million_events_month']
    ing = prices['ingestion_per_gb']
    cmp = prices['custom_metrics']
    usd = lambda v: f'${v:,.0f}' if v == int(v) else f'${v:,.2f}'
    B = {}
    B['run'] = (f'The OpenTelemetry demo capture, {cap["lines"]:,} lines, {c["events"]:,} events after grouping, {T.gb(c["bytes"]):.3f} GB '
                f'over {r["window_hours"]:g} hours. Engine `log10x/pipeline-10x:{r["engine_tag"]}`, log10x-mcp {r["mcp_version"]}, '
                f'prices read {r["prices_read_on"]}.')
    mm, ml = starter['minimum_retention_months'], starter['price_list_minimum_retention_months']
    B['rates'] = (f'**What a moved event costs at list.** Standard indexing avoided: ${idx["15d"]["annual"]:.2f} per million events '
                  f'at 15-day retention and ${idx["30d"]["annual"]:.2f} at 30-day, annual; ${idx["15d"]["on_demand"]:.2f} and '
                  f'${idx["30d"]["on_demand"]:.2f} on demand. What Flex adds depends on the tier the volume falls in. Within Flex Starter, '
                  f'below {prices["flex_compute"]["starter_monthly_limit_events"] / 1e9:g} billion events a month and '
                  f'{prices["flex_compute"]["tiers_by_cumulative_events_stored"][0][2] / 1e9:g} billion stored, storage and compute are '
                  f'billed together at ${starter["annual"]:.2f} per million stored per month, annual (${starter["on_demand"]:.2f} on demand), '
                  f'for at least {mm} months: Datadog\'s Flex docs give {mm}, 6, 12 or 15 months and its price list {ml}, 12 or 15. '
                  f'A moved event held {mm} months costs at least ${starter["annual"] * mm:.2f} per million over its life. On the scalable '
                  f'tiers above Starter, XS to L, storage is ${flex["annual"]:.2f} per million stored per month, annual '
                  f'(${flex["on_demand"]:.3f} on demand), held at least 30 days, plus a flat compute tier Datadog prices on request '
                  f'("{prices["flex_compute"]["price"]}"). {starter_sign_sentence(r)} Ingestion, ${ing["annual"]:.2f} per GB, is paid once '
                  f'on every event and unchanged by a move. The full rate table with every URL is in [`results/results.md`](results/results.md).')
    L = ['| Target | Patterns planned | Containers capped | Events the plan states | Events the engine marked tier_down | Share of the volume the plan states | Share of the bytes the engine moved | Events in Standard | Errors and warnings to Flex |',
         '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for t, v in r['targets'].items():
        p, e = v['plan'], v['engine']['by_route']
        tot = sum(x['bytes'] for x in e.values())
        td = e.get('tier_down', {'events': 0, 'bytes': 0})
        L.append(f'| {t}% | {len(p["planned_patterns"])} | {len(p["containers"])} | {p["stated_events_moved"]:,} | {td["events"]:,} | '
                 f'{p["achieved_pct_stated"]:.1f}% | {td["bytes"] / tot * 100:.1f}% | {e.get("pass", {"events": 0})["events"]:,} | '
                 f'{v["engine"]["protected_moved_events"]:,} |')
    B['moves'] = '\n'.join(L)
    N = []
    for t, v in r['targets'].items():
        p = v['plan']
        by_c = {}
        for x in p['planned_patterns']:
            by_c.setdefault(x['container'] or '(no container)', []).append(x['name'])
        n = len(p['planned_patterns'])
        if n <= 8:
            where = '; '.join(f'`{c}`: ' + ', '.join(f'`{x}`' for x in names) for c, names in by_c.items())
            line = f'- **{t}%**: {n} pattern{"s" if n != 1 else ""} in {len(p["containers"])} container{"s" if len(p["containers"]) != 1 else ""} ({where})'
        else:
            line = f'- **{t}%**: {n} patterns in {len(p["containers"])} containers'
        if p['unattributed_planned']:
            line += f'; {p["unattributed_planned"]} planned pattern{"s" if p["unattributed_planned"] != 1 else ""} carried no container and {"are" if p["unattributed_planned"] != 1 else "is"} not in the files'
        N.append(line + '.')
    B['moves-notes'] = '\n'.join(N)
    M = month_table(r, with_ingestion=False)
    B['month'] = '\n'.join(M)
    ds = c['datadog_series']
    per_target = [v['custom_metrics'] for v in r['targets'].values()]
    distinct = [ds['distinct_series_over_run']] + [x['distinct_over_run'] for x in per_target]
    targets = list(r['targets'])
    every = c['custom_metrics']
    allot, per100 = cmp['allotment_per_host']['pro'], cmp['per_100_per_month']['annual']
    every_cost = [usd(max(0, every * n - n * allot) / 100 * per100) for n in (10, 100, 300)]
    measured_cost = sorted({usd(x['fleet'][str(n)]['measured_usd_per_month']) for x in per_target for n in (10, 100, 300)})
    tags = [k for k in ds['tag_keys'] if k != 'statistic']
    B['custom-metrics'] = (
        f'**Custom metrics.** The `metrics` stage replays the capture through the engine\'s shipped Datadog metric output, posting to '
        f'a local stand-in for Datadog\'s intake; the one change to the image\'s config is the URI it posts to. Each series carried '
        + ', '.join(f'`{k}`' for k in tags) +
        (', and no host, pod or pipeline id' if not ds['node_or_process_tags'] and not ds['host_field'] else
         f', and {", ".join(ds["node_or_process_tags"] + ds["host_field"])}') +
        f', so every node posts the same series. The output keeps to the {per_target[0]["top_series_default"]} tag sets with the most '
        f'bytes, each from both aggregators: at most {ds["max_series_per_post"]:,} series in one post without a move, and '
        + ', '.join(f'{x["count_measured"]:,}' for x in per_target[:-1]) + f' and {per_target[-1]["count_measured"]:,} at '
        + ', '.join(targets[:-1]) + f' and {targets[-1]}%. A Pro plan includes {allot} custom metrics per host, so at 10, 100 and 300 '
        f'nodes the line is {" to ".join(measured_cost)}. While ranks settle, tag sets enter and leave the top, and the replay, which '
        f'delivers {r["window_hours"]:g} hours in under a minute, saw {min(distinct):,} to {max(distinct):,} distinct series in all; '
        f'on a live stream that settling happens once. Every tag set from every node would be {every:,} series per node, '
        f'{every_cost[0]}, {every_cost[1]} and {every_cost[2]} a month at ${per100:.0f} per 100.')
    fmt_filters = lambda fs: ', '.join(f'`{f}`' for f in fs) if len(fs) <= 4 else f'{len(fs)} services, from ' + ', '.join(f'`{f}`' for f in fs[:3])
    X = ['| Target | Arm | Index filters | Events moved | Over the plan | GB moved | Errors and warnings moved | Events of patterns the plan keeps under a cap | Events the plan moves that stay in Standard |',
         '|---:|---|---|---:|---:|---:|---:|---:|---:|']
    V = []
    for t, v in r['targets'].items():
        nf = v['native_filters']
        pl = nf['plan']
        X.append(f'| {t}% | per-pattern plan | caps on {len(pl["containers_capped"])} container{"s" if len(pl["containers_capped"]) != 1 else ""} | {pl["events"]:,} | 0 | '
                 f'{T.gb(pl["bytes"]):.3f} | {pl["errors_and_warnings"]:,} | 0 | 0 |')
        for label, a in (('service filters', nf['filters']), ('service filters, `-status:(error OR warn)`', nf['filters_without_errors_and_warnings'])):
            X.append(f'| {t}% | {label} | {fmt_filters(a["filters"])} | {a["events"]:,} | {a["overshoot_events"]:+,} | {T.gb(a["bytes"]):.3f} | '
                     f'{a["errors_and_warnings"]:,} | {a["kept_under_cap_events"]:,} | {a["plan_moved_left_events"]:,} |')
        fs = nf['filters_without_errors_and_warnings']
        tail = (f' They move {fs["overshoot_events"]:,} more events than the plan\'s {pl["events"]:,}, which the plan leaves in Standard' +
                (f', and leave in Standard {fs["plan_moved_left_events"]:,} events the plan moves, in services they do not name.' if fs['plan_moved_left_events'] else '.'))
        if nf['key_adds_nothing_at_this_target']:
            V.append(f'- **{t}%**: the falsifier holds. With the status exclusion, the filters move {fs["errors_and_warnings"]:,} errors and warnings '
                     f'against the plan\'s {pl["errors_and_warnings"]:,}, and none of the patterns the plan keeps under a cap: per-pattern control '
                     f'adds nothing on this capture at this target.' + tail)
        else:
            why = []
            if fs['errors_and_warnings'] > pl['errors_and_warnings']:
                why.append(f'{fs["errors_and_warnings"]:,} errors and warnings against the plan\'s {pl["errors_and_warnings"]:,}')
            if fs['kept_under_cap_events']:
                why.append(f'{fs["kept_under_cap_events"]:,} events of {fs["kept_under_cap_patterns"]:,} pattern{"s" if fs["kept_under_cap_patterns"] != 1 else ""} '
                           f'the plan keeps under a cap ({fs["kept_under_cap_events"] / fs["events"] * 100:.2f}% of the {fs["events"]:,} events the filters move)')
            V.append(f'- **{t}%**: the falsifier does not hold. With the status exclusion, the filters move ' + ' and '.join(why) + '.' + tail)
    B['native-filters'] = '\n'.join(X)
    B['native-verdict'] = '\n'.join(V)
    return B

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
    L.append(f'| Flex storage, scalable tiers XS to L, per million events stored per month, held at least 30 days; compute priced apart | ${flex["annual"]:.2f} | ${flex["on_demand"]:.3f} | {flex["quote"]}; {flex["minimum"]} "{flex["retention_quote"]}" | [{r["prices_read_on"]}]({flex["url"]}), [docs]({flex["retention_url"]}) |')
    L.append(f'| Flex Starter, storage and compute bundled, per million events stored per month, held at least {starter["minimum_retention_months"]} months | ${starter["annual"]:.2f} | ${starter["on_demand"]:.2f} | {starter["quote"]}; {starter["limit"]}. "{starter["retention_quote"]}" "{starter["billing_quote"]}" {starter["retention_note"]} | [{r["prices_read_on"]}]({starter["url"]}), [docs]({starter["retention_url"]}) |')
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
        L.append(f'| {t}% | {len(p["planned_patterns"])} | {len(p["containers"])} | {T.fmt_int(p["stated_events_moved"])} | {T.fmt_int(e["by_route"].get("tier_down", {"events": 0})["events"])} | {T.fmt_gb(e["by_route"].get("tier_down", {"bytes": 0})["bytes"])} | {T.fmt_int(e["by_route"].get("pass", {"events": 0})["events"])} | {T.fmt_int(e["protected_moved_events"])} | {v["custom_metrics"]["count_measured"]:,} |')
    L.append('')
    L.append('The engine moves each pattern\'s excess over its container\'s cap; the plan sets the cap at the largest pattern the container keeps and states the excess, less the share the severity floors keep. Ingestion is unchanged: every event is ingested once, at '
             f'${prices["ingestion_per_gb"]["annual"]:.2f} per GB, before any index routing.')
    L.append('')
    L.append(f'## A month at this capture\'s volume, an illustration')
    L.append('')
    L.append(f'The capture\'s {r["window_hours"]:g} hours scaled to a {r["month_hours"]}-hour month, at the rates above. The volume is one small demo cluster\'s; the rates are what carry.')
    L.append('')
    L.extend(month_table(r, with_ingestion=True))
    L.append('')
    c0 = r['targets'][str(r['targets_list'][0])]['custom_metrics'] if r.get('targets_list') else next(iter(r['targets'].values()))['custom_metrics']
    L.append(f'**Custom metrics.** The engine\'s shipped Datadog output, posting to a local stand-in for Datadog\'s intake, tagged each series with the pattern and where it ran ({", ".join(f"`{k}`" for k in c0["tag_keys"])}) and with nothing that names a node or a process, and published the {c0["top_series_default"]} tag sets with the most bytes, each from both aggregators: at most {c0["count_measured"]:,} series in one post, whatever the node count; the top {c0["top_series_default"]} label sets carry {c0["bytes_share_of_top_series"] * 100:.1f}% of the bytes. '
             f'Above a Pro plan\'s allotment of 100 per host that is {T.fmt_usd(c0["fleet"]["10"]["measured_usd_per_month"])} a month at 10 nodes, {T.fmt_usd(c0["fleet"]["100"]["measured_usd_per_month"])} at 100 and {T.fmt_usd(c0["fleet"]["300"]["measured_usd_per_month"])} at 300. '
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
        fa = u['flex_added']
        L.append(f'| Flex tier for {T.fmt_int(m["events_to_flex"])} events a month | {fa["tier"]} |')
        L.append(f'| Flex Starter, storage and compute, held {fa["starter_minimum_months"]} months, annual | {T.fmt_usd(fa["starter_minimum_annual"])} |')
        L.append(f'| Flex Starter, storage and compute, held {fa["starter_minimum_months"]} months, on-demand | {T.fmt_usd(fa["starter_minimum_on_demand"])} |')
        L.append(f'| Flex Starter, held {fa["starter_price_list_months"]} months, the price list\'s shortest, annual | {T.fmt_usd(fa["starter_price_list_annual"])} |')
        L.append(f'| Flex storage on a scalable tier above Starter, held 30 days, annual, compute apart ({fa["scalable_compute"]}) | {T.fmt_usd(fa["scalable_30_days_annual"])} |')
        L.append(f'| Net against 15-day Standard, annual, at the {fa["tier"]} tier{" before compute" if fa["at_tier_excludes_compute"] else ""} | {signed(u["net_against_15d_annual"])} |')
        L.append(f'| Net against 30-day Standard, annual, at the {fa["tier"]} tier{" before compute" if fa["at_tier_excludes_compute"] else ""} | {signed(u["net_against_30d_annual"])} |')
        L.append(f'| Ingestion, unchanged | {T.fmt_usd(u["ingestion_unchanged"])} |')
        c = v['custom_metrics']
        L.append(f'| Custom metrics from the engine\'s Datadog metric output, measured | at most {c["count_measured"]:,} series in one of {c["posts"]} posts, {c["distinct_over_run"]:,} distinct over the replay while ranks settle, the same from every node; above a Pro allotment {T.fmt_usd(c["fleet"]["10"]["measured_usd_per_month"])} at 10 nodes, {T.fmt_usd(c["fleet"]["300"]["measured_usd_per_month"])} at 300. Every tag set would be {c["count_every_set_one_node"]:,} per node |')
        L.append('')
    L.append('## Native filters at equal events')
    L.append('')
    L.append('Per target, the index filters a person writes in Datadog today, one per service, largest by events first until they reach the events the engine marked tier_down under the plan; the second variant adds `-status:(error OR warn)`. Computed from the control run\'s counts and each target\'s. The selection rule and the falsifier are in the README.')
    L.append('')
    for t, v in r['targets'].items():
        nf = v['native_filters']
        L.append(f'### {t}%')
        L.append('')
        L.append('| Arm | Filters | Events | Bytes | By severity |')
        L.append('|---|---|---:|---:|---|')
        L.append(f'| per-pattern plan | caps: {", ".join(f"`{c}`" for c in nf["plan"]["containers_capped"])} | {nf["plan"]["events"]:,} | {nf["plan"]["bytes"]:,} | '
                 + ', '.join(f'{k} {n:,}' for k, n in nf['plan']['by_severity'].items()) + ' |')
        for label, a in (('service filters', nf['filters']), ('with `-status:(error OR warn)`', nf['filters_without_errors_and_warnings'])):
            L.append(f'| {label} | {", ".join(f"`{x}`" for x in a["filters"])} | {a["events"]:,} | {a["bytes"]:,} | '
                     + ', '.join(f'{k} {n:,}' for k, n in a['by_severity'].items()) + ' |')
        L.append('')
        for label, a in (('Service filters', nf['filters']), ('With the status exclusion', nf['filters_without_errors_and_warnings'])):
            if a['top_kept_under_cap_moved']:
                L.append(f'{label}, the largest patterns the plan keeps under a cap that the filters move: '
                         + '; '.join(f'`{x["container"]}` `{x["pattern"]}` {x["events"]:,}' for x in a['top_kept_under_cap_moved']) + '.')
            if a['top_plan_moved_left']:
                L.append(f'{label}, the largest patterns the plan moves that the filters leave in Standard: '
                         + '; '.join(f'`{x["container"]}` `{x["pattern"]}` {x["events"]:,}' for x in a['top_plan_moved_left']) + '.')
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
    L.append('Stages: `data plan control policy replay count metrics report`. Needs Docker, Node 18 or later and about 1 GB of disk. `plan` installs the pinned log10x-mcp into `.mcp/` and asks it for a plan over MCP stdio; the server runs the pinned engine image for its own sampling. Every other stage runs the engine image on the capture. '
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
    L.append('| `filters.py` | the native-filter control: service filters at the plan\'s events, from the control and target counts |')
    L.append('| `../accounting-lib/ddcapture.py`, `datadog_config.py`, `datadog_series.py` | the `metrics` stage: a local stand-in for Datadog\'s intake, the shipped Datadog config with only its URI pointed at it, and the count of what was posted |')
    L.append('| `results/datadog-series-<run>.json`, `results/datadog-config.diff` | the series each post carried, and the one line changed in the shipped config |')
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
              ', '.join(f'{t}% moves {v["engine"]["by_route"].get("tier_down", {"events": 0})["events"]:,} events' for t, v in r['targets'].items()))
        return 0
    json.dump(r, open(results / 'results.json', 'w'), indent=1)
    open(results / 'results.md', 'w').write(render(r, prices))
    readme = here / 'README.md'
    readme.write_text(README.apply(readme.read_text(), readme_blocks(r, prices)))
    print(f'wrote {results / "results.md"} and the README\'s generated blocks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
