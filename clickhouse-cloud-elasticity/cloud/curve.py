#!/usr/bin/env python3
"""Per-phase load and CPU from the meter's per-minute readings.

Phases come from the events log (each phase.py line starts one). Minutes wholly
inside a phase, after the first --settle minutes, are summarised per replica:

  rows_per_s   written rows a second, from query_log inserts tagged with the phase
  util         (CGroupUserTime + CGroupSystemTime) / CGroupMaxCPU, the minute's average
  cg_cores     CGroupUserTime + CGroupSystemTime: cores busy in the replica's cgroup
  proc_cores   metric_log OSCPUVirtualTimeMicroseconds: cores busy in ClickHouse's threads
  insert, select, read, merge, other   cores by source: query_log tagged inserts,
               tagged selects, tagged stage reads, part_log MergeParts, untagged queries
  gib          CGroupMemoryTotal
  used_gib     CGroupMemoryUsed
  resident_gib MemoryResident: ClickHouse's resident set

and printed as one JSON line per phase with the median minute of each figure,
for the busiest replica and the mean over replicas, plus used_gib_top, the median minute
of the replica using the most memory. A phase named <phase>@<label>
(a segment written by arms_report.py) reads the rows tagged <phase>.

  curve.py --meter results/raw/meter.jsonl[.gz] --events results/raw/events.jsonl [--settle 2]
"""
import argparse
import collections
import gzip
import json
import statistics


def phases(events):
    out = []
    for line in open(events):
        r = json.loads(line)
        if "phase" in r and "event" not in r:
            out.append(r)
    spans = []
    for a, b in zip(out, out[1:] + [None]):
        spans.append((a["phase"], a.get("arm"), a.get("rows_per_s"), a.get("mode", "insert"), a["t"], b["t"] if b else 1e12))
    return spans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meter", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--settle", type=int, default=2)
    args = ap.parse_args()
    per = collections.defaultdict(lambda: collections.defaultdict(float))
    rows = collections.defaultdict(float)
    for line in gzip.open(args.meter, "rt") if args.meter.endswith(".gz") else open(args.meter):
        r = json.loads(line)
        src = r.get("src")
        if src == "pull":
            continue
        k = (r["m"], r["h"])
        if src == "async":
            per[k][r["metric"]] = r["avg"]
        elif src == "metric_log":
            per[k]["proc"] = int(r["cpu_virt_us"]) / 60e6
        elif src == "query_log":
            lc = r.get("lc") or ""
            cores = int(r["cpu_virt_us"]) / 60e6
            if lc.startswith("chce:") and lc.endswith(":insert"):
                per[k]["insert"] += cores
                rows[(r["m"], lc.split(":")[1])] += int(r["wr"])
            elif lc.startswith("chce:") and lc.endswith(":read"):
                per[k]["read"] += cores
            elif ":select:" in lc:
                per[k]["select"] += cores
            else:
                per[k]["other"] += cores
        elif src == "part_log" and r.get("ev") == "MergeParts":
            per[k]["merge"] += int(r.get("cpu_virt_us") or 0) / 60e6
    minutes = collections.defaultdict(dict)
    for (m, h), v in per.items():
        if v.get("CGroupMaxCPU"):
            minutes[m][h] = v
    for phase, arm, rate, mode, a, b in phases(args.events):
        ms = [m for m in sorted(minutes) if m >= a + args.settle * 60 and m + 60 <= b]
        if not ms:
            continue
        busy, mean, top_used = collections.defaultdict(list), collections.defaultdict(list), []
        for m in ms:
            hs = minutes[m]
            for v in hs.values():
                v["cg_cores"] = v.get("CGroupUserTime", 0) + v.get("CGroupSystemTime", 0)
                v["util"] = v["cg_cores"] / v["CGroupMaxCPU"]
                v["gib"] = v.get("CGroupMemoryTotal", 0) / 2**30
                v["used_gib"] = v.get("CGroupMemoryUsed", 0) / 2**30
                v["resident_gib"] = v.get("MemoryResident", 0) / 2**30
            top = max(hs.values(), key=lambda v: v["util"])
            for f in ("util", "cg_cores", "proc", "insert", "select", "read", "merge", "other", "gib", "used_gib",
                      "resident_gib"):
                busy[f].append(top.get(f, 0))
                mean[f].append(sum(v.get(f, 0) for v in hs.values()) / len(hs))
            busy["replicas"].append(len(hs))
            top_used.append(max(v["used_gib"] for v in hs.values()))
        wr = [rows.get((m, phase.split("@")[0]), 0) / 60 for m in ms]
        med = lambda xs: round(statistics.median(xs), 3)
        print(json.dumps({"phase": phase, "arm": arm, "mode": mode, "set_rows_per_s": rate, "minutes": len(ms),
                          "rows_per_s": round(statistics.median(wr)), "replicas": max(busy["replicas"]),
                          "busiest": {f: med(v) for f, v in busy.items() if f != "replicas"},
                          "busiest_util_max": round(max(busy["util"]), 3),
                          "used_gib_top": med(top_used),
                          "mean": {f: med(v) for f, v in mean.items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
