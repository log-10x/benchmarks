#!/usr/bin/env python3
"""coverage.py - what the engine does with vocabulary its library has never held.

The objection this file answers: "the engine's templates keep literal text
because the templates file was produced by the same run that encoded the file,
so of course every line resolves". That check is circular, and
`bench/engine_side.py` already demotes it to a consistency gate. The two
experiments here are not circular, because neither can be satisfied by
construction:

1. INVENTED VOCABULARY. Lines whose content words were made up for this test
   ("zorblatt frobnicator quuxify ... wibblewobble") are fed to the engine
   beside lines built from ordinary vocabulary. The invented words cannot sit
   in any symbol library, because they did not exist until this file was
   written. What comes back decides three claims:
     - the known-vocabulary line gets a readable template and a readable
       pattern name;
     - the invented line gets a template with no literal content and an EMPTY
       pattern name, so a coverage failure is visible in the artifact itself,
       never disguised as a confident wrong name;
     - the template hash on the invented line is IDENTICAL across its
       occurrences and across two independent engine runs, so the identifier
       stays deterministic even where coverage failed.

2. UNFAMILIAR STREAMS. Two public LogHub log sets the symbol library was never
   built for: Proxifier, a Windows consumer application, and the Apache error
   log. Both download from Zenodo record 3227177 into data/ (gitignored). The
   engine encodes each and this script measures the templates it minted: how
   many, how much literal text each keeps, and how many are pure variables. The
   counts are then compared with the counts the same engine version produced on
   the same files in the compaction ledger recorded six weeks before this
   script existed, so drift over time has a place to show up.

The engine runs as a pinned Docker image. If Docker or the image is absent the
script SKIPS with a clear message and touches nothing under results/, so a
rerun on a machine without Docker cannot destroy the committed artifact.

CAUTION, stated here and in the report: `@apps/mcp-file` writes `encoded.log`
as the ANALYSIS artifact. Each record carries `pattern=` and `patternHash=`
fields that exist for analysis, not for storage. Never compute a storage
reduction figure from that file.

Usage:
    python bench/coverage.py            # writes results/coverage.md and .json
    python bench/coverage.py --skip-loghub   # invented-vocabulary probe only
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import urllib.request

IMAGE = "log10x/pipeline-10x:1.1.5"

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
DATA_DIR = pathlib.Path(os.environ.get("PIB_DATA_DIR", str(REPO_ROOT / "data")))
ENGINE_OUT = DATA_DIR / "engine"

ZENODO_BASE = "https://zenodo.org/records/3227177/files"

# The counts the same engine version produced on the same two files in the
# compaction ledger, recorded six weeks before this script existed. A mismatch
# here is a falsifier firing, not a footnote.
LEDGER = {
    "Proxifier": {"events": 4257, "templates": 574},
    "Apache": {"events": 52004, "templates": 370},
}

# Two vocabularies, one probe file. Timestamps are fixed so the artifact is
# byte-identical across reruns. The invented words did not exist until this
# file was written, which is the entire point: no library anywhere can hold
# them.
KNOWN_LINES = [
    "2026-07-26 10:00:00 INFO Connection established to database",
    "2026-07-26 10:00:01 INFO Connection established to database",
]
INVENTED_LINES = [
    "2026-07-26 10:00:02 zorblatt frobnicator quuxify 7731 wibblewobble",
    "2026-07-26 10:00:03 zorblatt frobnicator quuxify 9142 wibblewobble",
    "2026-07-26 10:00:04 zorblatt frobnicator quuxify 5510 wibblewobble",
]
KNOWN_TEMPLATE_TEXT = "Connection established to database"


def fail(msg: str):
    print(f"FALSIFIER FIRED / CHECK FAILED: {msg}", file=sys.stderr)
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Docker plumbing
# ---------------------------------------------------------------------------

def engine_digest():
    """Return the image digest, or None with a reason when the engine is absent."""
    docker = shutil.which("docker")
    if docker is None:
        return None, "docker is not on PATH"
    try:
        r = subprocess.run([docker, "image", "inspect", IMAGE,
                            "--format", "{{index .RepoDigests 0}}|{{.Id}}"],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return None, f"docker not usable: {e}"
    if r.returncode != 0:
        return None, (f"image {IMAGE} is not present locally; "
                      f"`docker pull {IMAGE}` and rerun")
    repo_digest, image_id = (r.stdout.strip().split("|") + [""])[:2]
    return (repo_digest or image_id), None


def run_engine(input_path: pathlib.Path, name: str) -> pathlib.Path:
    """Encode one file. Artifacts land in data/engine/<name>/ and the directory
    is wiped first, so every run is read from a clean slate."""
    ENGINE_OUT.mkdir(parents=True, exist_ok=True)
    outdir = ENGINE_OUT / name
    if outdir.exists():
        shutil.rmtree(outdir)
    cmd = ["docker", "run", "--rm", "-i",
           "-e", f"LOG10X_MCP_RUNTIME_NAME={name}",
           "-e", f"TENX_RUNTIME_NAME={name}",
           "-v", f"{ENGINE_OUT}:/tmp/log10x-mcp-pull",
           IMAGE, "@apps/mcp-file"]
    with open(input_path, "rb") as f:
        r = subprocess.run(cmd, stdin=f, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        fail(f"engine run {name!r} exited {r.returncode}: {r.stderr[-2000:]}")
    for artifact in ("encoded.log", "templates.json"):
        if not (outdir / artifact).exists():
            fail(f"engine run {name!r} produced no {artifact} under {outdir}")
    return outdir


# ---------------------------------------------------------------------------
# Artifact parsing
# ---------------------------------------------------------------------------

def parse_encoded(path: pathlib.Path):
    """Yield (templateHash, pattern, patternHash) per encoded record.

    Record shape: `~<templateHash>,<epoch-ms>,<values...>,pattern=,<pattern>,
    patternHash=,<hash>`. The `pattern=` and `patternHash=` markers are fields
    of their own, each followed by its value field. `bench/engine_side.py`
    verifies that no template hash contains a comma.
    """
    out = []
    with open(path, errors="replace") as f:
        for line in f:
            toks = line.rstrip("\n").split(",")
            if not toks or not toks[0].startswith("~"):
                continue
            tpl_hash = toks[0][1:]
            pattern = pattern_hash = None
            for i, t in enumerate(toks):
                if t == "pattern=" and i + 1 < len(toks):
                    pattern = toks[i + 1]
                elif t == "patternHash=" and i + 1 < len(toks):
                    pattern_hash = toks[i + 1]
            out.append((tpl_hash, pattern, pattern_hash))
    return out


def load_templates(path: pathlib.Path) -> dict:
    """templateHash -> template string, from the JSONL templates artifact."""
    out = {}
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[rec["templateHash"]] = rec["template"]
    return out


def strip_variables(template: str) -> str:
    """Remove the variable markers: `$(...)` typed slots, then `$N` and `$`."""
    s = re.sub(r"\$\([^)]*\)", " ", template)
    s = re.sub(r"\$\d*", " ", s)
    return s


def literal_words(template: str) -> int:
    """Literal words: runs of two or more letters left after the variable
    markers are removed. The measure is deliberately blunt; its only job is to
    separate templates that pin down source text from templates that are all
    variables."""
    return len([w for w in re.findall(r"[A-Za-z]+", strip_variables(template))
                if len(w) >= 2])


def literal_alnum_chars(template: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]", strip_variables(template)))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_loghub(name: str) -> pathlib.Path:
    """Download <name>.tar.gz from Zenodo once, cache under data/, extract the
    .log member beside it. Returns the path of the extracted log file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DATA_DIR / f"{name}.log"
    tar_path = DATA_DIR / f"{name}.tar.gz"
    if log_path.exists() and log_path.stat().st_size > 0:
        return log_path
    if not (tar_path.exists() and tar_path.stat().st_size > 0):
        url = f"{ZENODO_BASE}/{name}.tar.gz?download=1"
        print(f"downloading {url}", file=sys.stderr, flush=True)
        tmp = tar_path.with_suffix(".part")
        req = urllib.request.Request(url, headers={"User-Agent": "pattern-identity-benchmark"})
        with urllib.request.urlopen(req) as resp, open(tmp, "wb") as out:
            shutil.copyfileobj(resp, out, 1 << 20)
        tmp.replace(tar_path)
        print(f"  cached {tar_path} ({tar_path.stat().st_size:,} bytes)",
              file=sys.stderr, flush=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        member = next((m for m in tf.getmembers()
                       if m.name.endswith(f"{name}.log")), None)
        if member is None:
            fail(f"{tar_path} holds no {name}.log member")
        with tf.extractfile(member) as src, open(log_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return log_path


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

def invented_vocabulary_probe() -> dict:
    """Feed known and invented vocabulary through the engine, twice."""
    probe_path = ENGINE_OUT / "probe-input.log"
    ENGINE_OUT.mkdir(parents=True, exist_ok=True)
    probe_path.write_text("\n".join(KNOWN_LINES + INVENTED_LINES) + "\n")

    runs = {}
    for run_name in ("probe", "probe-rerun"):
        outdir = run_engine(probe_path, run_name)
        templates = load_templates(outdir / "templates.json")
        records = parse_encoded(outdir / "encoded.log")
        if len(records) != len(KNOWN_LINES) + len(INVENTED_LINES):
            fail(f"{run_name}: expected {len(KNOWN_LINES) + len(INVENTED_LINES)} "
                 f"encoded records, found {len(records)}")
        known = records[:len(KNOWN_LINES)]
        invented = records[len(KNOWN_LINES):]

        # The known-vocabulary line: readable template, readable pattern.
        for tpl_hash, pattern, _ in known:
            if not pattern:
                fail(f"{run_name}: known-vocabulary line came back with an "
                     f"empty pattern")
            if KNOWN_TEMPLATE_TEXT not in templates[tpl_hash]:
                fail(f"{run_name}: known-vocabulary template lost its literal "
                     f"text: {templates[tpl_hash]!r}")

        # The invented line: empty pattern, zero literal content, one hash.
        inv_hashes = {tpl_hash for tpl_hash, _, _ in invented}
        if len(inv_hashes) != 1:
            fail(f"{run_name}: the invented-vocabulary occurrences carry "
                 f"{len(inv_hashes)} different template hashes: {sorted(inv_hashes)}")
        for tpl_hash, pattern, _ in invented:
            if pattern:
                fail(f"{run_name}: invented-vocabulary line came back with a "
                     f"non-empty pattern {pattern!r}, a confident wrong name")
        inv_hash = next(iter(inv_hashes))
        inv_template = templates[inv_hash]
        if literal_alnum_chars(inv_template) != 0:
            fail(f"{run_name}: invented-vocabulary template kept literal "
                 f"content: {inv_template!r}")

        runs[run_name] = {
            "known_template": templates[known[0][0]],
            "known_template_hash": known[0][0],
            "known_pattern": known[0][1],
            "invented_template": inv_template,
            "invented_template_hash": inv_hash,
            "invented_pattern_hash": invented[0][2],
            "records": len(records),
        }

    a, b = runs["probe"], runs["probe-rerun"]
    if a["invented_template_hash"] != b["invented_template_hash"]:
        fail("the invented-vocabulary template hash differs between two "
             f"independent engine runs: {a['invented_template_hash']!r} against "
             f"{b['invented_template_hash']!r}; the determinism claim retires")
    if a["known_template_hash"] != b["known_template_hash"]:
        fail("the known-vocabulary template hash differs between two "
             "independent engine runs; the determinism claim retires")
    return a


def loghub_analysis(name: str) -> dict:
    log_path = fetch_loghub(name)
    tar_path = DATA_DIR / f"{name}.tar.gz"
    raw_lines = sum(1 for _ in open(log_path, "rb"))
    outdir = run_engine(log_path, name)
    templates = load_templates(outdir / "templates.json")
    events = sum(1 for line in open(outdir / "encoded.log", errors="replace")
                 if line.startswith("~"))

    words = [literal_words(t) for t in templates.values()]
    pure_variable = sum(1 for t in templates.values() if literal_alnum_chars(t) == 0)

    exp = LEDGER[name]
    if events != exp["events"] or len(templates) != exp["templates"]:
        fail(f"{name}: this run minted {events:,} events and {len(templates):,} "
             f"templates against {exp['events']:,} and {exp['templates']:,} in the "
             f"compaction ledger six weeks earlier; cross-time determinism retires")

    return {
        "dataset": name,
        "source": f"{ZENODO_BASE}/{name}.tar.gz",
        "tarball_sha256": sha256(tar_path) if tar_path.exists() else None,
        "raw_lines": raw_lines,
        "events": events,
        "templates": len(templates),
        "median_literal_words": statistics.median(words),
        "pure_variable_templates": pure_variable,
        "ledger_events": exp["events"],
        "ledger_templates": exp["templates"],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(payload, md_path: pathlib.Path, json_path: pathlib.Path):
    L = []
    A = L.append
    A("# Coverage: what the engine does with vocabulary its library never held")
    A("")
    A("Generated by `bench/coverage.py`. Every number on this page was produced by "
      "that script against the pinned engine image below. The raw values are in "
      "`results/coverage_raw.json`.")
    A("")
    A(f"- engine image: `{payload['image']}`")
    A(f"- image digest: `{payload['image_digest']}`")
    A("")
    A("**Concession first.** Drain3 also names unfamiliar streams immediately, with no "
      "engine, no Docker image and no library, and that remains the right default when "
      "the emitting code is out of reach. What this page measures is narrower: how each "
      "side fails when the vocabulary is new. Drain fails by minting a first-sight "
      "literal that `bench/replay.py` shows moving when siblings arrive. The engine "
      "fails by handing back a template with no literal content and an empty pattern "
      "name, and the question here is whether that failure is visible, deterministic, "
      "and free of wrong names.")
    A("")
    A("**Why this is not circular.** The consistency checks in `bench/engine_side.py` "
      "compare two artifacts of one run and cannot fail; they are gates, not evidence. "
      "The two experiments below cannot be satisfied by construction: the probe words "
      "were invented for this test, so no library anywhere can hold them, and the two "
      "LogHub files are public logs the symbol library was never built for.")
    A("")
    A("## 1. Invented vocabulary")
    A("")
    A("Five lines, fixed timestamps. Two use ordinary vocabulary, three use words that "
      "did not exist until this benchmark was written, with a different number in each:")
    A("")
    A("```")
    for line in KNOWN_LINES + INVENTED_LINES:
        A(line)
    A("```")
    A("")
    p = payload["probe"]
    A("| line | template | pattern |")
    A("|---|---|---|")
    A(f"| known vocabulary | `{p['known_template']}` | `{p['known_pattern']}` |")
    A(f"| invented vocabulary | `{p['invented_template']}` | (empty) |")
    A("")
    A("Checked by the script, and each check is a falsifier that can fire:")
    A("")
    A("- The known-vocabulary line keeps its words: the template reads "
      f"\"{KNOWN_TEMPLATE_TEXT}\" and the pattern name `{p['known_pattern']}` is "
      "readable.")
    A("- The invented-vocabulary line comes back with an EMPTY pattern and a template "
      "with zero literal content. Unknown tokens become variables. The coverage "
      "failure is visible in the artifact itself; at no point does the engine hand "
      "back a confident wrong name.")
    A(f"- All {len(INVENTED_LINES)} occurrences carry the identical template hash "
      f"`{p['invented_template_hash']}`, and a second, independent engine run "
      "reproduces it byte for byte. The identifier stays deterministic where coverage "
      "failed, so the moment the library gains a symbol for the statement, everything "
      "already keyed on the hash re-resolves.")
    A("")
    A("## 2. Unfamiliar streams: LogHub Proxifier and Apache")
    A("")
    A("Two public log sets from Zenodo record 3227177, chosen because the symbol "
      "library was never built for them: Proxifier is Windows consumer software, and "
      "the Apache error log predates the engine. Downloaded into `data/` on first "
      "use, never vendored.")
    A("")
    A("| log set | raw lines | events | templates | median literal words per template | pure-variable templates |")
    A("|---|---:|---:|---:|---:|---:|")
    for r in payload["loghub"]:
        A(f"| {r['dataset']} | {r['raw_lines']:,} | {r['events']:,} | "
          f"{r['templates']:,} | {r['median_literal_words']:g} | "
          f"{r['pure_variable_templates']} |")
    A("")
    A("Events sit below raw lines because the engine groups continuation lines into "
      "their parent record. Raw lines count every record, including a final one with "
      "no trailing newline; Apache.log ends without one, so its figure sits one above "
      "`wc -l`, which counts newlines. "
      "A literal word is a run of two or more letters left after "
      "the variable markers are removed; the measure is blunt on purpose, because its "
      "only job is to separate templates that pin down source text from templates that "
      "are all variables.")
    A("")
    A("Cross-time determinism: the compaction ledger recorded the same engine version "
      "on the same two files six weeks before this script existed, at "
      + ", ".join(f"{r['ledger_events']:,} events and {r['ledger_templates']:,} "
                  f"templates for {r['dataset']}" for r in payload["loghub"])
      + ". This run reproduces both counts exactly, and the script fails loudly on "
        "any mismatch.")
    A("")
    for r in payload["loghub"]:
        A(f"- `{r['dataset']}.tar.gz` sha256 `{r['tarball_sha256']}`")
    A("")
    A("## Caution: the encoded artifact is for analysis")
    A("")
    A("`@apps/mcp-file` writes `encoded.log` as the ANALYSIS artifact. Every record "
      "carries `pattern=` and `patternHash=` fields that exist so tooling can read the "
      "stream without the templates file at hand. Those fields are not part of the "
      "storage encoding, so a size measured on this file is a measurement of the "
      "analysis format. Never compute a storage-reduction figure from it. No storage "
      "figure appears on this page.")
    A("")
    A("## What would prove this wrong")
    A("")
    A("- An invented-vocabulary line that ever yields two different template hashes, "
      "across occurrences or across independent runs, retires the determinism claim. "
      "Checked on every run of this script.")
    A("- An invented-vocabulary line that comes back with a non-empty pattern retires "
      "the claim that coverage failures are visible rather than mislabelled. Checked "
      "on every run.")
    A("- A known-vocabulary line whose template loses its literal text retires the "
      "readable-template claim. Checked on every run.")
    A("- A LogHub run that mints a material share of pure-variable templates retires "
      "the claim that the engine generalizes with readable templates; observed "
      + " and ".join(f"{r['pure_variable_templates']} of {r['templates']:,} on "
                     f"{r['dataset']}" for r in payload["loghub"]) + ".")
    A("- A rerun whose event or template counts differ from the compaction ledger's "
      "retires cross-time determinism. Checked on every run.")
    A("")
    A("## What is not claimed")
    A("")
    A("- Coverage of arbitrary streams is not claimed. The invented-vocabulary probe "
      "shows exactly what a coverage failure looks like, because that failure is the "
      "expected behaviour outside the library.")
    A("- Immediate naming of unfamiliar streams is not an advantage over Drain3, which "
      "does the same with less machinery. The measured difference is the failure "
      "shape: empty and deterministic against literal and mobile.")
    A("- The engine artifacts here are produced by a vendor-built image, and this "
      "repository does not build the engine from source. The pinned digest above is "
      "what a reader needs to hold the run to account.")
    A("")
    md_path.write_text("\n".join(L) + "\n")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-loghub", action="store_true",
                    help="run the invented-vocabulary probe only")
    ap.add_argument("--out-md", default=str(RESULTS_DIR / "coverage.md"))
    ap.add_argument("--out-json", default=str(RESULTS_DIR / "coverage_raw.json"))
    args = ap.parse_args()

    digest, why = engine_digest()
    if digest is None:
        print(f"SKIP: {why}")
        print("bench/coverage.py needs the pinned engine image to run. Nothing under")
        print("results/ was touched; the committed artifact stands as published.")
        return 0

    print(f"engine image {IMAGE}", flush=True)
    print(f"image digest {digest}", flush=True)

    print("\ninvented-vocabulary probe (two engine runs)", flush=True)
    probe = invented_vocabulary_probe()
    print(f"  known    template  {probe['known_template']}")
    print(f"  known    pattern   {probe['known_pattern']}")
    print(f"  invented template  {probe['invented_template']}")
    print(f"  invented pattern   (empty)")
    print(f"  invented hash      {probe['invented_template_hash']} "
          f"(identical across {len(INVENTED_LINES)} occurrences and 2 runs)")

    loghub = []
    if not args.skip_loghub:
        for name in LEDGER:
            print(f"\nLogHub {name}", flush=True)
            r = loghub_analysis(name)
            loghub.append(r)
            print(f"  raw lines {r['raw_lines']:,}  events {r['events']:,}  "
                  f"templates {r['templates']:,}")
            print(f"  median literal words {r['median_literal_words']:g}  "
                  f"pure-variable templates {r['pure_variable_templates']}")
            print(f"  ledger match: {r['ledger_events']:,} events, "
                  f"{r['ledger_templates']:,} templates, reproduced exactly")

    payload = {
        "script": "bench/coverage.py",
        "image": IMAGE,
        "image_digest": digest,
        "probe": probe,
        "loghub": loghub,
        "ledger": LEDGER,
    }

    if args.skip_loghub:
        print("\n--skip-loghub: report not written, the committed artifact covers "
              "both experiments")
        return 0

    md_path = pathlib.Path(args.out_md)
    json_path = pathlib.Path(args.out_json)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(payload, md_path, json_path)
    print(f"\nwrote {md_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
