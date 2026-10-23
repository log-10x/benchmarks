#!/usr/bin/env python3
"""Score the run against ROWS_RUN_METHOD.md, from the files the rig wrote.

  score.py <results-dir>   -> markdown on stdout

Criteria 1, 2, 6 and the pre-registered reports come from meter.log, timeline.jsonl
and budget-runs/*; criteria 3 to 5 and 7 need ClickHouse and the wire and are
scored by final.py while the containers are still up. Nothing here is a cost.
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


def main() -> int:
    res = sys.argv[1]
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
