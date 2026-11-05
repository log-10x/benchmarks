#!/usr/bin/env python3
"""Per-phase units, unit-hours and dollars, and the arm pairs' elasticity.

Units are 8 GiB of replica memory (2 vCPU each), summed over every replica serving.
Two meters, read independently:

  meter   the replicas' own asynchronous_metric_log, CGroupMemoryTotal per minute:
          each replica-minute counts its memory for the seconds it was sampled (n/60),
          so a make-before-break overlap counts all four replicas
  size    the sampler's Prometheus scrape every 60 s (size.jsonl), units x the gap to
          the next sample, gaps over 180 s not counted

Dollars are unit-hours x --price (0.2985, the published Scale compute rate per unit-hour
in AWS us-east-1, results/raw/pricing-quotes.md) and, separately, the change in usageCost
computeCHC between the poller's readings, shifted by --lag-min (the posting lag read
off the usage series; 0 prints the unshifted change), left out until the poller
has a reading past the phase's end plus that lag.

For each phase: hours, unit-hours both ways, mean units, the units over the last
--tail minutes (the size it settled at), and the CPU summary from curve.py. Each
phase is also cut at the driver's size events into segments named <phase>@<units>u
(a make-before-break overlap is its own segment), each with its hours, unit-hours
and CPU and memory, so a phase's settled size has its own utilisation. Memory is GiB per
replica, median minute: CGroupMemoryUsed and MemoryResident averaged over replicas, and
the used memory of the replica using the most. For each pair B<r> against A<r> (the arm
A run just before it) and A<r+1> (just after, only when it starts at B<r>'s end, so not
across an idle): the units ratio and the fall in units against the fall in rows (0.653)
and bytes (0.612). meter.jsonl and size.jsonl are read as committed, gzipped, when the
plain file is absent.

  arms_report.py --raw results/raw [--price 0.2985] [--lag-min 0] [--tail 30]
"""
import argparse
import collections
import gzip
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROWS, BYTES = 112205 / 171807, 24706958 / 40379948


def src(raw, name):
    p = raw / name
    return p if p.exists() else raw / (name + ".gz")


def lines(path):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)


def phases(events):
    out = [r for r in map(json.loads, open(events)) if "phase" in r and "event" not in r]
    return [(a, b["t"] if b else None) for a, b in zip(out, out[1:] + [None])]


def segments(events):
    evs = list(map(json.loads, open(events)))
    sizes = [(r["t"], r.get("units")) for r in evs if r.get("event") == "size"]
    out = []
    for p, end in phases(events):
        a, b = p["t"], end or 1e12
        cur = ([u for t, u in sizes if t <= a] or [None])[-1]
        cuts = [(a, cur)] + [(t, u) for t, u in sizes if a < t < b]
        for (t0, u), nxt in zip(cuts, cuts[1:] + [(b, None)]):
            out.append({"t": t0, "end": nxt[0], "phase": f"{p['phase']}@{u:g}u" if u else p["phase"], "of": p["phase"],
                        "arm": p.get("arm"), "rows_per_s": p.get("rows_per_s"), "mode": p.get("mode", "insert")})
    return out


def curve(meter, events):
    out = subprocess.run([sys.executable, str(HERE / "curve.py"), "--meter", str(meter), "--events", str(events)],
                         capture_output=True, text=True, check=True).stdout
    return {r["phase"]: r for r in map(json.loads, out.splitlines())}


def meter_units(path):
    per = collections.defaultdict(float)
    for line in lines(path):
        r = json.loads(line)
        if r.get("src") == "async" and r.get("metric") == "CGroupMemoryTotal":
            per[r["m"]] += r["avg"] / 2**33 * r.get("n", 60) / 60
    return per


def size_units(path):
    pts = []
    for line in lines(path):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("hosts"):
            pts.append((r["t"], sum(v["mem_total"] for v in r["hosts"].values()) / 2**33))
    return pts


def usage(path):
    """Cumulative computeCHC at each poll. A poll covers yesterday and today (UTC); a day that
    leaves the window keeps its last value, so the series does not drop at midnight."""
    pts, days = [], {}
    for line in open(path):
        r = json.loads(line)
        if "days" in r:
            days.update({k: v["computeCHC"] or 0 for k, v in r["days"].items()})
            pts.append((r["t"], sum(days.values()), r.get("amountSpent")))
    return pts


def at(pts, t):
    last = None
    for p in pts:
        if p[0] > t:
            break
        last = p
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--price", type=float, default=0.2985)
    ap.add_argument("--lag-min", type=float, default=0)
    ap.add_argument("--tail", type=float, default=30)
    args = ap.parse_args()
    raw = pathlib.Path(args.raw)
    meter = src(raw, "meter.jsonl")
    mu, su, us = meter_units(meter), size_units(src(raw, "size.jsonl")), usage(raw / "usage.jsonl")
    cpu = curve(meter, raw / "events.jsonl")
    segs = segments(raw / "events.jsonl")
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        for g in segs:
            fh.write(json.dumps({k: v for k, v in g.items() if k not in ("end", "of")}) + "\n")
        fh.write(json.dumps({"t": segs[-1]["end"], "phase": "stop"}) + "\n")
    seg_cpu = curve(meter, fh.name)
    pathlib.Path(fh.name).unlink()
    rows, spans = {}, {}
    for p, end in phases(raw / "events.jsonl"):
        name = p["phase"]
        if name == "stop" or not (name[0] in "AB" and name[1:].isdigit() or name.startswith("cal-")):
            continue
        a, b = p["t"], end or max(mu) + 60
        ms = [m for m in mu if a <= m and m + 60 <= b]
        uh_meter = sum(mu[m] for m in ms) / 60
        uh_size = 0.0
        for (t0, u0), (t1, _) in zip(su, su[1:]):
            if a <= t0 < b and t1 - t0 <= 180:
                uh_size += u0 * (min(t1, b) - t0) / 3600
        tail = [mu[m] for m in ms if m >= b - args.tail * 60]
        rec = {"phase": name, "arm": p.get("arm"), "mode": p.get("mode", "insert"), "stage": p.get("stage", "bench.stage"),
               "set_rows_per_s": p.get("rows_per_s"), "start": p["at"], "hours": round((b - a) / 3600, 3),
               "meter_minutes": len(ms), "unit_hours_meter": round(uh_meter, 3), "unit_hours_size": round(uh_size, 3),
               "mean_units": round(uh_meter * 60 / len(ms), 3) if ms else None,
               "tail_units": round(sum(tail) / len(tail), 3) if tail else None,
               "usd_meter": round(uh_meter * args.price, 3), "usd_size": round(uh_size * args.price, 3)}
        u0, u1 = at(us, a + args.lag_min * 60), at(us, b + args.lag_min * 60)
        if u0 and u1 and u1[0] > u0[0] and us[-1][0] >= b + args.lag_min * 60:
            rec["usage_computeCHC"] = round(u1[1] - u0[1], 3)
            rec["usage_readings"] = [round(u0[0]), round(u1[0])]
        c = cpu.get(name)
        if c:
            rec["rows_per_s"] = c["rows_per_s"]
            rec["busiest_util"], rec["busiest_util_max"], rec["mean_util"] = (
                c["busiest"]["util"], c["busiest_util_max"], c["mean"]["util"])
            rec["busiest_cores"] = {k: c["busiest"][k] for k in ("cg_cores", "insert", "select", "merge", "read")}
            rec["mean_cores"] = {k: c["mean"][k] for k in ("cg_cores", "insert", "select", "merge", "read")}
            rec["memory_gib"] = {"total": c["mean"]["gib"], "used_mean": c["mean"]["used_gib"],
                                 "resident_mean": c["mean"]["resident_gib"], "used_top": c["used_gib_top"]}
        rec["segments"] = []
        for g in segs:
            if g["of"] != name or g["phase"] == name:
                continue
            gm = [m for m in ms if g["t"] <= m and m + 60 <= min(g["end"], b)]
            sr = {"segment": g["phase"], "from": g["t"], "hours": round((min(g["end"], b) - g["t"]) / 3600, 3),
                  "unit_hours_meter": round(sum(mu[m] for m in gm) / 60, 3)}
            c = seg_cpu.get(g["phase"])
            if c:
                sr.update(minutes=c["minutes"], busiest_util=c["busiest"]["util"], busiest_util_max=c["busiest_util_max"],
                          mean_util=c["mean"]["util"], busiest_cg_cores=c["busiest"]["cg_cores"],
                          mean_cg_cores=c["mean"]["cg_cores"], total_gib=c["mean"]["gib"],
                          used_gib_mean=c["mean"]["used_gib"], resident_gib_mean=c["mean"]["resident_gib"],
                          used_gib_top=c["used_gib_top"])
            rec["segments"].append(sr)
        rows[name], spans[name] = rec, (a, end)
        print(json.dumps(rec))
    for r in range(1, 10):
        b = rows.get(f"B{r}")
        if not b:
            break
        for an in (f"A{r}", f"A{r + 1}"):
            a = rows.get(an)
            if not a or not a["tail_units"] or not b["tail_units"]:
                continue
            if an == f"A{r + 1}" and spans[f"B{r}"][1] != spans[an][0]:
                continue
            pair = {"pair": r, "B": f"B{r}", "A": an}
            for k in ("tail_units", "mean_units"):
                ratio = b[k] / a[k]
                pair[k] = {"A": a[k], "B": b[k], "ratio": round(ratio, 3),
                           "fall_over_rows_fall": round((1 - ratio) / (1 - ROWS), 3),
                           "fall_over_bytes_fall": round((1 - ratio) / (1 - BYTES), 3)}
            if a.get("usage_computeCHC") and b.get("usage_computeCHC"):
                ratio = (b["usage_computeCHC"] / b["hours"]) / (a["usage_computeCHC"] / a["hours"])
                pair["usage_per_hour"] = {"A": round(a["usage_computeCHC"] / a["hours"], 3),
                                          "B": round(b["usage_computeCHC"] / b["hours"], 3), "ratio": round(ratio, 3),
                                          "fall_over_rows_fall": round((1 - ratio) / (1 - ROWS), 3),
                                          "fall_over_bytes_fall": round((1 - ratio) / (1 - BYTES), 3)}
            print(json.dumps(pair))
    if us:
        print(json.dumps({"usage_last": {"t": round(us[-1][0]), "computeCHC_cum": round(us[-1][1], 3), "amountSpent": us[-1][2]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
