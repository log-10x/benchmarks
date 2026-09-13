#!/usr/bin/env python3
"""Does the same log line get the same name in two different places?

Two Drain3 instances each receive one side of a split of the same stream, which
models two forwarders that never exchange state. The same probe sequence is then
fed to both, and the names that come back are compared, stratified by how often
each line's shape occurs in the stream.

PRIMARY MEASUREMENT: the production path. A forwarder names a line with
`add_log_message`, which mints a cluster on first sight and always returns a
name. Both trained instances receive the same probe sequence through
`add_log_message` itself, in the same order, exactly as if two nodes with
different histories started seeing the same traffic. Two columns per stratum:

    template agreement     the two `template_mined` strings are equal
    cluster_id agreement   the two integers Drain returned are equal

A hash of the template string agrees exactly when the string agrees, so the
hash column would duplicate the template column and is not printed.

The probe pass itself is shared traffic: both instances ingest every probe, so
their states converge as the pass proceeds, which works in Drain's favour on
net. The divergence reported is what survives that convergence.

An earlier version of this benchmark probed both instances with the read-only
`match()` API and scored a `None` as disagreement. That was wrong: `match()`
returns `None` for a shape the instance never saw, so the headline number mixed
"the two names differ" with "one side has no name to offer", and on lines seen
once it reported 0.0 agreement for what is a coverage property of a
lookup API. Through the production path an unseen line is named immediately.
The `match()` measurement stays in this file as a SECONDARY result about
query-time lookup, with the blindness labelled as coverage.

SECONDARY MEASUREMENT: query-time lookup. `TemplateMiner.match()` is read-only
and hard-codes a required similarity of 1.0 in drain3 0.9.11. An instance that
never ingested a shape returns `None`: it has no name to offer a query. Two
quantities come out, and neither is ever collapsed into one number:

    coverage               the share of probes where BOTH instances already
                           hold a name, so a lookup can answer at all
    agreement when covered among those, the share where the two names match

The lookup pass runs before the probe ingest pass, so it observes the trained
instances exactly as the split left them.

ARMS:

    baseline    typed-token masking, memory only, tree-only lookup
    strong      drain3's own examples/drain3.ini masking block, FilePersistence
                carried across a mid-stream restart, fallback lookup. Drain3's
                strongest honest configuration on this data, and the arm every
                falsifier scores.
    shared      strong, plus instance B warm-starting from instance A's final
                snapshot. Not two peers: a chain. This measures the price of
                agreement.

Usage:
    python bench/identity.py                          # full file, 10 trials
    python bench/identity.py --lines 120000 --trials 3
    python bench/identity.py --arms strong --sim-th 0.4

Outputs, both committed artifacts:
    results/identity_raw.json   every per-trial count
    results/identity.md         the summary tables
"""

import argparse
import collections
import gzip
import json
import os
import pathlib
import shutil
import statistics
import sys
import tempfile
import time
import urllib.request

from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drainver  # noqa: E402  which distribution provides the drain3 module

# ---------------------------------------------------------------------------
# CONFIGURATION. Every Drain3 parameter this benchmark sets is named here.
# ---------------------------------------------------------------------------

# Not drain3's factory values (depth=4, sim_th=0.4, max_children=100, no cap).
# On this data these settings raise Drain3's agreement rather than lowering it;
# they are reported rather than tuned, and --sim-th reruns everything at any
# other similarity threshold so the choice stays contestable.
DRAIN_DEPTH = 6
DRAIN_SIM_TH = 0.6
DRAIN_MAX_CHILDREN = 20
DRAIN_MAX_CLUSTERS = 2000
DRAIN_EXTRA_DELIMITERS = []
# A genuine Drain3 default and the normalizer that does the work on this data. Left on in
# every arm, because a competent user leaves it on.
PARAMETRIZE_NUMERIC_TOKENS = True

# Chars of the application message fed to the miner. The cap helps Drain agree:
# two long lines that differ only past 1024 chars become one shape. It is
# reported rather than tuned.
LINE_CAP = 1024

DEFAULT_TRIALS = 10
DEFAULT_PROBES = 30000
DEFAULT_SEED = 100

# Frequency strata. A shape's frequency is its count over the whole stream under
# that arm's own reference pass, defined below.
BUCKETS = [
    (1, 1, "seen once"),
    (2, 10, "2 to 10"),
    (11, 100, "11 to 100"),
    (101, 1000, "101 to 1,000"),
    (1001, 10 ** 12, "over 1,000"),
]

# Baseline masking. Typed tokens a competent operator writes for this data.
BENCH_MASKING = [
    (r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "UUID"),
    (r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?", "TS"),
    (r"\b(\d{1,3}\.){3}\d{1,3}\b", "IP"),
    (r"\b[0-9a-fA-F]{16,}\b", "HEX"),
    (r"\b\d+\b", "NUM"),
]
BENCH_MASK_PREFIX, BENCH_MASK_SUFFIX = "<", ">"

# The masking block of drain3's examples/drain3.ini, transcribed verbatim,
# including that file's mask_prefix and mask_suffix. "Verbatim" scopes to the
# [MASKING] section alone. Note that the masking set shipped inside the `drain3`
# package itself is empty; the widely quoted "drain3 defaults" live in this
# example file.
INI_MASKING = [
    (r"((?<=[^A-Za-z0-9])|^)(([0-9a-f]{2,}:){3,}([0-9a-f]{2,}))((?=[^A-Za-z0-9])|$)", "ID"),
    (r"((?<=[^A-Za-z0-9])|^)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})((?=[^A-Za-z0-9])|$)", "IP"),
    (r"((?<=[^A-Za-z0-9])|^)([0-9a-f]{6,} ?){3,}((?=[^A-Za-z0-9])|$)", "SEQ"),
    (r"((?<=[^A-Za-z0-9])|^)([0-9A-F]{4} ?){4,}((?=[^A-Za-z0-9])|$)", "SEQ"),
    (r"((?<=[^A-Za-z0-9])|^)(0x[a-f0-9A-F]+)((?=[^A-Za-z0-9])|$)", "HEX"),
    (r"((?<=[^A-Za-z0-9])|^)([\-\+]?\d+)((?=[^A-Za-z0-9])|$)", "NUM"),
    (r"(?<=executed cmd )(\".+?\")", "CMD"),
]
INI_MASK_PREFIX, INI_MASK_SUFFIX = "<:", ":>"

# A reference pass assigns each line a shape and each shape a frequency. One
# instance sees the whole stream, in memory, and every line is then matched back
# against it read-only. full_search_strategy="fallback" is used here whatever the
# arm does, so tree-search false negatives cannot leak into the stratification.
#
# Each arm stratifies under its own configuration. Masking changes which lines
# share a shape, so "seen once" has to mean "seen once under the configuration
# being measured".
REFERENCE_MATCH_STRATEGY = "fallback"

# Some records carry an empty `log` field. Drain assigns them the empty-string
# template. Two instances that both return it are scored as agreeing, which is
# the correct reading of "same name" and is recorded here because a
# re-implementation that tests the template string for truthiness instead of for
# None will not reproduce these figures.
EMPTY_MESSAGE_TEMPLATES_COUNT_AS_A_NAME = True

ARM_DEFAULTS = {
    "persistence_restart": False,
    "warm_start_b_from_a": False,
    "match_strategy": "never",
}

ARMS = {
    "baseline": {
        "masking": BENCH_MASKING,
        "mask_prefix": BENCH_MASK_PREFIX,
        "mask_suffix": BENCH_MASK_SUFFIX,
        "label": "baseline: typed-token masking, memory only, tree-only lookup",
    },
    "strong": {
        "masking": INI_MASKING,
        "mask_prefix": INI_MASK_PREFIX,
        "mask_suffix": INI_MASK_SUFFIX,
        "persistence_restart": True,
        "match_strategy": "fallback",
        "label": "strong: drain3's examples/drain3.ini masking, FilePersistence across a "
                 "mid-stream restart, fallback lookup. Drain3's strongest honest configuration",
    },
    "shared": {
        "masking": INI_MASKING,
        "mask_prefix": INI_MASK_PREFIX,
        "mask_suffix": INI_MASK_SUFFIX,
        "persistence_restart": True,
        "warm_start_b_from_a": True,
        "match_strategy": "fallback",
        "label": "shared: strong, plus B warm-starts from A's final snapshot",
    },
}
for _name, _arm in ARMS.items():
    for _k, _v in ARM_DEFAULTS.items():
        _arm.setdefault(_k, _v)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
DATA_DIR = pathlib.Path(os.environ.get("PIB_DATA_DIR", str(REPO_ROOT / "data")))

# The data is a published GitHub release asset. It is downloaded on first use and
# cached under data/, never vendored into the repository. Loading is kept inside
# this file so the script runs on its own.
RELEASE_BASE = "https://github.com/log-10x/config/releases/download/otel-sample-v1"
SAMPLE_ASSET = "otel-sample-200mb.log"

# ---------------------------------------------------------------------------
# FALSIFIERS. Each one names a quantity that could come out either way on a
# rerun, a threshold fixed here before the run, and the arm that scores it.
# One of them fired against log10x on the first corrected run and stays
# recorded in the form it was registered.
# ---------------------------------------------------------------------------

# Production-path agreement on lines seen once. FIRED against log10x: two
# instances that never exchanged state give a line seen once the same name at
# ingest, because neither can generalize from one example and both mint the
# line's own literal text.
ADD_SEEN_ONCE_THRESHOLD = 0.50

# The stratum where generalization begins. If two instances stop diverging
# there, the divergence claim has nothing left to stand on.
ADD_TAIL_DIVERGENCE_FLOOR = 0.02

# The integer identifier. If it survives a split, the claim that it is arrival
# rank and nothing else is wrong.
ID_TRAVELS_THRESHOLD = 0.50

# Secondary, lookup path: disagreement among probes both instances can already
# answer, in the 11-to-100 stratum, which is where a fleet-wide statement fired
# once per pod lands. Below the floor, cross-instance disagreement is not
# material enough to act on.
LOOKUP_DISAGREEMENT_FLOOR = 0.02

FALSIFIERS = [
    {
        "id": "add_seen_once",
        "text": "Two Drain3 instances that never exchanged state give a line seen once the "
                "same name through the production path, add_log_message. Threshold "
                f"{ADD_SEEN_ONCE_THRESHOLD:.2f} at the strong arm. At or above it, the claim "
                "that a locally mined name is local to the process that mined it does not "
                "hold for lines seen once, and that part of the claim is withdrawn.",
        "arm": "strong",
    },
    {
        "id": "add_tail_divergence",
        "text": "Generalization drives the two instances apart. Threshold: production-path "
                f"template disagreement below {ADD_TAIL_DIVERGENCE_FLOOR:.2f} in the 2-to-10 "
                "stratum at the strong arm. Below it, the divergence claim retires. This "
                "check reruns at any similarity threshold via --sim-th; a sim_th at which "
                "it passes while the reference pass still resolves the stream into at least "
                "half the distinct shapes found at sim_th 0.6 retires the claim outright.",
        "arm": "strong",
    },
    {
        "id": "id_travels",
        "text": "The integer cluster_id does not survive the split. Threshold: cluster_id "
                f"agreement over all probes at or above {ID_TRAVELS_THRESHOLD:.2f} at the "
                "strong arm retires the claim that Drain's identifier is arrival rank and "
                "nothing else.",
        "arm": "strong",
    },
    {
        "id": "lookup_disagreement",
        "text": "Secondary, query-time lookup: where both instances already hold a name for "
                "the same line, the names agree. Threshold: disagreement below "
                f"{LOOKUP_DISAGREEMENT_FLOOR:.2f} in the 11-to-100 stratum at the strong arm. "
                "Below it, two independent miners disagree too rarely for the disagreement "
                "to be worth acting on, and the position does not survive.",
        "arm": "strong",
    },
]

# Quantities this file reports that are close to fixed by the design. Stated so
# they are read as descriptions of a mechanism rather than as tests that passed.
STRUCTURAL = [
    "Production-path agreement for lines seen once is high for a mechanical reason. "
    "Neither instance can generalize a shape it has one example of, so both mint the "
    "line's own literal text as the template and the two strings are equal. The "
    "agreement is genuine and it is conceded in full. The name they agree on is the "
    "pre-generalization literal, which is the name `bench/replay.py` shows moving as "
    "soon as a sibling arrives.",
    "Lookup coverage for lines seen once is near zero by construction. A shape the "
    "full-stream reference pass could not group with anything else occurs in exactly "
    "one line, that line lands in exactly one half, and `match()` requires a "
    "similarity of 1.0, so the other instance can answer only if some unrelated "
    "cluster of its own happens to generalize to the identical string. This is a "
    "coverage property of a lookup API, never a disagreement, and it is not scored "
    "as one anywhere on this page.",
]

# What this benchmark does not claim. Recorded here so the code carries it.
NOT_CLAIMED = [
    "Lossless template-plus-values storage is not novel. Prior art: CLP/YScope, "
    "US10484506B2.",
    "Generic template extraction is not novel. Prior art: Drain, Spell, IPLoM.",
    "Engine-side identifiers are not unconditionally stable. They depend on a "
    "pinned symbol library, an engine version, and library coverage of the "
    "emitting code.",
    "This file does not describe centralized query-time mining. The major SIEM "
    "platforms that mine patterns do it in one central pass at query time, over "
    "whatever the query returns, so no second instance exists to disagree. The "
    "split here indicts per-node mining and any design that persists a mined "
    "name, not those products as they ship today.",
    "A hash of the template is not measured separately. Equal strings hash equal "
    "and divergent strings hash divergent, so the hash column would restate the "
    "template column.",
    "A random half-split is the friendliest division available to Drain: both "
    "instances draw statistically identical samples of one stream. Fleet splits "
    "in production follow placement, so each node sees different source "
    "statements, which is harsher than anything measured here.",
]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def resolve_sample(asset: str = SAMPLE_ASSET) -> pathlib.Path:
    """Return a local path to the sample, downloading the release asset once."""
    for cand in (DATA_DIR / asset, DATA_DIR / (asset + ".gz")):
        if cand.exists() and cand.stat().st_size > 0:
            return cand
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / (asset + ".gz")
    url = f"{RELEASE_BASE}/{asset}.gz"
    print(f"downloading {url}", file=sys.stderr, flush=True)
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out, 1 << 20)
    tmp.replace(dest)
    print(f"  cached {dest} ({dest.stat().st_size:,} bytes)", file=sys.stderr, flush=True)
    return dest


def count_lines(path: pathlib.Path) -> int:
    """Count records in the asset by streaming, so the plain text never lands."""
    opener = gzip.open if path.suffix == ".gz" else open
    n = 0
    with opener(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def iter_messages(path: pathlib.Path, limit: int = None):
    """Yield the application message for each record of the sample.

    Every record is a Fluentd/Kubernetes envelope with the same key set. The
    application message sits in `log`; the rest is envelope. Feeding whole lines
    to a template miner measures envelope clustering, so the benchmark uses the
    extracted message. `python bench/data.py --stats` measures the byte share.
    """
    opener = gzip.open if path.suffix == ".gz" else open
    n = 0
    with opener(path, "rt", errors="replace") as f:
        for line in f:
            if limit is not None and n >= limit:
                return
            try:
                yield json.loads(line).get("log", "") or ""
            except Exception:
                yield ""
            n += 1


# ---------------------------------------------------------------------------
# Drain3 plumbing
# ---------------------------------------------------------------------------

def make_config(arm: dict, sim_th: float) -> TemplateMinerConfig:
    c = TemplateMinerConfig()
    c.drain_depth = DRAIN_DEPTH
    c.drain_sim_th = sim_th
    c.drain_max_children = DRAIN_MAX_CHILDREN
    c.drain_max_clusters = DRAIN_MAX_CLUSTERS
    c.drain_extra_delimiters = list(DRAIN_EXTRA_DELIMITERS)
    c.parametrize_numeric_tokens = PARAMETRIZE_NUMERIC_TOKENS
    c.mask_prefix = arm["mask_prefix"]
    c.mask_suffix = arm["mask_suffix"]
    c.masking_instructions = [MaskingInstruction(p, m) for p, m in arm["masking"]]
    c.profiling_enabled = False
    return c


def _feed(tm: TemplateMiner, messages, idxs) -> None:
    for i in idxs:
        tm.add_log_message(messages[i][:LINE_CAP])


def train(messages, idxs, arm: dict, sim_th: float, snapshot_path: pathlib.Path = None,
          warm_start_from: pathlib.Path = None) -> TemplateMiner:
    """Train one instance on `idxs`.

    With `persistence_restart`, the instance is torn down halfway through its
    own half and rebuilt from its FilePersistence snapshot, which is what a
    forwarder restart looks like to a competent operator who enabled state.

    The persistence handler is attached at the restart boundary only, so the
    state written and reloaded holds every cluster the instance had at that
    moment. That is the most favourable persistence behaviour available, ahead
    of what a periodic snapshot interval would preserve.
    """
    cfg = make_config(arm, sim_th)

    if warm_start_from is not None:
        tm = TemplateMiner(persistence_handler=FilePersistence(str(warm_start_from)), config=cfg)
        tm.persistence_handler = None
    else:
        tm = TemplateMiner(config=cfg)

    if not arm["persistence_restart"]:
        _feed(tm, messages, idxs)
        return tm

    mid = len(idxs) // 2
    _feed(tm, messages, idxs[:mid])

    fp = FilePersistence(str(snapshot_path))
    tm.persistence_handler = fp
    tm.save_state("restart")
    tm.persistence_handler = None

    tm2 = TemplateMiner(persistence_handler=fp, config=cfg)
    tm2.persistence_handler = None
    _feed(tm2, messages, idxs[mid:])

    tm2.persistence_handler = fp
    tm2.save_state("final")
    tm2.persistence_handler = None
    return tm2


def lookup_template(tm: TemplateMiner, message: str, strategy: str):
    """The read-only rule. None when this instance holds no name for the line."""
    c = tm.match(message[:LINE_CAP], full_search_strategy=strategy)
    return c.get_template() if c is not None else None


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def bucket_label(freq: int) -> str:
    for lo, hi, label in BUCKETS:
        if lo <= freq <= hi:
            return label
    raise ValueError(freq)


def reference_key(arm: dict):
    """Two arms share a reference pass when they normalize lines identically."""
    return (arm["mask_prefix"], arm["mask_suffix"],
            tuple(p for p, _ in arm["masking"]))


def reference_pass(messages, arm_name: str, sim_th: float):
    """Assign every line a shape and every shape a frequency, under one arm."""
    arm = ARMS[arm_name]
    tm = train(messages, range(len(messages)),
               {**arm, "persistence_restart": False, "warm_start_b_from_a": False},
               sim_th)
    shape = [None] * len(messages)
    freq = collections.Counter()
    unmatched = 0
    for i, m in enumerate(messages):
        t = lookup_template(tm, m, REFERENCE_MATCH_STRATEGY)
        if t is None:
            t = "<unmatched>"
            unmatched += 1
        shape[i] = t
        freq[t] += 1
    stats = {
        "clusters": len(tm.drain.clusters),
        "distinct_shapes": len(freq),
        "singleton_shapes": sum(1 for v in freq.values() if v == 1),
        "unmatched_probes": unmatched,
    }
    return shape, freq, stats


def run_trial(messages, arm_name: str, sim_th: float, split_a, split_b, probe,
              shape, freq, workdir):
    """One trial: train both instances, look up every probe read-only, then feed
    the same probe sequence to both through add_log_message itself."""
    arm = ARMS[arm_name]
    snap_a = workdir / f"{arm_name}_a.state"
    snap_b = workdir / f"{arm_name}_b.state"

    tm_a = train(messages, split_a, arm, sim_th, snapshot_path=snap_a)
    if arm["warm_start_b_from_a"]:
        tm_b = train(messages, split_b, arm, sim_th, snapshot_path=snap_b,
                     warm_start_from=snap_a)
    else:
        tm_b = train(messages, split_b, arm, sim_th, snapshot_path=snap_b)

    counts = {label: collections.Counter() for _, _, label in BUCKETS}

    # SECONDARY first, because it is read-only and must observe the instances
    # exactly as the split left them.
    strategy = arm["match_strategy"]
    for i in probe:
        c = counts[bucket_label(freq[shape[i]])]
        la = lookup_template(tm_a, messages[i], strategy)
        lb = lookup_template(tm_b, messages[i], strategy)
        if la is not None and lb is not None:
            c["lookup_agree" if la == lb else "lookup_differ"] += 1
        elif la is not None or lb is not None:
            c["one_blind"] += 1
        else:
            c["both_blind"] += 1

    # PRIMARY: the production path. The same probe sequence, in the same order,
    # through add_log_message itself on both instances. State mutates as it
    # would on two live nodes now seeing the same traffic.
    for i in probe:
        c = counts[bucket_label(freq[shape[i]])]
        ra = tm_a.add_log_message(messages[i][:LINE_CAP])
        rb = tm_b.add_log_message(messages[i][:LINE_CAP])
        c["tpl_agree" if ra["template_mined"] == rb["template_mined"] else "tpl_differ"] += 1
        c["id_agree" if ra["cluster_id"] == rb["cluster_id"] else "id_differ"] += 1

    out = {
        "clusters_a": len(tm_a.drain.clusters),
        "clusters_b": len(tm_b.drain.clusters),
        "lines_a": len(split_a),
        "lines_b": len(split_b),
        "buckets": {},
    }
    tot = collections.Counter()
    for _, _, label in BUCKETS:
        out["buckets"][label] = bucket_record(counts[label])
        tot.update(counts[label])
    out["all_events"] = bucket_record(tot)
    return out


def bucket_record(c) -> dict:
    n = c["tpl_agree"] + c["tpl_differ"]
    both_hold = c["lookup_agree"] + c["lookup_differ"]
    return {
        "n": n,
        "tpl_agree": c["tpl_agree"],
        "tpl_differ": c["tpl_differ"],
        "id_agree": c["id_agree"],
        "id_differ": c["id_differ"],
        "lookup_agree": c["lookup_agree"],
        "lookup_differ": c["lookup_differ"],
        "one_blind": c["one_blind"],
        "both_blind": c["both_blind"],
        # PRIMARY, over every probe: the production path always answers.
        "template_agreement": (c["tpl_agree"] / n) if n else None,
        "cluster_id_agreement": (c["id_agree"] / n) if n else None,
        # SECONDARY: share of probes where both instances already hold a name,
        # so a read-only lookup can answer at all.
        "lookup_coverage": (both_hold / n) if n else None,
        # Among those, the share where the two names are the same string.
        "lookup_agreement_when_covered": (c["lookup_agree"] / both_hold) if both_hold else None,
    }


PRIMARY_METRICS = [
    ("template_agreement", "template"),
    ("cluster_id_agreement", "cluster_id"),
]
SECONDARY_METRICS = [
    ("lookup_coverage", "coverage"),
    ("lookup_agreement_when_covered", "agree|covered"),
]
ALL_METRICS = PRIMARY_METRICS + SECONDARY_METRICS


def summarize(trials):
    """mean / stdev / min of each reported metric, across trials."""
    rows = {}
    keys = [label for _, _, label in BUCKETS] + ["all events"]
    for key in keys:
        recs = [(t["all_events"] if key == "all events" else t["buckets"][key]) for t in trials]
        row = {"probes_per_trial": int(statistics.mean(r["n"] for r in recs))}
        any_metric = False
        for metric, _ in ALL_METRICS:
            vals = [r[metric] for r in recs if r[metric] is not None]
            if not vals:
                row[metric] = None
                continue
            any_metric = True
            row[metric] = {
                "trials": len(vals),
                "mean": statistics.mean(vals),
                "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
                "min": min(vals),
            }
        rows[key] = row if any_metric else None
    return rows


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def fmt_primary(rows) -> str:
    head = (f"{'line frequency':>16} {'probes':>8} "
            f"{'template':>9} {'stdev':>7} {'cluster_id':>11}")
    lines = [head]
    for key in [label for _, _, label in BUCKETS] + ["all events"]:
        r = rows.get(key)
        if r is None:
            lines.append(f"{key:>16} {'0':>8} {'n/a':>9} {'n/a':>7} {'n/a':>11}")
            continue
        t = r.get("template_agreement")
        i = r.get("cluster_id_agreement")
        tc = "n/a" if t is None else f"{t['mean']:.4f}"
        sc = "n/a" if t is None else f"{t['stdev']:.4f}"
        ic = "n/a" if i is None else f"{i['mean']:.4f}"
        lines.append(f"{key:>16} {r['probes_per_trial']:>8,} {tc:>9} {sc:>7} {ic:>11}")
    return "\n".join(lines)


def fmt_secondary(rows) -> str:
    head = f"{'line frequency':>16} {'probes':>8} {'coverage':>9} {'agree|cov':>10}"
    lines = [head]
    for key in [label for _, _, label in BUCKETS] + ["all events"]:
        r = rows.get(key)
        if r is None:
            lines.append(f"{key:>16} {'0':>8} {'n/a':>9} {'n/a':>10}")
            continue
        cells = []
        for metric, _ in SECONDARY_METRICS:
            m = r.get(metric)
            cells.append("n/a" if m is None else f"{m['mean']:.4f}")
        lines.append(f"{key:>16} {r['probes_per_trial']:>8,} {cells[0]:>9} {cells[1]:>10}")
    return "\n".join(lines)


def md_primary_table(rows) -> str:
    out = ["| line frequency | probes/trial | template agreement | stdev | cluster_id agreement |",
           "|---|---:|---:|---:|---:|"]
    for key in [label for _, _, label in BUCKETS] + ["all events"]:
        r = rows.get(key)
        if r is None:
            out.append(f"| {key} | 0 | n/a | n/a | n/a |")
            continue
        t = r.get("template_agreement")
        i = r.get("cluster_id_agreement")
        bold = "**" if key in ("2 to 10", "all events") else ""
        tcell = "n/a" if t is None else f"{bold}{t['mean']:.4f}{bold}"
        scell = "n/a" if t is None else f"{t['stdev']:.4f}"
        icell = "n/a" if i is None else f"{bold}{i['mean']:.4f}{bold}"
        out.append(f"| {key} | {r['probes_per_trial']:,} | {tcell} | {scell} | {icell} |")
    out.append("")
    out.append("Probes per trial is the mean across trials; each trial samples its own probe "
               "set and its own split. Every cell is a mean across trials, with stdev and "
               "minimum in `results/identity_raw.json`.")
    return "\n".join(out)


def md_secondary_table(rows) -> str:
    out = ["| line frequency | probes/trial | coverage: both hold a name | agreement when covered |",
           "|---|---:|---:|---:|"]
    for key in [label for _, _, label in BUCKETS] + ["all events"]:
        r = rows.get(key)
        if r is None:
            out.append(f"| {key} | 0 | n/a | n/a |")
            continue
        cells = []
        for metric, _ in SECONDARY_METRICS:
            m = r.get(metric)
            cells.append("n/a" if m is None else f"{m['mean']:.4f}")
        out.append(f"| {key} | {r['probes_per_trial']:,} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def write_markdown(payload, path: pathlib.Path) -> None:
    cfg = payload["config"]
    ds = payload["dataset"]
    L = []
    A = L.append
    A("# Pattern identity: does the same line get the same name in two places?")
    A("")
    A("Generated by `bench/identity.py`. Every number on this page was produced by "
      "that script on the run recorded in `results/identity_raw.json`.")
    A("")
    A("## Procedure")
    A("")
    A("Two Drain3 instances each receive one random half of the same stream, disjoint, "
      "which models two forwarders that never exchange state. The same probe sequence is "
      "then fed to both, and the names that come back are compared, stratified by how "
      "often each line's shape occurs over the whole stream.")
    A("")
    A("**Primary, the production path.** A forwarder names a line with `add_log_message`, "
      "which mints a cluster on first sight and always returns a name. Both instances "
      "receive the same probe sequence through `add_log_message` itself, in the same "
      "order, exactly as if two nodes with different histories started seeing the same "
      "traffic. The probe pass itself is shared traffic, so the two states converge as it "
      "proceeds, which works in Drain's favour on net. Two columns: the "
      "`template_mined` strings are equal, and the integer `cluster_id`s are equal. A hash "
      "of the template agrees exactly when the string agrees, so a hash column would "
      "duplicate the template column.")
    A("")
    A("**Secondary, query-time lookup.** `TemplateMiner.match()` is read-only and requires "
      f"a similarity of 1.0 in {payload['env'].get('drain3_distribution', 'drain3')} "
      f"{payload['env']['drain3_version']}, so an instance that never ingested a shape "
      "returns `None`: it has no name to offer a query. That is **coverage**, never "
      "disagreement, and it is reported as coverage. An earlier version of this benchmark "
      "scored those `None`s as disagreement in its headline, which overstated the case; "
      "the correction is this page's structure. The lookup pass runs before the probe "
      "ingest pass, so it observes the instances exactly as the split left them.")
    A("")
    A(f"- data: `{ds['asset']}` from {ds['source_url']}")
    A(f"- lines available: {ds['lines_available']:,}; lines used: {ds['lines_used']:,}")
    A(f"- trials: {cfg['trials']}; probes per trial: {cfg['probes']:,}; seed: {cfg['seed']}")
    A(f"- {payload['env'].get('drain3_distribution', 'drain3')} "
      f"{payload['env']['drain3_version']}, Python {payload['env']['python']}")
    is_full = (ds["lines_used"] == ds["lines_available"]
               and cfg["trials"] == DEFAULT_TRIALS and cfg["seed"] == DEFAULT_SEED
               and cfg["probes"] == DEFAULT_PROBES and cfg["sim_th"] == DRAIN_SIM_TH)
    if is_full:
        A("- reproduce this page: `python bench/identity.py`, which is the full run, "
          "every line and every default")
    else:
        A(f"- reproduce this page: `python bench/identity.py --lines {ds['lines_used']} "
          f"--trials {cfg['trials']} --probes {cfg['probes']} --seed {cfg['seed']}"
          + (f" --sim-th {cfg['sim_th']}" if cfg["sim_th"] != DRAIN_SIM_TH else "") + "`")
        A(f"- the full run is `python bench/identity.py`, which uses all "
          f"{ds['lines_available']:,} lines and {DEFAULT_TRIALS} trials and takes longer")
    A(f"- every arm: depth={DRAIN_DEPTH}, sim_th={cfg['sim_th']}, "
      f"max_children={DRAIN_MAX_CHILDREN}, max_clusters={DRAIN_MAX_CLUSTERS}, "
      f"parametrize_numeric_tokens={cfg['parametrize_numeric_tokens']}, "
      f"message capped at {cfg['line_cap']} chars")
    A("")
    A("The settings that differ from drain3's factory values raise Drain3's agreement on "
      "this data rather than lowering it, and they are reported instead of tuned. "
      "`--sim-th` reruns everything at any other similarity threshold, which is how the "
      "2-to-10 falsifier below is meant to be attacked.")
    A("")
    A("Each arm is stratified by its own reference pass: one instance over the whole "
      "stream, in memory, every line then matched back against it read-only with fallback "
      "search. Masking changes which lines share a shape, so \"seen once\" means \"seen "
      "once under the configuration being measured\".")
    A("")
    A(f"{ds['empty_messages']:,} records carry an empty `log` field and Drain gives them "
      "the empty-string template. Two instances that both return it are scored as "
      "agreeing, which is the correct reading of \"same name\".")
    A("")
    A("| arm | clusters | distinct shapes | shapes seen once | lines the reference could not match |")
    A("|---|---:|---:|---:|---:|")
    for name in payload["arm_order"]:
        r = payload["arms"][name]["reference"]
        A(f"| `{name}` | {r['clusters']:,} | {r['distinct_shapes']:,} | "
          f"{r['singleton_shapes']:,} | {r['unmatched_probes']:,} |")
    A("")
    A("## Arms")
    A("")
    A("| arm | masking | state | lookup strategy | B warm-starts from A |")
    A("|---|---|---|---|---|")
    for name in payload["arm_order"]:
        a = ARMS[name]
        if a["masking"] is BENCH_MASKING:
            mask = "typed tokens (UUID, ISO timestamp, IP, long hex, integers)"
        else:
            mask = "drain3 `examples/drain3.ini`, `[MASKING]` block verbatim"
        state = ("FilePersistence across a mid-stream restart"
                 if a["persistence_restart"] else "memory only")
        A(f"| `{name}` | {mask} | {state} | `{a['match_strategy']}` | "
          f"{'yes' if a['warm_start_b_from_a'] else 'no'} |")
    A("")
    A("## Primary result: the production path")
    A("")
    for name in payload["arm_order"]:
        arm = payload["arms"][name]
        A(f"### `{name}`")
        A("")
        A(f"{ARMS[name]['label']}")
        A("")
        A(md_primary_table(arm["summary"]))
        A("")
        A(f"Lines fed: A {arm['lines_a_mean']:,.0f}, B {arm['lines_b_mean']:,.0f}. "
          f"Cluster count at the end of a trial: A {arm['clusters_a_mean']:.0f}, "
          f"B {arm['clusters_b_mean']:.0f}.")
        A("")
    A("Reading the strong arm, conceded row first: on lines seen once the two instances "
      "agree, because neither can generalize from one example and both mint the line's "
      "own literal text. The divergence sits where generalization begins: in the 2-to-10 "
      "and 11-to-100 strata, `create_template` wildcards the positions where each "
      "instance's own siblings happened to vary, so two instances with different histories "
      "settle on different intersections of the same statement's outputs. The integer "
      "`cluster_id` is arrival rank and rarely survives the split in any stratum.")
    A("")
    A("## Secondary result: query-time lookup")
    A("")
    A("The read-only `match()` API, the one a query-time consumer would call. `None` "
      "means the instance has no name to offer, which is a coverage property, so the "
      "first column is titled coverage and no cell here scores a `None` as a "
      "disagreement.")
    A("")
    for name in payload["arm_order"]:
        arm = payload["arms"][name]
        A(f"### `{name}`")
        A("")
        A(md_secondary_table(arm["summary"]))
        A("")
    A("Rarity costs the name its second copy: at \"seen once\" the name exists in exactly "
      "one instance, so nothing elsewhere can resolve a query keyed on it. Where both "
      "instances do hold a name, the disagreement among them tracks the same 2-to-10 and "
      "11-to-100 strata as the primary table.")
    A("")
    A("## What would prove this wrong")
    A("")
    checks = payload.get("falsifier_checks") or []
    if checks:
        for c in checks:
            A(f"- {c['text']}")
            verdict = "TRIGGERED" if c["triggered"] else "not triggered"
            A(f"  - observed: {c['observed']} -> {verdict}")
            if c.get("consequence"):
                A(f"  - {c['consequence']}")
    else:
        for f in FALSIFIERS:
            A(f"- {f['text']}")
    A("")
    A("## Fixed by the design, not tested by it")
    A("")
    for s in STRUCTURAL:
        A(f"- {s}")
    A("")
    A("## What is not claimed")
    A("")
    for f in NOT_CLAIMED:
        A(f"- {f}")
    A("")
    A("## Mechanism, read from the Drain3 source")
    A("")
    A("- `add_log_message`: an unmatched line creates a cluster immediately, on first "
      "sight, holding the full literal tokens. Drain3 has no minimum-support threshold. "
      "This is why the production path agrees on rare shapes: neither instance can "
      "generalize from one example, so both return the line's own literal text.")
    A("- `create_template(seq1, seq2)` returns `[token2 if token1 == token2 else "
      "param_str ...]` and writes the result back, so a cluster template is the running "
      "intersection of every line that ever matched it. Two instances with different "
      "histories hold different intersections, which is the whole divergence mechanism. "
      "The same mechanism is specified in the ICWS 2017 paper, so this is Drain working "
      "as designed rather than a bug in drain3.")
    A("- `tree_search` partitions on token count at the first level, so two outputs of "
      "one source statement with different token counts land in separate clusters "
      "whatever `depth` and `sim_th` are set to.")
    A("- `match()` calls `Drain.match`, which requires a similarity of 1.0 and defaults "
      "to `full_search_strategy=\"never\"`. It is a lookup, not a naming call, which is "
      "why its blindness is reported as coverage.")
    A("- `cluster_id` is `self.clusters_counter += 1`, which is arrival rank and nothing "
      "else.")
    A("")
    if payload.get("verdict"):
        A("## Verdict")
        A("")
        A(payload["verdict"])
        A("")
    path.write_text("\n".join(L) + "\n")


# ---------------------------------------------------------------------------

def _metric(payload, arm, key, metric):
    r = payload["arms"].get(arm, {}).get("summary", {}).get(key)
    return r.get(metric) if r else None


def evaluate_falsifiers(payload):
    """Check each stated falsifier against what the run produced."""
    order = payload["arm_order"]
    out = []

    def add(fid, observed, triggered, consequence=None):
        f = next(x for x in FALSIFIERS if x["id"] == fid)
        out.append({"id": fid, "text": f["text"], "observed": observed,
                    "triggered": bool(triggered), "consequence": consequence})

    if "strong" not in order:
        return out

    m = _metric(payload, "strong", "seen once", "template_agreement")
    if m:
        hit = m["mean"] >= ADD_SEEN_ONCE_THRESHOLD
        add("add_seen_once",
            f"strong arm, lines seen once, production-path template agreement "
            f"{m['mean']:.4f} (stdev {m['stdev']:.4f}, min {m['min']:.4f}; threshold "
            f"{ADD_SEEN_ONCE_THRESHOLD:.2f})",
            hit,
            consequence=(
                "TRIGGERED, and it stands as a concession: the claim that a locally mined "
                "name is local to the process that mined it is withdrawn for lines seen "
                "once. Two instances that never exchanged state give such a line the same "
                "name through the production path, because neither can generalize from one "
                "example and both mint the line's own literal text. What survives is in the "
                "rows below it, where generalization has begun, and in `bench/replay.py`, "
                "which shows the agreed literal moving as soon as a sibling arrives."
            ) if hit else "Not triggered on this run.")

    m = _metric(payload, "strong", "2 to 10", "template_agreement")
    if m:
        dis = 1.0 - m["mean"]
        below = dis < ADD_TAIL_DIVERGENCE_FLOOR
        sim_th = payload["config"]["sim_th"]
        observed = (f"strong arm, 2 to 10, production-path template disagreement {dis:.4f} "
                    f"(floor {ADD_TAIL_DIVERGENCE_FLOOR:.2f}; sim_th {sim_th})")
        if not below:
            add("add_tail_divergence", observed, False, consequence=None)
        elif sim_th == DRAIN_SIM_TH:
            add("add_tail_divergence", observed, True,
                consequence="The divergence claim retires at this similarity threshold.")
        else:
            # The registered falsifier carries a shape-count guard: a pass at a
            # non-default sim_th retires the claim only while the reference pass
            # still resolves at least half the distinct shapes found at the
            # default threshold. Scored here, never left to the reader.
            ref = payload["arms"]["strong"]["reference"]["distinct_shapes"]
            base = (payload.get("shape_guard") or {}).get("distinct_shapes_at_default")
            if base is None:
                add("add_tail_divergence",
                    observed + f"; shape-count guard unscored: this payload records "
                    f"{ref:,} distinct shapes at sim_th {sim_th} and no count at "
                    f"sim_th {DRAIN_SIM_TH}", False,
                    consequence="Below the floor, and the guard needs a fresh run "
                                "rather than --render-only to score; the claim does "
                                "not retire on an unscored guard.")
            elif ref >= 0.5 * base:
                add("add_tail_divergence",
                    observed + f"; shape-count guard holds: {ref:,} distinct shapes "
                    f"against {base:,} at sim_th {DRAIN_SIM_TH}", True,
                    consequence="The divergence claim retires outright: below the "
                                "floor while the reference pass still resolves at "
                                "least half the distinct shapes found at the default "
                                "threshold.")
            else:
                add("add_tail_divergence",
                    observed + f"; shape-count guard fails: {ref:,} distinct shapes "
                    f"against {base:,} at sim_th {DRAIN_SIM_TH}", False,
                    consequence="Below the floor only by coarsening the stream: the "
                                "reference pass resolves under half the distinct "
                                "shapes found at the default threshold, so this run "
                                "bought agreement by merging shapes and the claim "
                                "stands.")

    m = _metric(payload, "strong", "all events", "cluster_id_agreement")
    if m:
        add("id_travels",
            f"strong arm, all events, cluster_id agreement {m['mean']:.4f} "
            f"(threshold {ID_TRAVELS_THRESHOLD:.2f})",
            m["mean"] >= ID_TRAVELS_THRESHOLD,
            consequence=("The claim that Drain's identifier is arrival rank retires."
                         if m["mean"] >= ID_TRAVELS_THRESHOLD else None))

    m = _metric(payload, "strong", "11 to 100", "lookup_agreement_when_covered")
    if m:
        dis = 1.0 - m["mean"]
        add("lookup_disagreement",
            f"strong arm, 11 to 100, lookup disagreement among probes both instances can "
            f"answer {dis:.4f} (floor {LOOKUP_DISAGREEMENT_FLOOR:.2f})",
            dis < LOOKUP_DISAGREEMENT_FLOOR,
            consequence=("Two independent miners disagree too rarely to act on; the "
                         "position does not survive."
                         if dis < LOOKUP_DISAGREEMENT_FLOOR else None))
    return out


def build_verdict(payload) -> str:
    order = payload["arm_order"]
    bits = []
    ref_arm = "strong" if "strong" in order else order[0]

    t1 = _metric(payload, ref_arm, "seen once", "template_agreement")
    t2 = _metric(payload, ref_arm, "2 to 10", "template_agreement")
    t3 = _metric(payload, ref_arm, "11 to 100", "template_agreement")
    ia = _metric(payload, ref_arm, "all events", "cluster_id_agreement")
    ta = _metric(payload, ref_arm, "all events", "template_agreement")
    if t1 and t2 and t3:
        bits.append(
            f"Through the production path, at Drain3's strongest honest configuration, "
            f"two instances that never exchanged state agree on the template "
            f"{t1['mean']:.4f} of the time for lines seen once, {t2['mean']:.4f} at 2 to "
            f"10, and {t3['mean']:.4f} at 11 to 100. The singleton row is conceded: both "
            f"mint the same literal. The divergence sits exactly where generalization "
            f"begins.")
    if ta and ia:
        bits.append(
            f"Over all probes the template agrees {ta['mean']:.4f} and the integer "
            f"cluster_id agrees {ia['mean']:.4f}, so anything keyed on the integer is "
            f"keyed on arrival rank, and hashing the template inherits the template "
            f"column unchanged.")

    if "shared" in order and "strong" in order:
        s2 = _metric(payload, "shared", "2 to 10", "template_agreement")
        g2 = _metric(payload, "strong", "2 to 10", "template_agreement")
        c1 = _metric(payload, "shared", "seen once", "lookup_coverage")
        if s2 and g2 and c1 is not None:
            bits.append(
                f"Chaining the two instances through one snapshot moves 2-to-10 "
                f"production-path agreement from {g2['mean']:.4f} to {s2['mean']:.4f} and "
                f"lifts seen-once lookup coverage to "
                f"{c1['mean']:.4f}. That coverage figure lands near one half for a "
                f"structural reason: a shape seen once is in A's side or B's side with "
                f"equal probability, and only A's side reaches B through the snapshot. "
                f"Agreement is purchasable, and its price is one shared model that both "
                f"sides read and write in sequence, which is an architecture rather than "
                f"a setting.")
    return " ".join(bits)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    ap.add_argument("--probes", type=int, default=DEFAULT_PROBES)
    ap.add_argument("--lines", type=int, default=None,
                    help="use only the first N lines; default is the whole file")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--arms", default=",".join(ARMS),
                    help="comma separated subset of: " + ", ".join(ARMS))
    ap.add_argument("--sim-th", type=float, default=DRAIN_SIM_TH,
                    help="rerun every arm at this similarity threshold; the 2-to-10 "
                         "falsifier is meant to be attacked with this flag")
    ap.add_argument("--out-json", default=str(RESULTS_DIR / "identity_raw.json"))
    ap.add_argument("--out-md", default=str(RESULTS_DIR / "identity.md"))
    ap.add_argument("--render-only", action="store_true",
                    help="rebuild the report from an existing --out-json, run nothing")
    args = ap.parse_args()

    if args.render_only:
        payload = json.loads(pathlib.Path(args.out_json).read_text())
        payload["falsifiers"] = FALSIFIERS
        payload["structural"] = STRUCTURAL
        payload["not_claimed"] = NOT_CLAIMED
        payload["falsifier_checks"] = evaluate_falsifiers(payload)
        payload["verdict"] = build_verdict(payload)
        pathlib.Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        write_markdown(payload, pathlib.Path(args.out_md))
        print(f"rendered {args.out_md} from {args.out_json}")
        return 0

    arm_order = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arm_order:
        if a not in ARMS:
            ap.error(f"unknown arm {a!r}; known: {', '.join(ARMS)}")

    import random

    asset = SAMPLE_ASSET
    path = resolve_sample(asset)
    t0 = time.time()
    print(f"loading {path.name}", file=sys.stderr, flush=True)
    messages = list(iter_messages(path, limit=args.lines))
    n = len(messages)
    empty_messages = sum(1 for m in messages if m == "")
    # Counted, never assumed: with --lines the asset is streamed a second time so
    # the "lines available" figure on the report is measured rather than quoted.
    lines_available = n if args.lines is None else count_lines(path)
    print(f"  {n:,} lines of {lines_available:,} in {time.time() - t0:.0f}s",
          file=sys.stderr, flush=True)

    probes = min(args.probes, n)

    ref_cache = {}
    for name in arm_order:
        key = reference_key(ARMS[name])
        if key in ref_cache:
            continue
        print(f"reference pass for {name}", file=sys.stderr, flush=True)
        ref_cache[key] = reference_pass(messages, name, args.sim_th)
        st = ref_cache[key][2]
        print(f"  clusters={st['clusters']:,} shapes={st['distinct_shapes']:,} "
              f"seen-once shapes={st['singleton_shapes']:,} "
              f"unmatched={st['unmatched_probes']:,} ({time.time() - t0:.0f}s)",
              file=sys.stderr, flush=True)

    # The 2-to-10 falsifier's shape-count guard. A run at a non-default sim_th
    # retires the divergence claim only while its reference pass still resolves
    # at least half the distinct shapes found at the default threshold, so that
    # count is measured on the same lines and stored for evaluate_falsifiers.
    shape_guard = None
    if "strong" in arm_order and args.sim_th != DRAIN_SIM_TH:
        print(f"shape-count guard: reference pass at sim_th {DRAIN_SIM_TH}",
              file=sys.stderr, flush=True)
        _, _, guard_stats = reference_pass(messages, "strong", DRAIN_SIM_TH)
        shape_guard = {
            "default_sim_th": DRAIN_SIM_TH,
            "distinct_shapes_at_default": guard_stats["distinct_shapes"],
        }
        print(f"  distinct shapes at sim_th {DRAIN_SIM_TH}: "
              f"{guard_stats['distinct_shapes']:,} ({time.time() - t0:.0f}s)",
              file=sys.stderr, flush=True)

    # One probe sequence and one split per trial, shared by every arm, so
    # arm-to-arm differences are paired trial by trial.
    plan = []
    for t in range(args.trials):
        rnd = random.Random(args.seed + t)
        idx = list(range(n))
        rnd.shuffle(idx)
        split_a, split_b = idx[:n // 2], idx[n // 2:]
        probe = rnd.sample(range(n), probes)
        plan.append({"split": (split_a, split_b), "probe": probe})

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="pib-identity-"))
    arms_out = {}
    try:
        for name in arm_order:
            shape, freq, ref_stats = ref_cache[reference_key(ARMS[name])]
            trials = []
            for t, p in enumerate(plan):
                sa, sb = p["split"]
                trials.append(run_trial(messages, name, args.sim_th, sa, sb,
                                        p["probe"], shape, freq, workdir))
                print(f"  {name} trial {t + 1}/{args.trials} "
                      f"({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)
            arms_out[name] = {
                "definition": {k: v for k, v in ARMS[name].items() if k != "masking"},
                "masking_patterns": [p for p, _ in ARMS[name]["masking"]],
                "reference": ref_stats,
                "trials": trials,
                "summary": summarize(trials),
                "clusters_a_mean": statistics.mean(x["clusters_a"] for x in trials),
                "clusters_b_mean": statistics.mean(x["clusters_b"] for x in trials),
                "lines_a_mean": statistics.mean(x["lines_a"] for x in trials),
                "lines_b_mean": statistics.mean(x["lines_b"] for x in trials),
            }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    payload = {
        "script": "bench/identity.py",
        "env": {
            "drain3_distribution": drainver.distribution()[0],
            "drain3_version": drainver.distribution()[1],
            "python": ".".join(str(x) for x in sys.version_info[:3]),
        },
        "dataset": {
            "asset": asset,
            "source_url": f"{RELEASE_BASE}/{asset}.gz",
            "lines_available": lines_available,
            "lines_used": n,
            "empty_messages": empty_messages,
            "field": "log (application message extracted from the Fluentd/Kubernetes envelope)",
        },
        "config": {
            "trials": args.trials, "probes": probes, "seed": args.seed,
            "drain_depth": DRAIN_DEPTH, "sim_th": args.sim_th,
            "drain_max_children": DRAIN_MAX_CHILDREN, "drain_max_clusters": DRAIN_MAX_CLUSTERS,
            "drain_extra_delimiters": DRAIN_EXTRA_DELIMITERS,
            "parametrize_numeric_tokens": PARAMETRIZE_NUMERIC_TOKENS,
            "line_cap": LINE_CAP,
            "buckets": [[lo, hi, label] for lo, hi, label in BUCKETS],
            "reference_match_strategy": REFERENCE_MATCH_STRATEGY,
            "stratification": "per arm, from that arm's own reference pass",
            "add_seen_once_threshold": ADD_SEEN_ONCE_THRESHOLD,
            "add_tail_divergence_floor": ADD_TAIL_DIVERGENCE_FLOOR,
            "id_travels_threshold": ID_TRAVELS_THRESHOLD,
            "lookup_disagreement_floor": LOOKUP_DISAGREEMENT_FLOOR,
        },
        "arm_order": arm_order,
        "arms": arms_out,
        "falsifiers": FALSIFIERS,
        "structural": STRUCTURAL,
        "not_claimed": NOT_CLAIMED,
    }
    # Recorded only when measured, so a default-threshold rerun stays
    # byte-identical to the committed artifact and the git-diff gate holds.
    if shape_guard is not None:
        payload["shape_guard"] = shape_guard
    payload["falsifier_checks"] = evaluate_falsifiers(payload)
    payload["verdict"] = build_verdict(payload)

    out_json = pathlib.Path(args.out_json)
    out_md = pathlib.Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(payload, out_md)

    print()
    print("TWO INSTANCES, DISJOINT HALVES, SAME PROBE SEQUENCE THROUGH add_log_message")
    print("template   = the two template_mined strings are equal (PRIMARY)")
    print("cluster_id = the two integers Drain returned are equal (PRIMARY)")
    print("coverage   = both instances already hold a name, via read-only match() (SECONDARY)")
    print("agree|cov  = of those, the share where the two names are the same string")
    print(f"lines={n:,}  trials={args.trials}  probes/trial={probes:,}  "
          f"seed={args.seed}  sim_th={args.sim_th}")
    for name in arm_order:
        st = arms_out[name]["reference"]
        print()
        print(f"[{name}] {ARMS[name]['label']}")
        print(f"  reference: {st['clusters']:,} clusters, "
              f"{st['distinct_shapes']:,} distinct shapes, "
              f"{st['singleton_shapes']:,} seen exactly once, "
              f"{st['unmatched_probes']:,} unmatched")
        print("  PRIMARY, production path")
        print("  " + fmt_primary(arms_out[name]["summary"]).replace("\n", "\n  "))
        print("  SECONDARY, query-time lookup")
        print("  " + fmt_secondary(arms_out[name]["summary"]).replace("\n", "\n  "))
    if payload["falsifier_checks"]:
        print()
        print("FALSIFIER CHECKS")
        for c in payload["falsifier_checks"]:
            mark = "TRIGGERED" if c["triggered"] else "not triggered"
            print(f"  [{mark}] {c['id']}: {c['observed']}")
    if payload["verdict"]:
        print()
        print("VERDICT")
        for line in payload["verdict"].split(". "):
            if line.strip():
                print("  " + line.strip().rstrip(".") + ".")
    print()
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
