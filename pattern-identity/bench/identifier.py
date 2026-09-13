#!/usr/bin/env python3
"""identifier.py - the template string travels, the integer cluster_id does not.

Same lines, two arrival orders: the natural order of the public sample, and the
same lines shuffled with a fixed seed. Each line is named twice, once per pass,
at the moment it is ingested. Two names are compared:

    template_mined   the template string Drain assigned
    cluster_id       the integer Drain assigned

The template string is what a careful integrator hashes. The integer is what
Drain hands back first, what its own examples print, and what tends to end up in
a dashboard variable or an alert rule.

From drain3/drain.py, ``cluster_id`` is ``self.clusters_counter += 1`` at cluster
creation. It encodes discovery order and nothing else, so it does not survive a
reordering of the same data through the same code.

Drain's clustering comes out of this well. The template result is the strong one,
and it reproduces the published stability claim rather than refuting it. Drain
runs at its strongest honest configuration throughout: typed-token masking on,
``parametrize_numeric_tokens`` at its Drain3 default of True.

Falsifier, in both directions. If template agreement at the reference line count
drops below 0.95, the claim that Drain's templates are stable under reordering
fails and log10x has no business repeating it. If cluster_id agreement rises
above 0.01 at any line count, the claim that Drain's identifier is order-bound
fails and this exhibit is withdrawn. Both are asserted below.

Template agreement is a function of how much data each pass has seen, because a
template settles only once its siblings have arrived. Measured with this same
script, natural against shuffled, max_clusters=2000:

    python bench/identifier.py  5000   ->  template 0.8184   cluster_id 0.0002
    python bench/identifier.py 10000   ->  template 0.9038   cluster_id 0.0000
    python bench/identifier.py 30000   ->  template 0.9712   cluster_id 0.0000
    python bench/identifier.py 60000   ->  template 0.9860   cluster_id 0.0001

The 0.95 assert is therefore scoped to the 60,000-line reference run and is
skipped at other counts. The cluster_id assert holds everywhere.

Usage:  python bench/identifier.py [n_lines]        default 60000
"""

import pathlib
import random
import sys

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import data  # noqa: E402  the repo's downloader for the public release assets
import drainver  # noqa: E402  which distribution provides the drain3 module

SEED = 1
CAPS = (2000, 500)
REFERENCE_N = 60000

MASKING = [
    MaskingInstruction(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "UUID"),
    MaskingInstruction(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?", "TS"),
    MaskingInstruction(r"\b(\d{1,3}\.){3}\d{1,3}\b", "IP"),
    MaskingInstruction(r"\b[0-9a-fA-F]{16,}\b", "HEX"),
    MaskingInstruction(r"\b\d+\b", "NUM"),
]


def miner(max_clusters):
    c = TemplateMinerConfig()
    c.drain_depth = 6
    c.drain_sim_th = 0.6
    c.drain_max_children = 20
    c.drain_max_clusters = max_clusters
    c.masking_instructions = MASKING
    c.profiling_enabled = False
    return TemplateMiner(config=c)


def name_every_line(msgs, order, max_clusters):
    """Feed the lines in `order`; keep the name each line got as it went past."""
    tm = miner(max_clusters)
    named = {}
    for i in order:
        r = tm.add_log_message(msgs[i])
        named[i] = (r["cluster_id"], r["template_mined"])
    return named, len(tm.drain.clusters)


def main():
    if not __debug__:
        sys.exit("run this with asserts live (drop -O): the script checks its own claims")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
    path = data.ensure("otel-sample-200mb.log")
    msgs = [m[:1024] for m in data.iter_log_messages(path, limit=n)]
    n = len(msgs)

    natural = list(range(n))
    shuffled = list(range(n))
    random.Random(SEED).shuffle(shuffled)

    w = 78
    print("=" * w)
    print("IDENTIFIER: same lines, two arrival orders")
    print("=" * w)
    print(f"{drainver.label()}, depth=6 sim_th=0.6 "
          f"max_children=20, 1024-char cap")
    print("typed-token masking on, parametrize_numeric_tokens=True (Drain3 default)")
    print(f"source  {path.name}")
    print(f"lines   {n:,} application messages, the `log` field of each JSON record")
    print(f"orders  natural file order, and the same lines shuffled with seed {SEED}")
    print()
    print(f"{'max_clusters':>12} {'templates nat':>14} {'templates shuf':>15} "
          f"{'template agrees':>16} {'cluster_id agrees':>18}")

    results = {}
    for cap in CAPS:
        a, ca = name_every_line(msgs, natural, cap)
        b, cb = name_every_line(msgs, shuffled, cap)
        t_agree = sum(1 for i in range(n) if a[i][1] == b[i][1]) / n
        i_agree = sum(1 for i in range(n) if a[i][0] == b[i][0]) / n
        results[cap] = (t_agree, i_agree)
        print(f"{cap:>12} {ca:>14,} {cb:>15,} {t_agree:>16.4f} {i_agree:>18.4f}")

    for cap, (t_agree, i_agree) in results.items():
        assert i_agree < 0.01, f"cluster_id agreement rose at max_clusters={cap}: {i_agree}"
        if n == REFERENCE_N:
            assert t_agree > 0.95, \
                f"template agreement collapsed at max_clusters={cap}: {t_agree}"
    if n != REFERENCE_N:
        print(f"\nnote: the 0.95 template assert is scoped to the {REFERENCE_N:,}-line")
        print("reference run and was skipped here. Templates settle as volume arrives,")
        print("so agreement at a lower line count is genuinely lower. See the docstring.")

    t2000, i2000 = results[2000]
    print()
    print("=" * w)
    print(f"The template string agrees {t2000:.4f} of the time. The integer agrees "
          f"{i2000:.4f}.")
    print("=" * w)
    print("Drain's clustering is stable under reordering. The published shuffle result")
    print("reproduces here and stands. The identifier Drain returns alongside it is an")
    print("arrival counter, so it tracks discovery order instead of line content.")
    print()
    print("Cap pressure leaves the split intact. At max_clusters=500, with eviction live,")
    print(f"the template holds at {results[500][0]:.4f} and the integer falls further, to "
          f"{results[500][1]:.4f}.")
    print()
    print("So hashing the template is the correct repair, and it is the one log10x")
    print("recommends to anyone staying on Drain. What the hash cannot repair is the")
    print("template itself moving, which bench/replay.py shows in four lines, and the")
    print("frequency-dependent disagreement between two instances of Drain fed different")
    print("halves of one stream, which the split-instance benchmark in this repo measures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
