#!/usr/bin/env python3
"""
Driver behind the Log10x blog post "Drain pattern IDs: stable under reordering,
not under splits" (https://www.log10x.com/blog/the-drain-pattern-id-you-cant-trust/).

Reconstructed 2026-07-17 from the post's method section; the original script was
never committed. Validated against the post's published numbers (see README.md).

Corpus: otel-sample-200mb.log, release asset at
https://github.com/log-10x/config/releases/tag/otel-sample-v1
(215,039,161 bytes, 197,430 lines of OpenTelemetry-demo Kubernetes output).

Method (verbatim from the post):
  - Drain3: depth=6, similarity threshold 0.6, max 20 children per node,
    max 2000 clusters, parameter token `<*>`.
  - A typed-token preprocessor strips UUIDs, ISO timestamps, IPs, hex strings,
    and numbers, capped at 1024 chars.
  - A cluster's identity is its template STRING, never the internal cluster id.
  - Experiment 1 (shuffle): the full corpus in 30 random orders; pairwise
    template-set Jaccard across the 30 runs.
  - Experiment 2 (split): 30 trials; each slices the corpus into 4 disjoint
    quarters and runs a fresh Drain on each; pairwise Jaccard between the
    4 quarter sets (6 pairs per trial).
  - Per-event identity: on a 10,000-line sample, the fraction of lines whose
    matched template string is identical across all 30 reorderings.

Usage:
  python3 stability_measured.py baseline <corpus> [raw|logfield]
  python3 stability_measured.py full     <corpus> [raw|logfield]
"""

import hashlib
import itertools
import json
import random
import re
import statistics
import sys
import time

import drain3
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

SEED = 42
N_RUNS = 30
N_QUARTERS = 4
SAMPLE_SIZE = 10_000
MAX_LINE_CHARS = 1024

# Typed-token masking, applied before Drain. Order matters: UUIDs and
# timestamps are matched before the bare hex / number rules that would
# otherwise eat them piecemeal.
MASKS = [
    (re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), "<UUID>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
                r"(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TS>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "<IP>"),
    # hex runs of 6+ chars containing at least one digit (container ids,
    # commit shas, k8s pod-template hashes); plain 0x literals too
    (re.compile(r"\b0[xX][0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r"\b(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{6,}\b"), "<HEX>"),
    (re.compile(r"\b\d+(?:\.\d+)?\b"), "<NUM>"),
]


def preprocess(line: str) -> str:
    line = line[:MAX_LINE_CHARS]
    for rx, token in MASKS:
        line = rx.sub(token, line)
    return line


def load_lines(path: str, mode: str) -> list:
    raw = open(path, "rb").read().decode("utf-8", "replace")
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if mode == "logfield":
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln).get("log", ln))
            except json.JSONDecodeError:
                out.append(ln)
        lines = out
    return [preprocess(ln) for ln in lines]


def new_miner() -> TemplateMiner:
    cfg = TemplateMinerConfig()
    cfg.drain_depth = 6
    cfg.drain_sim_th = 0.6
    cfg.drain_max_children = 20
    cfg.drain_max_clusters = 2000
    cfg.profiling_enabled = False
    # no drain3-level masking; the typed-token preprocessor above runs instead
    cfg.masking_instructions = []
    return TemplateMiner(config=cfg)


def mine(lines, order=None):
    tm = new_miner()
    if order is None:
        for ln in lines:
            tm.add_log_message(ln)
    else:
        for i in order:
            tm.add_log_message(lines[i])
    templates = {c.get_template() for c in tm.drain.clusters}
    return tm, templates


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def baseline(lines):
    t0 = time.time()
    _, templates = mine(lines)
    dt = time.time() - t0
    print(f"baseline: {len(templates)} templates from {len(lines)} lines "
          f"in {dt:.0f}s ({len(lines)/dt:.0f} lines/s)")
    return len(templates)


def full(lines, corpus_sha, mode):
    n = len(lines)
    rng = random.Random(SEED)
    sample_idx = sorted(rng.sample(range(n), SAMPLE_SIZE))

    # --- Experiment 1: 30 shuffles ---
    shuffle_sets = []
    sample_templates = []          # per run: template matched per sampled line
    baseline_count = None
    for run in range(N_RUNS):
        run_rng = random.Random(SEED * 1_000 + run)
        order = list(range(n))
        run_rng.shuffle(order)
        t0 = time.time()
        tm, templates = mine(lines, order)
        shuffle_sets.append(templates)
        matched = []
        for i in sample_idx:
            m = tm.match(lines[i])
            matched.append(m.get_template() if m else None)
        sample_templates.append(matched)
        print(f"shuffle {run + 1}/{N_RUNS}: {len(templates)} templates "
              f"({time.time() - t0:.0f}s)", flush=True)

    shuffle_pairs = [jaccard(a, b)
                     for a, b in itertools.combinations(shuffle_sets, 2)]
    per_event_same = sum(
        1 for col in zip(*sample_templates)
        if col[0] is not None and all(t == col[0] for t in col))
    per_event_pct = 100.0 * per_event_same / SAMPLE_SIZE

    # --- Experiment 2: 30 four-way splits ---
    split_trials = []
    for trial in range(N_RUNS):
        trial_rng = random.Random(SEED * 2_000 + trial)
        order = list(range(n))
        trial_rng.shuffle(order)
        q = n // N_QUARTERS
        quarter_sets = []
        quarter_counts = []
        for k in range(N_QUARTERS):
            idx = order[k * q:(k + 1) * q] if k < N_QUARTERS - 1 \
                else order[(N_QUARTERS - 1) * q:]
            _, templates = mine(lines, idx)
            quarter_sets.append(templates)
            quarter_counts.append(len(templates))
        pair_j = [jaccard(a, b)
                  for a, b in itertools.combinations(quarter_sets, 2)]
        split_trials.append({"pairwise_jaccard": pair_j,
                             "clusters_per_quarter": quarter_counts})
        print(f"split {trial + 1}/{N_RUNS}: quarters={quarter_counts} "
              f"mean J={statistics.mean(pair_j):.4f}", flush=True)

    trial_means = [statistics.mean(t["pairwise_jaccard"]) for t in split_trials]
    all_quarter_counts = [c for t in split_trials
                          for c in t["clusters_per_quarter"]]

    # unshuffled baseline for the "templates on the full corpus" figure
    baseline_count = baseline(lines)

    results = {
        "post": "https://www.log10x.com/blog/the-drain-pattern-id-you-cant-trust/",
        "corpus": {
            "asset": "otel-sample-200mb.log",
            "release": "https://github.com/log-10x/config/releases/tag/otel-sample-v1",
            "bytes": 215039161,
            "lines": n,
            "sha256": corpus_sha,
        },
        "config": {
            "drain3_version": drain3.__version__
            if hasattr(drain3, "__version__") else "0.9.11",
            "depth": 6, "sim_th": 0.6, "max_children": 20,
            "max_clusters": 2000, "param_str": "<*>",
            "parametrize_numeric_tokens": True,
            "input_mode": mode,
            "max_line_chars": MAX_LINE_CHARS,
            "seed": SEED,
        },
        "baseline_templates_unshuffled": baseline_count,
        "shuffle": {
            "n_runs": N_RUNS,
            "templates_per_run": [len(s) for s in shuffle_sets],
            "pairwise_jaccard_mean": statistics.mean(shuffle_pairs),
            "pairwise_jaccard_std": statistics.stdev(shuffle_pairs),
            "pairwise_jaccard_min": min(shuffle_pairs),
            "pairwise_jaccard": shuffle_pairs,
        },
        "per_event_identity_10k": {
            "sample_size": SAMPLE_SIZE,
            "identical_across_all_runs": per_event_same,
            "pct": per_event_pct,
        },
        "split": {
            "n_trials": N_RUNS,
            "trial_mean_jaccard_mean": statistics.mean(trial_means),
            "trial_mean_jaccard_std": statistics.stdev(trial_means),
            "trial_mean_jaccard_range": [min(trial_means), max(trial_means)],
            "clusters_per_quarter_mean": statistics.mean(all_quarter_counts),
            "clusters_per_quarter_std": statistics.stdev(all_quarter_counts),
            "trials": split_trials,
        },
    }
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps({
        "baseline_templates": baseline_count,
        "shuffle_jaccard": f"{results['shuffle']['pairwise_jaccard_mean']:.4f}"
                           f" ± {results['shuffle']['pairwise_jaccard_std']:.4f}",
        "per_event_pct": f"{per_event_pct:.1f}",
        "split_jaccard": f"{results['split']['trial_mean_jaccard_mean']:.4f}"
                         f" ± {results['split']['trial_mean_jaccard_std']:.4f}",
        "clusters_per_quarter": f"{results['split']['clusters_per_quarter_mean']:.0f}"
                                f" ± {results['split']['clusters_per_quarter_std']:.0f}",
    }, indent=2))


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "raw"
    corpus_sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    lines = load_lines(path, mode)
    print(f"{len(lines)} lines loaded, mode={mode}, sha256={corpus_sha[:16]}…",
          flush=True)
    if cmd == "baseline":
        baseline(lines)
    elif cmd == "full":
        full(lines, corpus_sha, mode)
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
