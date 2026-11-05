#!/usr/bin/env python3
"""The feed: paced INSERT ... SELECT from the stage into bench.otel_logs.

The stage holds every record the Receiver returned in the split run, in order,
with `i` (position) and `kept` (1 when the Receiver passed it); bench.stage_b holds
the kept records only, in the same order, renumbered. K feeders each walk the
control file's "stage" (default bench.stage) from their own offset, keeping a
position per stage table; every tick each inserts its next slice of
rows/s x interval / K positions. Arm A reads bench.stage at R rows/s. Arm B reads
bench.stage_b at R x kept share, so both arms carry the same records a second with
the same cadence and number of inserts, and each reads only the rows it writes.
Arm B on bench.stage (filtering kept = 1) is kept for the read calibration.
Timestamps are shifted to the insert's own time, spread across the tick in order.

The insert runs server-side: this machine's link carries the statement, not the
rows. The stage read is part of each insert's CPU in query_log. A phase with
"mode": "read" runs the same slices as SELECT ... FORMAT Null and writes nothing,
so the stage read's own CPU is measured at the same rate and cadence
(log_comment chce:<phase>:<arm>:read).

The control file is re-read every tick, so a phase changes the arm or the rate
without a restart:  {"phase": "probe-1", "arm": "A", "rows_per_s": 2000}
A phase of "stop" ends the run.

  load.py --control control.json --log results/raw/load.jsonl [--feeders 4] [--interval 2]
"""
import argparse
import json
import pathlib
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from chhttp import CH  # noqa: E402

COLS = ("Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, "
        "ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, "
        "LogAttributes, EventName")
REST = COLS.split(", ", 1)[1]


def insert_sql(p, k, interval, arm, mode="insert", stage="bench.stage"):
    step_ns = int(interval * 1e9 / k)
    kept = " AND kept = 1" if arm == "B" and stage == "bench.stage" else ""
    select = (f"SELECT now64(9) - toIntervalNanosecond(toInt64({p + k - 1} - i) * {step_ns}), {REST} "
              f"FROM {stage} WHERE i >= {p} AND i < {p + k}{kept}")
    if mode == "read":
        return select + " FORMAT Null"
    return f"INSERT INTO bench.otel_logs ({COLS}) " + select


def read_control(path, last):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return last


def feeder(f, args, sizes, state, lock, out):
    ch = CH()
    pos = {}
    t_next = state["t0"] + f * args.interval / args.feeders
    while True:
        ctl = state["control"]
        if ctl.get("phase") == "stop":
            return
        now = time.time()
        if now < t_next:
            time.sleep(min(t_next - now, 1.0))
            continue
        t_next += args.interval
        rate = float(ctl.get("rows_per_s", 0))
        k = int(round(rate * args.interval / args.feeders))
        if k <= 0:
            continue
        stage = ctl.get("stage", "bench.stage")
        with lock:
            if stage not in sizes:
                sizes[stage] = int(ch.query(f"SELECT max(i) + 1 FROM {stage}")[0].strip())
        n_stage = sizes[stage]
        p = pos.get(stage, (n_stage * f) // args.feeders)
        if p + k > n_stage:
            p = 0
        mode = ctl.get("mode", "insert")
        rec = {"t": round(now, 3), "f": f, "phase": ctl.get("phase"), "arm": ctl.get("arm"), "mode": mode,
               "stage": stage, "p": p, "k": k}
        t1 = time.time()
        try:
            _, summary = ch.query(insert_sql(p, k, args.interval, ctl.get("arm"), mode, stage),
                                  {"log_comment": f"chce:{ctl.get('phase')}:{ctl.get('arm')}:{mode}"})
            rec["written_rows"] = int(summary.get("written_rows", 0))
            rec["read_rows"] = int(summary.get("read_rows", 0))
        except Exception as e:
            rec["error"] = repr(e)[:300]
        rec["ms"] = round((time.time() - t1) * 1000)
        if rec["ms"] > args.interval * 1000:
            rec["late"] = True
            t_next = max(t_next, time.time())
        pos[stage] = p + k
        with lock:
            out.write(json.dumps(rec, separators=(",", ":")) + "\n")
            out.flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--feeders", type=int, default=4)
    ap.add_argument("--interval", type=float, default=2.0)
    args = ap.parse_args()
    sizes = {"bench.stage": int(CH().query("SELECT max(i) + 1 FROM bench.stage")[0].strip())}
    state = {"t0": time.time() + 1, "control": read_control(args.control, {"phase": "idle", "rows_per_s": 0})}
    lock = threading.Lock()
    out = open(args.log, "a")
    out.write(json.dumps({"t": time.time(), "start": True, "stage_rows": sizes["bench.stage"], "feeders": args.feeders,
                          "interval": args.interval}) + "\n")
    out.flush()
    threads = [threading.Thread(target=feeder, args=(f, args, sizes, state, lock, out), daemon=True)
               for f in range(args.feeders)]
    for th in threads:
        th.start()
    while any(th.is_alive() for th in threads):
        time.sleep(1)
        state["control"] = read_control(args.control, state["control"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
