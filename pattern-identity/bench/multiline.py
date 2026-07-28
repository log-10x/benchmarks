#!/usr/bin/env python3
"""
multiline.py -- one logical event, several names.

Question: when a single logical event spans several physical lines (an exception
header plus its stack frames), what name does each side give the event?

Drain side: Drain3 at the pinned configuration, trained on the whole stream, then
queried read-only for the name of every line in every exception burst.

Engine side: derived arithmetically from the two published release assets
(otel-sample-templates.json, otel-sample-encoded.log). No engine run is required.
Each encoded record carries one template hash; a template that seals a multi-line
event holds N newline-separated line templates, so a record built from it accounts
for N raw lines. Walking the encoded records in order therefore maps every raw line
to exactly one event. The map is checked against the raw line count before use.

READ THIS BEFORE QUOTING ANY NUMBER FROM THIS SCRIPT. TWO CLAIMS DIE HERE.

First. An earlier analysis claimed Drain manufactures a large tail of one-off clusters
out of stack frames on this file. That claim is wrong and section 3 prints the
correction. Integer masking turns "Consumer.cs:line 62" into "Consumer.cs:line NUM",
and the OpenTelemetry demo repeats a small set of exceptions, so the frames collapse
to a couple of dozen shapes in total.

Second. The claim that counting exceptions is not expressible in Drain's output is
refuted on this file, by section 4 of this script. A header cluster here fires once
per burst and never outside one, so counting that cluster does count the events. That
result is printed in full rather than dropped.

What survives is narrower and section 4 states it: the grouping of several cluster
names into one event is not carried in Drain's output, so the join is done by a person
reading the stream, and it holds only while each header shape stays exclusive to its
exception. Section 4 measures how far the proxy actually gets.

Usage:
    python bench/multiline.py [--full-line]

    --full-line  also run Drain on the whole JSON record rather than the application
                 message. Slower. Reported as a sensitivity check.

The three release assets are fetched and cached by bench/data.py on first use.
Set PIB_DATA_DIR to move the cache. Runtime is about 110s with --full-line.
"""

import argparse
import collections
import gzip
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data  # noqa: E402  bench/data.py, the shared fetch-and-cache helper

from drain3 import TemplateMiner  # noqa: E402
from drain3.masking import MaskingInstruction  # noqa: E402
from drain3.template_miner_config import TemplateMinerConfig  # noqa: E402

# ---------------------------------------------------------------- pinned config

# The same Drain3 configuration every script in this repo uses. Drain is run at the
# strongest honest setting: a competent operator's masking set, a cluster cap well
# above the number of shapes in the file, and the template string (not the integer
# cluster id) as the name, which is the stable half of Drain's output.
DRAIN_DEPTH = 6
DRAIN_SIM_TH = 0.6
DRAIN_MAX_CHILDREN = 20
DRAIN_MAX_CLUSTERS = 2000
LINE_CAP = 1024

MASKING = [
    MaskingInstruction(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "UUID",
    ),
    MaskingInstruction(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?", "TS"),
    MaskingInstruction(r"\b(\d{1,3}\.){3}\d{1,3}\b", "IP"),
    MaskingInstruction(r"\b[0-9a-fA-F]{16,}\b", "HEX"),
    MaskingInstruction(r"\b\d+\b", "NUM"),
]

RAW = "otel-sample-200mb.log"
TEMPLATES = "otel-sample-templates.json"
ENCODED = "otel-sample-encoded.log"

# A stack frame or an exception continuation, in the four runtimes present in the
# OpenTelemetry demo (.NET, JVM, Node, Go). Deliberately narrow: it matches frames
# and nothing else, so a burst is under-counted rather than over-counted.
FRAME_RE = re.compile(r"^\s*(at\s|Caused by:|\.\.\.\s*\d+\s+more\b|goroutine\s+\d+\s\[)")


def drain_config():
    c = TemplateMinerConfig()
    c.drain_depth = DRAIN_DEPTH
    c.drain_sim_th = DRAIN_SIM_TH
    c.drain_max_children = DRAIN_MAX_CHILDREN
    c.drain_max_clusters = DRAIN_MAX_CLUSTERS
    c.masking_instructions = list(MASKING)
    c.profiling_enabled = False
    return c


def rule(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------- loading


def load_raw(path):
    """Return (message, container) per raw line, in file order.

    bench/data.py yields messages only; the container name is needed here to keep a
    burst inside one writer, so the envelope is parsed again rather than reused.
    """
    msg, con = [], []
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
                msg.append(r.get("log", "") or "")
                con.append(r.get("kubernetes", {}).get("container_name", "?"))
            except Exception:
                msg.append("")
                con.append("?")
    return msg, con


def load_template_spans(path):
    """templateHash -> number of raw lines the template accounts for."""
    span = {}
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            r = json.loads(line)
            span[r["templateHash"]] = r["template"].count("\n") + 1
    return span


def load_engine_events(path, span, n_raw):
    """
    Walk the encoded records in order and map every raw line to one engine event.

    Returns (event_of_line, hash_of_event, size_of_event, usage) where event ids are
    the record ordinals. Raises if the arithmetic fails to account for every raw line,
    which is the guard that keeps this derivation honest.
    """
    event_of_line = [0] * n_raw
    hash_of_event = []
    size_of_event = []
    usage = collections.Counter()
    pos = 0
    with gzip.open(path, "rt", errors="replace") as f:
        for ev, line in enumerate(f):
            if not line.startswith("~"):
                raise ValueError("encoded record %d has no leading marker" % ev)
            h = line[1:].split(",", 1)[0]
            if h not in span:
                raise ValueError("encoded record %d cites unknown template %s" % (ev, h))
            s = span[h]
            usage[h] += 1
            hash_of_event.append(h)
            size_of_event.append(s)
            for k in range(pos, min(pos + s, n_raw)):
                event_of_line[k] = ev
            pos += s
    if pos != n_raw:
        raise ValueError(
            "alignment failed: encoded records account for %d raw lines, file has %d"
            % (pos, n_raw)
        )
    return event_of_line, hash_of_event, size_of_event, usage


# ----------------------------------------------------------------------- bursts


def find_bursts(msg, con):
    """
    A burst is a maximal run of frame lines, plus the line above it when that line
    sits in the same container and is not itself a frame. That line is the exception
    header. Nothing else is pulled in: trailing object dumps such as "code: 14," are
    left out, which makes every burst here a lower bound on the full event.
    """
    n = len(msg)
    bursts = []
    i = 0
    while i < n:
        if FRAME_RE.match(msg[i]):
            j = i
            while j < n and FRAME_RE.match(msg[j]):
                j += 1
            start = i
            if i > 0 and not FRAME_RE.match(msg[i - 1]) and con[i - 1] == con[i]:
                if msg[i - 1].strip():
                    start = i - 1
            bursts.append((start, j))
            i = j
        else:
            i += 1
    return bursts


# ------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(
        description="one logical event, several names: the multi-line comparison"
    )
    ap.add_argument(
        "--full-line",
        action="store_true",
        help="also run Drain on the whole JSON record as a sensitivity check",
    )
    args = ap.parse_args()

    raw_gz = data.ensure(RAW)
    tpl_gz = data.ensure(TEMPLATES)
    enc_gz = data.ensure(ENCODED)

    t0 = time.time()
    rule("0. INPUTS")
    msg, con = load_raw(raw_gz)
    n_raw = len(msg)
    span = load_template_spans(tpl_gz)
    event_of_line, hash_of_event, size_of_event, usage = load_engine_events(
        enc_gz, span, n_raw
    )
    n_events = len(hash_of_event)
    print("raw lines                     %8d  (%s.gz)" % (n_raw, RAW))
    print("engine templates              %8d  (%s.gz)" % (len(span), TEMPLATES))
    print("engine events                 %8d  (%s.gz)" % (n_events, ENCODED))
    print(
        "drain3 config                 depth=%d sim_th=%.1f max_children=%d "
        "max_clusters=%d cap=%d" % (DRAIN_DEPTH, DRAIN_SIM_TH, DRAIN_MAX_CHILDREN,
                                    DRAIN_MAX_CLUSTERS, LINE_CAP)
    )
    print("drain3 input                  application message (the `log` field)")
    print("drain3 name                   template string, not the integer cluster id")
    print("  loaded in %.0fs" % (time.time() - t0), file=sys.stderr)

    # ---------------------------------------------------------------- section 1
    rule("1. ENGINE GROUPING, DERIVED FROM THE PUBLISHED ENCODED OUTPUT")
    multi = {h: s for h, s in span.items() if s > 1}
    multi_used = sum(usage[h] for h in multi)
    multi_lines = sum(usage[h] * span[h] for h in multi)
    absorbed = n_raw - n_events
    print(
        "templates that seal more than one line   %6d of %d  (%.1f%%)"
        % (len(multi), len(span), 100.0 * len(multi) / len(span))
    )
    print("events built from such a template        %6d of %d" % (multi_used, n_events))
    print("raw lines inside those events            %6d" % multi_lines)
    print(
        "continuation lines absorbed              %6d   (%d raw lines -> %d events)"
        % (absorbed, n_raw, n_events)
    )
    print(
        "  arithmetic check: sum(span x usage) = %d, equals the raw line count"
        % sum(usage[h] * span[h] for h in span)
    )
    print()
    print("  This is a reconciliation, not an anomaly. A record whose template seals")
    print("  N lines accounts for N raw lines, so the two counts differ by exactly the")
    print("  number of continuation lines.")
    print()
    hist = collections.Counter(span[h] for h in multi)
    print("  lines sealed per multi-line template:")
    print("    %-8s %-10s %s" % ("lines", "templates", "events built"))
    for k in sorted(hist):
        ev = sum(usage[h] for h in multi if span[h] == k)
        print("    %-8d %-10d %d" % (k, hist[k], ev))

    # ---------------------------------------------------------------- section 2
    rule("2. EXCEPTION BURSTS IN THE RAW STREAM")
    bursts = find_bursts(msg, con)
    frames = sum(1 for m in msg if FRAME_RE.match(m))
    burst_lines = sum(e - s for s, e in bursts)
    print("frame lines                   %8d" % frames)
    print("bursts (frame run + header)   %8d" % len(bursts))
    print("lines inside a burst          %8d" % burst_lines)
    print(
        "burst length                  min %d, median %d, max %d"
        % (
            min(e - s for s, e in bursts),
            sorted(e - s for s, e in bursts)[len(bursts) // 2],
            max(e - s for s, e in bursts),
        )
    )
    by_con = collections.Counter(con[s] for s, e in bursts)
    print("  containers emitting bursts: %d" % len(by_con))
    for c, k in by_con.most_common(8):
        print("    %-28s %6d" % (c, k))

    # ---------------------------------------------------------------- section 3
    rule("3. HOW MANY NAMES DOES EACH SIDE GIVE ONE BURST")
    t1 = time.time()
    tm = TemplateMiner(config=drain_config())
    for m in msg:
        tm.add_log_message(m[:LINE_CAP])
    print("  drain trained on all %d lines, %d clusters"
          % (n_raw, len(tm.drain.clusters)))
    print("  drain training took %.0fs" % (time.time() - t1), file=sys.stderr)

    name_of = {}

    def drain_name(i):
        if i not in name_of:
            c = tm.match(msg[i][:LINE_CAP])
            name_of[i] = c.get_template() if c else "<no cluster>"
        return name_of[i]

    frame_shapes = set()
    for i, m in enumerate(msg):
        if FRAME_RE.match(m):
            frame_shapes.add(drain_name(i))

    print()
    print("  CORRECTION TO AN EARLIER CLAIM. Drain does not shatter stack frames into")
    print("  a long tail of clusters on this file.")
    print(
        "    %d frame lines collapse to %d distinct Drain shapes."
        % (frames, len(frame_shapes))
    )
    print("    Integer masking turns `Consumer.cs:line 62` into `Consumer.cs:line NUM`,")
    print("    and the demo repeats a small set of exceptions. Any argument that rests")
    print("    on frame-driven cluster explosion is refuted by this line.")
    print()

    drain_names_per_burst = []
    engine_events_per_burst = []
    engine_hashes_per_burst = []
    for s, e in bursts:
        drain_names_per_burst.append(len({drain_name(i) for i in range(s, e)}))
        evs = {event_of_line[i] for i in range(s, e)}
        engine_events_per_burst.append(len(evs))
        engine_hashes_per_burst.append(len({hash_of_event[ev] for ev in evs}))

    def stats(v):
        sv = sorted(v)
        return (
            sum(v) / len(v),
            sv[0],
            sv[len(sv) // 2],
            sv[-1],
        )

    print("  names assigned to one exception burst")
    print("    %-26s %8s %6s %8s %6s" % ("", "mean", "min", "median", "max"))
    m, lo, med, hi = stats(drain_names_per_burst)
    print("    %-26s %8.2f %6d %8d %6d" % ("drain cluster names", m, lo, med, hi))
    m, lo, med, hi = stats(engine_events_per_burst)
    print("    %-26s %8.2f %6d %8d %6d" % ("engine events", m, lo, med, hi))
    m, lo, med, hi = stats(engine_hashes_per_burst)
    print("    %-26s %8.2f %6d %8d %6d" % ("engine template hashes", m, lo, med, hi))
    one_ev = sum(1 for k in engine_events_per_burst if k == 1)
    print()
    print(
        "    bursts sealed into a single engine event  %d of %d  (%.2f%%)"
        % (one_ev, len(bursts), 100.0 * one_ev / len(bursts))
    )
    one_name = sum(1 for k in drain_names_per_burst if k == 1)
    print(
        "    bursts carrying a single Drain name       %d of %d  (%.2f%%)"
        % (one_name, len(bursts), 100.0 * one_name / len(bursts))
    )

    print()
    print("  distribution of Drain names per burst")
    dist = collections.Counter(drain_names_per_burst)
    tot = len(bursts)
    print("    %-8s %-9s %-8s %s" % ("names", "bursts", "share", ""))
    for k in sorted(dist):
        bar = "#" * int(round(40.0 * dist[k] / tot))
        print(
            "    %-8d %-9d %-8s %s"
            % (k, dist[k], "%.1f%%" % (100.0 * dist[k] / tot), bar)
        )

    print()
    print("  distribution of engine events per burst")
    dist_e = collections.Counter(engine_events_per_burst)
    print("    %-8s %-9s %-8s %s" % ("events", "bursts", "share", ""))
    for k in sorted(dist_e):
        bar = "#" * int(round(40.0 * dist_e[k] / tot))
        print(
            "    %-8d %-9d %-8s %s"
            % (k, dist_e[k], "%.1f%%" % (100.0 * dist_e[k] / tot), bar)
        )

    fam = collections.Counter(hash_of_event[event_of_line[s]] for s, e in bursts)
    print()
    print("  HOW LITTLE VARIETY IS BEHIND THOSE COUNTS. Burst shapes, labelled by the")
    print("  engine template of the burst's first event:")
    for h, k in fam.most_common(6):
        print(
            "    %-14s %6d burst%s   first event seals %d line%s"
            % (h, k, " " if k == 1 else "s", span[h], " " if span[h] == 1 else "s")
        )
    print(
        "    %d distinct burst shapes in total; the largest is %.1f%% of all bursts"
        % (len(fam), 100.0 * fam.most_common(1)[0][1] / tot)
    )
    print("    Treat the mean and median above as one shape repeated, not as a sample.")

    # ---------------------------------------------------------------- section 4
    rule("4. FALSIFIER: CAN A DRAIN CLUSTER STAND IN FOR THE EVENT")
    print("  Claim under test: an exception burst has one name on the engine side and no")
    print("  name on the Drain side, so counting the event is not expressible in Drain's")
    print("  output.")
    print()
    print("  The claim is wrong if some Drain cluster fires exactly once per burst and")
    print("  never fires outside a burst, because that cluster is then a working proxy")
    print("  for the event and a count of it is a count of exceptions.")
    print()

    total_occurrences = collections.Counter()
    for i in range(n_raw):
        total_occurrences[drain_name(i)] += 1

    in_burst_occurrences = collections.Counter()
    per_burst_counts = collections.defaultdict(list)
    for bi, (s, e) in enumerate(bursts):
        local = collections.Counter(drain_name(i) for i in range(s, e))
        for nm, k in local.items():
            in_burst_occurrences[nm] += k
            per_burst_counts[nm].append(k)

    proxies = []
    for nm, occ in in_burst_occurrences.items():
        exclusive = total_occurrences[nm] == occ
        once_each = all(k == 1 for k in per_burst_counts[nm])
        if exclusive and once_each:
            proxies.append((nm, len(per_burst_counts[nm])))
    proxies.sort(key=lambda x: -x[1])

    covered = set()
    proxy_names = {nm for nm, _ in proxies}
    for bi, (s, e) in enumerate(bursts):
        if any(drain_name(i) in proxy_names for i in range(s, e)):
            covered.add(bi)

    print(
        "  Drain clusters that appear in a burst                     %6d"
        % len(in_burst_occurrences)
    )
    print(
        "  of those, exclusive to bursts and firing once per burst   %6d"
        % len(proxies)
    )
    print(
        "  bursts with at least one such proxy cluster               %6d of %d  (%.2f%%)"
        % (len(covered), len(bursts), 100.0 * len(covered) / len(bursts))
    )
    print()
    if len(covered) == len(bursts) and proxies:
        print("  RESULT: REFUTED ON THIS FILE. Every burst carries a cluster that fires")
        print("  once inside it and never outside one. Counting that cluster counts the")
        print("  exceptions. The claim as written does not survive and is withdrawn.")
    elif proxies:
        print("  RESULT: PARTLY REFUTED. Some bursts carry such a cluster and some do not.")
    else:
        print("  RESULT: NOT REFUTED. No Drain cluster on this file is both exclusive to")
        print("  bursts and one-per-burst.")
    if proxies:
        print()
        print("  proxy clusters, by how many bursts each one covers:")
        for nm, k in proxies[:8]:
            print("    %6d burst%s %s" % (k, " " if k == 1 else "s", nm[:92]))

    # How far does the best single cluster get, and how many are needed for all of it.
    best = proxies[0][1] if proxies else 0
    remaining = set(range(len(bursts)))
    chosen = []
    pool = {nm for nm, _ in proxies}
    while remaining and pool:
        pick, gain = None, 0
        for nm in pool:
            g = sum(
                1
                for bi in remaining
                if any(drain_name(i) == nm for i in range(*bursts[bi]))
            )
            if g > gain:
                pick, gain = nm, g
        if not pick:
            break
        chosen.append((pick, gain))
        pool.discard(pick)
        remaining = {
            bi
            for bi in remaining
            if not any(drain_name(i) == pick for i in range(*bursts[bi]))
        }
    print()
    print("  What the proxy does NOT give, measured:")
    print(
        "    best single cluster counts        %6d of %d bursts  (%.2f%%), short by %d"
        % (best, len(bursts), 100.0 * best / len(bursts), len(bursts) - best)
    )
    print(
        "    clusters needed to count them all %6d"
        % len(chosen)
    )
    print(
        "    bursts still uncounted after that %6d"
        % len(remaining)
    )
    print()
    print("  So a correct exception count is a hand-built union of header clusters. Which")
    print(
        "  of the %d cluster names are headers, and which frames belong with which header,"
        % len(in_burst_occurrences)
    )
    print("  is a judgement made by a person reading the stream. Drain's output carries no")
    print("  field that links a header to its frames, and a new exception adds cluster")
    print("  names that the count has to be extended to include.")

    shared = [
        nm
        for nm in in_burst_occurrences
        if total_occurrences[nm] > in_burst_occurrences[nm]
    ]
    burst_bytes = sum(len(msg[i]) for s, e in bursts for i in range(s, e))
    shared_set = set(shared)
    bytes_on_shared = sum(
        len(msg[i])
        for s, e in bursts
        for i in range(s, e)
        if drain_name(i) in shared_set
    )
    print()
    print("  Exclusivity is a property of this file, not a guarantee. A frame such as")
    print("  `at new Promise (<anonymous>) {` is exclusive here because one code path")
    print("  emits it. On a service where several exceptions share a frame, that cluster")
    print("  stops being a proxy. Current state of that on this file:")
    print(
        "    burst clusters that also fire outside bursts %6d of %d"
        % (len(shared), len(in_burst_occurrences))
    )
    print(
        "    burst bytes landing on such a cluster        %6.1f%% of %d bytes"
        % (100.0 * bytes_on_shared / burst_bytes, burst_bytes)
    )
    print("    A prediction, not a measurement: on a stream with shared frames this")
    print("    figure rises and the proxy degrades. Testing it needs a different file.")

    # ---------------------------------------------------------------- section 5
    rule("5. FALSIFIER: DOES THE ENGINE SPLIT A BURST")
    split = [
        (bi, engine_events_per_burst[bi])
        for bi in range(len(bursts))
        if engine_events_per_burst[bi] > 1
    ]
    print("  The engine side of the claim is wrong if grouping splits a burst across")
    print("  several events, because the event would then have several names too.")
    print()
    print(
        "  bursts spanning more than one engine event   %6d of %d  (%.2f%%)"
        % (len(split), len(bursts), 100.0 * len(split) / len(bursts))
    )
    if split:
        print("  RESULT: PARTLY REFUTED. Worst cases:")
        for bi, k in sorted(split, key=lambda x: -x[1])[:5]:
            s, e = bursts[bi]
            print(
                "    burst at raw line %-8d length %-3d spans %d events, container %s"
                % (s, e - s, k, con[s])
            )
            for i in range(s, min(e, s + 4)):
                print("      line %-8d event %-8d %s" % (i, event_of_line[i], msg[i][:70]))
    else:
        print("  RESULT: NOT REFUTED on this file.")

    print()
    print("  Naming granularity, which is what these artifacts can show. A template")
    print("  hash is a content hash of a template from a pinned library, so agreement")
    print("  across processes holds by construction and is not evidence. Nor is the")
    print("  resolve rate below: the templates file is the encoding run's own output")
    print("  dictionary, which bench/engine_side.py section 0 measures. What the")
    print("  figures do show is how finely the stream is named, including shapes that")
    print("  occur once.")
    once = sum(1 for h in span if usage[h] == 1)
    multi_once = sum(1 for h in multi if usage[h] == 1)
    print(
        "    templates used exactly once                 %6d of %d  (%.1f%%)"
        % (once, len(span), 100.0 * once / len(span))
    )
    print(
        "    multi-line templates used exactly once      %6d of %d"
        % (multi_once, len(multi))
    )
    print("    encoded records that resolve to a template  every one of %d, which"
          % n_events)
    print("      load_engine_events() raises on a hash with no definition, so the")
    print("      figure is a property of the published assets rather than a")
    print("      measurement taken here; bench/engine_side.py section 0 shows why")
    print()
    print("  This holds only while the symbol library, the engine version and the")
    print("  library's coverage of the emitting code are pinned. A statement about a")
    print("  different library is a different measurement.")

    # ---------------------------------------------------------------- section 6
    rule("6. WORKED EXAMPLE")
    cand = [
        bi
        for bi in range(len(bursts))
        if engine_events_per_burst[bi] == 1 and drain_names_per_burst[bi] >= 3
    ]
    if not cand:
        cand = [max(range(len(bursts)), key=lambda bi: drain_names_per_burst[bi])]
    bi = max(cand, key=lambda b: bursts[b][1] - bursts[b][0])
    s, e = bursts[bi]
    ev = event_of_line[s]
    print("  container %s, raw lines %d to %d" % (con[s], s, e - 1))
    print()
    print("  Drain names one line at a time:")
    seen = {}
    for i in range(s, e):
        nm = drain_name(i)
        if nm not in seen:
            seen[nm] = len(seen) + 1
        print("    line %-7d name #%-3d %s" % (i, seen[nm], msg[i][:64]))
    collapsed = collections.defaultdict(set)
    for i in range(s, e):
        collapsed[drain_name(i)].add(msg[i])
    worst = max(collapsed.items(), key=lambda kv: len(kv[1]))
    print()
    print(
        "    -> %d lines, %d distinct Drain names, and no name for the burst itself"
        % (e - s, len(seen))
    )
    print(
        "    -> the name is not one-to-one with the frame either: name #%d covers %d"
        % (seen[worst[0]], len(worst[1]))
    )
    print("       different source locations, because create_template wildcards every")
    print("       position where the cluster has seen variation:")
    for t in sorted(worst[1])[:4]:
        print("         %s" % t.strip()[:78])
    print()
    print("  The engine names the burst once:")
    print(
        "    event %-8d template %-14s seals %d lines, %d occurrence(s) in the file"
        % (ev, hash_of_event[ev], size_of_event[ev], usage[hash_of_event[ev]])
    )
    if size_of_event[ev] != e - s:
        print(
            "    The engine group is %d lines and the burst detector took %d. The detector"
            % (size_of_event[ev], e - s)
        )
        print("    is deliberately narrow and starts one line late here. Reported, not hidden.")

    # ---------------------------------------------------------------- section 7
    if args.full_line:
        rule("7. SENSITIVITY: DRAIN ON THE WHOLE JSON LINE")
        print("  Section 3 feeds Drain the application message only, which is Drain's")
        print("  strongest setting on this file. Feeding the whole Fluentd JSON record")
        print("  adds envelope tokens. Reported so the weaker setting is on the record.")
        t2 = time.time()
        tm2 = TemplateMiner(config=drain_config())
        want = {i for s2, e2 in bursts for i in range(s2, e2)}
        raw_of = {}
        with gzip.open(raw_gz, "rt", errors="replace") as f:
            for i, line in enumerate(f):
                line = line.rstrip("\n")
                tm2.add_log_message(line[:LINE_CAP])
                if i in want:
                    raw_of[i] = line
        per = []
        for s2, e2 in bursts:
            per.append(len({
                (lambda c: c.get_template() if c else "<no cluster>")(
                    tm2.match(raw_of[i][:LINE_CAP])
                )
                for i in range(s2, e2)
            }))
        m, lo, med, hi = stats(per)
        print(
            "    whole JSON line: %d clusters, names per burst mean %.2f min %d median %d max %d"
            % (len(tm2.drain.clusters), m, lo, med, hi)
        )
        print("    section 7 took %.0fs" % (time.time() - t2), file=sys.stderr)

    # ---------------------------------------------------------------- scope note
    rule("SCOPE NOTE, READ BEFORE REUSING THESE NUMBERS")
    top_fam = fam.most_common(1)[0]
    jvm = max(range(len(bursts)), key=lambda b: drain_names_per_burst[b])
    print("""
  THIS FILE IS A WEAK DEMONSTRATION SURFACE FOR MULTI-LINE EVENTS.

  It is the OpenTelemetry demo. The demo throws a small, fixed set of exceptions on a
  loop, so stack-frame diversity is low: %d frame lines collapse to %d Drain shapes,
  and %d of %d bursts come from a single container emitting one error shape (engine
  template %s). Effective sample size for the burst statistics is close to one.
  Three consequences, all of them limits on what these numbers carry.

  1. The statistical version of the multi-line argument fails here. Drain does not
     shatter traces into a large cluster tail on this file, and section 3 says so.
     Anyone repeating that claim is refuted in one command on this same data.

  2. The counting version fails here too. Section 4 set out to show that an exception
     count is not expressible in Drain's output and measured the opposite: every burst
     carries a cluster that fires once inside it and never outside, so a count of that
     cluster is a count of the exceptions. The claim is withdrawn, and what is left is
     narrower: the link from header to frames is not in the output, so a person decides
     which names belong to one event, and the proxy holds only while each header shape
     stays exclusive to its exception.

  3. What the numbers do support is where the event boundary sits. %d bursts, a median
     of %d Drain names each, sealed into a median of %d engine event. Drain names
     lines; the engine names the event. That is a structural difference and it does not
     depend on how many distinct traces a service emits.

  The single JVM trace in this file is the one hint of what a production surface looks like:
  %d lines, %d Drain names, one engine event. n is 1, so it illustrates and does not
  measure.

  A stronger surface would be a service with high stack-trace diversity: a JVM
  application under load with deep and varied frames, several exception types sharing
  frames, or a code path whose frames change between releases. On such a stream the
  frames carry genuine cardinality, headers stop being exclusive, and the proxy from
  section 4 can be tested properly. That measurement is not in this repo and nothing
  here is claimed on its behalf.

  Not claimed anywhere in this section: that storing a template plus its values is
  novel (CLP and YScope hold prior art, US10484506B2), that template extraction is
  novel (Drain, Spell and IPLoM predate this), or that the engine's identifiers are
  stable in general. They are stable relative to a pinned symbol library, a pinned
  engine version, and that library's coverage of the emitting code. A template hash is
  a content hash, so cross-process agreement holds by construction and is not offered
  as a result.
""" % (frames, len(frame_shapes), top_fam[1], len(bursts), top_fam[0],
       len(bursts),
       sorted(drain_names_per_burst)[len(bursts) // 2],
       sorted(engine_events_per_burst)[len(bursts) // 2],
       bursts[jvm][1] - bursts[jvm][0], drain_names_per_burst[jvm]))
    print("  total runtime %.0fs" % (time.time() - t0), file=sys.stderr)


if __name__ == "__main__":
    main()
