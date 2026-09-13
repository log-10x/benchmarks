#!/usr/bin/env python3
"""replay.py - template mutability inside one process.

One Drain3 instance. One cluster. Four lines, in order:

    1. a real log line, seen for the first time
    2. two sibling outputs of the same source statement
    3. the byte-identical first line again

The template string that names the first line, and its sha256, are different at
step 3 than they were at step 1. Drain reports ``change_type="none"`` on the
replay, because as far as Drain is concerned the line still belongs to the same
cluster it always did.

The instance is fed four lines in a fixed order and it renames one of them on
the way past. That is the whole exhibit: one process, one cluster, four lines.

Drain runs at its strongest honest configuration: typed-token masking enabled,
``parametrize_numeric_tokens`` at its Drain3 default of True. Masking still lets
this happen. The tokens that move are ``name=Jaeger`` and ``uid=webstore-traces``,
and a masking rule that normalized those would erase the identity of the
datasource being provisioned, which is the one thing the line is there to record.

Falsifier: if a future Drain3 leaves a first-sight template intact when siblings
arrive, or reports the rename to the caller, the asserts below fail and this
exhibit is withdrawn.

Usage:  python bench/replay.py
"""

import gzip
import hashlib
import json
import os
import pathlib
import sys

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drainver  # noqa: E402  which distribution provides the drain3 module

# Real lines from the public release asset otel-sample-200mb.log
# (github.com/log-10x/config, tag otel-sample-v1), file lines 1109-1111,
# container `grafana`. Grafana provisioning emits one of these per datasource.
SOURCE = "otel-sample-200mb.log lines 1109, 1110, 1111 (container grafana)"
PROBE = (
    'logger=provisioning.datasources t=2025-10-01T20:12:51.015068952Z level=info '
    'msg="inserting datasource from configuration" name=Jaeger uid=webstore-traces'
)
SIBLINGS = [
    'logger=provisioning.datasources t=2025-10-01T20:12:51.054230494Z level=info '
    'msg="inserting datasource from configuration" name=OpenSearch uid=webstore-logs',
    'logger=provisioning.datasources t=2025-10-01T20:12:51.103454394Z level=info '
    'msg="inserting datasource from configuration" name=Prometheus uid=webstore-metrics',
]

MASKING = [
    MaskingInstruction(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "UUID"),
    MaskingInstruction(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?", "TS"),
    MaskingInstruction(r"\b(\d{1,3}\.){3}\d{1,3}\b", "IP"),
    MaskingInstruction(r"\b[0-9a-fA-F]{16,}\b", "HEX"),
    MaskingInstruction(r"\b\d+\b", "NUM"),
]


def miner():
    """Drain3 at the configuration used for every number in this repo."""
    c = TemplateMinerConfig()
    c.drain_depth = 6
    c.drain_sim_th = 0.6
    c.drain_max_children = 20
    c.drain_max_clusters = 2000
    c.masking_instructions = MASKING
    c.profiling_enabled = False
    return TemplateMiner(config=c)


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- provenance
# The demonstration above needs no data file. This block is the audit trail:
# if a copy of the public sample is already cached, confirm the four lines are
# quoted verbatim from it. Nothing is downloaded here, so the exhibit stays
# instant and runs anywhere. `python bench/data.py` fetches the cache.

def cached_sample():
    root = pathlib.Path(__file__).resolve().parent.parent
    d = pathlib.Path(os.environ.get("PIB_DATA_DIR", str(root / "data")))
    for name in ("otel-sample-200mb.log.gz", "otel-sample-200mb.log"):
        p = d / name
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def check_provenance(wanted):
    path = cached_sample()
    if path is None:
        return ("provenance: sample not cached, embedded lines unchecked "
                "(run python bench/data.py)")
    opener = gzip.open if path.suffix == ".gz" else open
    found = set()
    with opener(path, "rt", errors="replace") as f:
        for line in f:
            try:
                m = json.loads(line).get("log", "")
            except ValueError:
                continue
            if m in wanted:
                found.add(m)
                if len(found) == len(wanted):
                    break
    assert len(found) == len(wanted), \
        f"embedded lines absent from {path}: {len(found)}/{len(wanted)} matched"
    return f"provenance: all {len(wanted)} lines quoted verbatim from {path.name}"


# ---------------------------------------------------------------------- run

def main():
    if not __debug__:
        sys.exit("run this with asserts live (drop -O): the script checks its own claims")
    wanted = {PROBE, *SIBLINGS}
    prov = check_provenance(wanted)

    tm = miner()
    feed = [PROBE, SIBLINGS[0], SIBLINGS[1], PROBE]
    steps = [tm.add_log_message(line[:1024]) for line in feed]

    before, after = steps[0], steps[3]
    b_tpl, a_tpl = before["template_mined"], after["template_mined"]

    # --- the conclusions, asserted so a Drain3 change breaks this loudly ---
    assert feed[0] == feed[3], "step 4 must be byte-identical to step 1"
    assert before["change_type"] == "cluster_created", before["change_type"]
    assert steps[1]["change_type"] == "cluster_template_changed", steps[1]["change_type"]
    assert after["change_type"] == "none", after["change_type"]
    assert all(s["cluster_id"] == 1 for s in steps), "all four lines are one cluster"
    assert all(s["cluster_count"] == 1 for s in steps), "one cluster exists throughout"
    assert b_tpl != a_tpl, "template must differ between first sight and replay"
    assert sha(b_tpl) != sha(a_tpl), "hash must differ between first sight and replay"
    assert "name=Jaeger" in b_tpl, "first-sight template names the datasource"
    assert "name=Jaeger" not in a_tpl, "replay template no longer names the datasource"

    ver = drainver.label()
    w = 78
    print("=" * w)
    print("REPLAY: one process, one cluster, four lines, fixed order")
    print("=" * w)
    print(f"{ver}, depth=6 sim_th=0.6 max_children=20 max_clusters=2000")
    print("typed-token masking on, parametrize_numeric_tokens=True (Drain3 default)")
    print(f"lines: {SOURCE}")
    print(prov)
    print()
    labels = ["1  first sight", "2  sibling    ", "3  sibling    ", "4  REPLAY of 1"]
    print(f"{'step':<16} {'change_type':<26} {'id':>3} {'size':>5} {'clusters':>9}")
    for lab, s in zip(labels, steps):
        print(f"{lab:<16} {s['change_type']:<26} {s['cluster_id']:>3} "
              f"{s['cluster_size']:>5} {s['cluster_count']:>9}")
    print()
    print("-" * w)
    print("BEFORE   step 1, the line on first sight")
    print("-" * w)
    print(f"  line      {PROBE}")
    print(f"  template  {b_tpl}")
    print(f"  sha256    {sha(b_tpl)}")
    print()
    print("-" * w)
    print("AFTER    step 4, the same bytes after two siblings arrived")
    print("-" * w)
    print(f"  line      {PROBE}")
    print(f"  template  {a_tpl}")
    print(f"  sha256    {sha(a_tpl)}")
    print()
    print("=" * w)
    print("The bytes are identical. The name is not.")
    print("=" * w)
    print("Drain reports change_type='none' on step 4, so a pipeline keying on the")
    print("template, or on a hash of it, writes two different names for one line while")
    print("being told the cluster held steady. An alert, dashboard, budget or join built")
    print("on the step-1 name matches zero events from step 2 onward, and a query that")
    print("matches zero events returns a number rather than an error.")
    print()
    print("Mechanism, from drain3/drain.py: create_template(seq1, seq2) returns")
    print("[token2 if token1 == token2 else param_str ...] and writes the result back to")
    print("the cluster. A template is the running intersection of every line that ever")
    print("matched it, so it can only lose literal tokens, and it loses them whenever a")
    print("sibling arrives. Sibling arrival order is a property of the stream.")
    print()
    print("Scope: this is one statement family in one process. How often two processes")
    print("end up on different names is measured by the split-instance benchmark in this")
    print("repo; the identifier consequence is measured in bench/identifier.py. Drain's")
    print("templates are good. What moves is the moment at which each one settles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
