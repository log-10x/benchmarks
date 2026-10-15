#!/usr/bin/env python3
"""engine_split.py - two engine instances on halves of one stream.

Section 2 of the README measures two Drain3 instances that each learn one
random half of the public sample and are then fed the same probe sequence.
This script runs the same protocol through the 10x engine:

- the same sample, the same seed, the same split and the same probe sequence
  per trial as `bench/identity.py` (the plan is rebuilt here with the same
  code and checked against `results/identity_raw.json`);
- each half goes through its own engine container, fed in the order Drain3
  receives it, followed by the probe records in probe order, so each instance
  names the probes after it has seen only its own half;
- both containers run the same pinned image with its shipped configuration
  (`@apps/dev`) and its own symbol library, plus one output module that writes
  each event's pattern name, pattern hash and template hash
  (`bench/engine_split.config.yaml`);
- for every probe record the two instances' answers are compared: the pattern
  hash (`tenx_hash`, the hash of the pattern name), the pattern name
  (`message_pattern`), and the template hash (`templateHash`).

The engine reads whole records (the Fluentd/Kubernetes JSON line), not the
`log` field Drain3 is given, and it groups consecutive records into one event
(a stack trace, a .NET header and its message). A probe record is credited
with the names of the event that holds it.

Strata. A probe is binned by line frequency two ways:
- under Drain3's strata: the shape and frequency Drain3's strong arm assigns in
  its own reference pass, so each row holds the very probes of the matching
  row in `results/identity.md`;
- under the engine's own strata: the number of records in the whole stream
  whose event carries the probe's pattern hash in a reference engine run over
  the whole stream in stream order.
Each table also reports the probes whose shape occurs in both halves.

The Drain3 strong arm is rerun here with per-probe results, only to score
Drain3 on the both-halves subset. Its per-trial counts over all probes must
equal `results/identity_raw.json` exactly, or the script stops.

Engine containers run one at a time. Engine outputs are cached under
data/engine-split/<version>/ so an interrupted run resumes; delete that folder
to rerun from scratch.

Usage:
    python bench/engine_split.py                 # 10 trials, writes results/engine_split.*
    python bench/engine_split.py --trials 1      # one trial
"""

import argparse
import collections
import gzip
import json
import os
import pathlib
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import identity  # noqa: E402  the Drain3 harness: plan, strata, arms

IMAGE = ("log10x/pipeline-10x:1.1.142@sha256:"
         "22ae67148bd7f6cbdf171c1b8da1c9c6c801290d43488693dfd8527e27138d05")
VERSION = "1.1.142"

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
RESULTS_DIR = REPO_ROOT / "results"
DATA_DIR = identity.DATA_DIR
CACHE = DATA_DIR / "engine-split" / VERSION
CONFIG = HERE / "engine_split.config.yaml"

# Fixed before the run. The claim under test: a pattern name taken from a pinned
# symbol library is the same on two nodes whatever each node saw before. It is
# retired for a stratum where two instances give the same probe record the same
# pattern hash less than this share of the time, under Drain3's strata. Drain3's
# strong arm scores 0.6022 template agreement at 2 to 10 on the same probes.
PATTERN_AGREEMENT_FLOOR = 0.99

STRATA = [label for _, _, label in identity.BUCKETS]


# ---------------------------------------------------------------------------
# Data and plan
# ---------------------------------------------------------------------------

def load_records(path: pathlib.Path):
    """The raw records, one per line, as bytes without the line end."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as f:
        return [line.rstrip(b"\n") for line in f]


def build_plan(n: int, trials: int, seed: int, probes: int):
    """The split and probe sequence of bench/identity.py, trial by trial."""
    plan = []
    for t in range(trials):
        rnd = random.Random(seed + t)
        idx = list(range(n))
        rnd.shuffle(idx)
        plan.append({"a": idx[:n // 2], "b": idx[n // 2:],
                     "probe": rnd.sample(range(n), probes)})
    return plan


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def image_digest():
    """The image's repo digest, or None with the reason, so the script can skip
    cleanly and leave the committed artifacts alone."""
    if shutil.which("docker") is None:
        return None, "docker is not on PATH"
    r = subprocess.run(["docker", "image", "inspect", IMAGE, "--format",
                        "{{index .RepoDigests 0}}"], capture_output=True, text=True)
    if r.returncode != 0:
        return None, f"image {IMAGE} is not present; `docker pull {IMAGE}` and rerun"
    return r.stdout.strip(), None


def run_engine(records, order, name: str):
    """Write records[order] to a file, run one engine container over it, and
    return per input position (pattern hash, template hash, pattern name,
    records in the event, position in the event)."""
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"pib-split-{name}-", dir=str(DATA_DIR)))
    try:
        inp = work / "input.log"
        with open(inp, "wb") as f:
            for i in order:
                f.write(records[i])
                f.write(b"\n")
        out = work / "out"
        out.mkdir()
        empty = work / "empty"
        empty.mkdir()
        cmd = ["docker", "run", "--rm", "--name", f"pib-split-{name}",
               "-e", "OUTPUT_DIR=/out",
               "-v", f"{out}:/out",
               "-v", f"{inp}:/in/input.log:ro",
               "-v", f"{empty}:/etc/tenx/config/data/sample/input:ro",
               "-v", f"{CONFIG}:/cfg/events.config.yaml:ro",
               IMAGE, "@apps/dev", "@/cfg/events.config.yaml",
               "inputFilePath", "/in/input.log"]
        t0 = time.time()
        with open(work / "engine.log", "wb") as log:
            r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            raise SystemExit(f"engine run {name} exited {r.returncode}; see {work}/engine.log")
        print(f"    engine {name}: {len(order):,} records in {time.time() - t0:.0f}s",
              file=sys.stderr, flush=True)
        return align(records, order, out / "events.jsonl", name)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def align(records, order, events_path: pathlib.Path, name: str):
    """Events come out in input order and an event's text is its records joined
    by newlines. Walk both and give every input position its event's names.
    Any mismatch stops the script."""
    res = [None] * len(order)
    pos = 0
    with open(events_path, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            parts = e["text"].split("\n")
            k = len(parts)
            for j, part in enumerate(parts):
                if pos + j >= len(order) or records[order[pos + j]].decode("utf-8") != part:
                    raise SystemExit(f"engine run {name}: event text does not match input "
                                     f"record at position {pos + j}")
                res[pos + j] = (e.get("tenx_hash"), e.get("templateHash"),
                                e.get("message_pattern"), k, j)
            pos += k
    if pos != len(order):
        raise SystemExit(f"engine run {name}: {pos:,} records in events, {len(order):,} in input")
    return res


class CachedTrials:
    """eng[t] reads trial t's two answer lists from the cache."""

    def __init__(self, n):
        self.n = n

    def __len__(self):
        return self.n

    def __getitem__(self, t):
        out = []
        for side in ("a", "b"):
            with gzip.open(CACHE / f"trial{t}_{side}.json.gz", "rt") as f:
                out.append(json.load(f))
        return out


def cached(path: pathlib.Path, fn):
    if path.exists():
        with gzip.open(path, "rt") as f:
            return json.load(f)
    val = fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with gzip.open(tmp, "wt") as f:
        json.dump(val, f)
    tmp.replace(path)
    return val


# ---------------------------------------------------------------------------
# Drain3, per probe
# ---------------------------------------------------------------------------

def drain_trial(messages, p, workdir: pathlib.Path):
    """identity.run_trial's primary pass for the strong arm, kept per probe.
    The read-only lookup pass is skipped: it does not change the instances."""
    arm = identity.ARMS["strong"]
    sim = identity.DRAIN_SIM_TH
    tm_a = identity.train(messages, p["a"], arm, sim, snapshot_path=workdir / "a.state")
    tm_b = identity.train(messages, p["b"], arm, sim, snapshot_path=workdir / "b.state")
    out = []
    for i in p["probe"]:
        m = messages[i][:identity.LINE_CAP]
        ra = tm_a.add_log_message(m)
        rb = tm_b.add_log_message(m)
        out.append(1 if ra["template_mined"] == rb["template_mined"] else 0)
    return out


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def bucket(freq: int) -> str:
    return identity.bucket_label(freq)


def score(plan, eng, drain, d_shape, d_freq, e_shape, e_freq):
    """Per trial, per stratum, under both strata: counts of agreement."""
    trials = []
    for t, p in enumerate(plan):
        side_a, side_b = eng[t]
        n_half_a = len(p["a"])
        set_a, set_b = set(p["a"]), set(p["b"])
        d_in_a = {d_shape[i] for i in set_a}
        d_in_b = {d_shape[i] for i in set_b}
        e_in_a = {e_shape[i] for i in set_a}
        e_in_b = {e_shape[i] for i in set_b}
        rec = {}
        for strata_name, shape, freq, ina, inb in (
                ("drain3", d_shape, d_freq, d_in_a, d_in_b),
                ("engine", e_shape, e_freq, e_in_a, e_in_b)):
            counts = {s: collections.Counter() for s in STRATA}
            for j, i in enumerate(p["probe"]):
                ra = side_a[n_half_a + j]
                rb = side_b[len(p["b"]) + j]
                s = shape[i]
                c = counts[bucket(freq[s])]
                both = s in ina and s in inb
                for scope in ("all", "both_halves") if both else ("all",):
                    c[f"{scope}_n"] += 1
                    c[f"{scope}_hash"] += ra[0] == rb[0]
                    c[f"{scope}_name"] += ra[2] == rb[2]
                    c[f"{scope}_tpl"] += ra[1] == rb[1]
                    c[f"{scope}_event"] += (ra[3], ra[4]) == (rb[3], rb[4])
                    if drain is not None:
                        c[f"{scope}_drain"] += drain[t][j]
            rec[strata_name] = {s: dict(counts[s]) for s in STRATA}
            tot = collections.Counter()
            for s in STRATA:
                tot.update(counts[s])
            rec[strata_name]["all events"] = dict(tot)
        trials.append(rec)
    return trials


def summarize(trials, strata_name, scope, with_drain):
    rows = {}
    for s in STRATA + ["all events"]:
        cells = [tr[strata_name][s] for tr in trials]
        ns = [c.get(f"{scope}_n", 0) for c in cells]
        row = {"probes_per_trial": statistics.mean(ns), "probes_total": sum(ns)}
        keys = ["hash", "name", "tpl", "event"] + (["drain"] if with_drain else [])
        for k in keys:
            vals = [c.get(f"{scope}_{k}", 0) / n for c, n in zip(cells, ns) if n]
            row[k] = statistics.mean(vals) if vals else None
            row[k + "_stdev"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
            row[k + "_differ_total"] = sum(n - c.get(f"{scope}_{k}", 0)
                                           for c, n in zip(cells, ns))
        rows[s] = row
    return rows


def fmt(v):
    return "n/a" if v is None else f"{v:.4f}"


def table(rows, with_drain, title_cols=None):
    head = ["line frequency", "probes/trial", "pattern hash", "pattern name",
            "template hash"]
    if with_drain:
        head.append("Drain3 strong, template")
    out = ["| " + " | ".join(head) + " |", "|---" + "|---:" * (len(head) - 1) + "|"]
    for s, r in rows.items():
        if not r["probes_total"]:
            continue
        cells = [s, f"{int(r['probes_per_trial']):,}", fmt(r["hash"]), fmt(r["name"]),
                 fmt(r["tpl"])]
        if with_drain:
            cells.append(fmt(r["drain"]))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def line_keys(records):
    """A line is a record's exact bytes. The records carry no timestamp of their
    own, so a line that repeats is the same record written again."""
    ids = {}
    return [ids.setdefault(r, len(ids)) for r in records]


def same_line_in_halves(plan, eng, keys, d_shape, d_freq):
    """No shared traffic: a line (container and message) that occurs in both halves,
    named by each instance in its own half. A record agrees when every record of the
    same line in the other half got the same answer. Scored over all such records and
    over records that both instances named as an event of their own (one record)."""
    trials = []
    singles = []
    for t, p in enumerate(plan):
        res_a, res_b = eng[t]
        side = {"a": (p["a"], res_a), "b": (p["b"], res_b)}
        for order, res in side.values():
            singles.append(sum(1 for r in res[:len(order)] if r[3] == 1))
        per_key = {}
        for s_, (order, res) in side.items():
            m = collections.defaultdict(lambda: [set(), set(), set(), set()])
            for pos, i in enumerate(order):
                r = res[pos]
                e = m[keys[i]]
                e[0].add(r[0]); e[1].add(r[1])
                if r[3] == 1:
                    e[2].add(r[0]); e[3].add(r[1])
            per_key[s_] = m
        counts = {s: collections.Counter() for s in STRATA}
        for s_, other in (("a", "b"), ("b", "a")):
            order, res = side[s_]
            om = per_key[other]
            for pos, i in enumerate(order):
                k = keys[i]
                if k not in om:
                    continue
                r = res[pos]
                c = counts[bucket(d_freq[d_shape[i]])]
                o = om[k]
                c["all_n"] += 1
                c["all_hash"] += o[0] == {r[0]}
                c["all_tpl"] += o[1] == {r[1]}
                if r[3] == 1 and o[2]:
                    c["single_n"] += 1
                    c["single_hash"] += o[2] == {r[0]}
                    c["single_tpl"] += o[3] == {r[1]}
        rec = {s: dict(counts[s]) for s in STRATA}
        tot = collections.Counter()
        for s in STRATA:
            tot.update(counts[s])
        rec["all events"] = dict(tot)
        trials.append(rec)
    rows = {}
    for s in STRATA + ["all events"]:
        row = {}
        for scope in ("all", "single"):
            ns = [tr[s].get(f"{scope}_n", 0) for tr in trials]
            row[f"{scope}_records_per_trial"] = statistics.mean(ns)
            for k in ("hash", "tpl"):
                vals = [tr[s].get(f"{scope}_{k}", 0) / n for tr, n in zip(trials, ns) if n]
                row[f"{scope}_{k}"] = statistics.mean(vals) if vals else None
        rows[s] = row
    return {"trials": trials, "summary": rows,
            "half_single_record_events_mean": statistics.mean(singles),
            "half_records": len(plan[0]["a"])}


def table_same_line(rows):
    out = ["| line frequency | records/trial | pattern hash | template hash |",
           "|---|---:|---:|---:|"]
    for s, r in rows.items():
        if not r["single_records_per_trial"]:
            continue
        out.append(f"| {s} | {r['single_records_per_trial']:,.0f} | {fmt(r['single_hash'])} | "
                   f"{fmt(r['single_tpl'])} |")
    return "\n".join(out)


def disagreements(plan, eng, records, d_shape, d_freq, limit=50):
    """Every probe on which the two instances' pattern hashes differ."""
    out = []
    for t, p in enumerate(plan):
        side_a, side_b = eng[t]
        for j, i in enumerate(p["probe"]):
            ra = side_a[len(p["a"]) + j]
            rb = side_b[len(p["b"]) + j]
            if ra[0] != rb[0] or ra[1] != rb[1]:
                try:
                    msg = json.loads(records[i]).get("log", "")
                except Exception:
                    msg = ""
                out.append({"trial": t, "probe_position": j, "line": i + 1,
                            "drain3_frequency": d_freq[d_shape[i]],
                            "a": {"tenx_hash": ra[0], "templateHash": ra[1],
                                  "pattern": ra[2], "event_records": ra[3],
                                  "position_in_event": ra[4]},
                            "b": {"tenx_hash": rb[0], "templateHash": rb[1],
                                  "pattern": rb[2], "event_records": rb[3],
                                  "position_in_event": rb[4]},
                            "log": msg[:200]})
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=identity.DEFAULT_TRIALS)
    ap.add_argument("--probes", type=int, default=identity.DEFAULT_PROBES)
    ap.add_argument("--seed", type=int, default=identity.DEFAULT_SEED)
    ap.add_argument("--skip-drain", action="store_true",
                    help="do not rerun Drain3 for the both-halves column")
    ap.add_argument("--out-json", default=str(RESULTS_DIR / "engine_split_raw.json"))
    ap.add_argument("--out-md", default=str(RESULTS_DIR / "engine_split.md"))
    args = ap.parse_args()

    t0 = time.time()
    digest, why = image_digest()
    if digest is None:
        print(f"SKIP engine_split: {why}; results/ left as committed", file=sys.stderr)
        return 0
    path = identity.resolve_sample()
    records = load_records(path)
    n = len(records)
    print(f"{n:,} records, image {digest}", file=sys.stderr, flush=True)

    plan = build_plan(n, args.trials, args.seed, args.probes)

    # The engine's strata, from one run over the whole stream in stream order.
    print("engine reference run, whole stream", file=sys.stderr, flush=True)
    ref = cached(CACHE / "reference.json.gz",
                 lambda: run_engine(records, list(range(n)), "ref"))
    e_shape = [r[0] for r in ref]
    e_freq = collections.Counter(e_shape)

    ref_stats = {"records": n, "events": sum(1 for r in ref if r[4] == 0),
                 "single_record_events": sum(1 for r in ref if r[3] == 1),
                 "distinct_pattern_hashes": len(e_freq),
                 "distinct_template_hashes": len({r[1] for r in ref})}

    # The two instances per trial, one container at a time. Answers stay in the
    # cache and are read back one trial at a time, so memory holds one trial.
    del ref
    for t, p in enumerate(plan):
        for side in ("a", "b"):
            cpath = CACHE / f"trial{t}_{side}.json.gz"
            if not cpath.exists():
                cached(cpath, lambda: run_engine(records, p[side] + p["probe"], f"t{t}{side}"))
        print(f"  engine trial {t + 1}/{len(plan)} ({time.time() - t0:.0f}s)",
              file=sys.stderr, flush=True)
    eng = CachedTrials(len(plan))

    # Drain3's strata, from the strong arm's own reference pass. Engine containers are
    # done by now, so Drain3 never runs beside one.
    messages = list(identity.iter_messages(path))
    assert n == len(messages), (n, len(messages))
    print("Drain3 strong reference pass", file=sys.stderr, flush=True)
    d_shape, d_freq, d_stats = identity.reference_pass(messages, "strong", identity.DRAIN_SIM_TH)
    print(f"  {d_stats['distinct_shapes']:,} shapes ({time.time() - t0:.0f}s)",
          file=sys.stderr, flush=True)

    # Drain3 per probe, checked against the committed identity run.
    drain = None
    same_cfg = False
    if not args.skip_drain:
        committed = json.loads((RESULTS_DIR / "identity_raw.json").read_text())
        same_cfg = (committed["config"]["seed"] == args.seed
                    and committed["config"]["probes"] == args.probes
                    and committed["dataset"]["lines_used"] == n)
        drain = []
        work = pathlib.Path(tempfile.mkdtemp(prefix="pib-split-drain-"))
        try:
            for t, p in enumerate(plan):
                per_probe = cached(CACHE / f"drain3_strong_trial{t}.json.gz",
                                   lambda: drain_trial(messages, p, work))
                drain.append(per_probe)
                if same_cfg and t < len(committed["arms"]["strong"]["trials"]):
                    want = committed["arms"]["strong"]["trials"][t]
                    for lo, hi, label in identity.BUCKETS:
                        got = sum(a for a, i in zip(per_probe, p["probe"])
                                  if lo <= d_freq[d_shape[i]] <= hi)
                        if got != want["buckets"][label]["tpl_agree"]:
                            raise SystemExit(f"Drain3 rerun trial {t} {label}: {got} agree, "
                                             f"identity_raw.json has "
                                             f"{want['buckets'][label]['tpl_agree']}")
                print(f"  Drain3 trial {t + 1}/{len(plan)} matches identity_raw.json "
                      f"({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)
        finally:
            shutil.rmtree(work, ignore_errors=True)


    trials = score(plan, eng, drain, d_shape, d_freq, e_shape, e_freq)
    with_drain = drain is not None
    summary = {f"{sn}/{sc}": summarize(trials, sn, sc, with_drain)
               for sn in ("drain3", "engine") for sc in ("all", "both_halves")}
    diffs = disagreements(plan, eng, records, d_shape, d_freq)
    halves = same_line_in_halves(plan, eng, line_keys(records), d_shape, d_freq)

    falsifier = []
    for s in STRATA:
        r = summary["drain3/all"][s]
        if r["probes_total"]:
            falsifier.append({"stratum": s, "pattern_hash_agreement": r["hash"],
                              "triggered": r["hash"] < PATTERN_AGREEMENT_FLOOR})

    payload = {
        "script": "bench/engine_split.py",
        "image": IMAGE,
        "image_repo_digest": digest,
        "config": {"trials": args.trials, "probes": args.probes, "seed": args.seed,
                   "engine_app": "@apps/dev", "output_config": "bench/engine_split.config.yaml",
                   "half_order": "the order bench/identity.py feeds Drain3 (shuffled)",
                   "pattern_agreement_floor": PATTERN_AGREEMENT_FLOOR},
        "dataset": {"asset": identity.SAMPLE_ASSET, "records": n},
        "drain3_reference": d_stats,
        "engine_reference": ref_stats,
        "drain3_rerun_matches_identity_raw": with_drain and same_cfg,
        "summary": summary,
        "trials": trials,
        "falsifier": falsifier,
        "disagreements": diffs,
        "same_line_in_halves": halves,
    }
    pathlib.Path(args.out_json).write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    write_md(payload, pathlib.Path(args.out_md), with_drain)
    print(pathlib.Path(args.out_md).read_text())
    print(f"done ({time.time() - t0:.0f}s)", file=sys.stderr)
    return 0


def write_md(payload, path: pathlib.Path, with_drain: bool):
    cfg = payload["config"]
    s = payload["summary"]
    er = payload["engine_reference"]
    L = []
    A = L.append
    A("# Two engine instances on halves of one stream")
    A("")
    A("Written by `bench/engine_split.py`. The protocol of `bench/identity.py`, section 2 of "
      "the README, with the 10x engine in place of Drain3: the same sample, seed, split and "
      "probe sequence per trial. Each half goes through its own engine container in the order "
      "Drain3 receives it, followed by the probe records; the two instances' answers for each "
      "probe record are compared.")
    A("")
    A(f"- image: `{payload['image']}`")
    A(f"- app: `{cfg['engine_app']}` with its shipped configuration and the image's own symbol "
      f"library, plus `{cfg['output_config']}`, which writes each event's pattern name, pattern "
      "hash and template hash")
    A(f"- trials: {cfg['trials']}; probes per trial: {cfg['probes']:,}; seed: {cfg['seed']}")
    A(f"- records: {payload['dataset']['records']:,}; each instance reads its half "
      f"({payload['dataset']['records'] // 2:,} records) and then the {cfg['probes']:,} probes")
    A(f"- engine reference run over the whole stream: {er['events']:,} events, "
      f"{er['distinct_pattern_hashes']:,} pattern hashes, {er['distinct_template_hashes']:,} "
      "template hashes")
    if with_drain and payload["drain3_rerun_matches_identity_raw"]:
        A("- the Drain3 column is the strong arm rerun per probe; its counts over all probes "
          "equal `results/identity_raw.json` trial by trial")
    elif with_drain:
        A("- the Drain3 column is the strong arm rerun per probe, on a configuration "
          "`results/identity_raw.json` does not hold, so it is not checked against it")
    A("")
    A("Each cell is the share of probe records on which the two instances agree, a mean across "
      "trials. The pattern hash is `tenx_hash`, the hash of the pattern name.")
    A("")
    A("## Under Drain3's strata (the probes of each row in `identity.md`)")
    A("")
    A("All probes:")
    A("")
    A(table(s["drain3/all"], with_drain))
    A("")
    A("Probes whose Drain3 shape occurs in both halves:")
    A("")
    A(table(s["drain3/both_halves"], with_drain))
    A("")
    A("## Under the engine's own strata")
    A("")
    A("A probe's frequency is the number of records in the whole stream whose event carries "
      "its pattern hash in the reference run.")
    A("")
    A("All probes:")
    A("")
    A(table(s["engine/all"], with_drain))
    A("")
    A("Probes whose pattern hash occurs in both halves:")
    A("")
    A(table(s["engine/both_halves"], with_drain))
    A("")
    A("## The same line in both halves, no shared traffic")
    A("")
    A("No probe pass: each instance's answers for the records of its own half, fed in the "
      "order above. A line is a record's exact bytes. For every record that both instances "
      "named as an event of its own (one record long) and whose line also occurs in the other "
      "half, the record agrees when every copy of that line the other instance named as an "
      "event of its own got the same answer. Binned under Drain3's strata.")
    A("")
    A("Records the feed joined to the record before them are left out: each half is fed "
      "shuffled, as Drain3 is, so an indented line follows an unrelated record and joins that "
      "record's event, which takes the unrelated record's name. That grouping comes from the "
      "shuffle, not from the stream; in the reference run, fed in stream order, "
      f"{er['single_record_events']:,} of {payload['dataset']['records']:,} records are "
      "events of their own; in the shuffled halves, "
      f"{payload['same_line_in_halves']['half_single_record_events_mean']:,.0f} of "
      f"{payload['same_line_in_halves']['half_records']:,} on average.")
    A("")
    A(table_same_line(payload["same_line_in_halves"]["summary"]))
    A("")
    A("## Falsifier")
    A("")
    A(f"Fixed before the run: two instances give a probe record the same pattern hash less than "
      f"{PATTERN_AGREEMENT_FLOOR} of the time in a stratum, under Drain3's strata.")
    A("")
    for f in payload["falsifier"]:
        A(f"- {f['stratum']}: {f['pattern_hash_agreement']:.4f}, "
          f"{'TRIGGERED' if f['triggered'] else 'not triggered'}")
    A("")
    A("## Disagreements")
    A("")
    d = payload["disagreements"]
    tot = sum(t["drain3"]["all events"].get("all_n", 0) for t in payload["trials"])
    ph = [x for x in d if x["a"]["tenx_hash"] != x["b"]["tenx_hash"]]
    th = [x for x in d if x["a"]["tenx_hash"] == x["b"]["tenx_hash"]]
    A(f"Of {tot:,} probe records, {len(ph)} got different pattern hashes from the two instances "
      f"and {len(th)} more got the same pattern hash and different template hashes. Every one "
      "is in `results/engine_split_raw.json` with both answers and the event that held it.")
    A("")
    if ph:
        A("Different pattern hashes:")
        A("")
        A("| trial | probe position | instance A: pattern, records in event | instance B: pattern, records in event | log |")
        A("|---:|---:|---|---|---|")
        for x in ph:
            log = x["log"][:60].replace("|", "\\|")
            A(f"| {x['trial'] + 1} | {x['probe_position']} | `{x['a']['pattern'][:60]}`, {x['a']['event_records']} | "
              f"`{x['b']['pattern'][:60]}`, {x['b']['event_records']} | `{log}` |")
        A("")
    if th:
        A("Same pattern hash, different template hashes, by pattern:")
        A("")
        A("| pattern | probe records | trials |")
        A("|---|---:|---:|")
        by = collections.defaultdict(list)
        for x in th:
            by[x["a"]["pattern"]].append(x)
        for pat, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            A(f"| `{pat[:90]}` | {len(xs)} | {len({x['trial'] for x in xs})} |")
        A("")
    path.write_text("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
