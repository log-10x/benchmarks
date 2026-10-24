#!/usr/bin/env python3
"""Score the run against ROWS_RUN_METHOD.md, from the files the rig wrote.

  score.py <results-dir>               -> markdown on stdout
  score.py <results-dir> --arms two    -> the two-arm run's three criteria and the comparison table

Criteria 1, 2, 6 and the pre-registered reports come from meter.log, timeline.jsonl
and budget-runs/*; criteria 3 to 5 and 7 need ClickHouse and the wire and are
scored by final.py while the containers are still up. Nothing here is a cost.

The two-arm scoring reads two-arm-windows.json (written at collect), or else the
last reading of each window in meter-tables.log, in windows of ten rig minutes
counted from T0, so every phase starts on a window.
"""
import glob
import json
import os
import re
import sys

WINDOW = 240


def load_jsonl(path):
    out = []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return out


# The two-arm run's windows, by index of ten rig minutes from T0, and the schedule phases.sh runs.
PRE = 5                    # minutes 50 to 60: both arms steady, two applied runs after the rate binds
AFTER = range(6, 16)       # the first growth step (60) to the end of the hold (160)
HOLD = range(12, 16)       # the hold at 5x, 120 to 160
PACE = [(0, 14, "baseline"), (30, 14, "dry run"), (40, 14, "held"), (60, 19, "growth"), (80, 24, "growth, inject"),
        (100, 30, "growth, storm"), (120, 35, "hold"), (160, 0, "drain")]


def floors_from_runs(res):
    out = []
    for d in sorted(glob.glob(os.path.join(res, "budget-runs", "*"))):
        rp = os.path.join(d, "report.txt")
        txt = open(rp).read() if os.path.exists(rp) else ""
        if "[DRY RUN]" in txt:
            continue
        m = re.search(r"keeps about ([0-9.]+)([kM]?) lines an hour whatever", txt)
        try:
            ep = int(__import__("calendar").timegm(__import__("time").strptime(os.path.basename(d), "%Y%m%dT%H%M%SZ")))
        except ValueError:
            continue
        if m:
            out.append((ep, float(m.group(1)) * {"": 1, "k": 1e3, "M": 1e6}[m.group(2)]))
    return sorted(out)


def two_arm_windows(res, t0, w):
    """{table: {index: fields}}, node and other-insert CPU by index, buckets, totals, and where they came from."""
    path = os.path.join(res, "two-arm-windows.json")
    if os.path.exists(path):
        doc = json.load(open(path))
        source = "two-arm-windows.json, read from ClickHouse at collect"
    else:
        doc = {"tables": {}, "node_us": {}, "other_inserts": {}}
        for rec in load_jsonl(os.path.join(res, "meter-tables.log")):
            for t, ws in rec.get("tables", {}).items():
                doc["tables"].setdefault(t, {}).update(ws)
            doc["node_us"].update(rec.get("node_us", {}))
            doc["other_inserts"].update(rec.get("other_inserts", {}))
        source = "meter-tables.log, the last reading of each window (collect did not run)"
    idx = lambda k: (int(k) - t0) // w
    tables = {t: {idx(k): v for k, v in ws.items()} for t, ws in doc.get("tables", {}).items()}
    node = {idx(k): v for k, v in doc.get("node_us", {}).items()}
    other = {idx(k): v for k, v in doc.get("other_inserts", {}).items()}
    bucket = {t: {idx(k): v for k, v in ws.items()} for t, ws in doc.get("bucket", {}).items()}
    return tables, node, other, bucket, doc.get("totals", {}), source


def score_two(res) -> int:
    tl = load_jsonl(os.path.join(res, "timeline.jsonl"))
    ev = {e["event"]: e for e in tl}
    t0 = int(open(os.path.join(res, "t0")).read().strip())
    arms = ev.get("arms", {})
    m = int(arms.get("m", 60))
    w = int(arms.get("window_s", 10 * m))
    rate = ev.get("rate_set")
    R = float(rate["R"]) if rate else 0.0
    bound = R * w / 3600
    tables, node, other, bucket, totals, source = two_arm_windows(res, t0, w)
    A, B = tables.get("otel_logs", {}), tables.get("otel_logs_rule", {})

    def rows(t, i):
        return t.get(i, {}).get("rows")

    def cpu(t, i):
        v = t.get(i)
        return None if v is None else (v.get("insert_us", 0) + v.get("merge_us", 0)) / 1e6

    def ratio(v, base):
        return None if v is None or not base else v / base

    def f(v, p=2):
        return "" if v is None else f"{v:.{p}f}"

    out = [f"# Two-arm run score, from {os.path.basename(res.rstrip('/'))}", ""]
    out.append(f"Arm A: the rows run, table `default.otel_logs`. Arm B: the collector rule ({', '.join(arms.get('top', []))} INFO and DEBUG to its bucket), table `default.otel_logs_rule`.")
    out.append(f"R = {int(R)} rows an hour, so R/6 of a window = {bound:.0f} rows (window {w} s, ten rig minutes at {m} s a minute, from T0 = {t0}). P = {rate['P'] if rate else 'n/a'}.")
    out.append(f"Source: {source}. The pre-step level is window {PRE} (minutes 50 to 60) for both arms; window 4 (40 to 50) holds the first applied run's pickup and is shown, not used.")
    marks = [(k, ev[k]["epoch"]) for k in ("phase_held", "phase_growth", "phase_hold_5x", "phase_drain") if k in ev]
    out.append("Phase marks, rig minutes after T0: " + ", ".join(f"{k} {(e - t0) / m:.1f}" for k, e in marks) + ".")
    out.append("")

    lvl_rows_b = rows(B, PRE)
    lvl_cpu_a, lvl_cpu_b = cpu(A, PRE), cpu(B, PRE)

    c1 = [(i, rows(A, i)) for i in AFTER]
    ok1 = bool(R) and all(v is not None and v <= 1.10 * bound for _, v in c1)
    out.append(f"## 1. Arm A's rows per window at or under 1.10 R/6 = {1.10 * bound:.0f}, from the first growth step to the end of the hold: {'PASS' if ok1 else 'FAIL'}")
    out.append(", ".join(f"w{i} {f(ratio(v, bound))}" for i, v in c1) + " (of R/6).")
    # the rows run's 4-minute test, reported: epoch-aligned windows of 240 s on the meter, bound (R + F)/15
    floors = floors_from_runs(res)
    def floor_at(x):
        v = 0.0
        for ep, fl in floors:
            if ep <= x:
                v = fl
        return v
    four = {}
    for rec in load_jsonl(os.path.join(res, "meter.log")):
        for k, n in rec.get("windows", {}).items():
            four[int(k)] = int(n)
    scored4 = sorted((k, n) for k, n in four.items() if t0 + 60 * m <= k and k + WINDOW <= t0 + 160 * m)
    over4 = [(k, n) for k, n in scored4 if R and n > (R + floor_at(k)) / (3600 / WINDOW)]
    top4 = max((n / ((R + floor_at(k)) / (3600 / WINDOW)) for k, n in scored4), default=0) if R else 0
    out.append(f"\nThe 4-minute test of the rows run, reported: {len(scored4)} windows, {len(over4)} over R/15 plus F/15, the largest at {top4:.2f} of its bound.")
    out.append("")

    c2 = [(i, rows(B, i)) for i in HOLD]
    ok2 = bool(lvl_rows_b) and all(v is not None and v > 1.5 * lvl_rows_b for _, v in c2)
    out.append(f"## 2. Arm B's rows per window above 1.5x its pre-step level ({lvl_rows_b} rows) in every window of the hold: {'PASS' if ok2 else 'FAIL'}")
    out.append(", ".join(f"w{i} {f(ratio(v, lvl_rows_b))}" for i, v in c2) + " (of the pre-step level).")
    if not ok2:
        out.append("\n**No differentiator** on rows: arm B did not rise above 1.5x in every window of the hold.")
    out.append("")

    c3a = [(i, cpu(A, i)) for i in AFTER]
    c3b = [(i, cpu(B, i)) for i in HOLD]
    ok3a = bool(lvl_cpu_a) and all(v is not None and v <= 1.10 * lvl_cpu_a for _, v in c3a)
    ok3b = bool(lvl_cpu_b) and all(v is not None and v > 1.5 * lvl_cpu_b for _, v in c3b)
    out.append(f"## 3. Insert plus merge CPU: {'PASS' if ok3a and ok3b else 'FAIL'} (arm A {'holds' if ok3a else 'does not hold'}; arm B {'rises' if ok3b else 'does not rise'})")
    out.append(f"Arm A, every window from the first growth step to the end of the hold at or under 1.10 of its pre-step {f(lvl_cpu_a)} s: "
               + ", ".join(f"w{i} {f(ratio(v, lvl_cpu_a))}" for i, v in c3a) + ".")
    out.append(f"Arm B, every window of the hold above 1.5x its pre-step {f(lvl_cpu_b)} s: "
               + ", ".join(f"w{i} {f(ratio(v, lvl_cpu_b))}" for i, v in c3b) + ".")
    out.append("Arm B's half is scored on the hold, as criterion 2 is; every window is in the table below.")
    if not ok3b:
        out.append("\n**No differentiator** on CPU: arm B's write CPU did not rise above 1.5x in every window of the hold.")
    out.append("\nNoise: these are ClickHouse's own user plus system time for the inserts into each table (system.query_log, Insert and AsyncInsertFlush, by `tables`) and the merges of each table (system.part_log MergeParts), on one container on one host, both arms sharing its three CPUs. Merge CPU depends on which parts the scheduler merged inside a window. The node column is the whole server (system.metric_log), both arms and everything else, and is noisier still.")
    out.append("")

    out.append("## Comparison, per window of ten rig minutes")
    out.append("| w | minutes | phase | lines/s | A rows | A of R/6 | B rows | B of pre-step | A insert s | A merge s | A CPU of pre-step | B insert s | B merge s | B CPU of pre-step | A inserts | B inserts | node s (noisy) | A bucket rows | B bucket rows |")
    out.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for i in range(0, 18):
        mn = 10 * i
        pace, phase = next((p, ph) for st, p, ph in reversed(PACE) if st <= mn)
        a, b = A.get(i, {}), B.get(i, {})
        out.append(" | ".join([
            f"| {i}", f"{mn}-{mn + 10}", phase, str(pace),
            str(a.get("rows", "")), f(ratio(rows(A, i), bound)),
            str(b.get("rows", "")), f(ratio(rows(B, i), lvl_rows_b)),
            f(a.get("insert_us", 0) / 1e6 if a else None), f(a.get("merge_us", 0) / 1e6 if a else None), f(ratio(cpu(A, i), lvl_cpu_a)),
            f(b.get("insert_us", 0) / 1e6 if b else None), f(b.get("merge_us", 0) / 1e6 if b else None), f(ratio(cpu(B, i), lvl_cpu_b)),
            str(a.get("inserts", 0) + a.get("flushes", 0)) if a else "", str(b.get("inserts", 0) + b.get("flushes", 0)) if b else "",
            f(node[i] / 1e6 if i in node else None, 1),
            str(bucket.get("otel_logs", {}).get(i, "")), str(bucket.get("otel_logs_rule", {}).get(i, ""))]) + " |")
    out.append("")

    def tot(t, key):
        return sum(v.get(key, 0) for v in tables.get(t, {}).values())
    out.append("## Totals for the run")
    out.append("| | arm A (`otel_logs`) | arm B (`otel_logs_rule`) |\n|---|---:|---:|")
    out.append(f"| rows written (part_log NewPart) | {tot('otel_logs', 'rows')} | {tot('otel_logs_rule', 'rows')} |")
    out.append(f"| rows in the table at collect | {totals.get('hot_rows', '')} | {totals.get('rule_rows', '')} |")
    out.append(f"| rows in the bucket | {totals.get('cold_rows', '')} | {totals.get('rule_cold_rows', '')} |")
    out.append(f"| inserts (of which async flushes) | {tot('otel_logs', 'inserts') + tot('otel_logs', 'flushes')} ({tot('otel_logs', 'flushes')}) | {tot('otel_logs_rule', 'inserts') + tot('otel_logs_rule', 'flushes')} ({tot('otel_logs_rule', 'flushes')}) |")
    out.append(f"| failed inserts | {tot('otel_logs', 'failed_inserts')} | {tot('otel_logs_rule', 'failed_inserts')} |")
    out.append(f"| insert CPU, s | {tot('otel_logs', 'insert_us') / 1e6:.1f} | {tot('otel_logs_rule', 'insert_us') / 1e6:.1f} |")
    out.append(f"| merge CPU, s | {tot('otel_logs', 'merge_us') / 1e6:.1f} | {tot('otel_logs_rule', 'merge_us') / 1e6:.1f} |")
    out.append(f"| merges | {tot('otel_logs', 'merges')} | {tot('otel_logs_rule', 'merges')} |")
    out.append(f"| counts table merge CPU, s | {tot('counts_by_type', 'merge_us') / 1e6:.1f} | {tot('counts_by_type_rule', 'merge_us') / 1e6:.1f} |")
    fl = totals.get("feed_lines")
    if fl is not None and totals.get("rule_rows", -1) >= 0 and totals.get("rule_cold_rows", -1) >= 0:
        both = totals["rule_rows"] + totals["rule_cold_rows"]
        out.append(f"\nArm B delivery: {fl} lines written to the feed, {both} rows in its table plus its bucket ({'equal' if both == fl else f'{both - fl:+d}'}). Arm A's delivery is final.py's criterion 5.")
    oth = sum(v.get("inserts", 0) + v.get("flushes", 0) for v in other.values())
    out.append(f"Inserts and async flushes into neither logs table over the run: {oth} ({sum(v.get('insert_us', 0) for v in other.values()) / 1e6:.1f} s CPU), not attributed to either arm.")
    out.append("")

    hold_a = [cpu(A, i) for i in HOLD if cpu(A, i) is not None]
    hold_b = [cpu(B, i) for i in HOLD if cpu(B, i) is not None]
    ga = (sum(hold_a) / len(hold_a)) / lvl_cpu_a if hold_a and lvl_cpu_a else None
    gb = (sum(hold_b) / len(hold_b)) / lvl_cpu_b if hold_b and lvl_cpu_b else None
    ab = sum(hold_a) / sum(hold_b) if hold_a and hold_b and sum(hold_b) else None
    out.append("## Projection, reported, not scored")
    out.append(f"Write CPU in the hold against the pre-step window: arm A {f(ga)}x, arm B {f(gb)}x. Arm A's write CPU over the hold as a share of arm B's: {f(ab)}.")
    out.append("The method's projection is Saving = W x R, W the buyer's write share of CPU from its own query_log, at $0.2985 per 8 GiB unit-hour (Scale), units set by the autoscaler (scale-down under 37.5% CPU). It is an inequality, not a bill; no bill is computed here.")
    print("\n".join(out))
    return 0


def main() -> int:
    res = sys.argv[1]
    if sys.argv[2:4] == ["--arms", "two"]:
        return score_two(res)
    tl = load_jsonl(os.path.join(res, "timeline.jsonl"))
    meter = load_jsonl(os.path.join(res, "meter.log"))
    ev = {e["event"]: e for e in tl}
    runs = sorted(glob.glob(os.path.join(res, "budget-runs", "*")))
    rate = next((e for e in tl if e["event"] == "rate_set"), None)
    R = float(rate["R"]) if rate else 0.0
    per_window_bound = R / (3600 / WINDOW)
    t_held = ev.get("phase_held", {}).get("epoch")
    t_drain = ev.get("phase_drain", {}).get("epoch")
    reloads = [e["epoch"] for e in tl if e["event"] == "budget_run" and not e.get("dry_run") and e.get("exit") == 0]

    out = [f"# Rows run score, from {os.path.basename(res.rstrip('/'))}", ""]
    out.append(f"R = {int(R)} rows an hour ({per_window_bound:.0f} a 4-minute window); P = {rate['P'] if rate else 'n/a'}.")
    out.append("")

    # criterion 1: every applied run exits 0 and commits; projection at or under R or floor stated
    c1 = []
    for d in runs:
        try:
            rc = int(open(os.path.join(d, "exit")).read().strip())
        except (OSError, ValueError):
            rc = -1
        txt = open(os.path.join(d, "report.txt")).read() if os.path.exists(os.path.join(d, "report.txt")) else ""
        m = re.search(r"table takes about ([0-9.]+)([kM]?) an hour", txt)
        proj = float(m.group(1)) * {"": 1, "k": 1e3, "M": 1e6}[m.group(2)] if m else None
        floor_said = "floor" in txt
        commit = json.load(open(os.path.join(d, "commit.json"))) if os.path.exists(os.path.join(d, "commit.json")) else {}
        c1.append((os.path.basename(d), rc, proj, commit.get("before") != commit.get("after"), floor_said))
    applied = [x for x in c1 if x[3]]
    ok1 = all(x[1] == 0 for x in c1) and all((x[2] is None) or (x[2] <= R * 1.001) or x[4] for x in applied if R)
    out.append(f"## 1. Runs: {'PASS' if ok1 else 'FAIL'}")
    out.append("| run | exit | projected an hour | committed |\n|---|---:|---:|---|")
    for name, rc, proj, committed, _ in c1:
        out.append(f"| {name} | {rc} | {'' if proj is None else int(proj)} | {committed} |")
    out.append("")

    # criterion 2 as METHOD.md writes it: each 4-minute window at or under R/15 plus the floor's share
    # of a window (F/15, F from the applied run in force at the window's start); each 10-minute meter
    # window's sum at or under R/6. From t_held + 20 minutes (two applied runs) to the drain.
    def unit(v, u):
        return float(v) * {"": 1, "k": 1e3, "M": 1e6}[u]
    floors = []
    for d in runs:
        rp = os.path.join(d, "report.txt")
        txt = open(rp).read() if os.path.exists(rp) else ""
        if "[DRY RUN]" in txt:
            continue
        m = re.search(r"keeps about ([0-9.]+)([kM]?) lines an hour whatever", txt)
        stamp = os.path.basename(d)
        try:
            ep = int(__import__("calendar").timegm(__import__("time").strptime(stamp, "%Y%m%dT%H%M%SZ")))
        except ValueError:
            continue
        if m:
            floors.append((ep, unit(m.group(1), m.group(2))))
    floors.sort()
    def floor_at(w):
        f = 0.0
        for ep, v in floors:
            if ep <= w:
                f = v
        return f
    windows = {}
    for rec in meter:
        for w, n in rec.get("windows", {}).items():
            windows[int(w)] = int(n)
    start = (t_held or 0) + 20 * 60
    scored = sorted((w, n) for w, n in windows.items() if t_held and t_drain and start <= w < t_drain)
    bound_of = {w: (R + floor_at(w)) / (3600 / WINDOW) for w, _ in scored}
    over = [(w, n) for w, n in scored if n > bound_of[w]]
    # 10-minute meter windows: read from system.part_log while the rig is up (exact); otherwise
    # prorate the 4-minute windows by overlap (an estimate, labelled as one)
    sums = {}
    sums_source = "system.part_log, exact"
    if t_held and t_drain:
        import subprocess
        q = (f"SELECT intDiv(toUnixTimestamp(event_time), 600) * 600 AS w, sum(rows) FROM system.part_log "
             f"WHERE event_type = 'NewPart' AND database = 'default' AND table = 'otel_logs' "
             f"AND event_time >= toDateTime({(start // 600 + 1) * 600}) AND event_time < toDateTime({(t_drain // 600) * 600}) "
             f"GROUP BY w ORDER BY w FORMAT TSV")
        r = subprocess.run(["docker", "exec", "cse-clickstack", "clickhouse-client", "--query", q], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                k, v = line.split("\t")
                sums[int(k)] = int(v)
        else:
            sums_source = "prorated from the 4-minute windows by overlap, an estimate"
            for w, n in scored:
                for k in range((w // 600) * 600, w + WINDOW, 600):
                    ov = max(0, min(w + WINDOW, k + 600) - max(w, k))
                    if ov and k >= (start // 600 + 1) * 600 and k + 600 <= t_drain:
                        sums[k] = sums.get(k, 0) + n * ov / WINDOW
    over10 = [(k, v) for k, v in sorted(sums.items()) if v > R / 6]
    out.append(f"## 2. Rows per window on the meter: {'PASS' if scored and not over and not over10 else 'FAIL'}")
    out.append(f"{len(scored)} windows scored from {start} to {t_drain}; {len(over)} over their bound (R/15 = {per_window_bound:.0f} plus F/15); {len(over10)} ten-minute sums over R/6 = {R / 6:.0f}.")
    out.append("| window (epoch) | rows | R/15 + F/15 | of that bound | of R/15 |\n|---|---:|---:|---:|---:|")
    for w, n in scored:
        out.append(f"| {w} | {n} | {bound_of[w]:.0f} | {n / bound_of[w] if bound_of[w] else 0:.2f} | {n / per_window_bound if per_window_bound else 0:.2f} |")
    out.append(f"\n10-minute meter windows ({sums_source}):\n")
    out.append("| 10-minute window (epoch) | rows | of R/6 |\n|---|---:|---:|")
    for k, v in sorted(sums.items()):
        out.append(f"| {k} | {int(v)} | {v / (R / 6) if R else 0:.2f} |")
    out.append("")

    # criterion 6: storm statement kept per window at most limit + 50; reload windows reported separately
    storm = ev.get("storm_start")
    out.append("## 6. Storm")
    if storm:
        series = [(r["epoch"], r.get("storm_hot_rows", 0)) for r in meter]
        out.append(f"Storm from {storm['epoch']} at {storm.get('rate')} lines a second until {storm.get('until')}. Hot rows of the storming statement by reading:")
        out.append("| epoch | storm rows in hot | reload within the window |\n|---|---:|---|")
        for ep, n in series:
            if storm["epoch"] - WINDOW <= ep <= int(storm.get("until", ep)) + 2 * WINDOW:
                w0 = (ep // WINDOW) * WINDOW
                rl = any(w0 <= r < w0 + WINDOW for r in reloads)
                out.append(f"| {ep} | {n} | {'yes' if rl else ''} |")
        out.append("The per-window increment against the statement's limit plus 50 is read from this table by hand; the limit is in the applied run's caps.csv for grafana.")
    else:
        out.append("No storm recorded.")
    out.append("")

    # reports
    out.append("## Reports, pre-registered")
    out.append("| run | floor F an hour | outside O an hour | kept an hour | moved an hour |\n|---|---:|---:|---:|---:|")
    for d in runs:
        txt = open(os.path.join(d, "report.txt")).read() if os.path.exists(os.path.join(d, "report.txt")) else ""
        f = re.search(r"keeps about ([0-9.]+[kM]?) lines an hour whatever", txt)
        o = re.search(r"Outside the Receiver: ([0-9.]+[kM]?) rows", txt)
        mv = re.search(r"with ([0-9.]+[kM]?) an hour of lines to the", txt)
        pj = re.search(r"table takes about ([0-9.]+[kM]?) an hour", txt)
        out.append(f"| {os.path.basename(d)} | {f.group(1) if f else ''} | {o.group(1) if o else ''} | {pj.group(1) if pj else ''} | {mv.group(1) if mv else ''} |")
    out.append("")
    out.append("Reload windows (an applied run committed inside them): " + ", ".join(str((r // WINDOW) * WINDOW) for r in reloads))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
