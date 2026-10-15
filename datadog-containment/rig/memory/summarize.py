#!/usr/bin/env python3
"""Summarize results/memory/: the Receiver's memory and CPU while the capture replayed.

Reads stats.tsv (one docker stats sample every 10 s), replay.out, inspect.json and
returned.json, and writes summary.json and memory.md. The window is from the first
replayed record to 60 s after the last; samples before it are reported as idle.
Percentiles are nearest-rank.
"""
import json
import math
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "results", "memory")
UNITS = {"B": 1, "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3, "kB": 1e3, "MB": 1e6, "GB": 1e9}


def size(s):
    m = re.fullmatch(r"([\d.]+)\s*([A-Za-z]+)", s.strip())
    return float(m.group(1)) * UNITS[m.group(2)]


def pct_rank(xs, p):
    xs = sorted(xs)
    return xs[max(0, math.ceil(p / 100 * len(xs)) - 1)]


def stats(xs):
    return {"samples": len(xs), "median": statistics.median(xs), "p99": pct_rank(xs, 99),
            "max": max(xs), "min": min(xs)}


def main():
    rows = []
    for line in open(os.path.join(OUT, "stats.tsv")):
        t, cpu, used, limit, mpct = line.rstrip("\n").split("\t")
        rows.append((int(t), float(cpu.rstrip("%")), size(used), size(limit)))
    rep = open(os.path.join(OUT, "replay.out")).read()
    start = int(re.search(r"replay start \S+ epoch (\d+)", rep).group(1))
    end = int(re.search(r"replay end \S+ epoch (\d+)", rep).group(1))
    sent = int(re.search(r"done: sent (\d+) records", rep).group(1))
    late = float(re.search(r"at most ([\d.]+) s", rep).group(1))
    win = [r for r in rows if start <= r[0] <= end + 60]
    idle = [r for r in rows if r[0] < start]
    mib = 1024 ** 2
    inspect = json.load(open(os.path.join(OUT, "inspect.json")))
    returned = json.load(open(os.path.join(OUT, "returned.json")))
    s = {
        "window": {"start_epoch": start, "end_epoch": end + 60, "minutes": round((end + 60 - start) / 60, 1),
                   "records_sent": sent, "in_order_records_max_seconds_late": late},
        "limits": {"memory_bytes": inspect["memory_limit_bytes"], "cpus": inspect["nano_cpus"] / 1e9},
        "memory_mib": {k: round(v / mib, 1) if k != "samples" else v
                       for k, v in stats([r[2] for r in win]).items()},
        "cpu_percent_of_one_core": {k: round(v, 2) if k != "samples" else v
                                    for k, v in stats([r[1] for r in win]).items()},
        "idle_before_replay": {"samples": len(idle),
                               "memory_mib_median": round(statistics.median(r[2] for r in idle) / mib, 1) if idle else None,
                               "cpu_percent_median": round(statistics.median(r[1] for r in idle), 2) if idle else None},
        "oom_killed": inspect["oom_killed"], "restart_count": inspect["restart_count"],
        "image": inspect["image"],
        "returned": returned,
    }
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(s, f, indent=1)
        f.write("\n")
    m, c = s["memory_mib"], s["cpu_percent_of_one_core"]
    lim = s["limits"]
    md = [
        "# Receiver memory and CPU",
        "",
        "Written by `rig/memory/summarize.py` from the files in this folder.",
        "",
        f"`{s['image']}`, limits {lim['cpus']:g} CPU and {lim['memory_bytes'] / mib:,.0f} MiB, "
        f"{s['window']['records_sent']:,} records replayed over {s['window']['minutes']} minutes "
        f"(to 60 s after the last record), one `docker stats` sample every 10 s.",
        "",
        "| measure | samples | median | p99 | max |",
        "|---|---:|---:|---:|---:|",
        f"| memory (MiB) | {m['samples']} | {m['median']} | {m['p99']} | {m['max']} |",
        f"| CPU (% of one core) | {c['samples']} | {c['median']} | {c['p99']} | {c['max']} |",
        "",
        f"Before the first record: memory median {s['idle_before_replay']['memory_mib_median']} MiB, "
        f"CPU median {s['idle_before_replay']['cpu_percent_median']}% ({s['idle_before_replay']['samples']} samples). "
        f"OOM killed: {str(s['oom_killed']).lower()}; restarts: {s['restart_count']}.",
        "",
        "Records the Receiver returned, by route: " + ", ".join(f"{k} {v:,}" for k, v in returned.items()) + ".",
        "",
    ]
    with open(os.path.join(OUT, "memory.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
