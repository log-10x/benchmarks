#!/usr/bin/env python3
"""
engine_side.py -- the engine's half, from published artifacts only.

This script reads the two published release assets and nothing else:

    otel-sample-templates.json   engine templates, JSONL
    otel-sample-encoded.log      engine-encoded events

The engine is never run here.

READ THIS BEFORE QUOTING ANY NUMBER FROM THIS SCRIPT.

1. The two assets are co-generated. Section 0 measures it: every hash the
   encoded file references has a definition, every definition is referenced, and
   the two counts are equal. The templates file is the dictionary the encoding
   run wrote for its own output. So "every encoded record resolves" is a
   consistency check between two artifacts from one run. It is reported as a
   gate, not as a falsifier, because it cannot fail unless the published assets
   are mismatched, and a check that cannot fail is not evidence.

2. How the symbol library behind those templates was produced, and whether it
   was compiled with sight of this stream, is not disclosed in the release
   assets. Nothing in this repository establishes it. Any reading of section 1
   as "the library covers unseen statements" is unsupported, and the held-out
   experiment that would support it needs the engine and is listed as future
   work.

3. This script presents no order-invariance result. Feeding the engine two
   halves of a stream and observing that a content hash of a template drawn from
   a pinned symbol library comes out identical is true by construction, not a
   measurement. log10x retired a published post for reporting that tautology and
   this benchmark does not repeat it.

What is left is measurable and is what the sections below report: how finely the
engine names this stream, how much literal text from the emitting statement each
name carries, and whether either degrades as a shape gets rarer.

TESTS THAT CAN FIRE, with thresholds fixed here before the run:

  F-anchor   If the share of templates whose MESSAGE BODY carries no
             alphanumeric literal exceeded ANCHOR_FLOOR in any frequency
             bucket, the name would be a label over a wildcard for a material
             share of the stream and the comparison against Drain would be
             unfair in log10x's favour. Section 2 and section 3 measure it, on
             the message body alone, because envelope literals are deployment
             values rather than source text.

  F-degrade  If rare templates degraded toward wildcards, the naming would be
             frequency-dependent after all. Section 3 compares the median count
             of alphanumeric literal tokens in the message body for templates
             used once against templates used over a thousand times.
             Below DEGRADE_RATIO of it, the claim dies.

CONSISTENCY GATES, which are checks on the published artifacts rather than
tests of the system:

  C1  every referenced template hash resolves (section 1)
  C2  events plus continuation lines equals the raw line count of the third
      published asset (section 4). This one ties the encoded asset to the raw
      asset non-trivially, since it depends on every template's line span.

Usage:
    python bench/engine_side.py [--data-dir DIR] [--no-verify-raw] [--out PATH]
"""

import argparse
import collections
import gzip
import json
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import data  # noqa: E402  bench/data.py, the shared download cache

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# The engine writes a variable slot as a bare `$` inside the template text.
VAR_MARKER = "$"

# Literal tokenisation, stated explicitly because the ratio it produces depends on
# it. Literal text is split on the variable marker and on the whitespace and JSON
# structural characters that delimit fields in these records. Every piece that
# survives is a literal the template pins down.
LITERAL_SPLIT = re.compile(r'[\s,:"{}\[\]/$]+')

# Each template covers a whole Fluentd/Kubernetes record: a `log` field holding
# the application message, wrapped in an envelope of container, image, pod and
# label values. The two are measured separately. Envelope literals are values of
# the deployment, so they anchor a name to this cluster rather than to the
# emitting statement, and a redeploy that changes an image tag or a pod hash
# changes them.
BODY_RE = re.compile(r'"log":"(.*)","docker":', re.S)

# Environment residue: a digit welded to a variable slot, which is what an
# image tag, a registry host or a pod-name fragment leaves behind after the
# variable parts are replaced. `demo:$.$.$-$7` and `$3.io` are the shapes.
RESIDUE_RE = re.compile(r"\$[0-9]|[0-9]\$")

# Thresholds, fixed before the run.
ANCHOR_FLOOR = 0.05     # share of a bucket allowed to carry no alphanumeric body literal
DEGRADE_RATIO = 0.50    # used-once median against over-1,000 median

# Frequency buckets, matched to the Drain side so the two tables line up.
BUCKETS = [
    ("used once", lambda c: c == 1),
    ("2 to 10", lambda c: 2 <= c <= 10),
    ("11 to 100", lambda c: 11 <= c <= 100),
    ("101 to 1,000", lambda c: 101 <= c <= 1000),
    ("over 1,000", lambda c: c > 1000),
]


def load_templates(path):
    """Return {templateHash: template text} from the JSONL templates asset."""
    out = {}
    dupes = 0
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            h = rec["templateHash"]
            if h in out:
                dupes += 1
            out[h] = rec["template"]
    return out, dupes


def iter_encoded(path):
    """Yield the template hash of each encoded record.

    A record is `~<templateHash>,<value>,<value>,...`. No template hash in the
    published file contains a comma, which the caller verifies, so splitting on
    the first comma recovers the hash exactly.
    """
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if not line.startswith("~"):
                yield None, line
                continue
            yield line[1:].split(",", 1)[0], None


def count_lines_gz(path):
    """Count lines of a gzipped asset by streaming, so the plain text never lands."""
    n = 0
    with gzip.open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def literal_tokens(template):
    return [p for p in LITERAL_SPLIT.split(template) if p]


def alnum_literals(template):
    return [p for p in literal_tokens(template) if any(ch.isalnum() for ch in p)]


def split_record(template):
    """Return (message body, envelope) for one template.

    The body is the `log` field. The envelope is everything else, recovered by
    removing the body from the record so no literal is counted twice.
    """
    m = BODY_RE.search(template)
    if not m:
        return None, template
    body = m.group(1)
    envelope = template[:m.start(1)] + template[m.end(1):]
    return body, envelope


def measure(args):
    st = {}

    tmpl_path = data.ensure("otel-sample-templates.json")
    enc_path = data.ensure("otel-sample-encoded.log")

    templates, dupes = load_templates(tmpl_path)
    st["n_templates"] = len(templates)
    st["duplicate_hashes"] = dupes
    st["hashes_with_comma"] = sum(1 for h in templates if "," in h)

    bodies = {}
    envelopes = {}
    body_extract_failures = 0
    for h, t in templates.items():
        b, e = split_record(t)
        if b is None:
            body_extract_failures += 1
            b = ""
        bodies[h] = b
        envelopes[h] = e
    st["body_extract_failures"] = body_extract_failures

    # ---- 1. resolution, and the provenance that bounds it ------------------
    used = collections.Counter()
    n_events = 0
    n_unresolved = 0
    n_malformed = 0
    unresolved_hashes = collections.Counter()
    for h, bad in iter_encoded(enc_path):
        if bad is not None:
            n_malformed += 1
            continue
        n_events += 1
        used[h] += 1
        if h not in templates:
            n_unresolved += 1
            unresolved_hashes[h] += 1
    st["n_events"] = n_events
    st["n_resolved"] = n_events - n_unresolved
    st["n_unresolved"] = n_unresolved
    st["n_malformed"] = n_malformed
    st["resolution"] = (n_events - n_unresolved) / n_events if n_events else 0.0
    st["distinct_hashes_used"] = len(used)
    st["unresolved_distinct"] = len(unresolved_hashes)
    st["defined_never_used"] = len(set(templates) - set(used))
    st["co_generated"] = (st["defined_never_used"] == 0
                          and st["unresolved_distinct"] == 0
                          and st["distinct_hashes_used"] == st["n_templates"])

    # ---- 2. symbol content, body and envelope apart ------------------------
    def profile(texts):
        lit = [len(literal_tokens(x)) for x in texts]
        alnum = [len(alnum_literals(x)) for x in texts]
        var = [x.count(VAR_MARKER) for x in texts]
        return {
            "lit_mean": statistics.mean(lit), "lit_median": statistics.median(lit),
            "lit_min": min(lit), "lit_max": max(lit),
            "alnum_mean": statistics.mean(alnum), "alnum_median": statistics.median(alnum),
            "alnum_min": min(alnum),
            "var_mean": statistics.mean(var), "var_median": statistics.median(var),
            "var_min": min(var), "var_max": max(var),
            "zero_literal": sum(1 for x in lit if x == 0),
            "zero_alnum": sum(1 for x in alnum if x == 0),
            "zero_alnum_share": sum(1 for x in alnum if x == 0) / len(alnum),
        }

    st["body"] = profile(list(bodies.values()))
    st["envelope"] = profile(list(envelopes.values()))
    st["whole_record"] = profile(list(templates.values()))

    # Environment residue in the envelope: how many names are pinned to values
    # of this deployment rather than to source text.
    residue = sum(1 for e in envelopes.values() if RESIDUE_RE.search(e))
    st["envelope_residue_templates"] = residue
    st["envelope_residue_share"] = residue / len(templates)

    # ---- 3. naming granularity across frequency ---------------------------
    rows = []
    for name, pred in BUCKETS:
        hs = [h for h, c in used.items() if pred(c)]
        ev = sum(used[h] for h in hs)
        alnum = [len(alnum_literals(bodies[h])) for h in hs] or [0]
        var = [bodies[h].count(VAR_MARKER) for h in hs] or [0]
        zero = sum(1 for a in alnum if a == 0)
        rows.append({
            "bucket": name,
            "templates": len(hs),
            "events": ev,
            "event_share": (ev / n_events) if n_events else 0.0,
            "body_alnum_median": statistics.median(alnum),
            "body_alnum_min": min(alnum),
            "body_var_median": statistics.median(var),
            "zero_alnum": zero,
            "zero_alnum_share": (zero / len(hs)) if hs else 0.0,
        })
    st["buckets"] = rows
    st["templates_used_once"] = rows[0]["templates"]
    st["templates_used_once_share"] = rows[0]["templates"] / len(templates)

    # Re-key on the message body alone, dropping the envelope, so the naming
    # granularity figure does not ride on deployment values.
    body_use = collections.Counter()
    for h, c in used.items():
        body_use[bodies[h]] += c
    st["distinct_bodies"] = len(body_use)
    st["singleton_bodies"] = sum(1 for v in body_use.values() if v == 1)
    st["singleton_body_share"] = st["singleton_bodies"] / len(body_use) if body_use else 0.0

    once = next(r for r in rows if r["bucket"] == "used once")
    often = next(r for r in rows if r["bucket"] == "over 1,000")
    st["degrade_ratio_observed"] = (
        once["body_alnum_median"] / often["body_alnum_median"]
        if often["body_alnum_median"] else float("nan"))
    st["f_degrade_fired"] = st["degrade_ratio_observed"] < DEGRADE_RATIO
    st["f_anchor_worst_bucket"] = max(rows, key=lambda r: r["zero_alnum_share"])
    st["f_anchor_fired"] = st["f_anchor_worst_bucket"]["zero_alnum_share"] > ANCHOR_FLOOR

    # ---- 4. line reconciliation -------------------------------------------
    # A template that seals a multi-line event holds N newline-separated line
    # templates, so an event built from it accounts for N raw lines. Grouping,
    # not loss.
    span = {h: t.count("\n") + 1 for h, t in templates.items()}
    st["multiline_templates"] = sum(1 for v in span.values() if v > 1)
    st["max_span"] = max(span.values())
    raw_from_templates = 0
    multiline_events = 0
    for h, c in used.items():
        s = span.get(h, 1)
        raw_from_templates += s * c
        if s > 1:
            multiline_events += c
    st["raw_lines_implied"] = raw_from_templates
    st["continuation_lines"] = raw_from_templates - n_events
    st["multiline_events"] = multiline_events

    st["raw_lines_counted"] = None
    st["reconciles"] = None
    if args.verify_raw:
        raw_path = data.ensure("otel-sample-200mb.log")
        st["raw_lines_counted"] = count_lines_gz(raw_path)
        st["reconciles"] = st["raw_lines_counted"] == raw_from_templates

    return st


# --------------------------------------------------------------------------
# reporting. Both renderers read the same dict, so the markdown cannot drift
# from what was measured.
# --------------------------------------------------------------------------

def render(st, md=False):
    L = []
    h1 = (lambda s: L.append(f"# {s}\n")) if md else (
        lambda s: L.append("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78))
    h2 = (lambda s: L.append(f"\n## {s}\n")) if md else (
        lambda s: L.append(f"\n{s}\n" + "-" * 78))
    p = lambda s="": L.append(s)
    pct = lambda x: f"{x:.4f}"

    h1("Engine side: naming granularity and literal anchoring")
    p()
    p("Computed from two published release assets, `otel-sample-templates.json` and")
    p("`otel-sample-encoded.log`, at tag `otel-sample-v1`. The engine is never run.")
    p("Reproduce with `python bench/engine_side.py`.")
    p()

    h2("0. What the two assets are, measured")
    p()
    if md:
        p("| quantity | value |")
        p("|---|---|")
        p(f"| templates defined | {st['n_templates']:,} |")
        p(f"| distinct templates referenced by the encoded file | {st['distinct_hashes_used']:,} |")
        p(f"| defined and never referenced | {st['defined_never_used']:,} |")
        p(f"| referenced with no definition | {st['unresolved_distinct']:,} |")
        p(f"| duplicate template hashes | {st['duplicate_hashes']:,} |")
        p(f"| hashes containing a comma | {st['hashes_with_comma']:,} (the parser depends on 0) |")
    else:
        p(f"templates defined                                  {st['n_templates']:>10,}")
        p(f"distinct templates referenced by the encoded file  {st['distinct_hashes_used']:>10,}")
        p(f"defined and never referenced                       {st['defined_never_used']:>10,}")
        p(f"referenced with no definition                      {st['unresolved_distinct']:>10,}")
        p(f"duplicate template hashes                          {st['duplicate_hashes']:>10,}")
        p(f"hashes containing a comma                          {st['hashes_with_comma']:>10,}")
    p()
    if st["co_generated"]:
        p("The three counts are equal and both residuals are zero, so the templates file is")
        p("the dictionary the encoding run wrote for its own output rather than a library")
        p("that existed beforehand. Two consequences, both binding on everything below:")
        p()
        p("  1. Section 1's resolution rate is a consistency check between two artifacts of")
        p("     one run. It cannot come out below 1.0 unless the published assets are")
        p("     mismatched, so it is reported as a gate and not as a falsifier.")
        p("  2. How the symbol library behind these templates was produced, and whether it")
        p("     was compiled with sight of this stream, is not disclosed in the release and")
        p("     is not established anywhere in this repository. Reading section 1 as")
        p("     evidence that the library covers unseen statements is unsupported. The")
        p("     experiment that would support it is a run against a library compiled")
        p("     without the statements being encoded, it needs the engine, and it is listed")
        p("     as future work.")
    else:
        p("The counts do not match, so the two assets are not a matched pair and every")
        p("figure below should be treated as suspect.")

    h2("1. Resolution (consistency gate C1)")
    p()
    p("Every encoded record leads with `~<templateHash>`. Resolution is a lookup of")
    p("that hash against the templates file.")
    p()
    if md:
        p("| quantity | value |")
        p("|---|---|")
        p(f"| events | {st['n_events']:,} |")
        p(f"| resolved to a template | {st['n_resolved']:,} |")
        p(f"| unresolved | {st['n_unresolved']:,} |")
        p(f"| malformed records | {st['n_malformed']:,} |")
        p(f"| resolution | {pct(st['resolution'])} |")
    else:
        p(f"events                              {st['n_events']:>12,}")
        p(f"resolved to a template              {st['n_resolved']:>12,}")
        p(f"unresolved                          {st['n_unresolved']:>12,}")
        p(f"malformed records                   {st['n_malformed']:>12,}")
        p(f"resolution                          {pct(st['resolution']):>12}")
    p()
    p(f"C1: {'PASS' if st['n_unresolved'] == 0 else 'FAIL'}"
      f" ({st['n_unresolved']:,} records failed to resolve). Per section 0 this is an")
    p("internal-consistency check on the published artifacts, not a measurement of what")
    p("the symbol library covers.")

    h2("2. Symbol content: message body against envelope")
    p()
    p("Each template covers a whole Fluentd/Kubernetes record. The `log` field holds the")
    p("application message; the rest is an envelope of container, image, pod and label")
    p("values. Measuring them together pads the literal count with deployment values,")
    p("so they are measured apart. A variable slot is an occurrence of `$`. A literal")
    p("token is a piece that survives splitting on `$` and on whitespace and the JSON")
    p('structural characters `, : " { } [ ] /`. Counts move with that rule, so the rule')
    p("is stated rather than assumed.")
    p()
    if md:
        p("| portion | literal tokens (median) | alphanumeric literals (median) |"
          " variable slots (median) | templates with no alphanumeric literal |")
        p("|---|---:|---:|---:|---:|")
        for label, key in (("message body", "body"), ("envelope", "envelope"),
                           ("whole record", "whole_record")):
            b = st[key]
            p(f"| {label} | {b['lit_median']:g} | {b['alnum_median']:g} |"
              f" {b['var_median']:g} | {b['zero_alnum']:,} |")
    else:
        p(f"{'portion':<14}{'lit med':>9}{'alnum med':>11}{'var med':>9}{'no alnum literal':>19}")
        for label, key in (("message body", "body"), ("envelope", "envelope"),
                           ("whole record", "whole_record")):
            b = st[key]
            p(f"{label:<14}{b['lit_median']:>9g}{b['alnum_median']:>11g}"
              f"{b['var_median']:>9g}{b['zero_alnum']:>19,}")
    p()
    p(f"{st['envelope_residue_templates']:,} of {st['n_templates']:,} templates"
      f" ({st['envelope_residue_share']:.1%}) carry a digit welded to a variable slot inside")
    p("the envelope: image-tag, registry-host and pod-name fragments left behind after the")
    p("variable parts were replaced. Those literals are values of this deployment, not text")
    p("from the emitting statement, and a redeploy that changes an image tag or a pod hash")
    p("changes the template, so it changes the content hash, so it changes the name. That")
    p("is the same identity property this benchmark scores Drain on, and on this artifact")
    p("set part of the engine's template identity has it.")
    p()
    p(f"On the message body alone, {st['body']['zero_alnum']:,} of {st['n_templates']:,}"
      f" templates ({st['body']['zero_alnum_share']:.2%}) carry no alphanumeric literal at all.")
    p("Most are fragments of pretty-printed configuration output, where a line of the")
    p("record is a brace or a quoted key. An earlier form of this page claimed that no")
    p("template lacks literal content. That was true only with the envelope counted, and")
    p("it is withdrawn here.")
    p()
    w = st["f_anchor_worst_bucket"]
    p(f"F-anchor: {'FIRED' if st['f_anchor_fired'] else 'holds'}."
      f" Worst bucket is \"{w['bucket']}\" at {w['zero_alnum_share']:.4f}"
      f" against a floor of {ANCHOR_FLOOR:.2f}.")

    h2("3. Naming granularity across frequency")
    p()
    p("Templates bucketed by how many events use them. The columns describe how much of")
    p("the emitting statement each name pins down, measured on the message body alone.")
    p("There is no resolution column here: per section 0 it is 1.0 in every bucket by")
    p("construction of the assets and it would say nothing.")
    p()
    if md:
        p("| events per template | templates | events | share of stream |"
          " alphanumeric body literals (median) | body variable slots (median) |"
          " no alphanumeric body literal |")
        p("|---|---:|---:|---:|---:|---:|---:|")
        for r in st["buckets"]:
            p(f"| {r['bucket']} | {r['templates']:,} | {r['events']:,} |"
              f" {r['event_share']:.4f} | {r['body_alnum_median']:g} |"
              f" {r['body_var_median']:g} | {r['zero_alnum']:,} |")
    else:
        p(f"{'events per template':<16}{'templates':>10}{'events':>10}{'share':>8}"
          f"{'alnum med':>11}{'var med':>9}{'no alnum':>10}")
        for r in st["buckets"]:
            p(f"{r['bucket']:<16}{r['templates']:>10,}{r['events']:>10,}"
              f"{r['event_share']:>8.4f}{r['body_alnum_median']:>11g}"
              f"{r['body_var_median']:>9g}{r['zero_alnum']:>10,}")
    p()
    p(f"{st['templates_used_once']:,} of {st['n_templates']:,} templates"
      f" ({st['templates_used_once_share']:.1%}) are used exactly once, and they account for"
      f" {st["buckets"][0]["event_share"]:.2%} of the stream. Re-keyed on the message body")
    p(f"alone, dropping the envelope entirely, {st['singleton_bodies']:,} of"
      f" {st['distinct_bodies']:,} distinct bodies ({st['singleton_body_share']:.1%}) still")
    p("occur exactly once, so the granularity is a property of the message rather than of")
    p("deployment values.")
    p()
    p(f"F-degrade: {'FIRED' if st['f_degrade_fired'] else 'holds'}."
      f" Median alphanumeric body literals is"
      f" {st['buckets'][0]['body_alnum_median']:g} for templates used once against"
      f" {st['buckets'][-1]['body_alnum_median']:g} for templates used over a thousand times,"
      f" a ratio of {st['degrade_ratio_observed']:.2f} against a floor of {DEGRADE_RATIO:.2f}.")
    p("A name for a rare shape pins down about as much source text as a name for a")
    p("common one on this sample. What that does NOT show is where the name came from:")
    p("these artifacts cannot distinguish a name drawn from a compiled statement from a")
    p("name the encoder assigned by some other route.")

    h2("4. Line reconciliation (consistency gate C2)")
    p()
    p("Raw lines outnumber events because multi-line records are grouped. A template")
    p("that seals a multi-line event holds several newline-separated line templates,")
    p("and an event built from it accounts for that many raw lines. A stack trace")
    p("becomes one composite event with one template and one pattern. Unlike C1 this")
    p("gate reaches outside the pair: it depends on every template's line span summing")
    p("to the line count of the third published asset, which the first two do not")
    p("contain.")
    p()
    if md:
        p("| quantity | value |")
        p("|---|---|")
        p(f"| templates spanning several lines | {st['multiline_templates']:,} |")
        p(f"| widest template span, in lines | {st['max_span']:,} |")
        p(f"| events built from a multi-line template | {st['multiline_events']:,} |")
        p(f"| events | {st['n_events']:,} |")
        p(f"| raw lines implied by template spans | {st['raw_lines_implied']:,} |")
        p(f"| continuation lines absorbed into group heads | {st['continuation_lines']:,} |")
        if st["raw_lines_counted"] is not None:
            p(f"| raw lines counted in the published asset | {st['raw_lines_counted']:,} |")
            p(f"| **C2** | **{'PASS' if st['reconciles'] else 'FAIL'}** |")
    else:
        p(f"templates spanning several lines             {st['multiline_templates']:>12,}")
        p(f"widest template span, in lines               {st['max_span']:>12,}")
        p(f"events built from a multi-line template      {st['multiline_events']:>12,}")
        p(f"events                                       {st['n_events']:>12,}")
        p(f"raw lines implied by template spans          {st['raw_lines_implied']:>12,}")
        p(f"continuation lines absorbed into group heads {st['continuation_lines']:>12,}")
        if st["raw_lines_counted"] is not None:
            p(f"raw lines counted in the published asset     {st['raw_lines_counted']:>12,}")
            p(f"C2                                           "
              f"{'PASS' if st['reconciles'] else 'FAIL':>12}")
    p()
    p(f"{st['n_events']:,} events plus {st['continuation_lines']:,} continuation lines"
      f" equals {st['raw_lines_implied']:,} raw lines.")

    h2("What this establishes")
    p()
    p("1. Naming granularity. The engine gives this stream"
       f" {st['n_templates']:,} names for {st['n_events']:,} events, and"
       f" {st['templates_used_once']:,} of those names are used exactly once. Re-keyed on")
    p("   the message body alone the singleton share is"
       f" {st['singleton_body_share']:.1%}. Name assignment does not wait for repetition.")
    p("2. Literal anchoring, scoped. On the message body,"
       f" {st['n_templates'] - st['body']['zero_alnum']:,} of {st['n_templates']:,} templates")
    p("   carry alphanumeric literal text, at a median of"
       f" {st['body']['alnum_median']:g} tokens, and that median does not fall with rarity.")
    p("3. Grouping. A multi-line record is sealed into one event with one name, and the")
    p("   arithmetic closes against the raw asset exactly.")

    h2("What this does NOT establish")
    p()
    p("1. Library coverage. Section 1 is a consistency check between two co-generated")
    p("   artifacts. It says nothing about a statement the library has not seen, which is")
    p("   the adversarial case. The held-out experiment needs the engine and is future")
    p("   work.")
    p("2. Provenance of the library. Whether the symbol library behind these templates was")
    p("   compiled with sight of this stream is not disclosed in the release assets and is")
    p("   not established here.")
    p("3. Where the name comes from. The anchoring statistics show that names carry source")
    p("   text. They cannot show that the text was drawn from a compiled statement rather")
    p("   than derived some other way, because both would look like this from outside.")
    p("4. Cross-instance agreement. Two engine deployments handed disjoint halves of one")
    p("   stream were never run here. That is the direct counterpart of the Drain split in")
    p("   `results/identity.md` and it is future work.")
    p("5. Order invariance. A content hash of a template drawn from a pinned symbol")
    p("   library is order-invariant by construction. Measuring it would restate the")
    p("   construction, so this repository omits the exercise on purpose.")
    p("6. Stability of a name across engine versions, library revisions, or redeployment.")
    p("   Section 2 shows the last of those three is a live risk on this artifact set:"
      f" {st['envelope_residue_share']:.1%} of templates carry deployment values in their")
    p("   envelope literals, so a new image tag or pod hash moves the name.")
    p()
    p("How to read this beside the Drain table. `results/identity.md` asks whether two")
    p("independently mined names for one line are the same string, which is agreement.")
    p("This page asks a weaker and prior question, whether a name exists at all and how")
    p("much source text it pins down, which is coverage and granularity. The buckets share")
    p("boundaries but partition different event sets: the engine's are whole records,")
    p("including multi-line groups, while Drain's are per-line message shapes. Read them")
    p("as two questions, not as two columns of one axis.")
    p()
    p("Prior art, stated so the claim stays narrow: template plus values storage is")
    p("long established (CLP/YScope, US10484506B2), and template extraction from log")
    p("text is long established (Drain, Spell, IPLoM). The claim on this page is about")
    p("naming granularity and literal anchoring on one sample, not about either of those.")
    p()

    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(
        description="Engine-side naming granularity and literal anchoring, "
                    "from published artifacts.")
    ap.add_argument("--data-dir", default=None,
                    help="directory holding the release assets (default: <repo>/data)")
    ap.add_argument("--no-verify-raw", dest="verify_raw", action="store_false",
                    help="skip streaming the 215 MB raw asset to check section 4")
    ap.add_argument("--out", default=str(REPO_ROOT / "results" / "engine_side.md"),
                    help="markdown destination")
    ap.set_defaults(verify_raw=True)
    args = ap.parse_args()

    if args.data_dir:
        data.DATA_DIR = pathlib.Path(args.data_dir)

    st = measure(args)

    print(render(st, md=False))

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(st, md=True))
    print(f"wrote {out}", file=sys.stderr)

    # Non-zero exit if a registered threshold was breached or a gate failed, so
    # this is usable as a CI gate.
    failed = (
        st["n_unresolved"] > 0
        or st["body_extract_failures"] > 0
        or st["f_anchor_fired"]
        or st["f_degrade_fired"]
        or (st["reconciles"] is False)
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
