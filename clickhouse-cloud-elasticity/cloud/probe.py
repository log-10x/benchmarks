#!/usr/bin/env python3
"""The floor probe: arm A at rising load until the service scales up one step.

Steps through rates (rows a second, minutes held). The size meter is the sampler's
size.jsonl (units = sum over replicas of the memory limit / 8 GiB). The first sample
whose units exceed the units at the start ends the climb: the rate in force is
held, the event is logged, and the probe exits 0.

With --hold-util, a step whose busiest replica runs at or above that share of its
CPU (CGroupUserTime + CGroupSystemTime over CGroupMaxCPU, median of the last five
samples once the step has run --settle minutes) stops the climb: the rate is held
for up to --hold-max minutes waiting for the step up, so the lifting load is not
overstated by the autoscaler's reaction time. Without a step up by then, the climb
resumes. Each step's utilisation is logged to the events file when it ends.
If every step passes without a step up, the last rate is held and the probe exits 1.

  probe.py --control c.json --events e.jsonl --size size.jsonl --steps 2000:10,5000:10,...
           [--hold-util 0.75] [--settle 5] [--hold-max 60]
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def samples(path, since):
    out = []
    with open(path) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("hosts") and r.get("t", 0) >= since:
                out.append(r)
    return out


def last_units(path):
    s = samples(path, 0)
    return (s[-1].get("units"), s[-1].get("at")) if s else (None, None)


def busiest(r):
    return max(((h.get("cg_user") or 0) + (h.get("cg_system") or 0)) / h["cpu"]
               for h in r["hosts"].values() if h.get("cpu"))


def log(events, rec):
    with open(events, "a") as fh:
        fh.write(json.dumps({"t": round(time.time(), 1), **rec}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--size", required=True)
    ap.add_argument("--steps", required=True)
    ap.add_argument("--hold-util", type=float, default=0)
    ap.add_argument("--settle", type=float, default=5)
    ap.add_argument("--hold-max", type=float, default=60)
    args = ap.parse_args()
    steps = [(float(r), float(m)) for r, m in (s.split(":") for s in args.steps.split(","))]
    base, base_at = last_units(args.size)
    print(f"base units {base} at {base_at}", flush=True)
    for n, (rate, minutes) in enumerate(steps, 1):
        subprocess.run([sys.executable, str(HERE / "phase.py"), args.control, args.events, f"probe-{n}", "A", str(rate),
                        f"floor probe step {n}: {rate:g} rows/s for up to {minutes:g} min; base units {base}"], check=True)
        start = time.time()
        end = start + minutes * 60
        held = False
        while time.time() < end:
            time.sleep(30)
            units, at = last_units(args.size)
            if units is not None and base is not None and units > base + 0.01:
                log(args.events, {"event": "scale_up_seen", "rate": rate, "step": n, "units": units, "sample_at": at,
                                  "base_units": base, "step_started": round(start, 1), "held": held})
                print(f"scale up seen at {at}: {base} -> {units} units, step {n}, {rate:g} rows/s; rate held", flush=True)
                return 0
            if args.hold_util and not held and time.time() - start >= args.settle * 60:
                recent = [busiest(r) for r in samples(args.size, start + args.settle * 60 - 300)][-5:]
                if len(recent) >= 3 and statistics.median(recent) >= args.hold_util:
                    held = True
                    end = time.time() + args.hold_max * 60
                    log(args.events, {"event": "hold", "rate": rate, "step": n, "median_busiest": round(statistics.median(recent), 3),
                                      "hold_until": round(end, 1)})
                    print(f"step {n}: busiest replica at {statistics.median(recent):.0%}; holding {rate:g} rows/s up to "
                          f"{args.hold_max:g} min", flush=True)
        util = [busiest(r) for r in samples(args.size, start + args.settle * 60)]
        log(args.events, {"event": "step_done", "rate": rate, "step": n, "held": held, "n": len(util),
                          "median_busiest": round(statistics.median(util), 3) if util else None,
                          "max_busiest": round(max(util), 3) if util else None})
        print(f"step {n} done, {rate:g} rows/s, units still {last_units(args.size)[0]}", flush=True)
    print("no step up across the probe; last rate held", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
