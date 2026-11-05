#!/usr/bin/env python3
"""The two arms, run to a schedule, then the stage-read calibration.

Natural pairs (pair 1, and pair 2's arm B):
  A1 (arm A, every staged row at --rate) until --a-until; then for each pair r:
  B<r>   arm B: bench.stage_b at --rate x --kept-share, so it carries the same
         records a second as arm A and reads only what it writes. Runs until the
         service has stepped down (every replica smaller than at the phase start)
         and --b-after-step minutes have passed at the new size, or --b-max hours.
  A<r+1> arm A again for --a-again minutes; a step up that has started by then
         (a replica larger than at the phase start) extends it until every replica
         is at the new size plus 15 minutes, at most --a-again-max minutes.

Resuming (--resume-b r --b-cut <epoch> --b-hold h): B<r> was labelled at the cut by
an earlier driver; hold it h hours from the cut, longer only if a step down has
started (then as above, within --b-max of the cut). No arm A after it.

Forced pairs (--forced n ...), after the natural ones: for each n,
  A<n>   PATCH replicaScaling minReplicaMemoryGb --pin (16) at the phase start, so
         arm A's size is set by config; arm A at --rate for --a-hold hours, and at
         least --a-settled hours after every replica reached the pinned size.
  B<n>   PATCH minReplicaMemoryGb back to --floor (8) at the cut, so every step
         down is the autoscaler's own; then as a natural B.
Every PATCH is logged with its time, request, status and the scaling fields of the
response to --patch-log and as an event. The API key is read from SSM once, into
this process, as soon as SSO allows; until then a forced pair waits in the phase it
is in and logs that it is waiting. At --idle-at, if SSO has still not primed, the
phase becomes "idle" (no load, no queries), the meter is paused (SIGSTOP) so its
SQL does not keep the service awake, and the service idles; once SSO primes the
meter resumes (SIGCONT) and the forced pair starts from the cold service.

  cal-readA, cal-readB, cal-readBfilter: mode=read for --calibrate minutes each:
         arm A's slices of bench.stage, arm B's of bench.stage_b, and arm B's
         slices filtered from bench.stage (what arm B would read without stage_b).
  stop.

The size is the sampler's size.jsonl: each sample lists every replica serving with
its memory. Every change in that list is logged to the events file, so the step
times and the make-before-break overlap are read from it afterwards.

  arms.py --control c.json --events e.jsonl --size size.jsonl --a-until <epoch> [--pairs 3]
  arms.py ... --pairs 0 --resume-b 2 --b-cut <epoch> --b-hold 4.5 --forced 3 4 --service <id> --patch-log p.jsonl
"""
import argparse
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import cloud_api  # noqa: E402

SCALING = ("id", "state", "minReplicaMemoryGb", "maxReplicaMemoryGb", "numReplicas", "autoscalingMode",
           "idleScaling", "idleTimeoutMinutes")


def latest(path):
    last = None
    with open(path) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("hosts"):
                last = r
    return last


def sizes(sample):
    return {h: round(v["mem_total"] / 2**30) for h, v in sample["hosts"].items()}


class Run:
    def __init__(self, args):
        self.a = args
        self.seen = None
        self.oid = None
        for line in open(args.events):
            r = json.loads(line)
            if r.get("event") == "size":
                self.seen = r["replicas"]

    def phase(self, name, arm, rate, note, *extra):
        subprocess.run([sys.executable, str(HERE / "phase.py"), self.a.control, self.a.events, name, arm, str(rate), note,
                        *extra], check=True)

    def log(self, rec):
        t = time.time()
        with open(self.a.events, "a") as fh:
            fh.write(json.dumps({"t": round(t, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)), **rec}) + "\n")

    def poll(self):
        s = latest(self.a.size)
        if s is None:
            return None
        cur = sizes(s)
        if cur != self.seen:
            self.log({"event": "size", "sample_at": s["at"], "replicas": cur, "units": s.get("units")})
            self.seen = cur
        return cur

    def wait_until(self, until):
        while time.time() < until:
            self.poll()
            self.prime()
            time.sleep(30)

    def prime(self):
        if self.oid or not self.a.service:
            return bool(self.oid)
        try:
            cloud_api._AUTH = cloud_api._AUTH or cloud_api.auth()
            self.oid = cloud_api.org_id()
        except (SystemExit, Exception) as e:
            if not getattr(self, "waiting_logged", False):
                self.log({"event": "sso_waiting", "error": str(e)[:200]})
                self.waiting_logged = True
            return False
        self.log({"event": "sso_primed"})
        return True

    def patch(self, phase, floor):
        body = {"minReplicaMemoryGb": floor, "maxReplicaMemoryGb": self.a.max_gb}
        t = time.time()
        out = cloud_api.call("PATCH", f"/organizations/{self.oid}/services/{self.a.service}/replicaScaling", body)
        res = out.get("result") or {}
        rec = {"t": round(t, 1), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)), "phase": phase,
               "request": body, "status": out.get("status") or out.get("httpStatus"),
               "response": {k: res[k] for k in SCALING if k in res}, "error": out.get("error") or out.get("text")}
        with open(self.a.patch_log, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        self.log({"event": "patch", **{k: rec[k] for k in ("phase", "request", "status", "response", "error")}})
        if rec["status"] != 200:
            sys.exit(f"replicaScaling PATCH returned {rec['status']}")

    def hold_b(self, r, t0, end, top):
        started = done = None
        cap = t0 + self.a.b_max * 3600
        while time.time() < end:
            cur = self.poll()
            if cur and top:
                if started is None and min(cur.values()) < top:
                    started = time.time()
                    end = cap
                    self.log({"event": "step_down_started", "pair": r, "replicas": cur, "after_s": round(started - t0)})
                if started is not None and done is None and max(cur.values()) < top:
                    done = time.time()
                    end = min(cap, done + self.a.b_after_step * 60)
                    self.log({"event": "step_down_done", "pair": r, "replicas": cur, "after_s": round(done - t0)})
            self.prime()
            time.sleep(30)
        if done is None:
            self.log({"event": "no_step_down", "pair": r, "hours": round((time.time() - t0) / 3600, 2), "replicas": self.poll()})

    def b(self, r, release=False):
        rate = round(self.a.rate * self.a.kept_share)
        start = self.poll() or {}
        top = max(start.values()) if start else None
        note = f"arm B pair {r}: bench.stage_b at {rate} rows/s; replicas at start {start}"
        if release:
            note += f"; minReplicaMemoryGb back to {self.a.floor} at the cut"
        self.phase(f"B{r}", "B", rate, note, "stage=bench.stage_b")
        t0 = time.time()
        if release:
            self.patch(f"B{r}", self.a.floor)
        end = t0 + self.a.b_max * 3600
        self.hold_b(r, t0, end, top)

    def resume_b(self, r, cut, hold):
        start = self.poll() or {}
        top = max(start.values()) if start else None
        self.log({"event": "resume", "phase": f"B{r}", "cut": cut, "hold_h": hold, "replicas": start})
        self.hold_b(r, cut, cut + hold * 3600, top)

    def a_again(self, n):
        start = self.poll() or {}
        top = max(start.values()) if start else None
        self.phase(f"A{n}", "A", self.a.rate, f"arm A again: bench.stage at {self.a.rate} rows/s; replicas at start {start}")
        t0 = time.time()
        base = end = t0 + self.a.a_again * 60
        cap = t0 + self.a.a_again_max * 60
        started = done = None
        while time.time() < end:
            cur = self.poll()
            if cur and top:
                if started is None and max(cur.values()) > top:
                    started = time.time()
                    self.log({"event": "step_up_started", "phase": f"A{n}", "replicas": cur, "after_s": round(started - t0)})
                if started is not None and done is None and min(cur.values()) > top:
                    done = time.time()
                    self.log({"event": "step_up_done", "phase": f"A{n}", "replicas": cur, "after_s": round(done - t0)})
                if started is not None and done is None:
                    end = cap
                elif done is not None:
                    end = min(max(base, done + 15 * 60), cap)
            time.sleep(30)
        if started is None:
            self.log({"event": "no_step_up", "phase": f"A{n}", "minutes": round((time.time() - t0) / 60), "replicas": self.poll()})

    def forced_a(self, n):
        if not self.prime():
            self.log({"event": "forced_waiting_sso", "phase": f"A{n}", "current": json.load(open(self.a.control)).get("phase")})
        idled = False
        while not self.prime():
            self.poll()
            if not idled and self.a.idle_at and time.time() >= self.a.idle_at:
                self.phase("idle", "-", 0, "forced_idle_no_sso: no load, no queries, meter paused until SSO primes")
                self.log({"event": "forced_idle_no_sso", "before": f"A{n}"})
                time.sleep(150)
                os.kill(int(open(self.a.meter_pid).read()), signal.SIGSTOP)
                self.log({"event": "meter_paused"})
                idled = True
            time.sleep(30)
        if idled:
            os.kill(int(open(self.a.meter_pid).read()), signal.SIGCONT)
            self.log({"event": "meter_resumed", "before": f"A{n}"})
        start = self.poll() or {}
        self.phase(f"A{n}", "A", self.a.rate, f"arm A pair {n}: bench.stage at {self.a.rate} rows/s; minReplicaMemoryGb "
                   f"{self.a.pin} at the phase start; replicas at start {start}")
        t0 = time.time()
        self.patch(f"A{n}", self.a.pin)
        end = t0 + self.a.a_hold * 3600
        cap = t0 + self.a.a_hold_max * 3600
        started = done = None
        while time.time() < end:
            cur = self.poll()
            if cur:
                if started is None and max(cur.values()) >= self.a.pin and min(start.values() or [0]) < self.a.pin:
                    started = time.time()
                    self.log({"event": "step_up_started", "phase": f"A{n}", "replicas": cur, "after_s": round(started - t0)})
                if done is None and min(cur.values()) >= self.a.pin:
                    done = time.time()
                    end = min(cap, max(end, done + self.a.a_settled * 3600))
                    self.log({"event": "step_up_done", "phase": f"A{n}", "replicas": cur, "after_s": round(done - t0)})
            time.sleep(30)
        if done is None:
            self.log({"event": "pin_not_reached", "phase": f"A{n}", "hours": round((time.time() - t0) / 3600, 2),
                      "replicas": self.poll()})

    def calibrate(self):
        rate_b = round(self.a.rate * self.a.kept_share)
        for name, arm, rate, extra in (("cal-readA", "A", self.a.rate, ["mode=read"]),
                                       ("cal-readB", "B", rate_b, ["mode=read", "stage=bench.stage_b"]),
                                       ("cal-readBfilter", "B", self.a.rate, ["mode=read"])):
            self.phase(name, arm, rate, "stage read calibration: slices read into Null, nothing inserted", *extra)
            self.wait_until(time.time() + self.a.calibrate * 60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--size", required=True)
    ap.add_argument("--a-until", type=float)
    ap.add_argument("--pairs", type=int, default=3)
    ap.add_argument("--rate", type=int, default=70000)
    ap.add_argument("--kept-share", type=float, default=112205 / 171807)
    ap.add_argument("--b-max", type=float, default=6)
    ap.add_argument("--b-after-step", type=float, default=60)
    ap.add_argument("--a-again", type=float, default=90)
    ap.add_argument("--a-again-max", type=float, default=150)
    ap.add_argument("--resume-b", type=int)
    ap.add_argument("--b-cut", type=float)
    ap.add_argument("--b-hold", type=float, default=4.5)
    ap.add_argument("--forced", type=int, nargs="*", default=[])
    ap.add_argument("--service")
    ap.add_argument("--patch-log")
    ap.add_argument("--pin", type=int, default=16)
    ap.add_argument("--floor", type=int, default=8)
    ap.add_argument("--max-gb", type=int, default=32)
    ap.add_argument("--a-hold", type=float, default=3.25)
    ap.add_argument("--a-settled", type=float, default=3)
    ap.add_argument("--a-hold-max", type=float, default=4)
    ap.add_argument("--idle-at", type=float)
    ap.add_argument("--meter-pid")
    ap.add_argument("--calibrate", type=float, default=15)
    args = ap.parse_args()
    if args.forced and not (args.service and args.patch_log):
        ap.error("--forced needs --service and --patch-log")
    if args.idle_at and not args.meter_pid:
        ap.error("--idle-at needs --meter-pid")
    run = Run(args)
    run.poll()
    run.prime()
    if args.a_until:
        run.wait_until(args.a_until)
    for r in range(1, args.pairs + 1):
        run.b(r)
        run.a_again(r + 1)
    if args.resume_b:
        run.resume_b(args.resume_b, args.b_cut, args.b_hold)
    for n in args.forced:
        run.forced_a(n)
        run.b(n, release=True)
    run.calibrate()
    subprocess.run([sys.executable, str(HERE / "phase.py"), args.control, args.events, "stop"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
